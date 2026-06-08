# RAPOR EKSİKLERİ VE DÜZELTMELER

## 🚨 KRİTİK (mutlaka yapılmalı)

### 1. Bireysel Katkı Beyanları (4 kişi)
- ⚠️ Mevcut: sadece Yasin
- Eksik: Yusuf Polat, Furkan Kılıç, Ramazan Acar
- **Çözüm:** `BIREYSEL_BEYANLAR.md` dosyasındaki taslakları rapora ekle

### 2. Kaynakça Düzeni
- ⚠️ Mevcut: Düz URL'ler + karışık metin
- **Çözüm:** `KAYNAKCA_IEEE.md` dosyasındaki 26 numaralı IEEE listesiyle değiştir

### 3. Görseller (Şekiller)
Raporda referans var ama görseller yok:
- ❌ Şekil 2.3: Sistem Blok Diyagramı (top.v entegrasyonu)
- ❌ Şekil 2.4: Loader FSM Durum Diyagramı (12 durum)
- ❌ Şekil 4.x: Gowin EDA EULA ekran görüntüsü
- **Çözüm:** Aşağıdaki "Görseller nasıl hazırlanır?" bölümüne bak

---

## 🟡 ÖNEMLİ (yapılması iyi olur)

### 4. Bellek Adres Tutarsızlığı
- §2.1'de `.mem` örneği `@00000020` ile başlıyor
- §2.2'de `PROGADDR_RESET = 0x0000_0000` deniyor
- **Çelişki!** İkisinden biri yanlış.
- **Çözüm:** `.mem` örneğini `@00000000` olarak değiştir VEYA PROGADDR_RESET'i 0x20 yap (ama bu durumda Verilog kodunu da güncellemen lazım)

### 5. Tablo Numaraları
"Tablo 2.x", "Tablo 4.x" gibi belirsiz yerler var. **Sıralı numara ver:**
- Tablo 2.3: Reset Vektörü Senkronizasyonu (mevcut "Tablo 2.x")
- Tablo 4.1: Sürdürülebilirlik Karşılaştırması
- Tablo 4.2: Lisans Envanteri (mevcut "Tablo 4.x")
- Tablo 4.3: SKA-PÇ Eşleme Matrisi

### 6. Test Sonuç Ekran Görüntüleri
- ❌ LED davranışı fotoğrafı (3 test için 3 farklı görsel)
- ❌ PicoRV32 IDE ekran görüntüsü (XMODEM transfer logu)
- ❌ Disassembler view (.mem inceleme)
- ❌ Gowin PnR raporu (kaynak kullanım yüzdeleri)
- **Çözüm:** Telefonla LED fotoğrafı çek, IDE'den Windows Snipping Tool ile ekran al

### 7. Sonuç (Conclusion) Bölümü
- Şartnamede zorunlu değil ama akademik raporlarda standart.
- 1 sayfalık §6 olarak ekleyebilirsin: "Tasarım hedefleri vs. ulaşılan sonuçlar"

---

## 🟢 YAN ARAÇLAR (teslim öncesi)

### 8. Video (5 dk)
Proje şartnamesi gereği:
> "Sistemin çalışmasını anlatan video... özgeçmişinize ekleyebileceğiniz kalitede olmalıdır."

**İçerik planı (5 dk):**
- 0:00-0:30 — Proje tanıtım (PicoRV32 + FPGA)
- 0:30-1:30 — IDE'de .asm yazma + ASSEMBLE
- 1:30-2:30 — LINK + ESTAB tablosu açıklama
- 2:30-3:30 — UART transfer canlı (paket diyagramı + ACK akışı)
- 3:30-4:30 — LED'de program çalışması (3 test)
- 4:30-5:00 — Sonuç + GitHub linki

### 9. Dosya İsimlendirme (LMS yükleme)
Şartname formatı:
```
BIL302_PROJE3_A.XX_B.YY_C.ZZ_070626.PDF
BIL302_PROJE1VIDEO_A.XX_B.YY_C.ZZ_070626.MP4
```

A.XX gibi kısaltmalar muhtemelen öğrenci numaralarının son 2 hanesi:
- Yasin Yılmaz: A.59
- Yusuf Polat: B.28
- Furkan Kılıç: C.37
- Ramazan Acar: D.69

Yani dosya: `BIL302_PROJE3_A.59_B.28_C.37_D.69_070626.PDF`

### 10. Format ve Yazı
Şartname:
> "Rapor yazım dili **Courier New ve 10 pt** olmalıdır."

⚠️ Mevcut Word dosyan muhtemelen Arial/Calibri. **Tüm metni seç (Ctrl+A) → Font = Courier New, Size = 10pt yap.**

---

## 📸 GÖRSELLER NASIL HAZIRLANIR?

### Şekil 2.3 — Sistem Blok Diyagramı
**Araç:** draw.io (ücretsiz, web tabanlı: https://app.diagrams.net/)
**İçerik:**
```
[PC: Python+IDE] --UART--> [BL616] --> [FPGA Pin18]
                                            |
                                            v
                                       [uart_rx.v]
                                            |
                                            v
  [crc16.v] <----> [loader_fsm.v] ----> [memory.v]
                                            |
                                            v
                                        [picorv32]
                                            |
                                            v
                                       [GPIO: LED+BTN]
```
- Modüller kutular halinde
- Sinyaller okları üzerinde isimlendirilmiş

### Şekil 2.4 — FSM Durum Geçiş Diyagramı
**Araç:** draw.io veya Lucidchart
**12 durum:**
S_INIT → S_SEND_C → S_WAIT_HDR → S_SEQ → S_NSEQ → S_DATA → S_CRC_HI → S_CRC_LO → S_SEND_ACK → S_WAIT_TX → S_DONE → cpu_resetn=1

Daire için her durum, ok için geçiş koşulu.

### Şekil 4.x — Gowin EULA Ekran Görüntüsü
**Yöntem:** Gowin IDE'yi aç → Help → About → License Agreement → Snipping Tool ile yakala.
"NON-COMMERCIAL" yazan satır kırmızı çerçeve ile vurgula.

---

## ✅ TESLIME HAZIR KONTROL LİSTESİ

- [ ] §6'da 4 kişinin bireysel beyanı + imzaları
- [ ] §7 Kaynakça IEEE formatına çevrilmiş, [1]-[26] numaralı
- [ ] Şekil 2.3 (sistem blok) eklenmiş
- [ ] Şekil 2.4 (FSM diagram) eklenmiş
- [ ] Şekil 4.x (EULA) eklenmiş (opsiyonel)
- [ ] Bellek adres tutarsızlığı (@00000020 vs 0x0000_0000) düzeltilmiş
- [ ] Tüm "Tablo X.x" referanslarına gerçek numara verilmiş
- [ ] Yazı tipi: Courier New 10pt
- [ ] Test LED fotoğrafları eklenmiş (en az 1)
- [ ] PDF olarak dışa aktarılmış: `BIL302_PROJE3_A.59_B.28_C.37_D.69_070626.PDF`
- [ ] 5 dakikalık video kaydedilmiş: `BIL302_PROJE1VIDEO_..._070626.MP4`
- [ ] LMS'e yüklenmiş (07.06.2026 23:59'dan önce)
