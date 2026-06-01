# Test 2: Fibonacci(10) -> 55 = 0x37 = 0b110111 (PÇ7 - orta karmasiklik)
        .text
        .globl _start
_start:
        addi    a0, zero, 10       # n = 10
        addi    t0, zero, 0        # a = 0
        addi    t1, zero, 1        # b = 1
        addi    s0, zero, 0        # i = 0

        beq     a0, zero, done
loop:
        add     t2, t0, t1         # c = a + b
        add     t0, zero, t1       # a = b
        add     t1, zero, t2       # b = c
        addi    s0, s0, 1
        blt     s0, a0, loop

done:
        lui     s1, 0x10000        # LED bank
        sw      t0, 0(s1)          # LED <- F(n)
halt:
        jal     zero, halt
