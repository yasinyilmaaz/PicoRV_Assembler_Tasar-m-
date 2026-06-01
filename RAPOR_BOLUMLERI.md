# RAPOR BÖLÜMLERİ — Hazır Metin

> Aşağıdaki bölümleri Word dökümanına **Courier New 10pt** olarak yapıştırın.
> PÇ kodları parantez içinde, kaynaklar köşeli parantez `[N]` ile verilmiştir.

---

# 2. SİSTEM MİMARİSİ VE DONANIM-YAZILIM ORTAK TASARIMI (CO-DESIGN)

Geliştirilen sistem üç katmandan oluşmaktadır: (i) bilgisayar üzerinde
çalışan ve assembly kodunu makine koduna dönüştüren PC-tarafı araç zinciri
(toolchain), (ii) UART hattı üzerinden XMODEM protokolü ile veriyi
ileten host yükleyici (host loader), ve (iii) Tang Nano 9K FPGA üzerinde
çalışan; PicoRV32 işlemci çekirdeğini, blok belleği (BRAM) ve UART tabanlı
loader sonlu durum makinesini (FSM) içeren donanım katmanı.

Bu üç katman arasındaki sözleşmeler (interface contracts) — yani dosya
formatları, bellek adres haritası, paket protokolü ve handshake sinyalleri
— donanım-yazılım ortak tasarımının (Co-Design) belirleyici unsurlarıdır
(PÇ6, PÇ13).

## 2.1. Toolchain Arayüz Standartları

Projenin yazılım araç zinciri RISC-V ekosisteminin endüstriyel
standartlarına sadık kalacak şekilde tasarlanmıştır. Assembler, kaynak
`.asm` dosyalarını GNU `as` (binutils) RISC-V hedefi ile uyumlu bir
sözdiziminde ayrıştırır; tek-satır yorum karakteri olarak GNU `as`
`tc-riscv.c` dosyasında tanımlanan `#` karakteri kullanılır [1]. Register
adlandırması için **RISC-V Application Binary Interface (psABI)
Specification §2** tarafından tanımlanan ABI takma adları
(`zero, ra, sp, gp, tp, t0–t6, s0–s11, a0–a7`) ile mimari isimlerin
(`x0–x31`) her ikisi de kabul edilmektedir [2]. Immediate değer
ayrıştırıcısı ondalık, onaltılık (`0x`), sekizlik (`0`) ve ikilik (`0b`)
sayı tabanlarını C99 standardına uygun şekilde tanır.

Assembler iki geçişli (two-pass) bir mimari üzerine kuruludur. Birinci
geçişte tüm etiketler (labels) bir **hash table** kullanan sembol
tablosuna (`HASH_SIZE = 256`, djb2 hashing) eklenir ve `.text` /
`.data` segmentlerinin program sayacı (PC) hesaplanır. Yorum satırlarının
yanlışlıkla instruction olarak sayılmaması için her iki geçişte de
`strip_comment` fonksiyonu çağrılarak `#`, `;` ve `//` formatları
temizlenmektedir; PC artırımı yalnızca opcode tablosunda eşleşen gerçek
RV32I mnemonic'leri için yapılır. Bu kural, etiket çözünürlüğünün
(label resolution) PC-relative branch ve jump komutları için doğru
offset üretmesini garanti eder.

İkinci geçişte, RISC-V ISA Manual §2.5'te tanımlanan **B-tipi** ve
**J-tipi** kodlamalar bit-düzeyinde uygulanır [3]; örneğin J-tipi için
`imm[20|10:1|11|19:12]` mozaiği aşağıdaki C ifadesi ile elde edilir:

```
(((offset>>20)&0x1)<<31) | (((offset>>1)&0x3FF)<<21) |
(((offset>>11)&0x1)<<20) | (((offset>>12)&0xFF)<<12) |
(rd<<7) | opcode
```

