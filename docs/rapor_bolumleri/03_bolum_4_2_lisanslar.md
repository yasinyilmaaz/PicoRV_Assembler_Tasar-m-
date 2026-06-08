# 4.2. Ekonomik ve Hukuki Sürdürülebilirlik: Lisanslama ve Teknolojik Bağımsızlık — SKA 8, SKA 9

Sistem tamamen açık kaynak bileşenler üzerine kuruludur: RISC-V ISA,
PicoRV32 (ISC lisansı), CPython, VS Code (MIT), pyserial (BSD) ve Gowin
EDA Education Edition (ücretsiz). Kapalı kaynak alternatiflere (ARM
Cortex-M, Vivado, Quartus, MATLAB) kıyasla toplam lisans/IP maliyeti
sıfırdır. Türkiye'de yerli çip endüstrisi (TÜBİTAK BİLGEM, ASELSAN) açık
RISC-V tasarımlarına geçişi stratejik bir hedef olarak ilan etmiştir;
geliştirilen bu toolchain aynı paradigmanın küçük ölçekli bir uygulamasıdır
[11]. Ekonomik bağımsızlığın yanı sıra bu tercih, mimarinin kapalı kaynak
lisans dayatmalarından kurtularak teknolojik bağımsızlık kazanmasının da
temelidir (SKA 8; SKA 9; PÇ8).

Ancak "açık kaynak", hukuki anlamda "yükümlülüksüz" demek değildir; her
bileşenin kendine özgü bir lisans sözleşmesi ve doğurduğu yükümlülükler
vardır. Projede kullanılan tüm yazılım ve donanım bileşenleri farklı
lisans katmanları altında çalışmaktadır; Tablo 4.2 bu envanteri özetler
(PÇ8).

## Tablo 4.2 — Proje Bileşenlerinin Lisans Envanteri

| Bileşen | Lisans / Hukuki Statü | Doğan Yükümlülük |
|---|---|---|
| **RISC-V ISA** (komut kümesi) | Açık, telifsiz (royalty-free) | Ücret / patent royalty'si yok |
| **PicoRV32** (RTL çekirdek) | ISC License (izin verici) | Özgün telif bildirimi korunmalı (Claire/Clifford Wolf) |
| **CPython 3.x** (yorumlayıcı) | PSF License (BSD-uyumlu) | Ticari kullanım serbest, atıf önerilir |
| **Tkinter** (GUI kütüphanesi) | PSF License (Python ile bundle) | CPython ile aynı kurallar |
| **pyserial** (UART API) | BSD 3-Clause | Telif bildirimi korunmalı |
| **Microsoft VS Code** (editör binary) | Microsoft Software License (MSL) | Telemetri toplanır; ticari kullanım serbest |
| **VS Code OSS** (kaynak kodu) | MIT License | Ticari kullanım + değişiklik serbest |
| **Gowin EDA Education** | Ücretsiz, NON-COMMERCIAL EULA | Ticari üründe kullanım yasak; üretime geçişte Commercial lisans zorunlu |
| **Tang Nano 9K (donanım)** | Sipeed Open Source Hardware (CERN OHL-W) | Şema/PCB değiştirilebilir; özgün atıf korunmalı |
| **GW1NR-9 FPGA çipi** | Proprietary (Gowin Semiconductor IP) | Çip satın alınır; içsel mimari kapalı |
| **BL616 USB-UART firmware** | Apache 2.0 (Bouffalo Lab) | Modifikasyon serbest, telif korunmalı |
| **XMODEM protokolü** | Kamuya açık (public domain, 1977) | Yükümlülük yok |
| **Özgün kod** (asm/link/loader/IDE) | Takıma ait | LICENSE dosyası eklenmesi önerilir |

## 4.2.1 Yazılım Lisansları — Katmanlı Analiz

### CPython ve Ekosistem (PSF / BSD)

Python yorumlayıcısı **Python Software Foundation License** altındadır;
bu lisans BSD ile uyumlu, izin verici (permissive) bir akademik
lisanstır. Ticari kullanım, modifikasyon ve yeniden dağıtım serbesttir.
pyserial kütüphanesi BSD 3-Clause altında dağıtılır; tek yükümlülük
özgün telif bildiriminin korunmasıdır. Bu sayede `host_loader.py` ve
`picorv_ide/main.py` modüllerimiz hem akademik hem ticari ortamlarda
hukuki engelle karşılaşmaksızın kullanılabilir (SKA 9; PÇ8).

