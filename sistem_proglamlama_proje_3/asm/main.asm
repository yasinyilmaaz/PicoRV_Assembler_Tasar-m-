.text
.global _start
.extern led_yak

_start:
    ; Ýstediðimiz LED deðerini (0 = Yan, 1 = Sön) x10'a atalým
    addi x10, x0, 0      // x10=0+0
    
    ; math.asm içindeki led_yak fonksiyonuna zýpla
    jal x1, led_yak       // ledin surekli yanmasý için geri donulduðünde sonsuz dongunun adresini x1 de tutuyorum.

sonsuz_dongu:
    beq x0, x0, sonsuz_dongu