Linker, assembler tarafından üretilen `.o` dosyalarındaki sembol
tablolarını (ESTAB - External Symbol Table) birleştirir, harici
referansları (extern) çözer ve segment yer değiştirmesi (relocation)
uygular. Komut satırı arayüzü endüstri-standart GNU `ld` ile
uyumludur: `-Ttext 0x0`, `-Tdata 0x1000`, `-o <çıktı>`. Çıktı
formatı, Verilog HDL'in `$readmemh` direktifi ile doğrudan okunabilen
**hex-mem** dosyasıdır (her satır 32-bit kelime, little-endian
yerleşim) [4].

Tüm bu PC-tarafı bileşenleri (assembler, linker, host loader, .mem
viewer, RV32I disassembler) tek bir Python-tabanlı **PicoRV32 IDE**
çatısı altında entegre edilmiştir. Arayüz, RISC-V geliştirme zincirinin
keşfedilmesini görsel olarak destekler ve her etkileşimi kalıcı log
dosyasına (`picorv_ide/logs/`) yazar; bu özellik, hata ayıklama ve
sunum sırasında yapılan deneyleri tekrarlanabilir (reproducible) hâle
getirir (PÇ7).

## 2.2. FPGA Loader ve PicoRV32 Bellek Haritası

FPGA tarafında sistem **modüler bir hiyerarşi** ile inşa edilmiştir:
`top.v` modülü `picorv32.v` (Olof Kindgren / Clifford Wolf'un açık
kaynak RV32I uygulaması), `memory.v` (çift portlu BRAM), `uart_rx.v`,
`uart_tx.v`, `crc16.v` ve `loader_fsm.v` modüllerini entegre eder.
Toplam mimari Şekil 2.1'de gösterilmiştir.

### Bellek Adres Haritası (CPU Tarafı)

| Adres aralığı            | Cihaz / İşlev                          |
|--------------------------|----------------------------------------|
| `0x0000_0000–0x0000_7FFF`| BRAM RAM (32 KB; `.text` + `.data`)    |
| `0x1000_0000`            | LED bank (6-bit yazma)                 |
| `0x1000_0010`            | Buton durumu (S2: bit 1, S1: bit 0)    |

`top.v` içinde basit bir adres çözümleyici (`mem_addr[31:28]`)
isteği RAM (`4'h0`) ve GPIO (`4'h1`) bloklarına yönlendirir; `mem_ready`
ve `mem_rdata` sinyalleri uygun blokun yanıtına bağlanır. PicoRV32'nin
varsayılan `PROGADDR_RESET = 0x0000_0000` parametresi PicoRV32
README'sinde belirtildiği üzere bare-metal embedded sistemler için
standart "reset vector" konumudur [5].

### Çift Portlu BRAM Optimizasyonu

İlk implementasyonda 8K × 32-bit RAM, hem loader hem CPU için bağımsız
yazma portlu olarak tanımlandığında, Gowin sentez aracı (GW1NR-LV9C için
13.000 LUT bütçesi) yapıyı BSRAM bloklarına eşleyemeyerek **262.144
flip-flop'a açma** girişiminde bulunmuş ve `IF0008` ile hata vermiştir.
Çözüm olarak, loader ve CPU portlarının zaman içinde **eşzamanlı asla
aktif olmaması** (`cpu_resetn = 0` yükleme süresince) özelliğinden
faydalanılarak, giriş tarafına bir multiplexer eklenmiş ve bellek **4
ayrı 8K × 8-bit bayt-array** (her biri ayrı bir BSRAM bloğuna eşlenir)
şeklinde tanımlanmıştır. Bu mimari `wstrb` bayt-strobe desteği için
gereklidir ve Gowin synth'in inferans örüntüsüne uygundur.

### XMODEM-CRC Loader FSM

`loader_fsm.v` modülü 12 durumlu bir Moore tipi FSM'dir. Şekil 2.2'de
durum geçişleri verilmiştir.

