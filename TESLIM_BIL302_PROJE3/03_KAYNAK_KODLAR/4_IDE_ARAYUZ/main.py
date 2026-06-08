"""
PicoRV32 Unified IDE
====================
Assembler + Linker + UART Loader  ·  Tek arayüz, tek workflow

Çalıştır:
    python picorv_ide\main.py
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

# host_app modülünü import edilebilir hale getir
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from host_app.host_loader import XmodemSender, load_firmware, crc16_xmodem
    import serial
    from serial.tools import list_ports
    SERIAL_OK = True
except Exception as e:
    SERIAL_OK = False
    SERIAL_ERR = str(e)

# ─────────────────────────────────────────────────────────────────────────────
# Tema (Catppuccin Mocha esinli)
# ─────────────────────────────────────────────────────────────────────────────
class Theme:
    BG          = "#1e1e2e"   # ana arka
    BG_ALT      = "#181825"   # panel arka
    SURFACE     = "#313244"   # kart yüzeyi
    SURFACE_HI  = "#45475a"   # vurgu
    TEXT        = "#cdd6f4"   # ana metin
    TEXT_DIM    = "#9399b2"   # ikincil
    BLUE        = "#89b4fa"
    GREEN       = "#a6e3a1"
    YELLOW      = "#f9e2af"
    ORANGE      = "#fab387"
    RED         = "#f38ba8"
    PURPLE      = "#cba6f7"
    PINK        = "#f5c2e7"
    TEAL        = "#94e2d5"

CFG_FILE = ROOT / "picorv_ide" / "config.json"


# ─────────────────────────────────────────────────────────────────────────────
# Yardımcılar
# ─────────────────────────────────────────────────────────────────────────────
def load_cfg():
    if CFG_FILE.exists():
        try:
            return json.loads(CFG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def save_cfg(cfg):
    CFG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Ana uygulama
# ─────────────────────────────────────────────────────────────────────────────
class PicoRVIde:
    def __init__(self, root):
        self.root = root
        self.cfg  = load_cfg()
        self.project_root = Path(self.cfg.get("project_root", str(ROOT / "sistem_proglamlama_proje_3")))
        self.tests_root   = Path(self.cfg.get("tests_root",   str(ROOT / "tests")))
        self.busy = False
        self.sender = None
        self.last_obj = None
        self.last_mem = None

        root.title("PicoRV32 IDE  ·  Assembler · Linker · UART Loader")
        root.geometry("1400x900")
        root.configure(bg=Theme.BG)
        root.minsize(1100, 720)

        # Kalıcı log dosyası
        log_dir = ROOT / "picorv_ide" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = log_dir / f"ide_{time.strftime('%Y%m%d_%H%M%S')}.log"
        try:
            self.log_fp = open(self.log_file, "a", encoding="utf-8")
        except Exception:
            self.log_fp = None

        self._setup_ttk_style()
        self._build_topbar()
        self._build_main_layout()
        self._build_statusbar()

        self.refresh_project_tree()
        self.refresh_ports()
        self._update_pipeline_status()
        self.log("PicoRV32 IDE başlatıldı.", color=Theme.TEAL)
        self.log(f"Proje kökü: {self.project_root}", color=Theme.TEXT_DIM)
        if not SERIAL_OK:
            self.log(f"[!] pyserial yüklü değil: {SERIAL_ERR}", color=Theme.RED)
            self.log("    pip install pyserial", color=Theme.YELLOW)

    # ─────────────────────────────────────────────────────────────
    # ttk stil tanımları
    # ─────────────────────────────────────────────────────────────
    def _setup_ttk_style(self):
        s = ttk.Style()
        s.theme_use("clam")

        s.configure("TNotebook", background=Theme.BG, borderwidth=0)
        s.configure("TNotebook.Tab",
                    background=Theme.BG_ALT, foreground=Theme.TEXT_DIM,
                    padding=(20, 10), borderwidth=0, font=("Segoe UI", 10, "bold"))
        s.map("TNotebook.Tab",
              background=[("selected", Theme.SURFACE)],
              foreground=[("selected", Theme.BLUE)])

        s.configure("Treeview",
                    background=Theme.SURFACE, foreground=Theme.TEXT,
                    fieldbackground=Theme.SURFACE, borderwidth=0, rowheight=24,
                    font=("Segoe UI", 9))
        s.configure("Treeview.Heading",
                    background=Theme.BG_ALT, foreground=Theme.BLUE,
                    borderwidth=0, font=("Segoe UI", 9, "bold"))
        s.map("Treeview",
              background=[("selected", Theme.SURFACE_HI)],
              foreground=[("selected", Theme.TEXT)])

        s.configure("Horizontal.TProgressbar",
                    background=Theme.GREEN, troughcolor=Theme.SURFACE,
                    borderwidth=0, lightcolor=Theme.GREEN, darkcolor=Theme.GREEN)

        s.configure("Vertical.TScrollbar",
                    background=Theme.SURFACE, troughcolor=Theme.BG_ALT,
                    borderwidth=0, arrowcolor=Theme.TEXT_DIM)

        s.configure("TCombobox",
                    fieldbackground=Theme.SURFACE, background=Theme.SURFACE,
                    foreground=Theme.TEXT, borderwidth=0)

    # ─────────────────────────────────────────────────────────────
    # Üst başlık çubuğu
    # ─────────────────────────────────────────────────────────────
    def _build_topbar(self):
        bar = tk.Frame(self.root, bg=Theme.BG_ALT, height=64)
        bar.pack(fill=tk.X, side=tk.TOP)
        bar.pack_propagate(False)

        # Logo + isim
        title = tk.Frame(bar, bg=Theme.BG_ALT); title.pack(side=tk.LEFT, padx=20)
        tk.Label(title, text="◆", font=("Segoe UI", 24),
                 bg=Theme.BG_ALT, fg=Theme.BLUE).pack(side=tk.LEFT, padx=(0, 8))
        col = tk.Frame(title, bg=Theme.BG_ALT); col.pack(side=tk.LEFT)
        tk.Label(col, text="PicoRV32 IDE", font=("Segoe UI", 14, "bold"),
                 bg=Theme.BG_ALT, fg=Theme.TEXT).pack(anchor="w")
        tk.Label(col, text="Assembler · Linker · UART Loader",
                 font=("Segoe UI", 8), bg=Theme.BG_ALT, fg=Theme.TEXT_DIM).pack(anchor="w")

        # Sağ taraf: proje kökü
        right = tk.Frame(bar, bg=Theme.BG_ALT); right.pack(side=tk.RIGHT, padx=20)
        self.proj_lbl = tk.Label(right, text=f"📁 {self.project_root.name}",
                                  font=("Segoe UI", 9), bg=Theme.BG_ALT, fg=Theme.YELLOW)
        self.proj_lbl.pack(side=tk.LEFT, padx=10)
        self._mk_btn(right, "Proje Değiştir", self.change_project,
                     bg=Theme.SURFACE, fg=Theme.TEXT, hover=Theme.SURFACE_HI).pack(side=tk.LEFT)

    # ─────────────────────────────────────────────────────────────
    # Workflow şeridi (Assemble → Link → Load)
    # ─────────────────────────────────────────────────────────────
    def _build_workflow_strip(self):
        strip = tk.Frame(self.root, bg=Theme.BG, height=84)
        strip.pack(fill=tk.X, padx=15, pady=12)
        strip.pack_propagate(False)

        steps = [
            ("1", "ASSEMBLE",    "(.asm → .o)",   Theme.BLUE,   self.quick_assemble),
            ("2", "LINK",        "(.o → .mem)",   Theme.ORANGE, self.quick_link),
            ("3", "LOAD",        "(UART → FPGA)", Theme.GREEN,  self.quick_load),
        ]

        for i, (num, name, sub, color, cb) in enumerate(steps):
            card = tk.Frame(strip, bg=Theme.SURFACE, cursor="hand2")
            card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)

            inner = tk.Frame(card, bg=Theme.SURFACE)
            inner.pack(fill=tk.BOTH, expand=True, padx=14, pady=10)

            # numara dairesi
            badge = tk.Label(inner, text=num, font=("Segoe UI", 14, "bold"),
                             bg=color, fg=Theme.BG, width=2, height=1)
            badge.pack(side=tk.LEFT, padx=(0, 14))

            txt = tk.Frame(inner, bg=Theme.SURFACE); txt.pack(side=tk.LEFT, fill=tk.X, expand=True)
            tk.Label(txt, text=name, font=("Segoe UI", 12, "bold"),
                     bg=Theme.SURFACE, fg=Theme.TEXT).pack(anchor="w")
            tk.Label(txt, text=sub, font=("Segoe UI", 9),
                     bg=Theme.SURFACE, fg=Theme.TEXT_DIM).pack(anchor="w")

            # tıklama
            for w in (card, inner, txt, badge):
                w.bind("<Button-1>", lambda e, f=cb: f())
                w.bind("<Enter>", lambda e, c=card: c.configure(bg=Theme.SURFACE_HI))
                w.bind("<Leave>", lambda e, c=card: c.configure(bg=Theme.SURFACE))

            if i < len(steps) - 1:
                tk.Label(strip, text="▶", font=("Segoe UI", 16),
                         bg=Theme.BG, fg=Theme.TEXT_DIM).pack(side=tk.LEFT)

        # Tek tıkla TÜM pipeline
        run_all = tk.Frame(strip, bg=Theme.BG); run_all.pack(side=tk.LEFT, padx=10)
        self._mk_btn(run_all, "▶  RUN ALL",
                     self.run_pipeline, bg=Theme.PURPLE, fg=Theme.BG,
                     hover=Theme.PINK, font=("Segoe UI", 11, "bold"),
                     padx=22, pady=14).pack()

    # ─────────────────────────────────────────────────────────────
    # Ana 3 sütun: sol ağaç · orta sekmeler · sağ log
    # ─────────────────────────────────────────────────────────────
    def _build_main_layout(self):
        # PIPELINE STATUS SERIDI - hangi dosya hangi adimda
        pipe_bar = tk.Frame(self.root, bg=Theme.BG_ALT, height=42)
        pipe_bar.pack(fill=tk.X, padx=15, pady=(4, 4))
        pipe_bar.pack_propagate(False)

        # Sol baslık
        tk.Label(pipe_bar, text="🧬 PIPELINE",
                 font=("Segoe UI", 9, "bold"),
                 bg=Theme.BG_ALT, fg=Theme.PURPLE,
                 padx=14).pack(side=tk.LEFT)

        # 3 etiket: ASM / OBJ / MEM
        self.pipe_asm_lbl = tk.Label(pipe_bar, text="📜 .asm: —",
                                      font=("Consolas", 9),
                                      bg=Theme.BG_ALT, fg=Theme.BLUE, padx=12)
        self.pipe_asm_lbl.pack(side=tk.LEFT)
        tk.Label(pipe_bar, text="▶", font=("Segoe UI", 11),
                 bg=Theme.BG_ALT, fg=Theme.TEXT_DIM).pack(side=tk.LEFT)
        self.pipe_obj_lbl = tk.Label(pipe_bar, text="📦 .o: —",
                                      font=("Consolas", 9),
                                      bg=Theme.BG_ALT, fg=Theme.ORANGE, padx=12)
        self.pipe_obj_lbl.pack(side=tk.LEFT)
        tk.Label(pipe_bar, text="▶", font=("Segoe UI", 11),
                 bg=Theme.BG_ALT, fg=Theme.TEXT_DIM).pack(side=tk.LEFT)
        self.pipe_mem_lbl = tk.Label(pipe_bar, text="💾 .mem: —",
                                      font=("Consolas", 9),
                                      bg=Theme.BG_ALT, fg=Theme.GREEN, padx=12)
        self.pipe_mem_lbl.pack(side=tk.LEFT)

        # Sag: timestamp
        self.pipe_ts_lbl = tk.Label(pipe_bar, text="",
                                     font=("Consolas", 8),
                                     bg=Theme.BG_ALT, fg=Theme.TEXT_DIM, padx=14)
        self.pipe_ts_lbl.pack(side=tk.RIGHT)

        # Dikey PanedWindow: üstte tab/ağaç + altta canlı log terminal.
        # Sürükleyerek yeniden boyutlandırılabilir.
        outer = tk.PanedWindow(self.root, orient=tk.VERTICAL,
                                bg=Theme.BG, sashwidth=6, sashrelief=tk.FLAT,
                                bd=0, sashpad=0)
        outer.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 6))

        # Üst kısım: sol ağaç + orta sekmeler (yatay)
        top_area = tk.Frame(outer, bg=Theme.BG)
        outer.add(top_area, minsize=200)

        # SOL — Dosya ağacı
        left = tk.Frame(top_area, bg=Theme.BG_ALT, width=260)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        left.pack_propagate(False)

        head = tk.Frame(left, bg=Theme.BG_ALT); head.pack(fill=tk.X, padx=10, pady=8)
        tk.Label(head, text="📂  PROJE",
                 font=("Segoe UI", 9, "bold"), bg=Theme.BG_ALT, fg=Theme.BLUE).pack(side=tk.LEFT)
        tk.Button(head, text="⟳", command=self.refresh_project_tree,
                  bg=Theme.BG_ALT, fg=Theme.TEXT_DIM, borderwidth=0,
                  activebackground=Theme.SURFACE, activeforeground=Theme.TEXT,
                  font=("Segoe UI", 11), cursor="hand2").pack(side=tk.RIGHT)

        self.tree = ttk.Treeview(left, show="tree", selectmode="browse")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.tree.bind("<Double-1>", self.on_tree_dbl)

        # ORTA — Notebook (sekmeler)
        center = tk.Frame(top_area, bg=Theme.BG)
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.nb = ttk.Notebook(center)
        self.nb.pack(fill=tk.BOTH, expand=True)
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

        self._build_tab_assembler()
        self._build_tab_linker()
        self._build_tab_loader()
        self._build_tab_inspect()
        self._build_tab_metrics()

        # ALT — CANLI LOG TERMINALI (PanedWindow'a eklenir, sürüklenebilir)
        bottom = tk.Frame(outer, bg=Theme.BG_ALT)
        outer.add(bottom, minsize=180)
        # Varsayılan: üst:alt = ~60:40
        self.root.after(50, lambda: outer.sash_place(0, 0, 480))

        loghead = tk.Frame(bottom, bg="#0a0a12", height=34); loghead.pack(fill=tk.X)
        loghead.pack_propagate(False)
        # macOS tarzı pencere kontrolleri (dekoratif)
        tk.Label(loghead, text="●", font=("Segoe UI", 13),
                 bg="#0a0a12", fg="#ff5f57").pack(side=tk.LEFT, padx=(14, 4))
        tk.Label(loghead, text="●", font=("Segoe UI", 13),
                 bg="#0a0a12", fg="#febc2e").pack(side=tk.LEFT, padx=(0, 4))
        tk.Label(loghead, text="●", font=("Segoe UI", 13),
                 bg="#0a0a12", fg="#28c840").pack(side=tk.LEFT, padx=(0, 14))
        tk.Label(loghead, text="picorv_ide ─ live log stream",
                 font=("Consolas", 10, "bold"), bg="#0a0a12", fg=Theme.GREEN
                 ).pack(side=tk.LEFT)
        self.log_count_lbl = tk.Label(loghead, text="0 satır",
                                       font=("Consolas", 9), bg="#0a0a12", fg=Theme.TEXT_DIM)
        self.log_count_lbl.pack(side=tk.LEFT, padx=14)
        self.log_file_lbl = tk.Label(loghead, text="",
                                      font=("Consolas", 9), bg="#0a0a12", fg=Theme.BLUE)
        self.log_file_lbl.pack(side=tk.LEFT)

        # Sağ kontroller
        ctrl = tk.Frame(loghead, bg="#0a0a12"); ctrl.pack(side=tk.RIGHT, padx=8)
        self.autoscroll_var = tk.IntVar(value=1)
        tk.Checkbutton(ctrl, text="auto-scroll", variable=self.autoscroll_var,
                       bg="#0a0a12", fg=Theme.TEXT_DIM,
                       activebackground="#0a0a12", activeforeground=Theme.TEXT,
                       selectcolor=Theme.SURFACE, borderwidth=0,
                       font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl, text="📁 logs",
                  command=self._open_log_dir,
                  bg="#0a0a12", fg=Theme.BLUE, borderwidth=0,
                  activebackground=Theme.SURFACE, activeforeground=Theme.BLUE,
                  font=("Segoe UI", 9), cursor="hand2").pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl, text="🧹 build",
                  command=self._clean_build_dir,
                  bg="#0a0a12", fg=Theme.ORANGE, borderwidth=0,
                  activebackground=Theme.SURFACE, activeforeground=Theme.ORANGE,
                  font=("Segoe UI", 9), cursor="hand2").pack(side=tk.LEFT, padx=4)
        tk.Button(ctrl, text="🗑 log",
                  command=self._clear_log,
                  bg="#0a0a12", fg=Theme.TEXT_DIM, borderwidth=0,
                  activebackground=Theme.SURFACE, activeforeground=Theme.TEXT,
                  font=("Segoe UI", 9), cursor="hand2").pack(side=tk.LEFT, padx=4)

        # Konsol metin + scrollbar — BÜYÜK FONT, GENİŞ ALAN
        cw = tk.Frame(bottom, bg="#0e0e16"); cw.pack(fill=tk.BOTH, expand=True)
        self.log_w = tk.Text(cw, bg="#0e0e16", fg=Theme.TEXT,
                              font=("Consolas", 11), borderwidth=0, padx=16, pady=10,
                              wrap="word", insertbackground=Theme.GREEN,
                              spacing1=1, spacing3=1)
        self.log_w.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(cw, orient="vertical", command=self.log_w.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_w.configure(yscrollcommand=sb.set)

        for c in (Theme.GREEN, Theme.YELLOW, Theme.RED, Theme.BLUE,
                  Theme.ORANGE, Theme.PURPLE, Theme.TEAL, Theme.TEXT_DIM, Theme.PINK):
            self.log_w.tag_configure(c, foreground=c)
        # Vurgu için bold tag
        self.log_w.tag_configure("bold", font=("Consolas", 10, "bold"))

        self._log_lines = 0
        if getattr(self, "log_file", None):
            self.log_file_lbl.configure(text=f"→ {self.log_file.name}")

    # ─────────────────────────────────────────────────────────────
    # Sekme: ASSEMBLER
    # ─────────────────────────────────────────────────────────────
    def _build_tab_assembler(self):
        tab = self._mk_tab("⚙  Assembler")

        # Üst: dosya seçimi
        top = self._mk_card(tab, "Kaynak Assembly Dosyası")
        self.asm_path = tk.StringVar()
        row = tk.Frame(top, bg=Theme.SURFACE); row.pack(fill=tk.X, pady=4)
        tk.Entry(row, textvariable=self.asm_path, bg=Theme.BG_ALT, fg=Theme.TEXT,
                 borderwidth=0, font=("Consolas", 10), insertbackground=Theme.TEXT
                 ).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 8))
        self._mk_btn(row, "📄  .asm seç", self.pick_asm,
                     bg=Theme.BLUE, fg=Theme.BG).pack(side=tk.LEFT)

        # Hızlı dosya butonları
        quick = tk.Frame(top, bg=Theme.SURFACE); quick.pack(fill=tk.X, pady=(8, 0))
        tk.Label(quick, text="Hızlı seçim:", bg=Theme.SURFACE, fg=Theme.TEXT_DIM,
                 font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 8))
        self.asm_quick_box = tk.Frame(quick, bg=Theme.SURFACE); self.asm_quick_box.pack(side=tk.LEFT)

        # Çıktı
        out = self._mk_card(tab, "Çıktı")
        outrow = tk.Frame(out, bg=Theme.SURFACE); outrow.pack(fill=tk.X)
        tk.Label(outrow, text="Hedef dizin:", bg=Theme.SURFACE, fg=Theme.TEXT,
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.asm_outdir = tk.StringVar(value=str(self.project_root / "build"))
        tk.Entry(outrow, textvariable=self.asm_outdir, bg=Theme.BG_ALT, fg=Theme.TEXT,
                 borderwidth=0, font=("Consolas", 9), insertbackground=Theme.TEXT, width=55
                 ).grid(row=0, column=1, sticky="ew", ipady=4)
        outrow.columnconfigure(1, weight=1)

        # Çalıştır
        action = tk.Frame(tab, bg=Theme.BG); action.pack(fill=tk.X, pady=12, padx=4)
        self._mk_btn(action, "⚙  ASSEMBLE",
                     self.quick_assemble, bg=Theme.BLUE, fg=Theme.BG,
                     hover=Theme.PURPLE, font=("Segoe UI", 11, "bold"),
                     padx=24, pady=12).pack(side=tk.LEFT)
        tk.Label(action, text="(Üretilen .o dosyası otomatik olarak Linker sekmesine eklenir)",
                 bg=Theme.BG, fg=Theme.TEXT_DIM, font=("Segoe UI", 8)
                 ).pack(side=tk.LEFT, padx=12)

        # Hex önizleme
        prev = self._mk_card(tab, ".asm  Önizleme")
        self.asm_preview = tk.Text(prev, bg=Theme.BG_ALT, fg=Theme.TEXT,
                                    font=("Consolas", 9), borderwidth=0, height=10,
                                    padx=10, pady=8, wrap="none")
        self.asm_preview.pack(fill=tk.BOTH, expand=True)
        self.asm_preview.tag_configure("kw",  foreground=Theme.PURPLE)
        self.asm_preview.tag_configure("reg", foreground=Theme.BLUE)
        self.asm_preview.tag_configure("num", foreground=Theme.ORANGE)
        self.asm_preview.tag_configure("cmt", foreground=Theme.TEXT_DIM)
        self.asm_preview.tag_configure("lbl", foreground=Theme.YELLOW)

        self._refresh_asm_quick()

    # ─────────────────────────────────────────────────────────────
    # Sekme: LINKER
    # ─────────────────────────────────────────────────────────────
    def _build_tab_linker(self):
        tab = self._mk_tab("🔗  Linker")

        # .o dosyaları
        files = self._mk_card(tab, "Object Dosyaları (.o)")
        row = tk.Frame(files, bg=Theme.SURFACE); row.pack(fill=tk.X, pady=4)
        self._mk_btn(row, "➕  .o ekle", self.add_obj_files,
                     bg=Theme.BLUE, fg=Theme.BG).pack(side=tk.LEFT, padx=(0, 8))
        self._mk_btn(row, "🗑  Temizle", self.clear_obj_files,
                     bg=Theme.SURFACE_HI, fg=Theme.TEXT).pack(side=tk.LEFT)

        self.obj_list = tk.Listbox(files, bg=Theme.BG_ALT, fg=Theme.TEXT,
                                    selectbackground=Theme.SURFACE_HI,
                                    font=("Consolas", 9), borderwidth=0, height=5)
        self.obj_list.pack(fill=tk.X, pady=(8, 0))

        # Adres ayarları
        addr = self._mk_card(tab, "Segment Adresleri")
        af = tk.Frame(addr, bg=Theme.SURFACE); af.pack(fill=tk.X)
        tk.Label(af, text=".text base (-Ttext):", bg=Theme.SURFACE, fg=Theme.TEXT,
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", padx=(0,8), pady=4)
        self.ttext = tk.StringVar(value="0x0")
        tk.Entry(af, textvariable=self.ttext, bg=Theme.BG_ALT, fg=Theme.BLUE,
                 borderwidth=0, font=("Consolas", 10), width=14,
                 insertbackground=Theme.TEXT).grid(row=0, column=1, padx=(0,20), ipady=4)
        tk.Label(af, text=".data base (-Tdata):", bg=Theme.SURFACE, fg=Theme.TEXT,
                 font=("Segoe UI", 9)).grid(row=0, column=2, sticky="w", padx=(0,8))
        self.tdata = tk.StringVar(value="0x1000")
        tk.Entry(af, textvariable=self.tdata, bg=Theme.BG_ALT, fg=Theme.ORANGE,
                 borderwidth=0, font=("Consolas", 10), width=14,
                 insertbackground=Theme.TEXT).grid(row=0, column=3, ipady=4)

        tk.Label(addr, text="PicoRV32 PROGADDR_RESET = 0x00000000  ·  hex veya decimal kabul edilir",
                 bg=Theme.SURFACE, fg=Theme.TEXT_DIM, font=("Segoe UI", 8)
                 ).pack(anchor="w", pady=(8, 0))

        # Çıktı dosyası
        out = self._mk_card(tab, "Çıktı Firmware (.mem)")
        self.mem_path = tk.StringVar(value=str(self.project_root / "build" / "firmware.mem"))
        tk.Entry(out, textvariable=self.mem_path, bg=Theme.BG_ALT, fg=Theme.TEXT,
                 borderwidth=0, font=("Consolas", 9), insertbackground=Theme.TEXT
                 ).pack(fill=tk.X, ipady=6)

        # Çalıştır
        action = tk.Frame(tab, bg=Theme.BG); action.pack(fill=tk.X, pady=12, padx=4)
        self._mk_btn(action, "🔗  LINK ET",
                     self.quick_link, bg=Theme.ORANGE, fg=Theme.BG,
                     hover=Theme.YELLOW, font=("Segoe UI", 11, "bold"),
                     padx=24, pady=12).pack(side=tk.LEFT)

        # ESTAB tablosu
        sym = self._mk_card(tab, "ESTAB · Symbol Table")
        cols = ("Symbol", "Address", "Scope", "Section")
        self.estab = ttk.Treeview(sym, columns=cols, show="headings", height=6)
        for c, w in zip(cols, (260, 140, 80, 80)):
            self.estab.heading(c, text=c)
            self.estab.column(c, width=w, anchor="w")
        self.estab.pack(fill=tk.BOTH, expand=True)

        # Ham linker stdout
        raw = self._mk_card(tab, "Linker Ham Çıktı (stdout)")
        self.linker_raw = tk.Text(raw, bg=Theme.BG_ALT, fg=Theme.TEXT,
                                   font=("Consolas", 9), borderwidth=0, height=8,
                                   padx=10, pady=8, wrap="word")
        self.linker_raw.pack(fill=tk.BOTH, expand=True)
        self.linker_raw.tag_configure("hdr", foreground=Theme.PURPLE, font=("Consolas", 9, "bold"))
        self.linker_raw.tag_configure("ok",  foreground=Theme.GREEN)
        self.linker_raw.tag_configure("addr", foreground=Theme.ORANGE)

    # ─────────────────────────────────────────────────────────────
    # Sekme: LOADER
    # ─────────────────────────────────────────────────────────────
    def _build_tab_loader(self):
        tab = self._mk_tab("📡  UART Loader")

        # Bağlantı kartı
        conn = self._mk_card(tab, "FPGA UART Bağlantısı")
        cf = tk.Frame(conn, bg=Theme.SURFACE); cf.pack(fill=tk.X)
        tk.Label(cf, text="COM Port:", bg=Theme.SURFACE, fg=Theme.TEXT,
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", padx=(0,8), pady=4)
        self.port_var = tk.StringVar(value=self.cfg.get("port", ""))
        self.port_cb = ttk.Combobox(cf, textvariable=self.port_var, width=14, font=("Consolas", 10))
        self.port_cb.grid(row=0, column=1, ipady=2, padx=(0, 12))
        self.port_cb.bind("<<ComboboxSelected>>",
                          lambda e: self.log(f"🔌 COM seçildi: {self.port_var.get()}", color=Theme.BLUE))

        self._mk_btn(cf, "⟳", self.refresh_ports, bg=Theme.SURFACE_HI,
                     fg=Theme.TEXT, padx=8, pady=2).grid(row=0, column=2, padx=(0, 20))

        tk.Label(cf, text="Baud:", bg=Theme.SURFACE, fg=Theme.TEXT,
                 font=("Segoe UI", 9)).grid(row=0, column=3, sticky="w", padx=(0,8))
        self.baud_var = tk.StringVar(value=str(self.cfg.get("baud", 115200)))
        tk.Entry(cf, textvariable=self.baud_var, bg=Theme.BG_ALT, fg=Theme.GREEN,
                 borderwidth=0, font=("Consolas", 10), width=10,
                 insertbackground=Theme.TEXT).grid(row=0, column=4, ipady=4)

        # Firmware seç
        fw = self._mk_card(tab, "Firmware Dosyası (.mem / .bin)")
        row = tk.Frame(fw, bg=Theme.SURFACE); row.pack(fill=tk.X)
        self.fw_path = tk.StringVar()
        tk.Entry(row, textvariable=self.fw_path, bg=Theme.BG_ALT, fg=Theme.TEXT,
                 borderwidth=0, font=("Consolas", 9), insertbackground=Theme.TEXT
                 ).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 8))
        self._mk_btn(row, "📄  Firmware seç", self.pick_fw,
                     bg=Theme.GREEN, fg=Theme.BG).pack(side=tk.LEFT)

        # Hızlı .mem seçimleri
        quick = tk.Frame(fw, bg=Theme.SURFACE); quick.pack(fill=tk.X, pady=(8, 0))
        tk.Label(quick, text="Hızlı seçim:", bg=Theme.SURFACE, fg=Theme.TEXT_DIM,
                 font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 8))
        self.fw_quick_box = tk.Frame(quick, bg=Theme.SURFACE); self.fw_quick_box.pack(side=tk.LEFT)

        # Yükle butonu + progress
        action = tk.Frame(tab, bg=Theme.BG); action.pack(fill=tk.X, pady=12, padx=4)
        self.load_btn = self._mk_btn(action, "📡  YÜKLE  (XMODEM-CRC)",
                                      self.quick_load, bg=Theme.GREEN, fg=Theme.BG,
                                      hover=Theme.TEAL, font=("Segoe UI", 11, "bold"),
                                      padx=24, pady=12)
        self.load_btn.pack(side=tk.LEFT)

        tk.Label(action, text="⚠  Yüklemeden önce Tang Nano 9K'da S1 (reset) butonuna basın!",
                 bg=Theme.BG, fg=Theme.YELLOW, font=("Segoe UI", 9, "italic")
                 ).pack(side=tk.LEFT, padx=12)

        # Progress
        prog = self._mk_card(tab, "Aktarım Durumu")
        self.pb = ttk.Progressbar(prog, length=600, mode="determinate")
        self.pb.pack(fill=tk.X, pady=4)

        stats = tk.Frame(prog, bg=Theme.SURFACE); stats.pack(fill=tk.X, pady=8)
        self.stat_pkt   = self._stat_card(stats, "PAKET",  "0/0", Theme.BLUE)
        self.stat_retry = self._stat_card(stats, "RETRY",  "0",   Theme.YELLOW)
        self.stat_bytes = self._stat_card(stats, "BAYT",   "0",   Theme.PURPLE)
        self.stat_time  = self._stat_card(stats, "SÜRE",   "0s",  Theme.GREEN)
        self.stat_state = self._stat_card(stats, "DURUM",  "—",   Theme.TEXT_DIM)

        # Protokol diyagramı
        proto = self._mk_card(tab, "XMODEM-CRC Paket Yapısı")
        self._build_packet_diagram(proto)

    def _stat_card(self, parent, label, value, color):
        c = tk.Frame(parent, bg=Theme.BG_ALT); c.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        tk.Label(c, text=label, font=("Segoe UI", 7, "bold"),
                 bg=Theme.BG_ALT, fg=Theme.TEXT_DIM).pack(pady=(8, 0))
        v = tk.Label(c, text=value, font=("Consolas", 14, "bold"),
                     bg=Theme.BG_ALT, fg=color)
        v.pack(pady=(0, 8))
        return v

    def _build_packet_diagram(self, parent):
        cv = tk.Canvas(parent, bg=Theme.SURFACE, height=70, highlightthickness=0)
        cv.pack(fill=tk.X)
        # SOH | seq | ~seq | 128 byte data | CRCH | CRCL
        boxes = [
            ("SOH",      Theme.PINK,   45),
            ("seq",      Theme.BLUE,   45),
            ("~seq",     Theme.BLUE,   45),
            ("128 byte payload", Theme.GREEN, 280),
            ("CRC H",    Theme.ORANGE, 55),
            ("CRC L",    Theme.ORANGE, 55),
        ]
        x = 14
        for lbl, col, w in boxes:
            cv.create_rectangle(x, 14, x+w, 50, fill=col, outline="")
            cv.create_text(x + w//2, 32, text=lbl, fill=Theme.BG,
                           font=("Segoe UI", 9, "bold"))
            x += w + 4

    # ─────────────────────────────────────────────────────────────
    # Sekme: INSPECT (.mem inceleme + disassembly)
    # ─────────────────────────────────────────────────────────────
    def _build_tab_inspect(self):
        tab = self._mk_tab("🔍  İnceleme")

        # Üst seçim
        top = self._mk_card(tab, ".mem Dosyası")
        row = tk.Frame(top, bg=Theme.SURFACE); row.pack(fill=tk.X)
        self.insp_path = tk.StringVar()
        tk.Entry(row, textvariable=self.insp_path, bg=Theme.BG_ALT, fg=Theme.TEXT,
                 borderwidth=0, font=("Consolas", 9), insertbackground=Theme.TEXT
                 ).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 8))
        self._mk_btn(row, "📄  Dosya seç", self.pick_inspect,
                     bg=Theme.BLUE, fg=Theme.BG).pack(side=tk.LEFT, padx=4)
        self._mk_btn(row, "🔍  İncele", self.do_inspect,
                     bg=Theme.PURPLE, fg=Theme.BG).pack(side=tk.LEFT)

        # 2 sütun: hex / disasm
        cols = tk.Frame(tab, bg=Theme.BG); cols.pack(fill=tk.BOTH, expand=True, pady=8)

        left = tk.Frame(cols, bg=Theme.SURFACE); left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        tk.Label(left, text="HEX  (32-bit words, big-endian gösterim)",
                 font=("Segoe UI", 9, "bold"), bg=Theme.SURFACE, fg=Theme.BLUE
                 ).pack(anchor="w", padx=10, pady=(8, 0))
        self.hex_w = tk.Text(left, bg=Theme.BG_ALT, fg=Theme.TEXT,
                              font=("Consolas", 10), borderwidth=0, padx=10, pady=8,
                              wrap="none")
        self.hex_w.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        right = tk.Frame(cols, bg=Theme.SURFACE); right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 0))
        tk.Label(right, text="DISASSEMBLY  (RV32I)",
                 font=("Segoe UI", 9, "bold"), bg=Theme.SURFACE, fg=Theme.ORANGE
                 ).pack(anchor="w", padx=10, pady=(8, 0))
        self.dis_w = tk.Text(right, bg=Theme.BG_ALT, fg=Theme.TEXT,
                              font=("Consolas", 10), borderwidth=0, padx=10, pady=8,
                              wrap="none")
        self.dis_w.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # ─────────────────────────────────────────────────────────────
    # Sekme: METRİKLER / RAPOR (Tablo 3.2 + Tablo 3.3)
    # ─────────────────────────────────────────────────────────────
    def _build_tab_metrics(self):
        tab = self._mk_tab("📊  Rapor")

        # === ÜST: Tablo 3.2 (Yükleme Süreleri - log'dan) ===
        top_card = self._mk_card(tab, "Tablo 3.2 · FPGA Yükleme Süreleri (otomatik)")

        bar1 = tk.Frame(top_card, bg=Theme.SURFACE); bar1.pack(fill=tk.X, pady=(0, 6))
        self._mk_btn(bar1, "🔄  Mevcut log'dan yenile",
                     self.refresh_upload_metrics,
                     bg=Theme.BLUE, fg=Theme.BG,
                     hover=Theme.PURPLE).pack(side=tk.LEFT, padx=(0, 6))
        self._mk_btn(bar1, "📂  Başka log seç",
                     self.pick_other_log,
                     bg=Theme.SURFACE_HI, fg=Theme.TEXT).pack(side=tk.LEFT, padx=(0, 6))
        self._mk_btn(bar1, "💾  CSV kaydet",
                     self.export_metrics_csv,
                     bg=Theme.GREEN, fg=Theme.BG).pack(side=tk.LEFT, padx=(0, 6))
        self._mk_btn(bar1, "📝  Markdown kopyala",
                     self.copy_metrics_markdown,
                     bg=Theme.ORANGE, fg=Theme.BG).pack(side=tk.LEFT)

        cols = ("Test Programı", "Boyut (B)", "Paket", "Teorik (s)",
                "Ölçülen (s)", "Retry", "Etkin (B/s)")
        self.upload_tree = ttk.Treeview(top_card, columns=cols, show="headings", height=10)
        widths = (200, 80, 60, 80, 80, 60, 90)
        for c, w in zip(cols, widths):
            self.upload_tree.heading(c, text=c)
            self.upload_tree.column(c, width=w, anchor="w")
        self.upload_tree.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        # Özet istatistik bar'ı (alt strip)
        sum_bar = tk.Frame(top_card, bg=Theme.BG_ALT); sum_bar.pack(fill=tk.X, pady=(8, 0))
        self.metric_sum_lbl = tk.Label(sum_bar,
            text="📈 Toplam: 0 yükleme · 0 retry · 0.00 s",
            font=("Consolas", 10, "bold"), bg=Theme.BG_ALT, fg=Theme.GREEN,
            padx=14, pady=8)
        self.metric_sum_lbl.pack(side=tk.LEFT)

        # === ALT: Tablo 3.3 (FPGA Kaynak Tüketimi - GOWIN rpt) ===
        bot_card = self._mk_card(tab, "Tablo 3.3 · FPGA Sentez Kaynak Tüketimi (GOWIN)")

        rpt_row = tk.Frame(bot_card, bg=Theme.SURFACE); rpt_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(rpt_row, text="GOWIN PnR raporu:",
                 bg=Theme.SURFACE, fg=Theme.TEXT_DIM,
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 8))
        self.rpt_path = tk.StringVar(value="")
        tk.Entry(rpt_row, textvariable=self.rpt_path, bg=Theme.BG_ALT, fg=Theme.TEXT,
                 borderwidth=0, font=("Consolas", 9), insertbackground=Theme.TEXT
                 ).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 6))
        self._mk_btn(rpt_row, "📂  .rpt seç", self.pick_pnr_report,
                     bg=Theme.BLUE, fg=Theme.BG).pack(side=tk.LEFT, padx=2)
        self._mk_btn(rpt_row, "🔍  Otomatik bul", self.auto_find_pnr_report,
                     bg=Theme.PURPLE, fg=Theme.BG).pack(side=tk.LEFT, padx=2)

        # Kaynak istatistik kartları
        cards = tk.Frame(bot_card, bg=Theme.SURFACE); cards.pack(fill=tk.X, pady=8)
        self.rsrc_lut  = self._rsrc_card(cards, "LUT",      "—", Theme.BLUE)
        self.rsrc_ff   = self._rsrc_card(cards, "REGISTER", "—", Theme.GREEN)
        self.rsrc_bsm  = self._rsrc_card(cards, "B-SRAM",   "—", Theme.ORANGE)
        self.rsrc_dsp  = self._rsrc_card(cards, "DSP",      "—", Theme.PURPLE)
        self.rsrc_pin  = self._rsrc_card(cards, "I/O PIN",  "—", Theme.PINK)

        # Detaylı raw çıktı
        det = tk.Frame(bot_card, bg=Theme.SURFACE); det.pack(fill=tk.X, pady=(8, 0))
        tk.Label(det, text="Detaylı Resource Usage:",
                 bg=Theme.SURFACE, fg=Theme.TEXT_DIM,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.rsrc_detail = tk.Text(det, bg=Theme.BG_ALT, fg=Theme.TEXT,
                                   font=("Consolas", 9), borderwidth=0,
                                   height=8, padx=10, pady=6, wrap="word")
        self.rsrc_detail.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        self.rsrc_detail.tag_configure("hdr", foreground=Theme.BLUE, font=("Consolas", 9, "bold"))
        self.rsrc_detail.tag_configure("num", foreground=Theme.YELLOW)
        self.rsrc_detail.tag_configure("pct", foreground=Theme.GREEN)

        # Cached parsed data
        self._upload_rows = []
        self._rsrc_data   = {}

        # Açılışta otomatik mevcut log'u yükle
        self.root.after(500, self.refresh_upload_metrics)

    def _rsrc_card(self, parent, label, value, color):
        c = tk.Frame(parent, bg=Theme.BG_ALT)
        c.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        tk.Label(c, text=label, font=("Segoe UI", 7, "bold"),
                 bg=Theme.BG_ALT, fg=Theme.TEXT_DIM).pack(pady=(8, 0))
        v = tk.Label(c, text=value, font=("Consolas", 13, "bold"),
                     bg=Theme.BG_ALT, fg=color)
        v.pack(pady=(0, 2))
        pct = tk.Label(c, text="", font=("Consolas", 8),
                       bg=Theme.BG_ALT, fg=Theme.TEXT_DIM)
        pct.pack(pady=(0, 8))
        return (v, pct)

    # ─── Tablo 3.2: Log parse ───────────────────────────────────
    def refresh_upload_metrics(self):
        log_file = getattr(self, "log_file", None)
        if not log_file or not Path(log_file).exists():
            self.log("[!] Mevcut log dosyası yok.", color=Theme.YELLOW)
            return
        self._parse_log_uploads(Path(log_file))

    def pick_other_log(self):
        log_dir = ROOT / "picorv_ide" / "logs"
        p = filedialog.askopenfilename(
            initialdir=str(log_dir),
            filetypes=[("Log", "*.log"), ("Tümü", "*.*")],
            parent=self.root)
        if p:
            self._parse_log_uploads(Path(p))
            self.log(f"📊 Log analizi: {Path(p).name}", color=Theme.PURPLE)

    def _parse_log_uploads(self, log_path: Path):
        import re as _re
        try:
            text = log_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            self.log(f"[X] Log okuma: {e}", color=Theme.RED); return

        upload_re = _re.compile(
            r"📡\s+(?P<file>\S+?)(?:__\d+_\d+)?\.mem\s+·\s+(?P<bytes>\d+)\s+bayt\s+·\s+(?P<pkts>\d+)\s+paket")
        success_re = _re.compile(
            r"✅\s+BAŞARILI\s+·\s+paket=(?P<pkts>\d+)\s+retry=(?P<retry>\d+)\s+süre=(?P<dur>[\d.]+)s")

        results = []
        current = None
        for line in text.splitlines():
            m = upload_re.search(line)
            if m:
                current = {"file": m.group("file"),
                           "bytes": int(m.group("bytes")),
                           "pkts": int(m.group("pkts"))}
                continue
            m = success_re.search(line)
            if m and current:
                current["retry"] = int(m.group("retry"))
                current["duration"] = float(m.group("dur"))
                results.append(current); current = None

        # Aggregate aynı dosyalar için
        from collections import OrderedDict
        agg = OrderedDict()
        for r in results:
            name = r["file"]
            if name not in agg:
                agg[name] = {"bytes": r["bytes"], "pkts": r["pkts"],
                             "durations": [], "retries": []}
            agg[name]["durations"].append(r["duration"])
            agg[name]["retries"].append(r["retry"])

        # Treeview'i temizle ve doldur
        for it in self.upload_tree.get_children():
            self.upload_tree.delete(it)
        self._upload_rows = []

        total_uploads = len(results)
        total_retry   = sum(sum(d["retries"]) for d in agg.values())
        total_dur     = sum(sum(d["durations"]) for d in agg.values())

        for name, data in agg.items():
            avg_dur = sum(data["durations"]) / len(data["durations"])
            avg_ret = sum(data["retries"]) / len(data["retries"])
            teorik  = data["pkts"] * 0.01155  # 11.55 ms/paket
            rate    = data["bytes"] / avg_dur if avg_dur > 0 else 0
            row = (name + ".asm",
                   f"{data['bytes']}",
                   f"{data['pkts']}",
                   f"{teorik:.3f}",
                   f"{avg_dur:.3f}",
                   f"{avg_ret:.1f}" if avg_ret > 0 else "0",
                   f"{rate:.0f}")
            self.upload_tree.insert("", tk.END, values=row)
            self._upload_rows.append(row)

        self.metric_sum_lbl.configure(
            text=f"📈 Toplam: {total_uploads} yükleme · {total_retry} retry "
                 f"· {total_dur:.2f} s · {len(agg)} benzersiz program")
        self.log(f"📊 Tablo 3.2 güncellendi: {len(agg)} program × "
                 f"{total_uploads} yükleme", color=Theme.PURPLE)

    # ─── Tablo 3.3: GOWIN PnR raporu parse ───────────────────────
    def pick_pnr_report(self):
        # Tipik GOWIN PnR rpt yolu
        default = ROOT / "gowin_program" / "fpga_project" / "impl" / "pnr"
        p = filedialog.askopenfilename(
            initialdir=str(default if default.exists() else ROOT),
            filetypes=[("Report", "*.rpt *.txt *.rpt.txt"), ("Tümü", "*.*")],
            parent=self.root)
        if p:
            self.rpt_path.set(p)
            self._parse_pnr_report(Path(p))

    def auto_find_pnr_report(self):
        # GOWIN impl/pnr klasöründe *.rpt veya *.rpt.txt ara
        search_dirs = [
            ROOT / "gowin_program" / "fpga_project" / "impl" / "pnr",
            ROOT / "gowin_program" / "fpga_project" / "impl",
        ]
        found = []
        for d in search_dirs:
            if d.exists():
                found.extend(d.glob("*.rpt"))
                found.extend(d.glob("*.rpt.txt"))
                found.extend(d.glob("*_pnr_report.txt"))
        if not found:
            self.log("[!] GOWIN PnR raporu bulunamadı. "
                     "Önce Place & Route çalıştırın.", color=Theme.YELLOW)
            return
        # En yeni
        found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        p = found[0]
        self.rpt_path.set(str(p))
        self.log(f"📂 Otomatik bulundu: {p.name}", color=Theme.GREEN)
        self._parse_pnr_report(p)

    def _parse_pnr_report(self, p: Path):
        import re as _re
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            self.log(f"[X] Rapor okuma: {e}", color=Theme.RED); return

        # GOWIN report formati: "Resource | Used | Total | Utilization"
        # Cesitli formatlar olabilir:
        #   "LUT4       2145     8640     24.83%"
        #   "Total Logic       3215 / 8640  ( 37.21%)"
        #   "Register          1124 / 6480  ( 17.34%)"
        patterns = {
            "LUT":       _re.compile(r"(?:Total\s+)?(?:LUT4?|Logic)\D+(\d+)\s*/?\s*(\d+)?\s*[\(\s]+\s*([\d.]+)\s*%?", _re.IGNORECASE),
            "Register":  _re.compile(r"Register(?:\s+as\s+FF)?\D+(\d+)\s*/?\s*(\d+)?\s*[\(\s]+\s*([\d.]+)\s*%?", _re.IGNORECASE),
            "BSRAM":     _re.compile(r"B[-_]?SRAM\D+(\d+)\s*/?\s*(\d+)?\s*[\(\s]+\s*([\d.]+)\s*%?", _re.IGNORECASE),
            "DSP":       _re.compile(r"DSP\D+(\d+)\s*/?\s*(\d+)?\s*[\(\s]+\s*([\d.]+)\s*%?", _re.IGNORECASE),
            "Pin":       _re.compile(r"(?:Total\s+)?Pins?\D+(\d+)\s*/?\s*(\d+)?\s*[\(\s]+\s*([\d.]+)\s*%?", _re.IGNORECASE),
        }
        # Daha güvenli: satır-satır bul
        rsrc = {}
        for line in txt.splitlines():
            line_clean = line.strip()
            for key, pat in patterns.items():
                if key in rsrc: continue
                m = pat.search(line_clean)
                if m:
                    used = int(m.group(1))
                    total = int(m.group(2)) if m.group(2) else None
                    pct = float(m.group(3))
                    rsrc[key] = (used, total, pct)
                    break

        self._rsrc_data = rsrc

        # Kartları güncelle
        def upd(card, key, color):
            v, pct_lbl = card
            if key in rsrc:
                used, total, pct = rsrc[key]
                v.configure(text=f"{used}")
                if total:
                    pct_lbl.configure(text=f"/ {total}  ·  {pct:.1f}%", fg=color)
                else:
                    pct_lbl.configure(text=f"({pct:.1f}%)", fg=color)
            else:
                v.configure(text="—")
                pct_lbl.configure(text="bulunamadı", fg=Theme.RED)

        upd(self.rsrc_lut, "LUT",      Theme.BLUE)
        upd(self.rsrc_ff,  "Register", Theme.GREEN)
        upd(self.rsrc_bsm, "BSRAM",    Theme.ORANGE)
        upd(self.rsrc_dsp, "DSP",      Theme.PURPLE)
        upd(self.rsrc_pin, "Pin",      Theme.PINK)

        # Detay panel
        self.rsrc_detail.delete("1.0", tk.END)
        self.rsrc_detail.insert(tk.END, f"📄 {p.name}\n\n", "hdr")
        for k, (u, t, pct) in rsrc.items():
            self.rsrc_detail.insert(tk.END, f"{k:12} ", "hdr")
            self.rsrc_detail.insert(tk.END, f"{u:>6}", "num")
            if t:
                self.rsrc_detail.insert(tk.END, f" / {t:>6}  ")
            else:
                self.rsrc_detail.insert(tk.END, "         ")
            self.rsrc_detail.insert(tk.END, f"{pct:>6.2f}%\n", "pct")
        if not rsrc:
            self.rsrc_detail.insert(tk.END,
                "Tanınan kaynak satırı bulunamadı.\n"
                "Bu GOWIN sürümünün rapor formatı farklı olabilir.\n"
                "Detaylı debug için raporu Notepad ile açın.", "")

        self.log(f"📊 Tablo 3.3 güncellendi: {len(rsrc)} kaynak okundu",
                 color=Theme.PURPLE)

    # ─── Export ──────────────────────────────────────────────────
    def export_metrics_csv(self):
        if not self._upload_rows:
            self.log("[!] Önce log'u yükleyin.", color=Theme.YELLOW); return
        p = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile="tablo_3_2_yukleme_sureleri.csv",
            filetypes=[("CSV", "*.csv")], parent=self.root)
        if not p: return
        with open(p, "w", encoding="utf-8") as f:
            f.write("Test Programı,Kod Boyutu (bayt),Paket Sayısı,"
                    "Teorik Süre (s),Ölçülen Süre (s),Retry,Etkin Hız (B/s)\n")
            for row in self._upload_rows:
                f.write(",".join(str(c) for c in row) + "\n")
        self.log(f"💾 CSV: {p}", color=Theme.GREEN)

    def copy_metrics_markdown(self):
        if not self._upload_rows:
            self.log("[!] Önce log'u yükleyin.", color=Theme.YELLOW); return
        md = "| Test Programı | Boyut (B) | Paket | Teorik (s) | Ölçülen (s) | Retry | Etkin (B/s) |\n"
        md += "|---|---:|---:|---:|---:|---:|---:|\n"
        for row in self._upload_rows:
            md += "| " + " | ".join(str(c) for c in row) + " |\n"

        if self._rsrc_data:
            md += "\n\n## Tablo 3.3 — FPGA Kaynak Tüketimi\n\n"
            md += "| Kaynak | Kullanılan | Toplam | Yüzde |\n|---|---:|---:|---:|\n"
            for k, (u, t, pct) in self._rsrc_data.items():
                md += f"| {k} | {u} | {t or '—'} | {pct:.2f}% |\n"

        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(md)
            self.log("📝 Markdown panoya kopyalandı (Ctrl+V ile yapıştır)",
                     color=Theme.ORANGE)
        except Exception as e:
            self.log(f"[X] Pano: {e}", color=Theme.RED)

    # ─────────────────────────────────────────────────────────────
    # Status bar
    # ─────────────────────────────────────────────────────────────
    def _build_statusbar(self):
        sb = tk.Frame(self.root, bg=Theme.BG_ALT, height=26)
        sb.pack(fill=tk.X, side=tk.BOTTOM)
        sb.pack_propagate(False)
        self.status = tk.Label(sb, text="● Hazır",
                                font=("Segoe UI", 8), bg=Theme.BG_ALT, fg=Theme.GREEN, padx=12)
        self.status.pack(side=tk.LEFT)

        # Acil busy reset
        btn = tk.Button(sb, text="🔓 busy kilidini sıfırla",
                        command=self._force_unbusy,
                        bg=Theme.BG_ALT, fg=Theme.YELLOW, borderwidth=0,
                        activebackground=Theme.SURFACE, activeforeground=Theme.YELLOW,
                        font=("Segoe UI", 8), cursor="hand2")
        btn.pack(side=tk.LEFT, padx=8)

        tk.Label(sb, text=f"Python {sys.version.split()[0]}  ·  pyserial: {'OK' if SERIAL_OK else 'YOK'}",
                 font=("Segoe UI", 8), bg=Theme.BG_ALT, fg=Theme.TEXT_DIM, padx=12
                 ).pack(side=tk.RIGHT)

    def _force_unbusy(self):
        self.busy = False
        self.log("🔓 busy=False olarak zorlandı.", color=Theme.YELLOW)
        self.set_status("Hazır (zorlandı)", Theme.YELLOW)

    def _update_pipeline_status(self):
        """Pipeline seridindeki .asm / .o / .mem bilgilerini guncelle."""
        try:
            asm = self.asm_path.get().strip()
            obj = getattr(self, "last_obj", None)
            mem = getattr(self, "last_mem", None) or self.fw_path.get().strip()
            ts  = getattr(self, "_latest_ts", "")

            self.pipe_asm_lbl.configure(
                text=f"📜 .asm: {Path(asm).name if asm else '—'}")
            self.pipe_obj_lbl.configure(
                text=f"📦 .o: {Path(obj).name if obj else '—'}")
            self.pipe_mem_lbl.configure(
                text=f"💾 .mem: {Path(mem).name if mem else '—'}")
            if ts:
                # YYYYMMDD_HHMMSS -> HH:MM:SS
                hh = ts[9:11] if len(ts) >= 11 else ts
                mm = ts[11:13] if len(ts) >= 13 else ""
                ss = ts[13:15] if len(ts) >= 15 else ""
                self.pipe_ts_lbl.configure(text=f"⏱ {hh}:{mm}:{ss}")
            else:
                self.pipe_ts_lbl.configure(text="")
        except Exception:
            pass

    def _on_tab_change(self, event=None):
        try:
            name = self.nb.tab(self.nb.select(), "text").strip()
            self.log(f"⇄ Sekme: {name}", color=Theme.TEAL)
        except Exception:
            pass

    def _open_log_dir(self):
        d = ROOT / "picorv_ide" / "logs"
        d.mkdir(exist_ok=True)
        try:
            os.startfile(str(d))  # Windows
        except Exception:
            self.log(f"Log klasoru: {d}", color=Theme.BLUE)

    # ─────────────────────────────────────────────────────────────
    # UI yardımcıları
    # ─────────────────────────────────────────────────────────────
    def _mk_tab(self, label):
        f = tk.Frame(self.nb, bg=Theme.BG, padx=14, pady=10)
        self.nb.add(f, text=" " + label + " ")
        return f

    def _mk_card(self, parent, title):
        wrap = tk.Frame(parent, bg=Theme.BG); wrap.pack(fill=tk.X, pady=6)
        tk.Label(wrap, text=title, font=("Segoe UI", 8, "bold"),
                 bg=Theme.BG, fg=Theme.TEXT_DIM).pack(anchor="w", pady=(0, 4))
        card = tk.Frame(wrap, bg=Theme.SURFACE, padx=14, pady=12)
        card.pack(fill=tk.X)
        return card

    def _mk_btn(self, parent, text, cmd, bg, fg, hover=None, font=("Segoe UI", 9, "bold"),
                padx=14, pady=8):
        # Tüm butonlar tıklandığında: (a) görsel "press" flash, (b) log mesajı,
        # (c) komut çalıştır. Etkileşim her seferinde ekranda + log dosyasında
        # iz birakir.
        def wrapped():
            # Görsel flash
            try:
                orig = b.cget("bg")
                b.configure(bg=Theme.SURFACE_HI, relief=tk.SUNKEN)
                b.update_idletasks()
                self.root.after(80, lambda: b.configure(bg=orig, relief=tk.FLAT))
            except Exception:
                pass
            # Log
            label = (text or "").strip().replace("\n", " ")
            self.log(f"▶ [{label}] tiklandi", color=Theme.PINK)
            # Komut
            try:
                if cmd: cmd()
            except Exception as e:
                self.log(f"[X] EXCEPTION in '{label}': {e!r}", color=Theme.RED)

        b = tk.Button(parent, text=text, command=wrapped, bg=bg, fg=fg, font=font,
                      borderwidth=0, padx=padx, pady=pady, cursor="hand2",
                      activebackground=hover or bg, activeforeground=fg,
                      relief=tk.FLAT)
        if hover:
            b.bind("<Enter>", lambda e: b.configure(bg=hover))
            b.bind("<Leave>", lambda e: b.configure(bg=bg))
        return b

    # ─────────────────────────────────────────────────────────────
    # Konsola yaz
    # ─────────────────────────────────────────────────────────────
    def log(self, msg, color=None):
        ts = time.strftime("%H:%M:%S")
        # Terminal prompt: yesil "►"
        self.log_w.insert(tk.END, "  ► ", Theme.GREEN)
        self.log_w.insert(tk.END, f"{ts}  ", Theme.TEXT_DIM)
        # Başlık satırı (─, ━, ▶ ile başlayan) bold + renk
        tags = (color,) if color else ()
        if msg.startswith("─") or msg.startswith("━") or msg.startswith("▶"):
            tags = tags + ("bold",)
        self.log_w.insert(tk.END, msg + "\n", tags)

        self._log_lines += 1
        if getattr(self, "log_count_lbl", None):
            self.log_count_lbl.configure(text=f"·  {self._log_lines} satır")

        if getattr(self, "autoscroll_var", None) is None or self.autoscroll_var.get():
            self.log_w.see(tk.END)
        try:
            self.root.update_idletasks()
        except Exception:
            pass

        # Diske kalıcı yaz
        if getattr(self, "log_fp", None):
            try:
                self.log_fp.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
                self.log_fp.flush()
            except Exception:
                pass

    def _clear_log(self):
        self.log_w.delete("1.0", tk.END)
        self._log_lines = 0
        self.log_count_lbl.configure(text="·  0 satır")
        self.log("Konsol temizlendi.", color=Theme.TEXT_DIM)

    def _clean_build_dir(self):
        """build/ klasöründeki .o ve .mem dosyalarını sil (zaman damgalı geçmiş)."""
        bd = self.project_root / "build"
        if not bd.exists(): return
        n = 0
        for f in bd.glob("*.o"):
            try: f.unlink(); n += 1
            except: pass
        for f in bd.glob("*.mem"):
            try: f.unlink(); n += 1
            except: pass
        self.log(f"🧹 build/ temizlendi: {n} dosya silindi", color=Theme.ORANGE)
        self.refresh_project_tree()
        self._refresh_fw_quick()

    def set_status(self, txt, color=Theme.GREEN):
        self.status.configure(text="● " + txt, fg=color)

    # ─────────────────────────────────────────────────────────────
    # Proje işlemleri
    # ─────────────────────────────────────────────────────────────
    def change_project(self):
        d = filedialog.askdirectory(initialdir=str(self.project_root),
                                     title="Proje kökünü seç")
        if d:
            self.project_root = Path(d)
            self.cfg["project_root"] = str(self.project_root)
            save_cfg(self.cfg)
            self.proj_lbl.configure(text=f"📁 {self.project_root.name}")
            self.refresh_project_tree()
            self.asm_outdir.set(str(self.project_root / "build"))
            self.mem_path.set(str(self.project_root / "build" / "firmware.mem"))
            self._refresh_asm_quick()
            self._refresh_fw_quick()
            self.log(f"Proje değişti: {self.project_root}", color=Theme.YELLOW)

    def refresh_project_tree(self):
        self.tree.delete(*self.tree.get_children())
        roots = [
            ("📂 sistem_proglamlama_proje_3", self.project_root, ".asm,.c,.mem,.o,.h,.py,.md,.ps1"),
            ("🧪 tests",                       self.tests_root,   ".asm"),
            ("🔌 host_app",                    ROOT / "host_app", ".py"),
            ("⚡ gowin_program",               ROOT / "gowin_program", ".v,.cst,.gprj"),
        ]
        for label, path, exts in roots:
            if not path.exists(): continue
            allowed = set(exts.split(","))
            self._tree_add(label, path, allowed, parent="")

    def _tree_add(self, label, path: Path, exts, parent=""):
        node = self.tree.insert(parent, "end", text=label, open=(parent == ""), values=(str(path),))
        try:
            items = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except Exception:
            return
        for p in items:
            if p.name.startswith(".") or p.name in {"__pycache__", "impl"}: continue
            if p.is_dir():
                self._tree_add("📁 " + p.name, p, exts, node)
            elif p.suffix in exts or "*" in exts:
                icon = {"asm": "📜", "v": "⚡", "c": "🔧", "mem": "💾",
                        "o": "📦", "py": "🐍", "md": "📘", "ps1": "🟦",
                        "cst": "📌", "gprj": "🎯"}.get(p.suffix.lstrip("."), "📄")
                self.tree.insert(node, "end", text=f"{icon} {p.name}", values=(str(p),))

    def on_tree_dbl(self, event):
        sel = self.tree.selection()
        if not sel: return
        path = self.tree.item(sel[0], "values")
        if not path: return
        p = Path(path[0])
        if not p.is_file(): return
        self.log(f"📂 ağaçtan açıldı: {p.name}", color=Theme.TEAL)
        if p.suffix == ".asm":
            self.asm_path.set(str(p))
            self.nb.select(0)
            self._show_asm_preview(p)
        elif p.suffix == ".o":
            self.obj_list.insert(tk.END, str(p))
            self.nb.select(1)
        elif p.suffix == ".mem":
            self.fw_path.set(str(p))
            self.insp_path.set(str(p))
            self.nb.select(2)

    # ─────────────────────────────────────────────────────────────
    # Hızlı dosya butonları
    # ─────────────────────────────────────────────────────────────
    def _refresh_asm_quick(self):
        for w in self.asm_quick_box.winfo_children(): w.destroy()
        search_dirs = [self.tests_root, self.project_root / "asm"]
        files = []
        for d in search_dirs:
            if d.exists():
                files.extend(sorted(d.glob("*.asm")))
        for f in files[:8]:
            self._mk_btn(self.asm_quick_box, f.stem,
                         lambda p=f: (self.asm_path.set(str(p)), self._show_asm_preview(p)),
                         bg=Theme.BG_ALT, fg=Theme.BLUE,
                         hover=Theme.SURFACE_HI, font=("Consolas", 8),
                         padx=8, pady=4).pack(side=tk.LEFT, padx=2)

    def _refresh_fw_quick(self):
        if not hasattr(self, "fw_quick_box"): return
        for w in self.fw_quick_box.winfo_children(): w.destroy()
        bd = self.project_root / "build"
        if not bd.exists(): return
        for f in sorted(bd.glob("*.mem"))[:8]:
            self._mk_btn(self.fw_quick_box, f.stem,
                         lambda p=f: self.fw_path.set(str(p)),
                         bg=Theme.BG_ALT, fg=Theme.GREEN,
                         hover=Theme.SURFACE_HI, font=("Consolas", 8),
                         padx=8, pady=4).pack(side=tk.LEFT, padx=2)

    # ─────────────────────────────────────────────────────────────
    # ASM ÖNİZLEME (basit sözdizimi renklendirme)
    # ─────────────────────────────────────────────────────────────
    KW = {"add","sub","sll","xor","srl","sra","or","and",
          "addi","xori","ori","andi","slli","srli","srai","slti",
          "lb","lh","lw","sb","sh","sw",
          "beq","bne","blt","bge","jal","jalr","lui","auipc",
          ".text",".data",".globl",".word",".byte"}

    def _show_asm_preview(self, path: Path):
        try:
            txt = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            self.log(f"Önizleme okunamadı: {e}", color=Theme.RED)
            return
        self.asm_preview.delete("1.0", tk.END)
        for line in txt.splitlines():
            self._color_line(line)

    def _color_line(self, line):
        i = 0
        # yorum
        if "#" in line:
            cidx = line.find("#")
            head, comment = line[:cidx], line[cidx:]
        else:
            head, comment = line, ""
        # label
        m = re.match(r"^(\s*)([A-Za-z_]\w*)\s*:", head)
        if m:
            self.asm_preview.insert(tk.END, m.group(1))
            self.asm_preview.insert(tk.END, m.group(2) + ":", "lbl")
            head = head[m.end():]
        # tokenler
        for tok in re.split(r"(\s+|,|\(|\))", head):
            if not tok: continue
            low = tok.strip().lower()
            if low in self.KW:
                self.asm_preview.insert(tk.END, tok, "kw")
            elif re.fullmatch(r"x([0-9]|[12][0-9]|3[01])", low) or low in {
                "zero","ra","sp","gp","tp","fp",
                "a0","a1","a2","a3","a4","a5","a6","a7",
                "t0","t1","t2","t3","t4","t5","t6",
                "s0","s1","s2","s3","s4","s5","s6","s7","s8","s9","s10","s11"}:
                self.asm_preview.insert(tk.END, tok, "reg")
            elif re.fullmatch(r"-?(0x[0-9a-fA-F]+|0b[01]+|\d+)", low):
                self.asm_preview.insert(tk.END, tok, "num")
            else:
                self.asm_preview.insert(tk.END, tok)
        if comment:
            self.asm_preview.insert(tk.END, comment, "cmt")
        self.asm_preview.insert(tk.END, "\n")

    # ─────────────────────────────────────────────────────────────
    # ASSEMBLER aksiyonları
    # ─────────────────────────────────────────────────────────────
    def pick_asm(self):
        p = filedialog.askopenfilename(
            initialdir=str(self.tests_root if self.tests_root.exists() else self.project_root),
            filetypes=[("Assembly", "*.asm"), ("Tümü", "*.*")])
        if p:
            self.asm_path.set(p)
            self._show_asm_preview(Path(p))
            self.log(f"📜 .asm seçildi: {Path(p).name}", color=Theme.BLUE)
            self._update_pipeline_status()

    def quick_assemble(self):
        self.log("─ ASSEMBLE isteği alındı ─", color=Theme.BLUE)
        if self.busy:
            self.log("[!] Başka bir işlem sürüyor (busy=True).", color=Theme.YELLOW)
            return
        asm = self.asm_path.get().strip()
        if not asm or not Path(asm).exists():
            self.log(f"[X] Geçerli .asm yok: '{asm}'", color=Theme.RED)
            messagebox.showwarning("Dosya yok",
                "Önce bir .asm dosyası seç (sol ağaçtan çift tıkla veya 📄 .asm seç).",
                parent=self.root)
            return
        outdir = Path(self.asm_outdir.get()); outdir.mkdir(parents=True, exist_ok=True)
        # Zaman damgalı benzersiz isim: <stem>__YYYYMMDD_HHMMSS.o
        stem = Path(asm).stem
        ts   = time.strftime("%Y%m%d_%H%M%S")
        obj  = outdir / f"{stem}__{ts}.o"
        # Pipeline state — link/load adımları için tutulur
        self._latest_obj_stem = stem
        self._latest_ts       = ts
        # C assembler oncelikli (kullanici tercihi); WDAC engellerse Python fallback
        asm_exe = self.project_root / "toolchain" / "bin" / "assembler.exe"
        asm_py  = self.project_root / "toolchain" / "py" / "asm.py"
        if asm_exe.exists():
            cmd = [str(asm_exe), asm, str(obj)]
            self.log(f"⚙  assembler.exe {Path(asm).name} → {obj.name}", color=Theme.BLUE)
        elif asm_py.exists():
            cmd = [sys.executable, str(asm_py), asm, str(obj)]
            self.log(f"⚙  python asm.py {Path(asm).name} → {obj.name}", color=Theme.BLUE)
        else:
            self.log(f"[X] Ne assembler.exe ne asm.py bulundu", color=Theme.RED)
            self.log("    .\\build.ps1 -Tool veya toolchain/py/asm.py kontrol et",
                     color=Theme.YELLOW); return
        self.set_status("Assemble ediliyor…", Theme.BLUE)
        self._update_pipeline_status()
        threading.Thread(target=self._run_assemble, args=(cmd, asm, obj), daemon=True).start()

    def _run_assemble(self, cmd, asm, obj):
        self.busy = True
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20,
                                encoding="utf-8", errors="replace")
            for line in (r.stdout or "").splitlines():
                if line.strip(): self.log("  " + line, color=Theme.TEXT_DIM)
            for line in (r.stderr or "").splitlines():
                if line.strip(): self.log("  [stderr] " + line, color=Theme.RED)
            self.log(f"  rc={r.returncode}", color=Theme.TEXT_DIM)
            if r.returncode == 0 and obj.exists():
                self.last_obj = obj
                self.log(f"[+] OK: {obj.name}", color=Theme.GREEN)
                self.root.after(0, lambda: self._add_to_obj_list(obj))
                # Pipeline: Linker'in mem_path'ini otomatik olarak ayni timestamp ile guncelle
                next_mem = obj.parent / (obj.stem + ".mem")
                self.root.after(0, lambda: self.mem_path.set(str(next_mem)))
                self.set_status("Assemble OK", Theme.GREEN)
                self.root.after(0, self._update_pipeline_status)
            else:
                self.log(f"[X] Assembler hatasi (rc={r.returncode}, obj_exists={obj.exists()})",
                         color=Theme.RED)
                self.set_status("Hata", Theme.RED)
        except Exception as e:
            self.log(f"[X] EXCEPTION assemble: {e!r}", color=Theme.RED)
        finally:
            self.busy = False

    def _add_to_obj_list(self, p: Path):
        items = self.obj_list.get(0, tk.END)
        if str(p) in items: return
        self.obj_list.insert(tk.END, str(p))

    # ─────────────────────────────────────────────────────────────
    # LINKER aksiyonları
    # ─────────────────────────────────────────────────────────────
    def add_obj_files(self):
        files = filedialog.askopenfilenames(
            initialdir=str(self.project_root / "build"),
            filetypes=[("Object", "*.o")])
        for f in files:
            if f not in self.obj_list.get(0, tk.END):
                self.obj_list.insert(tk.END, f)

    def clear_obj_files(self):
        self.obj_list.delete(0, tk.END)

    def _auto_mem_name(self):
        """Zaman damgalı benzersiz .mem yolu üret."""
        stem = getattr(self, "_latest_obj_stem", None) or "firmware"
        ts   = getattr(self, "_latest_ts", None) or time.strftime("%Y%m%d_%H%M%S")
        return self.project_root / "build" / f"{stem}__{ts}.mem"

    def quick_link(self):
        self.log("─ LINK isteği alındı ─", color=Theme.ORANGE)
        # Eğer mem_path "firmware.mem" gibi default ise, otomatik benzersiz isim ver
        cur = (self.mem_path.get() or "").strip()
        if (not cur) or cur.endswith("firmware.mem") or "__" not in Path(cur).stem:
            new = self._auto_mem_name()
            self.mem_path.set(str(new))
            self.log(f"  Çıktı dosyası otomatik isimlendirildi → {new.name}",
                     color=Theme.TEXT_DIM)
        if self.busy:
            self.log("[!] Başka bir işlem sürüyor (busy=True). Bekleyin veya 'busy' kilidini sıfırlayın.",
                     color=Theme.YELLOW)
            return

        # 1) Object dosyalarını topla — Listbox boşsa otomatik keşfet
        objs = list(self.obj_list.get(0, tk.END))
        if not objs:
            self.log("Listbox boş, otomatik .o keşfi yapılıyor…", color=Theme.TEXT_DIM)
            # a) last_obj varsa
            if self.last_obj and Path(self.last_obj).exists():
                objs = [str(self.last_obj)]
                self.log(f"  ➜ son üretilen: {self.last_obj}", color=Theme.TEXT_DIM)
            else:
                # b) build/ klasöründen tüm .o dosyalarını çek
                build_dir = self.project_root / "build"
                found = sorted(build_dir.glob("*.o")) if build_dir.exists() else []
                if found:
                    objs = [str(p) for p in found]
                    for p in found:
                        self.log(f"  ➜ {p.name}", color=Theme.TEXT_DIM)
                else:
                    self.log(f"[X] {build_dir}\\*.o yok. Önce ASSEMBLE yap.", color=Theme.RED)
                    messagebox.showwarning("Object dosyası yok",
                        f"{build_dir} klasöründe .o yok.\n\n"
                        "Önce Assembler sekmesinden bir .asm dosyasını derle, "
                        "sonra Link et.", parent=self.root)
                    return
            # bulduklarımızı listbox'a da ekle
            self.obj_list.delete(0, tk.END)
            for o in objs: self.obj_list.insert(tk.END, o)

        # 2) Çıktı yolu
        mem_str = self.mem_path.get().strip()
        if not mem_str:
            mem_str = str(self.project_root / "build" / "firmware.mem")
            self.mem_path.set(mem_str)
        out = Path(mem_str)
        out.parent.mkdir(parents=True, exist_ok=True)

        # 3) Linker: C exe oncelikli, Python fallback
        link_exe = self.project_root / "toolchain" / "bin" / "linker.exe"
        link_py = self.project_root / "toolchain" / "py" / "link.py"
        if link_exe.exists():
            base_cmd = [str(link_exe)]
            tool_label = "linker.exe"
        elif link_py.exists():
            base_cmd = [sys.executable, str(link_py)]
            tool_label = "python link.py"
        else:
            self.log(f"[X] Linker bulunamadi: ne link.py ne linker.exe", color=Theme.RED)
            messagebox.showerror("Linker yok",
                "toolchain/py/link.py veya toolchain/bin/linker.exe bulunamadi.",
                parent=self.root)
            return

        # 4) Komutu kur ve çalıştır
        cmd = base_cmd + [
               "-Ttext", self.ttext.get().strip() or "0x0",
               "-Tdata", self.tdata.get().strip() or "0x1000",
               "-o", str(out), *objs]
        self.set_status("Linkleniyor…", Theme.ORANGE)
        self.log(f"🔗  {tool_label} → {out.name}", color=Theme.ORANGE)
        self.log(f"   Cikti yolu: {out}", color=Theme.TEXT_DIM)
        threading.Thread(target=self._run_link, args=(cmd, out), daemon=True).start()

    def _run_link(self, cmd, out):
        self.busy = True
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=20,
                                encoding="utf-8", errors="replace")
            for line in (r.stdout or "").splitlines():
                if line.strip(): self.log("  " + line, color=Theme.TEXT_DIM)
            for line in (r.stderr or "").splitlines():
                if line.strip(): self.log("  [stderr] " + line, color=Theme.RED)
            self.log(f"  rc={r.returncode}", color=Theme.TEXT_DIM)
            # Ham çıktıyı linker tabındaki text widget'a yaz (renklendirerek)
            self.linker_raw.delete("1.0", tk.END)
            for line in r.stdout.splitlines():
                if line.startswith("---") or "ESTAB" in line or "Pass" in line:
                    self.linker_raw.insert(tk.END, line + "\n", "hdr")
                elif "tamamlandi" in line or "Cikti" in line:
                    self.linker_raw.insert(tk.END, line + "\n", "ok")
                elif "0x" in line:
                    self.linker_raw.insert(tk.END, line + "\n", "addr")
                else:
                    self.linker_raw.insert(tk.END, line + "\n")
            self._parse_estab(r.stdout)
            if out.exists():
                self.last_mem = out
                self.fw_path.set(str(out))
                self.insp_path.set(str(out))
                self.log(f"[+] OK: {out.name}", color=Theme.GREEN)
                self.set_status("Link OK", Theme.GREEN)
                self.root.after(0, self._refresh_fw_quick)
                self.root.after(0, self._update_pipeline_status)
            else:
                self.log("[X] .mem üretilmedi", color=Theme.RED)
                self.set_status("Hata", Theme.RED)
        except Exception as e:
            self.log(f"[X] {e}", color=Theme.RED)
        finally:
            self.busy = False

    def _parse_estab(self, text):
        for i in self.estab.get_children(): self.estab.delete(i)
        rows = 0
        section = "?"
        # Section ipuçlari: "object dosyasi", ".text base", ".data base"
        cur_obj = "—"
        cur_section = "—"
        for raw in text.splitlines():
            line = raw.strip()
            # Object adi (linker "xxx.o:" satırı basabiliyor)
            mobj = re.match(r"^(.+\.o):\s*$", line)
            if mobj:
                cur_obj = Path(mobj.group(1)).name
                continue
            # .text / .data base
            mb = re.match(r"^\.(text|data)\s*base\s*=\s*(0x[0-9a-fA-F]+)", line)
            if mb:
                cur_section = "." + mb.group(1)
                self.estab.insert("", tk.END,
                    values=(f"<{cur_obj} {cur_section} base>", mb.group(2), "object", cur_section))
                rows += 1
                continue
            # Symbol -> 0xADDR
            m = re.search(r"([A-Za-z_]\w*)\s*->\s*(0x[0-9a-fA-F]+)", line)
            if m:
                self.estab.insert("", tk.END,
                    values=(m.group(1), m.group(2), "global", cur_section))
                rows += 1
        if rows == 0:
            # Hic eslesme yoksa ham cikti dump et (debug)
            for line in text.splitlines():
                if line.strip():
                    self.estab.insert("", tk.END, values=(line.strip()[:60], "", "", ""))
        self.log(f"   ESTAB tabloya {rows} satir aktarildi", color=Theme.TEXT_DIM)

    # ─────────────────────────────────────────────────────────────
    # LOADER aksiyonları
    # ─────────────────────────────────────────────────────────────
    def refresh_ports(self):
        if not SERIAL_OK:
            self.port_cb["values"] = []; return
        ports = [p.device for p in list_ports.comports()]
        self.port_cb["values"] = ports
        if not self.port_var.get() and ports:
            self.port_var.set(ports[-1])
        self.log(f"COM portları: {', '.join(ports) if ports else 'yok'}", color=Theme.TEXT_DIM)

    def pick_fw(self):
        p = filedialog.askopenfilename(
            initialdir=str(self.project_root / "build"),
            filetypes=[("Firmware", "*.mem *.hex *.bin"), ("Tümü", "*.*")])
        if p:
            self.fw_path.set(p)
            self.log(f"💾 firmware seçildi: {Path(p).name}", color=Theme.GREEN)

    def quick_load(self):
        self.log("─ LOAD isteği alındı ─", color=Theme.GREEN)
        if self.busy:
            self.log("[!] Başka bir işlem sürüyor (busy=True).", color=Theme.YELLOW)
            return
        if not SERIAL_OK:
            messagebox.showerror("pyserial yok",
                                  "pip install pyserial komutu ile kur."); return
        port = self.port_var.get().strip()
        if not port:
            messagebox.showwarning("Port", "COM port seç."); return
        path = self.fw_path.get().strip()
        if not path:
            if self.last_mem and Path(self.last_mem).exists():
                path = str(self.last_mem); self.fw_path.set(path)
            else:
                messagebox.showwarning("Firmware", "Bir .mem dosyası seç."); return
        try:
            baud = int(self.baud_var.get())
        except ValueError:
            messagebox.showerror("Baud", "Geçersiz baud."); return

        self.cfg["port"] = port; self.cfg["baud"] = baud; save_cfg(self.cfg)
        self.pb["value"] = 0
        self.stat_pkt.configure(text="0/0"); self.stat_retry.configure(text="0")
        self.stat_bytes.configure(text="0");  self.stat_time.configure(text="0s")
        self.stat_state.configure(text="bağlanıyor…")
        self.set_status("Yükleme başladı…", Theme.GREEN)
        threading.Thread(target=self._run_load, args=(port, baud, path), daemon=True).start()

    def _run_load(self, port, baud, path):
        self.busy = True
        t0 = time.time()
        try:
            data = load_firmware(path)
            total_pkts = (len(data) + 127) // 128
            self.stat_bytes.configure(text=f"{len(data)} B")
            self.stat_pkt.configure(text=f"0/{total_pkts}")
            self.log(f"📡  {Path(path).name}  ·  {len(data)} bayt  ·  {total_pkts} paket",
                      color=Theme.GREEN)
            s = XmodemSender(port, baud, log=lambda m: self.log(m, color=Theme.TEXT_DIM))
            self.stat_state.configure(text="'C' bekleniyor…")

            def on_prog(done, total):
                self.pb["maximum"] = total
                self.pb["value"]   = done
                self.stat_pkt.configure(text=f"{done}/{total}")
                self.stat_time.configure(text=f"{time.time()-t0:.1f}s")
                self.stat_state.configure(text="aktarım…")

            ok, st = s.send(data, on_progress=on_prog)
            s.close()
            self.stat_retry.configure(text=str(st.get("retries", 0)))
            self.stat_time.configure(text=f"{st.get('elapsed', time.time()-t0):.2f}s")
            if ok:
                self.stat_state.configure(text="✓ tamam", fg=Theme.GREEN)
                self.log("─" * 50, color=Theme.TEXT_DIM)
                self.log(f"✅ BAŞARILI · paket={st['packets']} retry={st['retries']} "
                         f"süre={st.get('elapsed', 0):.2f}s", color=Theme.GREEN)
                self.set_status("Yükleme OK", Theme.GREEN)
                self.root.after(0, self._update_pipeline_status)
                # Rapor sekmesi varsa otomatik yenile (yeni yukleme satiri eklensin)
                if hasattr(self, "upload_tree"):
                    self.root.after(300, self.refresh_upload_metrics)
            else:
                self.stat_state.configure(text="✗ hata", fg=Theme.RED)
                self.log("❌ HATA", color=Theme.RED)
                self.set_status("Yükleme HATA", Theme.RED)
        except Exception as e:
            self.log(f"[X] {e}", color=Theme.RED)
            self.set_status("Hata", Theme.RED)
        finally:
            self.busy = False

    # ─────────────────────────────────────────────────────────────
    # Pipeline (RUN ALL)
    # ─────────────────────────────────────────────────────────────
    def run_pipeline(self):
        if self.busy: return
        if not self.asm_path.get():
            messagebox.showwarning("Eksik", "Önce bir .asm dosyası seç."); return
        threading.Thread(target=self._run_pipeline_seq, daemon=True).start()

    def _run_pipeline_seq(self):
        self.log("━" * 50, color=Theme.PURPLE)
        self.log("▶  PIPELINE BAŞLATILDI: assemble → link → load", color=Theme.PURPLE)
        self.log("━" * 50, color=Theme.PURPLE)
        # 1
        self.quick_assemble()
        while self.busy: time.sleep(0.1)
        if not self.last_obj: return
        # 2
        self.obj_list.delete(0, tk.END)
        self.obj_list.insert(tk.END, str(self.last_obj))
        # otomatik .mem ismi: asm_dosya_adı.mem
        mem = self.project_root / "build" / (Path(self.asm_path.get()).stem + ".mem")
        self.mem_path.set(str(mem))
        self.quick_link()
        while self.busy: time.sleep(0.1)
        if not self.last_mem: return
        # 3 - kullanıcı reset basmış olmalı; uyar
        self.log("⚠  Tang Nano 9K'da S1 (reset) butonuna basın → ENTER ile devam",
                  color=Theme.YELLOW)
        time.sleep(2)  # kısa nefes
        self.quick_load()

    # ─────────────────────────────────────────────────────────────
    # .mem inceleme + disassembly
    # ─────────────────────────────────────────────────────────────
    def pick_inspect(self):
        p = filedialog.askopenfilename(
            initialdir=str(self.project_root / "build"),
            filetypes=[("Firmware", "*.mem *.hex"), ("Tümü", "*.*")])
        if p:
            self.insp_path.set(p)
            self.do_inspect()

    def do_inspect(self):
        p = self.insp_path.get().strip()
        if not p or not Path(p).exists(): return
        words = []
        for line in Path(p).read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.split("//")[0].strip()
            if not line or line.startswith("@"): continue
            for tok in line.split():
                if re.fullmatch(r"[0-9a-fA-F]{8}", tok):
                    words.append(int(tok, 16))
        # Hex
        self.hex_w.delete("1.0", tk.END)
        for i, w in enumerate(words):
            self.hex_w.insert(tk.END, f"0x{i*4:08X}    0x{w:08X}\n")
        # Disasm
        self.dis_w.delete("1.0", tk.END)
        for i, w in enumerate(words):
            self.dis_w.insert(tk.END, f"0x{i*4:08X}    {disassemble(w)}\n")
        self.log(f"🔍 {len(words)} kelime ({len(words)*4} bayt) incelendi", color=Theme.PURPLE)


# ─────────────────────────────────────────────────────────────────────────────
# Mini RV32I disassembler (raporlama için)
# ─────────────────────────────────────────────────────────────────────────────
ABI_NAMES = ["zero","ra","sp","gp","tp","t0","t1","t2",
             "s0","s1","a0","a1","a2","a3","a4","a5",
             "a6","a7","s2","s3","s4","s5","s6","s7",
             "s8","s9","s10","s11","t3","t4","t5","t6"]

def _r(n): return ABI_NAMES[n & 0x1F]

def disassemble(w: int) -> str:
    op = w & 0x7F
    rd = (w >> 7) & 0x1F
    f3 = (w >> 12) & 0x7
    rs1 = (w >> 15) & 0x1F
    rs2 = (w >> 20) & 0x1F
    f7 = (w >> 25) & 0x7F
    imm_i = (w >> 20)
    if imm_i & 0x800: imm_i |= ~0xFFF
    imm_s = ((w >> 25) << 5) | ((w >> 7) & 0x1F)
    if imm_s & 0x800: imm_s |= ~0xFFF
    imm_b = (((w >> 31) & 1) << 12) | (((w >> 7) & 1) << 11) | \
            (((w >> 25) & 0x3F) << 5) | (((w >> 8) & 0xF) << 1)
    if imm_b & 0x1000: imm_b |= ~0x1FFF
    imm_u = w & 0xFFFFF000
    imm_j = (((w >> 31) & 1) << 20) | (((w >> 12) & 0xFF) << 12) | \
            (((w >> 20) & 1) << 11) | (((w >> 21) & 0x3FF) << 1)
    if imm_j & 0x100000: imm_j |= ~0x1FFFFF

    if op == 0x33:
        mn = {0:"add" if f7==0 else "sub", 1:"sll", 4:"xor", 5:"srl" if f7==0 else "sra",
              6:"or", 7:"and"}.get(f3, "?")
        return f"{mn:6} {_r(rd)}, {_r(rs1)}, {_r(rs2)}"
    if op == 0x13:
        mn = {0:"addi", 4:"xori", 6:"ori", 7:"andi", 2:"slti",
              1:"slli", 5:"srai" if f7==0x20 else "srli"}.get(f3, "?")
        if f3 in (1, 5):
            return f"{mn:6} {_r(rd)}, {_r(rs1)}, {imm_i & 0x1F}"
        return f"{mn:6} {_r(rd)}, {_r(rs1)}, {imm_i}"
    if op == 0x03:
        mn = {0:"lb", 1:"lh", 2:"lw"}.get(f3, "lx")
        return f"{mn:6} {_r(rd)}, {imm_i}({_r(rs1)})"
    if op == 0x23:
        mn = {0:"sb", 1:"sh", 2:"sw"}.get(f3, "sx")
        return f"{mn:6} {_r(rs2)}, {imm_s}({_r(rs1)})"
    if op == 0x63:
        mn = {0:"beq", 1:"bne", 4:"blt", 5:"bge"}.get(f3, "bx")
        return f"{mn:6} {_r(rs1)}, {_r(rs2)}, {imm_b:+}"
    if op == 0x37:
        return f"{'lui':6} {_r(rd)}, 0x{imm_u >> 12:05X}"
    if op == 0x17:
        return f"{'auipc':6} {_r(rd)}, 0x{imm_u >> 12:05X}"
    if op == 0x6F:
        return f"{'jal':6} {_r(rd)}, {imm_j:+}"
    if op == 0x67:
        return f"{'jalr':6} {_r(rd)}, {imm_i}({_r(rs1)})"
    if w == 0:
        return "nop  (00000000)"
    return f"???   0x{w:08X}"


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.15)
    except Exception:
        pass
    app = PicoRVIde(root)
    root.mainloop()
