"""
PicoRV32 FPGA XMODEM-CRC Host Loader
====================================

Linker tarafından üretilen firmware.mem / .bin dosyasını,
Tang Nano 9K üzerindeki UART tabanlı loader FSM'e
128 baytlık paketler halinde CRC-16/XMODEM doğrulamasıyla gönderir.

Protokol özeti (PÇ7):
  Host                                  FPGA
  ----                                  ----
                              <----     'C'  (CRC modu başlatma daveti)
   SOH | seq | ~seq | 128B | CRCH | CRCL  ---->
                              <----     ACK (paket doğru)
                              <----     NAK (yeniden gönder)
   ... son paket ...
   EOT                                ---->
                              <----     ACK   (yükleme tamam, CPU resetn=1)

Kullanım:
  python host_loader.py firmware.mem
  python host_loader.py firmware.bin --port COM5 --baud 115200
"""

from __future__ import annotations
import argparse
import os
import sys
import time
import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext, messagebox
from threading import Thread

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None

# --- XMODEM-CRC sabitleri ---
SOH = 0x01
EOT = 0x04
ACK = 0x06
NAK = 0x15
CAN = 0x18
C_CHAR = 0x43  # 'C'
PACKET_SIZE = 128
PAD = 0x00     # son paket için doldurma baytı

# ---------------------------------------------------------------------------
# Yardımcılar
# ---------------------------------------------------------------------------
def crc16_xmodem(data: bytes) -> int:
    """CRC-16/XMODEM: poly 0x1021, init 0x0000, no reflect, no xorout."""
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def load_firmware(path: str) -> bytes:
    """firmware.mem (Verilog $readmemh) veya .bin/.hex okur, ham bayt döner."""
    with open(path, "rb") as f:
        head = f.read(8)
    is_mem = head.startswith(b"@") or all(
        c in b"0123456789abcdefABCDEF@\r\n /\t" for c in head if c
    )

    if path.endswith(".bin") or not is_mem:
        with open(path, "rb") as f:
            return f.read()

    # .mem / .hex: her satır 32-bit kelime (little-endian gönderimi için ters)
    words = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.split("//")[0].strip()
            if not line or line.startswith("@"):
                continue
            for tok in line.split():
                if len(tok) == 8:
                    w = int(tok, 16)
                    # PicoRV32 little-endian: düşük bayt önce
                    words.append(w & 0xFF)
                    words.append((w >> 8) & 0xFF)
                    words.append((w >> 16) & 0xFF)
                    words.append((w >> 24) & 0xFF)
    return bytes(words)


def build_packet(seq: int, payload: bytes) -> bytes:
    if len(payload) < PACKET_SIZE:
        payload = payload + bytes([PAD] * (PACKET_SIZE - len(payload)))
    crc = crc16_xmodem(payload)
    return bytes([SOH, seq & 0xFF, (~seq) & 0xFF]) + payload + bytes([crc >> 8, crc & 0xFF])


# ---------------------------------------------------------------------------
# Çekirdek transfer
# ---------------------------------------------------------------------------
class XmodemSender:
    def __init__(self, port: str, baud: int, log=print):
        if serial is None:
            raise RuntimeError("pyserial kurulu değil:  pip install pyserial")
        self.ser = serial.Serial(port, baud, timeout=2)
        self.log = log

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass

    def wait_for_C(self, timeout_s: float = 15.0) -> bool:
        """FPGA 'C' karakteri gönderene kadar bekler."""
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            b = self.ser.read(1)
            if b == bytes([C_CHAR]):
                self.log(f"[OK] FPGA 'C' aldı (CRC modu).")
                return True
            if b:
                self.log(f"[~] Beklenmedik bayt: 0x{b[0]:02X}")
        return False

    def send(self, data: bytes, on_progress=None) -> tuple[bool, dict]:
        stats = {"packets": 0, "retries": 0, "bytes": len(data), "t0": time.time()}
        if not self.wait_for_C():
            return False, stats

        seq = 1
        idx = 0
        total = (len(data) + PACKET_SIZE - 1) // PACKET_SIZE
        while idx < len(data):
            chunk = data[idx: idx + PACKET_SIZE]
            pkt = build_packet(seq, chunk)
            retries = 0
            while True:
                self.ser.write(pkt)
                self.ser.flush()
                resp = self.ser.read(1)
                if resp == bytes([ACK]):
                    stats["packets"] += 1
                    if on_progress:
                        on_progress(stats["packets"], total)
                    self.log(f"  paket {seq:3d}/{total}  ACK")
                    break
                elif resp == bytes([NAK]):
                    retries += 1
                    stats["retries"] += 1
                    self.log(f"  paket {seq:3d}  NAK (yeniden #{retries})")
                    if retries > 10:
                        self.log("[X] 10 NAK, iptal.")
                        return False, stats
                else:
                    self.log(f"[X] Yanıt yok / beklenmedik: {resp!r}")
                    return False, stats
            seq = (seq + 1) & 0xFF
            if seq == 0:
                seq = 1
            idx += PACKET_SIZE

        # EOT
        self.ser.write(bytes([EOT]))
        self.ser.flush()
        resp = self.ser.read(1)
        ok = (resp == bytes([ACK]))
        stats["t1"] = time.time()
        stats["elapsed"] = stats["t1"] - stats["t0"]
        if ok:
            self.log(f"[OK] EOT-ACK. CPU resetn serbest. ({stats['elapsed']:.2f} s)")
        else:
            self.log(f"[X] EOT için ACK gelmedi ({resp!r}).")
        return ok, stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def run_cli():
    p = argparse.ArgumentParser(description="PicoRV32 XMODEM-CRC loader")
    p.add_argument("file", nargs="?", help="firmware.mem / .bin yolu")
    p.add_argument("--port", default=None, help="COMx (örn. COM5)")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--list", action="store_true", help="seri portları listele")
    p.add_argument("--gui", action="store_true", help="grafik arayüzü aç")
    args = p.parse_args()

    if args.gui or not args.file:
        run_gui()
        return

    if args.list or not args.port:
        print("Mevcut portlar:")
        for x in list_ports.comports():
            print(f"  {x.device}  -  {x.description}")
        if not args.port:
            return

    data = load_firmware(args.file)
    print(f"[i] {len(data)} bayt yüklenecek -> {args.port} @ {args.baud}")
    s = XmodemSender(args.port, args.baud)
    try:
        ok, st = s.send(data)
    finally:
        s.close()
    print(f"[i] paket={st['packets']} retry={st['retries']} süre={st.get('elapsed',0):.2f}s")
    sys.exit(0 if ok else 1)


