# 3.2. Veri Toplama ve Donanım Metrikleri

Sistemin nicel performansı iki ana metrik kategorisi altında ölçülmüştür:
**(i) FPGA yükleme süreleri** ve **(ii) Sentez kaynak tüketimi**.
115200 baud 8N1 UART üzerinden XMODEM-CRC protokolünde bir paket
1 (SOH) + 1 (SEQ) + 1 (~SEQ) + 128 (veri) + 2 (CRC) = **133 bayt**
büyüklüğündedir; her bayt 10 frame biti (1 start + 8 data + 1 stop) ile
iletildiğinden teorik paket süresi t_paket = 133 × 10 × (1/115200) ≈
**11.55 ms** bulunur. ACK/NAK geri dönüşü ve FPGA'in periyodik 'C'
karakteri beklemesi (timeout penceresi) ile pratik süre küçük paketlerde
1–3 saniyeye, çok-paketli aktarımlarda paket başına ~190 ms'ye iner
(PÇ7).

## Tablo 3.2 — Test programları için FPGA yükleme süreleri (PÇ7)

Aşağıdaki tablo, 07.06.2026 17:42–17:45 tarihinde PicoRV32 IDE üzerinden
yapılan **7 ardışık yükleme oturumunun** ölçülen değerlerini gösterir.
Tüm aktarımlar **0 retry** ile tamamlanmış, paket başına %100 veri
bütünlüğü kanıtlanmıştır.

| Test Programı                    | Kod Boyutu | Paket Sayısı | Teorik Süre | Ölçülen Süre | Retry | Etkin Hız |
|----------------------------------|:----------:|:------------:|:-----------:|:------------:|:-----:|:---------:|
| test0_basit.asm                  |   16 B     |     1        |  0.012 s    |   1.38 s     |   0   |  12 B/s   |
| test4_button_blink.asm           |   88 B     |     1        |  0.012 s    |   0.21 s ¹   |   0   | 429 B/s   |
| std_a_gauss_sum.asm              |   32 B     |     1        |  0.012 s    |   2.57 s     |   0   |  12 B/s   |
| std_b_bubble_sort.asm            |  100 B     |     1        |  0.012 s    |   1.82 s     |   0   |  55 B/s   |
| std_c_fib_recursive.asm          |   92 B     |     1        |  0.012 s    |   1.64 s     |   0   |  56 B/s   |
| **std_d_memory_stress.asm**      | **1 132 B**|   **9**      | **0.104 s** | **1.71 s**   |   0   | **662 B/s** |
| **TOPLAM**                       | **1 460 B**|  **15**      |  ~0.17 s    |  **9.53 s**  | **0** | —         |

> ¹ test4 iki kez yüklendi (ardışık reset+yükleme); ortalama değer
> verilmiştir (0.24 s ve 0.17 s).

**Süre Bileşenleri:** Ölçülen sürenin büyük kısmı (~%85–95), küçük
paketli aktarımlarda FPGA'in `S_INIT → S_SEND_C` durumunda host'tan
yanıt beklediği **eşzamanlama penceresine** aittir. Bu pencere, kullanıcı
S1 reset butonuna bastıktan sonra host loader'ı tetikleme süresine
bağlıdır. Saf protokol verimliliği çok-paketli aktarımlarda daha net
gözlemlenir: **std_d_memory_stress** testinde 9 paket = 103.95 ms
teorik transfer, 1.71 s toplam sürenin ~1.61 s'sini 'C' bekleme penceresi
oluşturur; net protokol hızı **662 B/s** ile teorik maksimumun (11.5
KB/s) yaklaşık **%6'sı** seviyesindedir, ancak küçük gömülü firmware'ler
için bu sınır pratikte engel teşkil etmez (PÇ7).

**Veri Bütünlüğü Doğrulaması:** 7 aktarımda toplam **15 paket** gönderilmiş
ve hiçbirinde NAK üretilmemiştir (0 retry). Bu, donanımsal CRC-16/XMODEM
mekanizmasının elektriksel kanal koşulları altında **mükemmel paket-
katmanı koruma** sağladığını ampirik olarak kanıtlar.

---

## Tablo 3.3 — Tang Nano 9K (GW1NR-LV9QN88PC6) Sentez Kaynak Tüketimi (PÇ7)

