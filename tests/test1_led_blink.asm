# Test 1: LED Sayac (PÇ7 - gozle gorulur dongu)
# Her ~500 ms'de bir 6-bit sayac ilerler. Binary counter pattern.
        .text
        .globl _start
_start:
        lui     a0, 0x10000        # LED bank
        addi    a1, zero, 0
loop:
        sw      a1, 0(a0)          # LED <- sayac
        addi    a1, a1, 1
        andi    a1, a1, 0x3F

        # ~500 ms gecikme: 27MHz / (6 cyc * 2 instr) ~ 2.2M iter
        # lui t0, 0x230 = 2293760 iter -> ~510 ms
        lui     t0, 0x230
delay:
        addi    t0, t0, -1
        bne     t0, zero, delay

        jal     zero, loop
