# PC Toolchain — Assembler + Linker

Özgün RV32I derleme zinciri (C + Python).

## 📁 Yapı

```
sistem_proglamlama_proje_3/
├── README.md            ← Bu dosya
├── build.ps1            ← -Tool / -Asm / -All / -Clean
├── .gitignore
│
├── toolchain/
│   ├── src/             ← C kaynak kodlar
│   │   ├── assembler.c  ← İki-geçişli RV32I assembler
│   │   └── linker.c     ← ESTAB + relocation linker
│   ├── bin/             ← Derlenmiş .exe'ler
│   │   ├── assembler.exe
│   │   └── linker.exe
│   └── py/              ← Python eşdeğerleri (WDAC fallback)
│       ├── asm.py
│       └── link.py
│
└── build/               ← Üretilen .o ve .mem (gitignored)
```

## 🚀 Kullanım

### Toolchain'i derle (bir kere)
```powershell
.\build.ps1 -Tool
```

### Tek .asm dosyasını derle
```powershell
.\build.ps1 -Asm ..\tests\std_a_gauss_sum.asm
# Çıktı: build\std_a_gauss_sum.mem
```

### Tüm .asm dosyalarını topluca
```powershell
.\build.ps1 -All
```

### build/ klasörünü temizle
```powershell
.\build.ps1 -Clean
```

### Özel başlangıç adresleri
```powershell
.\build.ps1 -Asm ..\tests\std_d_memory_stress.asm -Ttext 0x20 -Tdata 0x1000
```

## 🔧 Manuel Komutlar (script'siz)

```powershell
# Assembly → Object
.\toolchain\bin\assembler.exe ..\tests\std_a_gauss_sum.asm build\std_a.o

# Object → Firmware
.\toolchain\bin\linker.exe -Ttext 0x0 -Tdata 0x1000 -o build\std_a.mem build\std_a.o
```

Python fallback (eğer .exe WDAC tarafından engellenirse):
```powershell
python toolchain\py\asm.py  ..\tests\std_a_gauss_sum.asm build\std_a.o
python toolchain\py\link.py -Ttext 0x0 -Tdata 0x1000 -o build\std_a.mem build\std_a.o
```

## 🎯 Desteklenen RV32I Komutları

- **R-type:** add, sub, sll, xor, srl, sra, or, and, slt, sltu
- **I-type:** addi, xori, ori, andi, slti, slli, srli, srai
- **Load:** lb, lh, lw, lbu, lhu
- **Store (S-type):** sb, sh, sw
- **Branch (B-type):** beq, bne, blt, bge, bltu, bgeu
- **Jump:** jal, jalr
- **U-type:** lui, auipc

## 📝 Direktifler

- `.text` / `.data` — segment seçimi
- `.globl` / `.global` — sembol dışa açma
- `.extern` — dış sembol
- `.word VAL` — 32-bit veri
- `.space N` — N bayt rezerv (sıfırlarla)

## 🔣 Sayı Tabanları

```
addi a0, zero, 63         # decimal
addi a0, zero, 0x3F       # hex
addi a0, zero, 0b111111   # binary
addi a0, zero, 077        # octal
addi a0, zero, -1         # signed negative
```

## 🏷️ ABI Register Adları (RISC-V psABI)

`zero, ra, sp, gp, tp, t0..t6, s0..s11, fp, a0..a7` + `x0..x31` (mimari).
