# =====================================================================
# test_pic_break.asm
# ---------------------------------------------------------------------
# AMAÇ:
#   Position-Independent Code (PIC) sınırlarını gözle görülür hâle getirir.
#   "Adres uyumsuzluğu sessiz hata olur" iddiasını doğrudan test eder.
#
# ÇALIŞMA MANTIĞI:
#   1. auipc komutu, "şu anki PC adresini" runtime'da okur ve t0'a yazar
#   2. Programda HARDCODED bir adres (0x400) sabitlenmiştir (t1)
#   3. t0 ile t1 karşılaştırılır:
#      - Eşit: kod gerçekten 0x400'de duruyor   -> SUCCESS (0b101010)
#      - Farklı: kod aslında başka adreste     -> FAIL    (0b010101)
#
# TEST SENARYOSU (sunum için):
#
#   Senaryo A - HER ŞEY 0x400:
#     top.v PROGADDR_RESET = 0x400
#     loader_fsm cur_waddr = 256 (= 0x400/4)
#     IDE Linker -Ttext   = 0x400
#     SONUC: LED 0b101010 yanar (3 katman mutabık)
#
#   Senaryo B - DONANIM ESKİ, LİNKER YENİ:
#     top.v PROGADDR_RESET = 0x300 (DEGISTIRILMEDI)
#     loader_fsm cur_waddr = 192 (= 0x300/4)
#     IDE Linker -Ttext   = 0x400 (DEGISTIRILDI)
#     SONUC: LED 0b010101 yanar (PIC sınırı kırıldı)
#
# AKADEMIK MESAJ:
#   "RV32I PC-relative komut kümesi koda kayma toleransı sağlar, ancak
#    auipc gibi runtime PC'yi okuyan komutlar (veya jump table'lar,
#    .word label referansları, mutlak adres aritmetiği) bu toleransı
#    kırar. Co-design'da 3 katmanın aynı adreste mutabık olması
#    güvenli mühendislik tercihidir."
#
# SINANAN RV32I:
#   U-tipi: auipc, lui
#   I-tipi: addi
#   B-tipi: bne
#   S-tipi: sw
#   J-tipi: jal
# =====================================================================
        .text
        .globl _start

_start:
        # ---- 1. Runtime PC'yi yakala ----
        auipc   t0, 0              # t0 = runtime PC of this instruction
                                   # Link-time'da: 0x400 (Ttext)
                                   # Runtime'da: gerçek yüklenme adresi

        # ---- 2. Beklenen link-time PC'yi sabit yükle ----
        lui     t1, 0              # t1 = 0
        addi    t1, t1, 0x400      # t1 = 0x400 (hardcoded beklenen değer)

        # ---- 3. Karşılaştır: eşit DEĞİLSE FAIL'e dallan ----
        bne     t0, t1, fail

# ---------------------------------------------------------------------
# SUCCESS DALI: 0x400 ile mutabık çalışıyor → 0b101010 = 42
# ---------------------------------------------------------------------
success:
        addi    t2, zero, 42       # 0b101010 (LED 1, 3, 5 yanar)
        lui     t3, 0x10000        # LED bank adresi
        sw      t2, 0(t3)
        jal     zero, halt

# ---------------------------------------------------------------------
# FAIL DALI: Adres farklı → 0b010101 = 21
# ---------------------------------------------------------------------
fail:
        addi    t2, zero, 21       # 0b010101 (LED 0, 2, 4 yanar)
        lui     t3, 0x10000
        sw      t2, 0(t3)

# ---------------------------------------------------------------------
# SONSUZ HALT
# ---------------------------------------------------------------------
halt:
        jal     zero, halt
