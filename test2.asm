    addi r1, x0, 5     ; HATA 1: 'r1' geçersiz (x ile başlamalı)
git:carp x3, x1, x2    ; HATA 2: 'carp' geçersiz (Desteklenmeyen komut)
   beq x1, x2, git    ; HATA 3: 'git' etiketi tanımlanmamış
  .end