### VS Code: İki Farklı Lisans Katmanı

Geliştirme editörü olarak Microsoft Visual Studio Code kullanılmıştır.
VS Code'un hukuki yapısı çift katmanlıdır:

- **VS Code OSS** (kaynak kodu): GitHub'da MIT lisansıyla yayınlanır;
  ücretsiz olarak fork'lanabilir, modifiye edilip yeniden dağıtılabilir
  (örn. *VSCodium* projesi).
- **Microsoft VS Code** (binary dağıtım): Microsoft Software License
  altındadır; ücretsizdir ancak telemetri verisi toplar ve Marketplace
  ile bağımlıdır.

Akademik kullanım her iki katman için de serbesttir; ticari kullanımda
ise Microsoft EULA'sı geçerlidir ancak ek ücret istemez. Projenin tüm
kaynak kodu standart `.py`, `.c`, `.v` formatlarında olduğundan
editör bağımlılığı yoktur — başka bir IDE (Sublime, Vim, Notepad++) ile
de derlenebilir (SKA 9).

### Gowin EDA Education Edition — NON-COMMERCIAL Kısıtı

Gowin EDA Education Edition sürümünün EULA'sı **"NON-COMMERCIAL"**
(ticari olmayan) kısıtı içerir (bkz. Şekil 4.1); bu sürümle üretilen
bitstream'in ticari bir üründe kullanılması lisans ihlali oluşturur ve
ticarileştirme aşamasında ücretli **Commercial Edition**'a geçiş yasal
bir zorunluluk hâline gelir. Projenin akademik kapsamı bu kısıtla tam
olarak uyumludur (SKA 8; PÇ8).

## 4.2.2 Donanım Lisansları

### Sipeed Tang Nano 9K — Açık Donanım (Open Source Hardware)

Projenin hedef donanımı olan Tang Nano 9K geliştirme kartı, Sipeed
tarafından **CERN Open Hardware License (CERN OHL-W v2)** kapsamında
açık donanım olarak yayınlanmıştır. Kartın elektriksel şeması, PCB
yerleşimi (Gerber dosyaları) ve mekanik çizimleri Sipeed'in resmi
GitHub deposunda kamuya açık biçimde erişilebilirdir [20]. Bu durum
şu hukuki kazanımları sağlar:

- Kart **modifiye edilebilir** (örn. ek pin başlığı, dahili sensör)
  ve yeniden üretilebilir; özgün atıf korunduğu sürece ticari amaçla
  da çoğaltılabilir.
- Üniversite atölyelerinde **prototip-PCB üretimi** için referans
  tasarım olarak kullanılabilir.
- Üretici bağımlılığı düşüktür; aynı şema kullanılarak başka
  üreticilerden alternatif kartlar üretilebilir (vendor lock-in
  yoktur) (SKA 9; PÇ8).

### Gowin GW1NR-9 FPGA Çipi — Kapalı IP

