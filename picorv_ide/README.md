# PicoRV32 Unified IDE

Tek pencerede **Assembler · Linker · UART Loader** + canlı .mem inceleme/disassembly.

## Çalıştır
```powershell
cd C:\Users\Yasin\Desktop\sunum3
python picorv_ide\main.py
```

## Özellikler
- **Workflow şeridi** — 3 büyük buton (Assemble → Link → Load) + `RUN ALL` pipeline
- **Dosya ağacı** — projenin tüm `.asm`, `.o`, `.mem`, `.v` dosyaları
- **Assembler sekmesi** — sözdizimi renklendirmeli .asm önizleme
- **Linker sekmesi** — `.text`/`.data` adresleri, ESTAB sembol tablosu
- **Loader sekmesi** — COM seçimi, XMODEM paket diyagramı, canlı istatistik (paket/retry/süre)
- **İnceleme sekmesi** — `.mem` hex view + **RV32I disassembly** yan yana
- **Konsol** — zaman damgalı, renkli loglar
- **Config** — son COM port, proje kökü `config.json`'a kaydedilir

## Bağımlılık
```powershell
pip install pyserial
```
