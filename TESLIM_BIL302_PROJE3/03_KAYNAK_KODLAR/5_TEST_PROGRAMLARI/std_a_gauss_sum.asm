# ====================================================================
# Standard Test A: Gauss Toplama Serisi
#   sum = 1 + 2 + 3 + ... + N
#
# Akademik Kaynak (Reference):
#   Patterson, D. & Hennessy, J. (2017).
#   "Computer Organization and Design: The Hardware/Software Interface,
#    RISC-V Edition" (1st ed.), Morgan Kaufmann.
#   Chapter 2, Example 2.10 "Compiling a do-while Loop in C".
#
# Beklenen Sonuc:
#   N = 10  -> sum = 55 = 0x37 = 0b110111  (6 LED: 0b110111)
#
# Bu test sunlari kanitlar:
#   - Donguden cikis (loop / bne)
#   - ALU toplama (add)
#   - Memory-mapped I/O yazma (sw)
# ====================================================================
        .text
        .globl _start
_start:
        addi    a0, zero, 10           # N = 10
        addi    a1, zero, 0            # sum = 0

# do { sum += i; i--; } while (i != 0);
loop:
        add     a1, a1, a0             # sum = sum + i
        addi    a0, a0, -1             # i--
        bne     a0, zero, loop         # i != 0 ?

# LED bank'a sonucu yaz (0x1000_0000)
        lui     t0, 0x10000
        sw      a1, 0(t0)

halt:
        jal     zero, halt
