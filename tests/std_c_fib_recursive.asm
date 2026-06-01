# ====================================================================
# Standard Test C: Recursive Fibonacci
#   fib(n) = fib(n-1) + fib(n-2)   ;  fib(0)=0, fib(1)=1
#
# Akademik Kaynak (Reference):
#   Patterson, D. & Hennessy, J. (2017).
#   "Computer Organization and Design: RISC-V Edition",
#   Section 2.8.6 "Recursive Procedures" (Figure 2.27 - factorial),
#   Fibonacci'ye uyarlandi.
#
#   RISC-V Foundation, riscv-tests:
#   https://github.com/riscv-software-src/riscv-tests
#   benchmarks/fib/  (recursive Fibonacci benchmark, n=20).
#
#   MIT 6.004 Computation Structures, RISC-V Lab 6 "Recursion on RISC-V"
#   https://6004.mit.edu/
#
# Beklenen Sonuc:
#   fib(8) = 21 = 0x15 = 0b010101
#   LED'ler: LED4, LED2, LED0 yanik. Digerleri sonuk.
#
# Test edilen ozellikler:
#   - Recursive jal/jalr (alt program cagrisi)
#   - Stack yonetimi (sp, push/pop kontekst)
#   - return register (ra) kaydetme/yukleme
#   - Karsilastirmali dallanma (blt)
#   - C ABI uyumlulugu (a0 = arg/return)
# ====================================================================
        .text
        .globl _start

# Stack tepesi RAM sonunda (32KB BSRAM -> 0x8000), 16 bayt margin.
_start:
        lui     sp, 8                  # sp = 0x8000
        addi    sp, sp, -16            # sp = 0x7FF0 (guvenli ust)

        addi    a0, zero, 8            # n = 8
        jal     ra, fib                # a0 = fib(8)

        # Sonucu LED'lere yaz
        lui     t0, 0x10000
        sw      a0, 0(t0)

halt:
        jal     zero, halt

# --------------------------------------------------------------------
# int fib(int n) {
#     if (n < 2) return n;
#     return fib(n-1) + fib(n-2);
# }
#
# Stack frame layout (12 byte, 4-byte aligned):
#   sp+0  : kayit edilmis ra
#   sp+4  : kayit edilmis n (orijinal a0)
#   sp+8  : fib(n-1) sonucu (gecici)
# --------------------------------------------------------------------
fib:
        # Base case: n < 2  ->  return n  (a0 zaten n)
        addi    t0, zero, 2
        blt     a0, t0, fib_ret

        # Prolog: stack frame ac
        addi    sp, sp, -12
        sw      ra, 0(sp)
        sw      a0, 4(sp)              # n'i kaydet

        # Recursive: fib(n - 1)
        addi    a0, a0, -1
        jal     ra, fib
        sw      a0, 8(sp)              # fib(n-1) sakla

        # Recursive: fib(n - 2)
        lw      a0, 4(sp)              # n'i geri yukle
        addi    a0, a0, -2
        jal     ra, fib                # a0 = fib(n-2)

        # Toplam: a0 = fib(n-2) + fib(n-1)
        lw      t1, 8(sp)
        add     a0, a0, t1

        # Epilog: stack frame kapat
        lw      ra, 0(sp)
        addi    sp, sp, 12

fib_ret:
        jalr    zero, 0(ra)            # ret