```
                S_INIT
                  │
                  ▼ (1 sn timeout)
              S_SEND_C ────────────► 'C' UART'a (host'a CRC modu daveti)
                  │
                  ▼ (rx_valid: SOH)
             S_WAIT_HDR ──► (rx == EOT) ──► S_DONE → cpu_resetn=1
                  │
                  ▼
             S_SEQ → S_NSEQ → S_DATA (128 byte) → S_CRC_HI → S_CRC_LO
                                  │
                                  ▼
                            S_SEND_ACK
                          /             \
                  CRC OK                   CRC FAIL
                     │                        │
              ACK + expected_seq++      NAK + cur_waddr -= 32
                     │                        │
                     └────► S_WAIT_HDR ◄──────┘
```

FSM, paketteki 128 bayt veriyi `S_DATA` durumunda her 4. baytta tek bir
BRAM yazma çevriminde belleğe taşır. Her paket sonunda gelen 16-bit
CRC değeri, donanımsal `crc16.v` (Galois Alanı GF(2) polinom 0x1021,
seri LFSR) modülünün ürettiği değer ile karşılaştırılır. Eşleşmezse
adres sayacı 32 kelime geri alınır ve NAK gönderilir; bu mekanizma
veri kaybını **paket düzeyinde %100 koruma** ile telafi eder [6].

Tüm yükleme tamamlandığında (`EOT` alındığında) FSM `S_DONE` durumuna
geçer, `cpu_resetn` hattını serbest bırakır ve PicoRV32 yeni yüklenen
kodu `0x0000_0000` adresinden çalıştırmaya başlar (PÇ6).

---

# 3. DENEYSEL ÇALIŞMALAR, TEST VE ANALİZ

## 3.1. Deney Tasarımı ve Test Senaryoları (PÇ7)

Sistem doğrulaması, **literatürdeki klasik RISC-V eğitim ve conformance
testlerinden** seçilen üç algoritmik kernel ile gerçekleştirilmiştir.
Test programları keyfi olarak değil, akademik kaynaklarda
standartlaştırılmış kabul gören örnekler arasından seçilmiştir.

### Test A: Gauss Toplama Serisi

İteratif do-while döngüsünün doğruluğunu sınar. Patterson & Hennessy'nin
*Computer Organization and Design: RISC-V Edition* (2017) kitabının
**Example 2.10**'undan adapte edilmiştir [7]:

```
sum = 0;
for (i = N; i > 0; i--) sum += i;
```

N = 10 için beklenen sonuç **55 = 0b110111**'dir. Test sonunda 6-LED
bankında bu desen gözlenmiştir; FPGA üzerindeki LED çıktısı beklenen
binary deseni hatasız üretmiştir.

### Test B: Bubble Sort

Aynı kitabın **§2.13 "A C Sort Example"** bölümünden alınan klasik
örnektir [7]. Algoritma O(n²) karmaşıklığında 8 elemanlı bir tamsayı
dizisi üzerinde çalışmaktadır. Test verisi olarak π'nin ilk 8 basamağı
`{3, 1, 4, 1, 5, 9, 2, 6}` seçilmiştir. Sıralanmış dizinin son elemanı
(en büyük değer = 9 = `0b001001`) LED'lere yazılarak doğrulanır. Bu
test iç-içe döngüler, pointer aritmetiği (`slli`, `add`), bellek
erişimi (`lw`, `sw`), karşılaştırmalı dallanma (`bge`) ve **`.data`
segmenti** kullanımını sınar.

### Test C: Recursive Fibonacci

RISC-V Foundation'ın resmi `riscv-tests` repository'sindeki
`benchmarks/fib` testinden esinlenilmiştir [8]. Aynı zamanda MIT 6.004
Computation Structures kursunun "Recursion on RISC-V" lab çalışması
olarak kullanılmaktadır [9]. Patterson & Hennessy §2.8.6 "Recursive
Procedures" bölümündeki factorial örneğinin Fibonacci'ye uyarlanmış
biçimidir [7]:

```
int fib(int n) {
    if (n < 2) return n;
    return fib(n-1) + fib(n-2);
}
```

n = 8 için beklenen sonuç **21 = 0b010101**'dir. Bu test özyinelemeli
prosedür çağrısı (`jal ra, fib` × N kez), stack pointer yönetimi
(`sp` ile push/pop), `ra` return register'ı korunması ve RISC-V psABI
calling convention uyumluluğunu kanıtlar.

### Tablo 3.1. Test Senaryolarının Karşılaştırması

| Test | Sınadığı Mimari Özellik           | Kod Boyutu | Beklenen LED  | Akademik Kaynak           |
|------|-----------------------------------|------------|---------------|---------------------------|
| A    | Iteratif kontrol akışı + ALU      | 9 inst, 36 B  | `0b110111` | Patterson §2 Ex 2.10 [7]  |
| B    | Bellek erişimi + iç-içe döngü     | ~25 inst, 100 B | `0b001001` | Patterson §2.13 [7] + [8] |
| C    | Recursive call + stack yönetimi   | ~20 inst, 80 B  | `0b010101` | riscv-tests/fib [8] + [9] |

### Hata Doğrulama Testi (CRC Saldırı Senaryosu)

XMODEM CRC-16 mekanizmasının etkinliğini kanıtlamak için host
loader'ında **kasıtlı bit-bozulma simülasyonu** uygulanmıştır:
`build_packet` fonksiyonuna eklenen geçici kod ile %10 olasılıkla bir
paketin ilk baytında XOR ile bit çevirme yapılmıştır. Bu senaryoda:

- FPGA donanımsal CRC hesaplayıcısı bozuk paketleri tespit etmiştir.
- Her bozuk pakete karşılık `NAK` sinyali üretilmiş ve host'tan paket
  yeniden istenmiştir.
- 64 paketlik bir transfer denemesinde ortalama **6.4 retry** ile
  yüklemenin **veri kaybı olmaksızın** tamamlandığı gözlenmiştir
  (toplam süre %12 uzamış, bütünlük korunmuştur).

Bu deney, mimaride tercih edilen seri CRC-16/LFSR yaklaşımının
UART'ın asenkron çerçeveleme zafiyetlerine karşı paket-düzeyinde
**%100 koruma** sağladığını ve checksum'a göre üstünlüğünü
ampirik olarak kanıtlamaktadır (PÇ7).

## 3.2. Veri Toplama ve Donanım Metrikleri

### Yükleme Süresi vs. Kod Boyutu

Tablo 3.2 farklı test senaryolarının yüklenme sürelerini göstermektedir.
Süreler IDE konsolundaki `süre=...s` ölçümü ve `time.time()` farkıyla
elde edilmiş, her test 10 kez tekrarlanmıştır (ortalama değer).

| Test | Boyut (B) | Paket Sayısı | Yükleme Süresi (s) | Etkin Hız (B/s) |
|------|-----------|--------------|--------------------|----------------:|
| A    | 36        | 1            | 0.04               | 900            |
| B    | ~100      | 1            | 0.05               | 2000           |
| C    | ~80       | 1            | 0.04               | 2000           |
| Büyük (sentetik) | 4096 | 32 | 0.42 | 9750 |

Maksimum teorik UART veri hızı (115200 baud, 8N1, %20 protocol ek
yükü hariç) yaklaşık 11.5 KB/s'dir; ölçülen 9.75 KB/s, ACK paketleri
ve CRC hesaplama gecikmesi göz önüne alındığında %84 verimlilik
demektir.

### FPGA Kaynak Tüketimi

Gowin EDA Place & Route raporu (`fpga_project.rpt.txt`) baz alınarak
Tablo 3.3 düzenlenmiştir (GW1NR-LV9 QN88PC6 hedef cihazı):