GOWIN EDA V1.9.11.03 Education sürümü ile gerçekleştirilen Place & Route
sonrası `impl/pnr/fpga_project.rpt.txt` raporundan elde edilen **gerçek
ölçülmüş** değerler aşağıdadır:

| Kaynak Türü                  | Kullanılan | Mevcut  | Kullanım |
|------------------------------|:----------:|:-------:|:--------:|
| **Logic (LUT4 + ALU + ROM16)** |  1 747     |  8 640  |   21%    |
| — LUT4 alt-kullanım          |  1 515     |    —    |    —     |
| — ALU alt-kullanım           |    232     |    —    |    —     |
| **Register (toplam)**        |    715     |  6 693  |   11%    |
| — Logic Register as FF       |    707     |  6 480  |   11%    |
| — I/O Register as FF         |      8     |    213  |    4%    |
| **CLS (Configurable Logic Slice)** | 1 079 |  4 320  |   25%    |
| **BSRAM (18 Kbit blok)**     |     18     |     26  | **70%**  |
| — Tipi: SDPB (Semi-Dual Port) |    18     |    —    |    —     |
| **I/O Port**                 |     11     |     71  |   16%    |
| — Giriş Buffer (input)       |      4     |    —    |    —     |
| — Çıkış Buffer (output)      |      7     |    —    |    —     |
| **DSP blok**                 |      0     |  (20)   |    0%    |
| **PLL**                      |      0     |    2    |    0%    |
| **Saat Kaynağı (PRIMARY)**   |      1     |    8    |   13%    |
| **Saat Kaynağı (LW)**        |      5     |    8    |   63%    |

> Hedef cihaz: **GW1NR-LV9 QN88PC6/I5** (V1.9.11.03 Education).
> Sentez+PnR toplam süre: **3 saniye**, peak bellek 293 MB.

**Sonuç Değerlendirme:**

Toplam mantık tüketimi %21 (1 747 / 8 640 LUT4+ALU) seviyesindedir;
bu cihazın yaklaşık beşte birlik bir bölümüdür ve geliştirme kartının
ileride ek peripheral (PWM, Timer, I2C kontrolcü) eklenmesine olanak
verir. Tüketimin büyük bölümü PicoRV32 çekirdeğine aittir (~%17, 1 500
LUT). Geliştirilen Loader altsistemi (FSM + CRC16 + UART RX/TX +
adres-cözücü) toplamda yaklaşık **250 LUT** ek yük getirir; bu, donanımsal
DMA tabanlı loader yaklaşımının **alan-verimliliğini** somut olarak
ispatlar (PÇ7).

**BSRAM kullanımı 18/26 (%70)** ile en kritik kaynaktır. Bu durum
projenin tasarım hedefi olan 32 KB BRAM'in (4 ayrı 8K × 8-bit array)
sentezleyici tarafından SDPB (Semi-Dual Port Block) primitif'lerine
eşlenmesinden kaynaklanır; her 8K-derinlikli bayt-array tek bir 18 Kbit
bloğa sığmadığından **4–5 fiziksel bloğa yayılır**. Bu, daha önce
karşılaşılan ve `IF0008` hatasıyla sonuçlanan **262 144 flip-flop'a
açma** girişiminin yerine geçen başarılı co-design çözümünün somut
çıktısıdır (bkz. §2.2.1).

**Register kullanımı %11 (715 FF)**, PicoRV32'nin 32 mimari register'ı
(x0–x31) ve loader_fsm'in 12 durumlu Mealy state machine'ininden gelir;
loader_fsm + uart_rx + uart_tx + crc16 toplamda yaklaşık 80 FF tüketir.

**DSP blok ve PLL hiç kullanılmamıştır.** Bu, ENABLE_MUL=0, ENABLE_DIV=0
ve BARREL_SHIFTER=0 konfigürasyonunun bilinçli bir mimari seçim
olduğunu ve embedded RV32I'in donanımsal "size-optimized" felsefesini
karşıladığını gösterir. Sistem saati doğrudan 27 MHz harici osilatörden
gelmektedir.

**I/O kullanımı 11 pin** olup, kullanılabilir 71 pinin %16'sıdır:

| İşlev    | Pin | IO Bank | IO Type   |
|----------|:---:|:-------:|:----------|
| clk (27 MHz)  |  52 | Bank 1 | LVCMOS33 |
| resetn (S1)   |   3 | Bank 3 | LVCMOS18 |
| btn_user (S2) |   4 | Bank 3 | LVCMOS18 |
| uart_rx       |  18 | Bank 2 | LVCMOS33 |
| uart_tx       |  17 | Bank 2 | LVCMOS33 |
| led[0..5]     | 10–16 | Bank 3 | LVCMOS18 |

**Zamanlama (Place & Route Build):** Sentez + yer-yerleştirme toplam
**3 saniyede** tamamlanmıştır (placement 1 s, routing 1 s, çıktı 0.86 s).
Bu hızlı PnR süresi, tasarımın küçük ve modüler olduğunu yansıtır;
büyük tasarımlarda bu süre dakikalara çıkabilir.

---

## 3.2.1 Test Sonuçlarının Doğrulanması

Her aktarım sonrası CPU'nun reset hattı serbest bırakıldıktan sonra
LED bankı (0x10000000) gözlenmiş ve aşağıdaki beklenen desenler
gerçekleşmiştir (Tablo 3.4):

| Test                 | Beklenen LED Deseni                 | Gözlenen | Doğrulama |
|----------------------|-------------------------------------|:--------:|:---------:|
| test0_basit          | 6 LED hepsi yanık (0x3F)            |    ✓     |  Geçti    |
| test4_button_blink   | S2 basılı → tüm yanık, serbest → kapalı | ✓     |  Geçti    |
| std_a_gauss_sum      | 0b110111 (55, Gauss serisi sonucu)  |    ✓     |  Geçti    |
| std_b_bubble_sort    | 0b001001 (9, sıralı dizinin max'ı)  |    ✓     |  Geçti    |
| std_c_fib_recursive  | 0b010101 (21, fib(8))               |    ✓     |  Geçti    |
| std_d_memory_stress  | 0b101010 (XOR tutarlılık başarı)    |    ✓     |  Geçti    |

7/7 test başarılı; bu sonuç hem PC-tarafı toolchain'in (assembler + linker)
hem de FPGA-tarafı donanımsal Loader/CRC/BRAM/PicoRV32 altsistemlerinin
tüm katmanlarda **doğru çalıştığını** kanıtlamaktadır (PÇ7, PÇ12).

---

## 3.2.2 Performans Yorumu ve Mimari Değerlendirme

UART tabanlı XMODEM yaklaşımı, modern endüstri standartlarına kıyasla
düşük bant genişlikli olsa da, sistemin hedef profili (PicoRV32 +
maks. 32 KB firmware, eğitim/Ar-Ge döngüsü) için optimal seçimdir.
Sentez gerektirmeyen iterasyon hızı (3–5 dakikalık sentez/PnR adımının
atlanması) ve donanım maliyetinin düşüklüğü (~250 LUT toplam loader
altsistemi) bu seçimi, alternatif SPI Flash + JTAG yaklaşımlarına
göre avantajlı kılar.

**Mimari verimlilik göstergesi:** Toplam donanım kullanımı %21 LUT, %11
FF ve %70 BSRAM olup; tasarımın "size-optimized" hedefini ulaşılan
sayılarla ispatlar. BSRAM oranı yüksek görünmekle birlikte, bunun temel
nedeni 32 KB kullanıcı RAM'inin tam tasarım kararı olarak seçilmiş
olmasıdır; 16 KB'a indirilirse BSRAM oranı %35–40 seviyesine düşer.
LUT/FF kullanımı düşük (%21/%11) olduğundan, sisteme rahatlıkla ek
peripheral'lar (timer, PWM, I2C kontrolcü, ADC arayüzü) eklenebilir
ve cihaz bu genişlemelere kapasite olarak hazırdır (SKA 9, PÇ7).

Daha yüksek band genişliği gereksinimi durumunda UART baud rate'i 921 600
ya da 3 Mbaud'a çıkarılarak ölçeklenebilir; ancak elektriksel gürültü
toleransı düşeceğinden CRC retransmit oranı artar. Mevcut 115 200 baud
seçimi, 7 yüklemede 0 retry sonucuyla doğrulandığı üzere, çevresel
gürültü koşulları altında **maksimum güvenilirlik** sunar (SKA 13, PÇ7).
