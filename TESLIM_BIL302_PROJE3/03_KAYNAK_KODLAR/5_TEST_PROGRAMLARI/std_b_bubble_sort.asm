# ====================================================================
# Standard Test B: Bubble Sort
#   8 elemanli bir diziyi artan sirada siralar, en buyuk elemani
#   LED bank'a yazar.
#
# Akademik Kaynak (Reference):
#   Patterson, D. & Hennessy, J. (2017).
#   "Computer Organization and Design: RISC-V Edition", Section 2.13
#   "A C Sort Example to Put It All Together".
#
#   RISC-V Foundation, riscv-tests repository (rv32ui ailesi),
#   https://github.com/riscv-software-src/riscv-tests
#
# Beklenen Sonuc:
#   Giris dizi: {3, 1, 4, 1, 5, 9, 2, 6}  (Pi'nin ilk 8 basamagi)
#   Siralandiktan sonra arr[7] = 9 = 0b1001  (LED 3 ve LED 0 yanik)
#
# Test edilen ozellikler:
#   - Ic-ice dongu (i, j)
#   - Bellek erisimi (lw, sw)
#   - Yardimci adres hesabi (slli, add)
#   - Karsilastirmali dallanma (bge)
#   - Veri segmenti (.data section, -Tdata 0x1000)
# ====================================================================
        .data
arr:    .word   3, 1, 4, 1, 5, 9, 2, 6      # 8 eleman x 4 byte = 32 byte

        .text
        .globl _start
_start:
        # a0 = arr base = 0x00001000
        lui     a0, 1                       # a0 = 1 << 12 = 0x1000

        # s0 = n = 8
        addi    s0, zero, 8
        # s1 = i = n - 1
        addi    s1, s0, -1

# for (i = n-1; i > 0; i--)
outer:
        beq     s1, zero, done              # i == 0 -> done

        # j = 0
        addi    s2, zero, 0

# for (j = 0; j < i; j++)
inner:
        beq     s2, s1, next_outer          # j == i -> exit inner

        # addr = arr + j*4
        slli    t0, s2, 2                   # t0 = j * 4
        add     t1, a0, t0                  # t1 = &arr[j]

        lw      t2, 0(t1)                   # t2 = arr[j]
        lw      t3, 4(t1)                   # t3 = arr[j+1]

        # if arr[j+1] >= arr[j]: skip swap
        bge     t3, t2, no_swap

        # swap
        sw      t3, 0(t1)
        sw      t2, 4(t1)

no_swap:
        addi    s2, s2, 1
        jal     zero, inner

next_outer:
        addi    s1, s1, -1
        jal     zero, outer

# Sonuc: arr[n-1] LED'lere yaz (en buyuk eleman = 9)
done:
        slli    t0, s0, 2                   # n*4
        addi    t0, t0, -4                  # (n-1)*4
        add     t0, a0, t0                  # &arr[n-1]
        lw      t1, 0(t0)                   # arr[n-1]

        lui     t2, 0x10000
        sw      t1, 0(t2)

halt:
        jal     zero, halt
