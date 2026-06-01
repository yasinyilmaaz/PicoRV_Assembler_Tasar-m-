# Test 0: TUM LED'leri yak (ABI register isimleri + hex literal kullanir)
# Bu test, RISC-V psABI standardina uygun assembler ozelliklerini dogrular.
        .text
        .globl _start
_start:
        lui     a0, 0x10000        # a0 = 0x10000000 (LED bank)
        addi    a1, zero, 0x3F     # a1 = 63 (hex literal)
        sw      a1, 0(a0)          # LED <- 0x3F
halt:
        jal     zero, halt         # sonsuz dur