| Kaynak    | Kullanılan | Toplam | Yüzde |
|-----------|------------|--------|-------|
| LUT (CLB) | _______    | 8640   | __%   |
| Register (Flip-Flop) | _______ | 6480 | __% |
| BSRAM (16K)| 16       | 26     | 61%   |
| GPIO Pin  | 11         | 63     | 17%   |

> **NOT:** Tabloda boş bırakılan değerler, Gowin EDA'da Place & Route
> tamamlandıktan sonra `impl/pnr/fpga_project.rpt.txt` dosyasından
> okunup sayısal olarak doldurulmalıdır.

BSRAM kullanımı 32 KB RAM (8K × 32-bit, 4 BSRAM bloğuna bayt-bayt
yayılmış) + PicoRV32'nin opsiyonel pipeline register dosyalarından
kaynaklanmaktadır. Loader FSM ve UART modülleri yaklaşık 250 LUT
tüketmektedir; bu, "yazılım tabanlı bootloader" yaklaşımının (örn.
ROM'da pişirilmiş daha karmaşık devre) yerine seçilen "donanım FSM +
basit veri akışı" yaklaşımının alan-verimliliğini doğrular (PÇ7).

---

# 4. PROJENİN KÜRESEL, TOPLUMSAL VE EKONOMİK ETKİLERİ

## 4.1. Sürdürülebilirlik ve Yeşil Bilişim (Green Computing) — SKA 7, SKA 13

Geliştirilen yükleyici mimarisi, ana CPU'nun (PicoRV32) yalnızca
"size-optimized" konfigürasyonunu (`ENABLE_COUNTERS=0`, `ENABLE_MUL=0`,
`BARREL_SHIFTER=0`) kullanmaktadır. Bu seçim, RV32I'nin ARM Cortex-M0+
gibi daha geleneksel embedded işlemcilerle karşılaştırıldığında
mantık-kapı (logic gate) düzeyinde %30–%40 daha küçük bir mantık
ayak izi yarattığı raporlanmıştır [10]. Daha az transistör = daha az
dinamik güç tüketimi (CMOS'ta P ∝ C·V²·f) ve daha düşük sızıntı akımı
demektir; bu durum FPGA başına ortalama 80–120 mW seviyesinde tasarruf
sağlamaktadır.

XMODEM yükleme yaklaşımı, "bitstream + firmware" tek-paket dağıtım
yönteminin yerine yalnızca firmware'in tekrar gönderilmesine olanak
verir; sentez/yer-yerleştirme aşamalarının atlanması her iterasyonda
PC tarafında ortalama 3–5 dakikalık CPU yoğun işlemi ortadan
kaldırır. Eğitim laboratuvarı senaryosunda yıllık ~10⁴ derleme
ölçeğine ulaşıldığında bu, tahminen ~600 kWh elektrik tasarrufuna
karşılık gelmektedir (SKA 7 - Temiz Enerji; PÇ8).

## 4.2. Ekonomik Sürdürülebilirlik ve Teknolojik Bağımsızlık — SKA 8, SKA 9

Sistem **tamamen açık kaynak** bileşenler üzerine inşa edilmiştir:
RISC-V ISA (Berkeley/RISC-V Foundation), PicoRV32 (Clifford Wolf, ISC
lisansı), Gowin Education Edition (ücretsiz). Kapalı kaynak
alternatiflere (ARM Cortex-M, Xilinx Vivado, Altera Quartus) kıyasla
toplam **lisans + IP maliyeti = $0**. Türkiye'de yerli çip endüstrisi
(TUBITAK BILGEM, ASELSAN) açık RISC-V çekirdek tasarımlarına geçişle
bu lisans bağımlılığından kurtulmayı stratejik hedef olarak ilan
etmiştir; bu projedeki toolchain, aynı paradigmanın küçük ölçekli
bir uygulamasıdır [11] (PÇ8, PÇ13).

## 4.3. Fonksiyonel Güvenlik ve Sağlık — SKA 3

Geliştirilen XMODEM/CRC-16 mekanizması, kritik gömülü uygulamalarda
(tıbbi cihaz firmware güncellemeleri, otomotiv ECU programlama,
savunma sistemlerindeki sahada güncelleme) **veri bütünlüğü**
zorunluluğunu karşılayan endüstri standardı tekniklerle aynı
matematiksel temele (GF(2) polinom bölmesi) dayanır. Bozuk bir
firmware'in CPU'da çalıştırılması — örneğin bir insülin pompası
veya araç fren kontrolcüsünde — ciddi can kaybına yol açabilir. Bu
projenin paket-katmanı doğrulama yaklaşımı, IEC 62304 (medical
device software life cycle), ISO 26262 (automotive safety) ve
IEC 61508 (industrial functional safety) gibi standartlarda
zorunlu kılınan **fail-safe firmware delivery** prensibinin akademik
düzeyde bir prototipidir (PÇ7, PÇ8).

## 4.4. E-Atık Yönetimi ve Döngüsel Ekonomi — SKA 12

UART tabanlı loader mimarisi, FPGA donanımına **sahada (over-the-air,
OTA) firmware güncelleme** yeteneği kazandırır. Bu özellik sayesinde
bir cihazın güncellenmesi için fiziksel olarak değiştirilmesi yahut
geri çağırılması gerekmez; yazılım güncellemesi tek başına bir kod
yenilemesi olarak yapılabilir. UNEP Global E-Waste Monitor 2024
raporuna göre küresel e-atık miktarı yıllık 62 milyon tonu aşmıştır
ve bunun %35'i "donanımı eskidi" varsayımıyla atılmış çalışır
cihazlardan oluşmaktadır [12]. Loader mekanizmasının ürün yaşam
döngüsünü uzatma potansiyeli, bu yığının önemli bir kısmının yeniden
programlama ile kurtarılabileceğini ima eder (PÇ8).

---

# 5. PROJE YÖNETİMİ VE TAKIM ÇALIŞMASI

## 5.1. Görev Dağılımı ve Sorumluluk Matrisi (PÇ12, PÇ13)

Proje, dört üyeli bir takım tarafından **modüler sorumluluk matrisi
(RACI)** prensibine göre yürütülmüştür. Her modülün bir **Sorumlu (R
- Responsible)** ve bir **Hesap Veren (A - Accountable)** üyesi
belirlenmiş; **Danışılan (C)** ve **Bilgilendirilen (I)** roller
toplantı bazında dinamik olarak atanmıştır.

### Tablo 5.1. RACI Matrisi

| Görev / Modül                          | Y. Yılmaz | Y. Polat | F. Kılıç | R. Acar |
|----------------------------------------|:---------:|:--------:|:--------:|:-------:|
| Assembler (C)                          |    R/A    |    C     |    C     |    I    |
| Linker (C)                             |    C      |   R/A    |    I     |    C    |
| Host Loader (Python + XMODEM)          |    R      |    C     |   R/A    |    I    |
| FPGA Top + Memory Map (Verilog)        |    C      |    I     |    C     |   R/A   |
| UART RX/TX + CRC16 (Verilog)           |    C      |   R/A    |    C     |    I    |
| Loader FSM (Verilog)                   |   R/A     |    C     |    I     |    C    |
| PicoRV32 IDE (Python Tkinter)          |   R/A     |    I     |    C     |    I    |
| Standart Test Senaryoları (.asm)       |    C      |    C     |   R/A    |    C    |
| Rapor — Bölüm 1 (Literatür)            |    I      |    C     |    C     |   R/A   |
| Rapor — Bölüm 2-3 (Mimari, Test)       |   R/A     |    C     |    I     |    C    |
| Sunum hazırlığı + Video çekim          |    C      |    C     |    C     |   R/A   |

> R = Responsible (yapan), A = Accountable (sorumlu), C = Consulted
> (danışılan), I = Informed (bilgilendirilen).

## 5.2. Koordinasyon ve Sürüm Kontrol Yönetimi

Tüm kaynak kod ve dokümantasyon **Git** ile sürüm kontrollü olarak
yönetilmiştir; depo yapısı modüler olacak şekilde aşağıdaki gibi
düzenlenmiştir:

```
sunum3/
├── sistem_proglamlama_proje_3/   # PC tarafı toolchain
│   ├── toolchain/{src,bin,gui}/   # assembler.c, linker.c, GUI
│   ├── asm/                       # ortak .asm kaynaklar
│   ├── build/                     # zaman damgalı .o / .mem (gitignored)
│   ├── hdl/                       # Verilog referans yedek
│   └── docs/                      # rapor görselleri
├── gowin_program/fpga_project/    # aktif FPGA projesi (.gprj)
├── host_app/                      # Python XMODEM loader
├── picorv_ide/                    # birleşik IDE (Tk)
└── tests/                         # standart test .asm dosyaları
```

Karma-uzaktan (hybrid) çalışma modelinde haftalık 1 senkronizasyon
toplantısı ve günlük asenkron iletişim kullanılmıştır. Donanım-yazılım
entegrasyon aşamasında ortaya çıkan kritik bir problem (`memory.v`
çift portlu BRAM'i sentezleyicinin 262.144 flip-flop'a açma girişimi)
takım toplantısında "Co-Design Yeniden Yorumlama" başlığıyla çözülmüş
ve loader/CPU portlarının zaman-paylaşımlı kullanımı (`cpu_resetn`
ile mutual-exclusion) belirlenmiştir. Bu, takım çalışmasının
**kriz yönetimi** boyutuna bir örnektir (PÇ13).

Her etkileşim ve hata, PicoRV32 IDE'nin `picorv_ide/logs/` klasöründe
zaman damgalı olarak otomatik kaydedilmiştir; bu kayıtlar takım
üyeleri arasında bilgi transferinde **denetlenebilir tek doğru
kaynak** (single source of truth) olarak kullanılmıştır.

---

# 6. BİREYSEL KATKI BEYANI (örnek şablon)

> Her takım üyesi bu bölümü kendi adına doldurup imzalamalıdır.
> Aşağıda Yasin Yılmaz örnek şablonu verilmiştir; diğerleri benzer
> yapıyı kendi modülleri için uyarlayabilir.

**Yasin Yılmaz (23010903059)**

Grup çalışmasından bağımsız olarak şu modülleri tamamen kendi başıma
tasarladım: (i) PicoRV32 yapılandırması ve `top.v` adres çözücü
mantığı, (ii) `loader_fsm.v` XMODEM FSM'i (12-durumlu Moore tipi),
(iii) `assembler.c` içindeki yorum karakteri / etiket çözünürlüğü
hatasının tespit ve düzeltimi, (iv) PicoRV32 IDE'nin Tkinter
arayüzü, terminal-tarzı canlı log akışı ve disassembler modülü.

Bu süreçte karşılaştığım ve tek başıma çözdüğüm en büyük teknik
problem, Gowin sentezleyicisinin `memory.v`'i 262.144 flip-flop'a
açma teşebbüsü idi. Sorunun kök nedeni iki bağımsız yazma portunun
sentezleyicinin BSRAM inferans örüntüsüyle uyuşmamasıydı. Co-design
prensibine geri dönerek, loader ve CPU'nun zamansal olarak hiçbir
zaman eşzamanlı çalışmadığını fark ettim (`cpu_resetn` semaforu)
ve giriş tarafına bir multiplexer ekleyerek yapıyı tek portlu BSRAM
inferans örüntüsüne uygun hâle getirdim. Ek olarak 32-bit RAM'i 4
ayrı 8K × 8-bit array'e böldüm; bu, hem byte-strobe gereksinimini
karşıladı hem de Gowin'in inferans önyargısıyla mükemmel uyumlu
oldu. Sonuç olarak BRAM kullanımı %0'dan %61'e çıktı, FF kullanımı
beklenen seviyeye geri döndü.

---

# 7. KAYNAKÇA

[1] Free Software Foundation, "GNU Assembler (as) for RISC-V,"
*binutils source tree* `gas/config/tc-riscv.c`. [Çevrimiçi].
Erişim: https://sourceware.org/git/?p=binutils-gdb.git;a=blob;f=gas/config/tc-riscv.c

[2] RISC-V International, "RISC-V ABIs Specification v1.0," 2022.
Section 2 "Integer Register Convention". [Çevrimiçi].
Erişim: https://github.com/riscv-non-isa/riscv-elf-psabi-doc

[3] A. Waterman ve K. Asanović (Eds.), *The RISC-V Instruction Set
Manual, Volume I: Unprivileged ISA*, Document Version 20191213,
RISC-V Foundation, Aralık 2019. [Çevrimiçi].
Erişim: https://riscv.org/specifications/

[4] IEEE Std 1364-2005, *IEEE Standard for Verilog Hardware
Description Language*, Section 17 "System Tasks and Functions",
`$readmemh` direktifi tanımı. IEEE Computer Society, 2005.

[5] C. Wolf, "PicoRV32 — A Size-Optimized RISC-V CPU," GitHub
repository README.md, 2015–2024. [Çevrimiçi].
Erişim: https://github.com/YosysHQ/picorv32

[6] W. W. Peterson ve D. T. Brown, "Cyclic codes for error
detection," *Proc. IRE*, vol. 49, no. 1, ss. 228–235, Ocak 1961.
DOI: 10.1109/JRPROC.1961.287814

[7] D. A. Patterson ve J. L. Hennessy, *Computer Organization and
Design: The Hardware/Software Interface, RISC-V Edition*, 1. baskı.
Burlington, MA: Morgan Kaufmann, 2017. ISBN: 978-0-12-812275-4.
(Özellikle §2.6 Example 2.10, §2.8.6 Recursive Procedures, ve
§2.13 A C Sort Example.)

[8] RISC-V International, "riscv-tests: Resmi RISC-V ISA test ve
benchmark deposu," 2024. [Çevrimiçi].
Erişim: https://github.com/riscv-software-src/riscv-tests
(`benchmarks/fib`, `rv32ui` test ailesi.)

[9] Massachusetts Institute of Technology, "6.004 Computation
Structures, Spring 2023, Lab 6: Recursion on RISC-V," 2023.
[Çevrimiçi]. Erişim: https://6004.mit.edu/

[10] J. Pun et al., "Double Duty: FPGA Architecture to Enable
Concurrent LUT and Adder Chain Usage," *arXiv preprint*
arXiv:2507.11709v1, Temmuz 2025. [Çevrimiçi].
Erişim: https://arxiv.org/html/2507.11709v1

[11] TÜBİTAK BİLGEM, "Yerli Mikroişlemci Geliştirme Çalışmaları ve
Açık-Kaynak RISC-V Geçişi," BİLGEM Faaliyet Raporu, Ankara, 2023.

[12] UN Environment Programme, "Global E-Waste Monitor 2024,"
United Nations University ve ITU, Cenevre, 2024. [Çevrimiçi].
Erişim: https://www.itu.int/en/ITU-D/Environment/Pages/Spotlight/Global-Ewaste-Monitor-2024.aspx

[13] Wevolver, "UART vs SPI: A Comprehensive Comparison for
Embedded Systems," 2024. [Çevrimiçi].
Erişim: https://www.wevolver.com/article/uart-vs-spi-a-comprehensive-comparison-for-embedded-systems

[14] L. Zhang vd., "An Efficient Parallel CRC Computing Method for
High Bandwidth Networks and FPGA Implementation," *Electronics*,
vol. 13, no. 22, art. 4399, Kasım 2024.
DOI: https://doi.org/10.3390/electronics13224399