# ---------------------------------------------------------------------------
# Tk GUI (sunumda canlı göstermek için)
# ---------------------------------------------------------------------------
class LoaderGUI:
    def __init__(self, root):
        self.root = root
        root.title("PicoRV32 FPGA Loader  ·  XMODEM/CRC-16")
        root.geometry("760x520")
        root.configure(bg="#1e1e2e")

        top = tk.Frame(root, bg="#1e1e2e"); top.pack(fill=tk.X, padx=12, pady=10)
        tk.Label(top, text="FPGA UART LOADER", font=("Segoe UI", 16, "bold"),
                 bg="#1e1e2e", fg="#cdd6f4").pack(side=tk.LEFT)

        cfg = tk.Frame(root, bg="#181825"); cfg.pack(fill=tk.X, padx=12, pady=6)
        tk.Label(cfg, text="Port:", bg="#181825", fg="#cdd6f4").grid(row=0, column=0, padx=6, pady=6)
        self.port_cb = ttk.Combobox(cfg, width=14, values=self._ports())
        self.port_cb.grid(row=0, column=1)
        tk.Label(cfg, text="Baud:", bg="#181825", fg="#cdd6f4").grid(row=0, column=2, padx=6)
        self.baud_e = tk.Entry(cfg, width=8); self.baud_e.insert(0, "115200")
        self.baud_e.grid(row=0, column=3)
        tk.Button(cfg, text="Portları Yenile", command=self._refresh,
                  bg="#89b4fa", fg="#1e1e2e").grid(row=0, column=4, padx=10)

        fl = tk.Frame(root, bg="#1e1e2e"); fl.pack(fill=tk.X, padx=12, pady=6)
        self.file_e = tk.Entry(fl, bg="#313244", fg="#cdd6f4", width=70)
        self.file_e.pack(side=tk.LEFT, padx=4)
        tk.Button(fl, text="Dosya Seç", command=self._pick,
                  bg="#fab387", fg="#1e1e2e").pack(side=tk.LEFT, padx=4)
        tk.Button(fl, text="YÜKLE", command=self._send,
                  bg="#a6e3a1", fg="#1e1e2e", font=("Segoe UI", 10, "bold")
                  ).pack(side=tk.LEFT, padx=10)

        self.pb = ttk.Progressbar(root, length=720, mode="determinate")
        self.pb.pack(padx=12, pady=8)

        self.log = scrolledtext.ScrolledText(root, bg="#11111b", fg="#a6e3a1",
                                             font=("Consolas", 10), height=18)
        self.log.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

    def _ports(self):
        return [p.device for p in list_ports.comports()] if serial else []

    def _refresh(self):
        self.port_cb["values"] = self._ports()

    def _pick(self):
        f = filedialog.askopenfilename(
            filetypes=[("Firmware", "*.mem *.hex *.bin"), ("Tümü", "*.*")])
        if f:
            self.file_e.delete(0, tk.END); self.file_e.insert(0, f)

    def _log(self, msg):
        self.log.insert(tk.END, msg + "\n"); self.log.see(tk.END); self.root.update_idletasks()

    def _send(self):
        port = self.port_cb.get().strip()
        if not port:
            messagebox.showwarning("Port", "Lütfen bir COM portu seçin."); return
        path = self.file_e.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showwarning("Dosya", "Geçerli bir firmware dosyası seçin."); return
        try:
            baud = int(self.baud_e.get())
        except ValueError:
            messagebox.showerror("Baud", "Geçersiz baud."); return

        self.log.delete(1.0, tk.END); self.pb["value"] = 0
        Thread(target=self._worker, args=(port, baud, path), daemon=True).start()

    def _worker(self, port, baud, path):
        try:
            data = load_firmware(path)
            self._log(f"[i] Firmware: {len(data)} bayt ({(len(data)+127)//128} paket)")
            s = XmodemSender(port, baud, log=self._log)
            ok, st = s.send(data, on_progress=self._progress)
            s.close()
            self._log("-"*60)
            self._log(f"Sonuç: {'BAŞARILI' if ok else 'HATA'}   "
                      f"paket={st['packets']} retry={st['retries']} "
                      f"süre={st.get('elapsed',0):.2f}s")
        except Exception as e:
            self._log(f"[!] Hata: {e}")

    def _progress(self, done, total):
        self.pb["maximum"] = total
        self.pb["value"]   = done


def run_gui():
    root = tk.Tk()
    LoaderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        run_gui()
    else:
        run_cli()
