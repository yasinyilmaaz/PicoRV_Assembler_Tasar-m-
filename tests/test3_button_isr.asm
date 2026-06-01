# Test 3: Buton kontrollu kayan LED (PÇ7 - I/O + dallanma)
# Buton basili degil -> sola, basili -> saga
        .text
        .globl _start
_start:
        lui     s1,  0x10000       # GPIO base
        addi    a0,  zero, 1       # mask = 0b000001
        addi    a1,  zero, 1       # yon = sola

main:
        lw      t0, 16(s1)         # buton oku (0x10000010)
        andi    t0, t0, 0x2        # bit1 = btn_user
        beq     t0, zero, sol
        addi    a1, zero, -1       # buton basili -> saga
        jal     zero, dirset
sol:
        addi    a1, zero, 1
dirset:

        bge     a1, zero, kay_sola
        srli    a0, a0, 1          # saga kay
        bne     a0, zero, write_led
        addi    a0, zero, 0x20     # bit5'e sar
        jal     zero, write_led
kay_sola:
        slli    a0, a0, 1
        andi    a0, a0, 0x3F
        bne     a0, zero, write_led
        addi    a0, zero, 1        # bit0'a sar

write_led:
        sw      a0, 0(s1)

        # ~150 ms gecikme
        lui     t1, 0xA4
delay:
        addi    t1, t1, -1
        bne     t1, zero, delay

        jal     zero, main
