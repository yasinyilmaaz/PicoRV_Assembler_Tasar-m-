# RISC-V Toolchain & PicoRV32 FPGA Loader

PicoRV32 (RV32I) alt kümesi için **assembler + linker + FPGA loader** zinciri.
Tang Nano 9K üzerinde UART/XMODEM-CRC ile firmware yükleme.

---

## 📁 Klasör Yapısı

```
sistem_proglamlama_proje_3/
│
├── README.md              ← Bu dosya
├── build.ps1              ← Tek komutla derleme/asm script'i
│
├── toolchain/             ← PC tarafı yazılım zinciri
│   ├── src/               ←   C kaynak kodları
│   │   ├── assembler.c    ←     RV32I -> .o (custom object)
│   │   └── linker.c       ←     .o + ESTAB -> .mem (firmware)
│   ├── bin/               ←   Derlenmiş .exe'ler
│   │   ├── assembler.exe
│   │   └── linker.exe
│   └── gui/               ←   Linker görsel arayüzü
│       └── arayuz.py
│
├── asm/                   ← Assembly kaynak dosyaları (.asm)
│   ├── led.asm
│   └── main.asm
│
├── build/                 ← Üretilen .o ve .mem dosyaları
│
├── hdl/                   ← FPGA tarafı Verilog (eski sürüm/yedek)
│   ├── top.v              ←   NOT: aktif geliştirme ../gowin_program/ altında
│   ├── memory.v
│   ├── picorv32.v
│   ├── pinler.cst
│   └── firmware.mem
│
├── docs/                  ← Rapor görselleri, diyagramlar
│   └── images/
│
└── tools/                 ← Yardımcı script'ler
    └── google_groups_scraper.py
```

Aktif FPGA projesi: `../gowin_program/fpga_project/`
Test assembly programları: `../tests/`
Host loader (Python): `../host_app/host_loader.py`

---

## 🚀 Hızlı Başlangıç

### 1) Toolchain'i derle (bir kere)
```powershell
.\build.ps1 -Tool
```

### 2) Tek bir .asm dosyasını .mem'e çevir
```powershell
.\build.ps1 -Asm asm\led.asm
# -> build\led.mem üretilir
```

### 3) Tüm .asm dosyalarını topluca derle
```powershell
.\build.ps1 -All
# asm\ ve ..\tests\ altındaki her .asm dosyasını işler
```

### 4) build/ klasörünü temizle
```powershell
.\build.ps1 -Clean
```

### Özel başlangıç adresleri
```powershell
.\build.ps1 -Asm asm\main.asm -Ttext 0x100 -Tdata 0x2000
```

---

## 🔧 Manuel Komutlar (script'siz)

```powershell
# Assembly  ->  Object
.\toolchain\bin\assembler.exe asm\led.asm build\led.o

# Object  ->  Firmware (.mem)
.\toolchain\bin\linker.exe -Ttext 0x0 -Tdata 0x1000 -o build\led.mem build\led.o

# Çoklu obje linkleme
.\toolchain\bin\linker.exe -Ttext 0x0 -Tdata 0x1000 `
    -o build\firmware.mem build\main.o build\utils.o
```

### Linker argümanları
| Argüman | Açıklama | Örnek |
|---|---|---|
| `-Ttext 0xADDR` | `.text` segmenti başlangıcı | `0x0` (PicoRV32 boot) |
| `-Tdata 0xADDR` | `.data` segmenti başlangıcı | `0x1000` |
| `-o file.mem` | Çıktı dosyası | `firmware.mem` |
| (pozisyonel) | Bir veya daha fazla `.o` | `main.o utils.o` |

---

## 🖥️ Linker GUI

```powershell
python toolchain\gui\arayuz.py
```

ESTAB (External Symbol Table) ve üretilen firmware'i görsel olarak gösterir.

---

## 📡 FPGA'e Gönderim (uçtan uca)

```powershell
# 1. Toolchain hazır
.\build.ps1 -Tool

# 2. Test programını derle
.\build.ps1 -Asm ..\tests\test1_led_blink.asm

# 3. FPGA'e UART üzerinden yükle
cd ..
python host_app\host_loader.py
#   - Dosya:  sistem_proglamlama_proje_3\build\test1_led_blink.mem
#   - Port:   COMx
#   - YÜKLE  ->  XMODEM-CRC ile aktarım, ACK/NAK
```

Tang Nano 9K'da loading LED'i söner → kullanıcı programı çalışmaya başlar.

---

## 📦 Bağımlılıklar

- **GCC** (MinGW / MSYS2)        - C toolchain derleme
- **Python 3** + `pyserial`       - host loader
- **GOWIN EDA**                   - FPGA sentez/yükleme
- **Tang Nano 9K** (GW1NR-LV9)    - hedef donanım
