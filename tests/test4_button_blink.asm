# test_button.asm: S2 butonu basili oldukca tum LED'ler yanar.
# Brakildikta hepsi soner. MMIO okuma yolunun (lw) en basit testi.
        .text
        .globl _start
_start:
        lui     s0, 0x10000            # LED bank = 0x10000000
        addi    s1, s0, 16             # BTN bank = 0x10000010

loop:
        lw      t0, 0(s1)              # butonu oku
        andi    t0, t0, 2              # bit[1] (btn_user) izole
        bne     t0, zero, off          # bit=1 (serbest) ise sondur

on:                                    # buton basili: tum LED'leri yak
        addi    t1, zero, 0            # aktif dusuk: 0 = yanik
        sw      t1, 0(s0)
        jal     zero, loop

off:                                   # buton serbest: tum LED'leri sondur
        addi    t1, zero, 0x3F         # aktif dusuk: 1 = sonuk
        sw      t1, 0(s0)
        jal     zero, loop