Kart üzerindeki FPGA çipinin (GW1NR-LV9QN88PC6/I5) içsel mimarisi
(LUT topology, BSRAM yapısı, fiziksel yerleşim) Gowin Semiconductor
şirketinin tescilli **fikri mülkiyetidir** (proprietary IP). Çip
ticari olarak satın alınır; içeriği reverse-engineering ile
incelenemez. Bu durum açık donanım kart ile kapalı FPGA çipi arasında
bir hukuki dengesizlik yaratır: tasarımcı kartı çoğaltabilir ancak
çip kaynağını başka üreticiden temin edemez. Bu kısıt akademik
çalışmaları engellemez; ancak savunma sanayii gibi tam egemenlik
gerektiren uygulamalarda **yerli FPGA çipi geliştirme** (örn. TÜBİTAK
BİLGEM'in açık RISC-V tabanlı SoC çalışmaları) stratejik önem
kazanmaktadır [11] (SKA 8; SKA 9; PÇ8).

### BL616 USB-UART Köprü Çipi — Açık Firmware

Tang Nano 9K kartı üzerindeki USB-UART köprüsünü sağlayan BL616
mikrokontrolör çipi (Bouffalo Lab), RISC-V mimarisi üzerine
kurulmuştur ve üretici firmware'i **Apache 2.0** lisansı altında
yayınlamıştır. Bu sayede USB-UART köprü davranışı (baud rate
düzenleyici, paket buffer'lama vb.) gerekirse modifiye edilebilir;
örneğin standart altı baud rate'ler (örn. 1 Mbps) için firmware
yeniden derlenebilir (SKA 9; PÇ8).

## 4.2.3 Düzenleyici ve Standart Yükümlülükleri

RISC-V komut kümesi, ARM (mimari lisansı + çip başına telif) ve x86
(patent korumalı, lisanslanamaz) mimarilerinin aksine telifsiz ve açık
bir standarttır; bu durum patent ihlali (patent litigation) riskini
hukuki olarak büyük ölçüde ortadan kaldırır. Kullanılan PicoRV32
çekirdeği izin verici (permissive) ISC lisansı altındadır ve ticari
kullanıma, değiştirmeye ve yeniden dağıtıma izin verir; tek hukuki
yükümlülük, özgün telif bildiriminin (Claire/Clifford Wolf) kaynak
kodda korunmasıdır. Bu nedenle projede `picorv32.v` dosyasındaki telif
başlığı silinmeden saklanmıştır.

Son olarak regülasyon boyutunda, loader'ın tıbbi cihaz, otomotiv veya
savunma gibi kritik alanlarda kullanılması hâlinde IEC 62304 [24], ISO
26262 [25] ve IEC 61508 [26] standartlarına göre sertifikasyon yasal
bir zorunluluk hâline gelir; CRC-16 tabanlı veri bütünlüğü bu
standartların talep ettiği güvenli yazılım aktarımı ilkesinin
önkoşuludur (ayrıntı için bkz. Bölüm 4.3). Açık kaynak ve kamuya açık
yazılımın çoğu yargı bölgesinde ihracat kontrolü (export control)
kapsamı dışında tutulması ise, toolchain'in uluslararası akademik
paylaşımı önünde hukuki bir engel bulunmadığını gösterir (SKA 9; PÇ8).

## 4.2.4 Maliyet Karşılaştırması

Tablo 4.3, proje bileşenlerinin gerçek piyasa maliyetlerini ticari
alternatiflerle karşılaştırır:

## Tablo 4.3 — Proje vs. Kapalı Kaynak Alternatif Maliyet Analizi

| Kategori | Bizim Projemiz | Tipik Ticari Alternatif | Yıllık Tasarruf (USD) |
|---|---|---|---|
| **CPU IP lisansı** | PicoRV32 (ISC, ücretsiz) | ARM Cortex-M3 (~$1500/yıl) | $1500 |
| **EDA aracı** | Gowin EDA Edu (ücretsiz) | Xilinx Vivado Std. (~$3000/yıl) | $3000 |
| **Editör/IDE** | VS Code (ücretsiz) | IAR Embedded Workbench (~$2900/yıl) | $2900 |
| **Compiler/Toolchain** | Özgün C kodu (ücretsiz) | GCC ARM (ücretsiz) veya ARM CC (~$5000/yıl) | $0–5000 |
| **Geliştirme kartı** | Tang Nano 9K (~$13 alımı) | Xilinx Arty A7 (~$129) | $116 (bir kerelik) |
| **TOPLAM (yıllık)** | **~$13 (kart)** | **~$10500/yıl + $129 (kart)** | **~$10400/yıl** |

Açık kaynak yaklaşımı sayesinde 4 kişilik bir öğrenci takımı, sıfır
yıllık lisans maliyetiyle tam donanımlı bir gömülü SoC tasarım
ortamına erişebilmektedir. Bu durum eğitim demokratikleşmesi (SKA 4
— Nitelikli Eğitim) ve KOBİ'ler için Ar-Ge başlangıç engelini
düşürmesi açısından (SKA 8, SKA 9) doğrudan ekonomik etkidir (PÇ8).
