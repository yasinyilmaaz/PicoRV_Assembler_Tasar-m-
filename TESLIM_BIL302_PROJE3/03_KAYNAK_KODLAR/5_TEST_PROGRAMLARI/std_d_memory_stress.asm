# =====================================================================
# std_d_memory_stress.asm
# ---------------------------------------------------------------------
# AMAÇ:
#   BRAM bant genişliği ve bellek bütünlüğü stres testi. 256 elemanlı
#   (1 KB) .data bölgesindeki dizi önce 0..255 değerleriyle doldurulur,
#   ardından her elemanın indeksiyle XOR'u alınıp akümülatöre toplanır.
#   Tutarlı bellekte akümülatör 0'a düşer; aksi halde veri bozulması
#   olduğu kanıtlanır.
#
# BEKLENEN DAVRANIŞ:
#   Başarılı: xor_acc = 0 → LED'lere 0b101010 yazılır (LED 1, 3, 5 yanar)
#   Hatalı:   xor_acc ≠ 0 → LED'lere 0b010101 yazılır (LED 0, 2, 4 yanar)
#
# SINANAN RV32I KOMUT SINIFLARI:
#   U-tipi: lui
#   I-tipi: addi, lw, slli
#   S-tipi: sw
#   R-tipi: add, xor
#   B-tipi: bne, beq
#   J-tipi: jal
#
# BELLEK HARİTASI:
#   .text:    0x00000020  (kod başlangıcı, -Ttext 0x20)
#   .data:    0x00001000  (buffer başı, -Tdata 0x1000)
#   buffer:   0x00001000 - 0x000013FF (256 × 4 byte = 1 KB rezerv)
#   LED bank: 0x10000000
#   Stack:    0x00007FF0 (bu programda kullanılmaz)
#
# KARMAŞIKLIK KATEGORİSİ:
#   - Bellek sınırlarını zorlayan: 256 sw + 256 lw = 512 BRAM erişimi
#   - Aritmetik akümülatör (XOR fold doğrulaması)
#   - Karşılaştırmalı dallanma + memory-mapped LED gösterimi
# =====================================================================

        .data
buffer: .space 1024                  # 256 word × 4 byte = 1024 byte rezerv

        .text
        .globl _start

_start:
        lui     sp, 8                # sp = 0x00008000 (geçici)
        addi    sp, sp, -16          # sp = 0x00007FF0 (RAM tepesi - 16 margin)
        lui     s0, 1                # s0 = 0x00001000 (buffer base = .data)
        addi    s1, zero, 256        # s1 = N = 256 (iter sayısı)
        addi    s2, zero, 0          # s2 = xor_acc (XOR akümülatörü)

# ---------------------------------------------------------------------
# AŞAMA 1: YAZMA DÖNGÜSÜ  -  buffer[i] = i, i = 0..255
# ---------------------------------------------------------------------
        addi    t0, zero, 0          # t0 = i (yazma sayacı)
write_loop:
        slli    t1, t0, 2            # t1 = i * 4 (word offset)
        add     t2, s0, t1           # t2 = &buffer[i] = s0 + i*4
        sw      t0, 0(t2)            # buffer[i] = i (32-bit store)
        addi    t0, t0, 1            # i++
        bne     t0, s1, write_loop   # i < N ise döngüye devam

# ---------------------------------------------------------------------
# AŞAMA 2: OKUMA + XOR DOĞRULAMA  -  xor_acc ^= (buffer[i] ^ i)
# Tutarlı bellekte her terim sıfır; akümülatör 0 verir
# ---------------------------------------------------------------------
        addi    t0, zero, 0          # t0 = i (okuma sayacı, sıfırla)
read_loop:
        slli    t1, t0, 2            # t1 = i * 4
        add     t2, s0, t1           # t2 = &buffer[i]
        lw      t3, 0(t2)            # t3 = buffer[i] (BRAM'den oku)
        xor     t3, t3, t0           # t3 = buffer[i] XOR i (beklenen: 0)
        xor     s2, s2, t3           # xor_acc ^= t3 (akümülatör güncelle)
        addi    t0, t0, 1            # i++
        bne     t0, s1, read_loop    # i < N ise döngüye devam

# ---------------------------------------------------------------------
# AŞAMA 3: KARAR + LED GÖSTERİMİ
# ---------------------------------------------------------------------
        lui     s3, 0x10000          # s3 = LED bank adresi (0x10000000)
        beq     s2, zero, success    # xor_acc == 0 → başarı dalına atla

fail:
        addi    t4, zero, 21         # t4 = 0b010101 = 21 (hata deseni)
        sw      t4, 0(s3)            # LED'e yaz (LED 0, 2, 4 yanar)
        jal     zero, halt

success:
        addi    t4, zero, 42         # t4 = 0b101010 = 42 (başarı deseni)
        sw      t4, 0(s3)            # LED'e yaz (LED 1, 3, 5 yanar)

# ---------------------------------------------------------------------
# AŞAMA 4: SONSUZ HALT  -  kontrol PC asla geri dönmesin
# ---------------------------------------------------------------------
halt:
        jal     zero, halt           # j . (sonsuz döngü)
