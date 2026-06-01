# Test 1b: Tum LED'ler 1 sn ON, 1 sn OFF - cok bariz
        .text
        .globl _start
_start:
        lui     a0, 0x10000
        addi    a2, zero, 63       # mask = 6 LED hepsi
        addi    a3, zero, 0        # off
main:
        sw      a2, 0(a0)          # ON
        jal     ra, wait1s
        sw      a3, 0(a0)          # OFF
        jal     ra, wait1s
        jal     zero, main

wait1s:
        lui     t0, 0x460          # ~4.5M iter -> ~1 sn
w1:
        addi    t0, t0, -1
        bne     t0, zero, w1
        jalr    zero, 0(ra)
