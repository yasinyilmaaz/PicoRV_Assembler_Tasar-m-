# PicoRV32 FPGA UART Loader Sistemi

**BIL302 Sistem Programlama — Proje 3** · Sakarya Uygulamalı Bilimler Üniversitesi

PicoRV32 (RV32I) işlemci çekirdeği için **özgün assembler + linker araç zincirini**, Tang Nano 9K FPGA üzerinde çalışan **UART/XMODEM-CRC tabanlı donanımsal yükleyici (loader)** ile uçtan uca bütünleştiren co-design projesi.

---

## 🗂️ Klasör Yapısı

```
sunum3/
│
├── README.md                       ← Bu dosya
├── .gitignore
│
├── docs/                           ← 📚 Dokümantasyon
│   ├── SISTEM_RAPORU.pdf           ← 50 sayfalık teknik doküman
│   ├── generate_report.py          ← PDF üretici (ReportLab)
│   └── rapor_bolumleri/            ← Word'e yapıştırılabilir bölümler
│       ├── 01_genel_bolumler.md
│       ├── 02_bolum_3_2_metrikler.md
│       ├── 03_bolum_4_2_lisanslar.md
│       ├── 04_bireysel_beyanlar.md
│       ├── 05_kaynakca_ieee.md
│       ├── 06_eksikler_takip.md
│       └── 07_riscv_tests_karsilastirma.md
│
├── sistem_proglamlama_proje_3/     ← 🔧 PC TOOLCHAIN (C + Python)
│   ├── README.md
│   ├── build.ps1                   ← Tek komutla derleme
│   ├── toolchain/
│   │   ├── src/                    ← assembler.c, linker.c
│   │   ├── bin/                    ← assembler.exe, linker.exe
│   │   └── py/                     ← asm.py, link.py (WDAC-safe fallback)
│   └── build/                      ← Üretilen .o ve .mem (gitignored)
│
├── gowin_program/                  ← ⚡ FPGA PROJESİ (GOWIN EDA)
│   └── fpga_project/
│       ├── fpga_project.gprj
│       └── src/
│           ├── top.v, memory.v, picorv32.v
│           ├── loader_fsm.v, crc16.v
│           ├── uart_rx.v, uart_tx.v
│           └── pinler.cst
│
├── host_app/                       ← 📡 HOST LOADER
│   └── host_loader.py              ← XMODEM-CRC16 Python sender
│
├── picorv_ide/                     ← 🖥 BİRLEŞİK IDE
│   ├── main.py                     ← Tkinter arayüz
│   ├── README.md
│   └── logs/                       ← Oturum log'ları (gitignored)
│
└── tests/                          ← 🧪 ASSEMBLY TEST SENARYOLARI
    ├── STANDART_TESTLER.md
    ├── test0_basit.asm             ← LED tüm yanık
    ├── test4_button_blink.asm      ← S2 buton kontrolü
    ├── std_a_gauss_sum.asm         ← Patterson §2 Ex 2.10
    ├── std_b_bubble_sort.asm       ← Patterson §2.13
    ├── std_c_fib_recursive.asm     ← riscv-tests/towers
    └── std_d_memory_stress.asm     ← BRAM bant genişliği
```

---

## 🚀 Hızlı Başlangıç

### 1. Toolchain'i derle (bir kere)

```powershell
cd sistem_proglamlama_proje_3
.\build.ps1 -Tool
```

### 2. Bir test programını derle

```powershell
.\build.ps1 -Asm ..\tests\std_a_gauss_sum.asm
# Çıktı: build\std_a_gauss_sum.mem
```

### 3. FPGA'e yükle (GOWIN EDA + IDE)

```powershell
# Önce bitstream'i FPGA'e yaz (bir kere): GOWIN EDA → P&R → Programmer
# Sonra:
cd ..
python picorv_ide\main.py
# IDE'den .mem dosyasını seç, S1 reset, YÜKLE
```

---

## 📦 Ana Bileşenler

| Bileşen | Dil | Görev |
|---|---|---|
| **assembler.c** + **asm.py** | C + Python | RV32I .asm → .o derleme (iki geçişli) |
| **linker.c** + **link.py** | C + Python | .o → .mem (ESTAB, relocation) |
| **host_loader.py** | Python | UART üzerinden XMODEM-CRC ile firmware gönderme |
| **picorv_ide/main.py** | Python (Tkinter) | Tüm zincirin görsel arayüzü + canlı log + Rapor sekmesi |
| **top.v** | Verilog | PicoRV32 + memory + GPIO + loader entegrasyonu |
| **loader_fsm.v** | Verilog | 12-durumlu XMODEM-CRC FSM |
| **crc16.v** | Verilog | GF(2) LFSR (poly 0x1021) |
| **memory.v** | Verilog | 32 KB BRAM (4 × 8K × 8-bit, dual-source mux) |

---

## 🎯 Hedef Donanım

- **Sipeed Tang Nano 9K** (Gowin GW1NR-LV9 QN88PC6/I5)
- 27 MHz sistem saati
- 6 LED (aktif düşük, Pin 10-16)
- 2 buton (S1=reset, S2=user)
- USB-UART köprü (BL616, 115200 baud 8N1)

## ⚙️ Bellek Haritası

| Adres aralığı | Cihaz |
|---|---|
| `0x0000_0000 – 0x0000_7FFF` | BRAM (32 KB, kod + veri + stack) |
| `0x1000_0000` (W) | LED bank (bit[5:0]) |
| `0x1000_0010` (R) | Buton (bit[0]=S1, bit[1]=S2) |

---

## 📚 Belge ve Raporlar

Tüm doküman çalışması `docs/` klasöründedir:

- **`docs/SISTEM_RAPORU.pdf`** — 50 sayfalık teknik anatomi (modül başına detay)
- **`docs/rapor_bolumleri/`** — BIL302 raporuna doğrudan yapıştırılabilir Markdown bölümler

---

## 🔗 GitHub

```
https://github.com/yasinyilmaaz/PicoRV_Assembler_Tasar-m-
```

Branch'ler:
- **`main`** = en güncel hâl
- **`sunum3`** = bu proje
- **`sunum2`** = bir önceki proje (referans)
