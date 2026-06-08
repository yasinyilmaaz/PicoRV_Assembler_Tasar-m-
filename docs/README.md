# 📚 Dokümantasyon

## Ana Belgeler

| Dosya | İçerik | Boyut |
|---|---|---|
| **SISTEM_RAPORU.pdf** | 50 sayfalık modül-by-modül teknik anatomi | ~230 KB |
| **generate_report.py** | PDF üretici (ReportLab, Arial+Consolas TTF gömülü) | — |

## Rapor Bölümleri (Word'e yapıştırılabilir Markdown)

`rapor_bolumleri/` altında, BIL302 Proje 3 raporunun ilgili bölümlerine
doğrudan kopyalanabilir hâlde:

| # | Dosya | İçerik |
|---|---|---|
| 01 | `01_genel_bolumler.md` | §1-§5 genel taslak |
| 02 | `02_bolum_3_2_metrikler.md` | **§3.2** — Tablo 3.2 (yükleme süreleri) + Tablo 3.3 (GOWIN sentez kaynakları) **gerçek ölçülmüş değerlerle** |
| 03 | `03_bolum_4_2_lisanslar.md` | **§4.2** — Lisans envanteri (12 bileşen) + maliyet karşılaştırması |
| 04 | `04_bireysel_beyanlar.md` | **§6** — 4 üyenin (Yasin, Yusuf, Furkan, Ramazan) bireysel katkı beyan taslakları |
| 05 | `05_kaynakca_ieee.md` | **§7** — IEEE formatında 26 numaralandırılmış kaynak |
| 06 | `06_eksikler_takip.md` | Eksik kalanlar ve düzeltme kontrol listesi |
| 07 | `07_riscv_tests_karsilastirma.md` | Bizim testler ↔ resmi `riscv-tests` karşılaştırması |

## PDF'i Yeniden Üretmek

```powershell
cd docs
python generate_report.py
# Çıktı: SISTEM_RAPORU.pdf
```

> ReportLab ve Windows TrueType fontları gerekir.
> Arial + Consolas, Windows kurulumlarında otomatik gelir.

## Word'e Yapıştırma Akışı

1. İlgili `.md` dosyasını Notepad'le aç
2. Tüm metni kopyala (Ctrl+A, Ctrl+C)
3. Word'e yapıştır: **Paste Special → Unformatted Text**
4. Tüm metni seç → font: **Courier New 10pt** (şartname gereği)
5. Tabloları manuel olarak `Insert → Table` ile yeniden çiz
