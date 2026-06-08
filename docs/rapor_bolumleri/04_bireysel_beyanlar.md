# 6. BİREYSEL KATKI BEYANI (4 üye için tam set)

> Her takım üyesi kendi paragrafının altına **ad-soyad imzasını** atmalıdır.

---

## Yasin Yılmaz (23010903059)

PicoRV32 yapılandırması ve `top.v` adres çözücü mantığı, `loader_fsm.v`
XMODEM FSM'i (12 durumlu Mealy tipi) ve `memory.v` bellek modülünü
tasarladım. Ayrıca tüm sistemi entegre eden `picorv_ide/main.py`
Tkinter tabanlı geliştirme arayüzünü ve RV32I disassembler modülünü
kendi başıma geliştirdim. En büyük teknik problem Gowin
sentezleyicisinin `memory.v`'yi 262 144 flip-flop'a açma teşebbüsüydü;
loader ile CPU'nun hiçbir zaman eş zamanlı çalışmadığını
(`cpu_resetn` semaforu) fark ederek girişe multiplexer ekledim ve
32-bit RAM'i 4 ayrı 8K × 8-bit array'e bölerek yapıyı tek portlu BSRAM
inferans örüntüsüne uygun hale getirdim. Bu çözüm BRAM kullanımını
beklenen seviyeye düşürdü ve sentezin başarıyla tamamlanmasını
sağladı.

İmza: ____________________

---

## Yusuf Polat (24010903128)

`uart_rx.v` ve `uart_tx.v` modüllerinin 8N1 framing mantığını, iki
kademeli senkronizör (metastability filtre) tasarımını ve baud rate
sayacının 27 MHz osilatörden 115 200 baud türetmesini ben tamamladım.
Ayrıca sistemin uçtan uca doğrulanmasını gerçekleştiren test
metodolojisini kurguladım: %10 kasıtlı bit bozulması senaryosunda
CRC-16 mekanizmasının doğru NAK üretip üretmediğini ölçtüm. En büyük
teknik zorluk, oversampling sırasında start bitinin ortasında doğru
örnekleme yakalamak ve glitch'lere karşı koruma yapmaktı; HALF (117)
saat sonrası ikinci kontrol mantığını ekleyerek bu problemi çözdüm.

İmza: ____________________

---

## Furkan Kılıç (23010903037)

PC tarafındaki yazılım araç zincirinin (Assembler ve Linker) C
implementasyonunu ben tamamladım. Özellikle iki geçişli (Pass 1 /
Pass 2) assembler mimarisini, djb2 hash table sembol depolamasını ve
RISC-V psABI uyumlu register/ABI isim ayrıştırıcısını sıfırdan
yazdım. Linker tarafında ESTAB sembol birleştirme algoritmasını ve
PC-relative branch/jump offset hesabını implemente ettim. En zor
sorun, Pass 1'in yorum satırlarını instruction olarak sayması nedeniyle
etiket adreslerinin yanlış kaymasıydı; `strip_comment()` fonksiyonunu
ekleyerek `#`, `;`, `//` yorumlarını temizledim ve PC artımını yalnızca
`is_real_opcode()` ile filtrelenen gerçek RV32I komutlarına bağladım.
Bu düzeltmeyle branch ve jal offset'leri doğru sign-extended değerler
üretmeye başladı.

İmza: ____________________

---

## Ramazan Acar (23010903069)

XMODEM-CRC tabanlı host loader'ın Python implementasyonunu ben yaptım:
pyserial üzerinden COM port keşfi, 'C' karakteri ile handshake,
128 baytlık paket inşası, CRC-16/XMODEM hesabı ve 10 retry toleransıyla
çalışan ACK/NAK döngüsü. Ayrıca proje boyunca üretilen 50+ sayfalık
teknik raporun düzenini, IEEE atıf formatını ve şekil/tablo
numaralandırmasını yönettim. En büyük teknik problem `.mem` dosyasının
little-endian bayt sırasıyla doğru parse edilmesiydi; başlangıçta
PicoRV32'nin bayt sırasını ters anlamış ve hatalı paketler göndermiştim.
`load_firmware()` fonksiyonunda `w & 0xFF`, `(w >> 8) & 0xFF` ... şeklinde
LSB-first dönüşümü ekleyerek FPGA tarafındaki `byte_lane` mantığıyla
tam uyumlu hâle getirdim.

İmza: ____________________
