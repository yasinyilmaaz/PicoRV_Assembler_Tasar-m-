# Standart RISC-V Test Senaryoları

Bu klasördeki test programları, **bilinen akademik kaynaklardan** ve
**resmi RISC-V test repository'lerinden** alınma klasik algoritmik kernel'lerdir.
Tasarımı keyfi değildir; her biri raporlandırılabilir bir referansa sahiptir.

---

## Test A — Gauss Toplama Serisi

**Dosya:** `std_a_gauss_sum.asm`

**Algoritma:** `sum = 1 + 2 + ... + N`, iteratif do-while döngüsü.

**Akademik Referans:**
> Patterson, D. A., & Hennessy, J. L. (2017).
> *Computer Organization and Design: The Hardware/Software Interface,
> RISC-V Edition* (1st ed., pp. 92-94, Example 2.10).
> Morgan Kaufmann. ISBN: 978-0-12-812275-4.

**Beklenen Çıktı:** N=10 → sum = 55 = `0b110111` (LED5,4,2,1,0 yanık)

**Sınadığı Mimari Özellikler:**
- Iteratif kontrol akışı (`bne`)
- ALU toplama (`add`)
- Memory-mapped I/O yazma (`sw`)

---

## Test B — Bubble Sort

**Dosya:** `std_b_bubble_sort.asm`

**Algoritma:** O(n²) klasik bubble sort, 8-elemanlı `int` dizi üzerinde.
Sıralama tamamlandıktan sonra dizinin son elemanı (en büyük) LED'lere yazılır.

**Akademik Referans:**
> Patterson, D. A., & Hennessy, J. L. (2017).
> *Computer Organization and Design: RISC-V Edition*,
> Section 2.13 "A C Sort Example to Put It All Together", pp. 132-138.
> Morgan Kaufmann.

> RISC-V International (2024). **riscv-tests** (rv32ui ailesi).
> https://github.com/riscv-software-src/riscv-tests
> (Resmi RISC-V ISA conformance test repository).

**Test Verisi:** π'nin ilk 8 basamağı `{3, 1, 4, 1, 5, 9, 2, 6}` →
sıralandıktan sonra `{1, 1, 2, 3, 4, 5, 6, 9}`.

**Beklenen Çıktı:** `arr[7] = 9 = 0b001001` (LED3 ve LED0 yanık)

**Sınadığı Mimari Özellikler:**
- İç-içe döngüler (nested loops)
- Pointer aritmetiği (`slli`, `add`)
- Bellek erişimi (`lw`, `sw`)
- Karşılaştırmalı dallanma (`bge`)
- `.data` segmenti (linker `-Tdata 0x1000`)

---

## Test C — Recursive Fibonacci

**Dosya:** `std_c_fib_recursive.asm`

**Algoritma:** Klasik özyinelemeli Fibonacci tanımı
`fib(n) = fib(n-1) + fib(n-2)`, `fib(0)=0`, `fib(1)=1`.

**Akademik Referans:**
> Patterson, D. A., & Hennessy, J. L. (2017).
> *Computer Organization and Design: RISC-V Edition*,
> Section 2.8.6 "Recursive Procedures", pp. 114-117 (Figure 2.27).
> Morgan Kaufmann.

> RISC-V International. **riscv-tests/benchmarks/fib**.
> https://github.com/riscv-software-src/riscv-tests/tree/master/benchmarks
> (Recursive Fibonacci benchmark, default n=20).

> MIT 6.004 *Computation Structures* (2023), Lab 6: "Recursion on RISC-V".
> https://6004.mit.edu/

**Beklenen Çıktı:** `fib(8) = 21 = 0b010101` (LED4, LED2, LED0 yanık)

**Sınadığı Mimari Özellikler:**
- Özyinelemeli alt program çağrısı (`jal ra, fib` × N kez)
- Stack pointer yönetimi (`sp`, push/pop)
- Return adresi koruma (`ra` kaydetme/yükleme)
- RISC-V C ABI uyumluluğu (`a0` = argüman + dönüş değeri)
- Kontekst geri yükleme (`lw`, `addi sp, sp, 12`)

---

## Kaynak Materyallerinin Toplam Listesi

1. **Patterson, D. A. & Hennessy, J. L.** (2017). *Computer Organization
   and Design: The Hardware/Software Interface, RISC-V Edition*. Morgan Kaufmann.
   — Mimari eğitimde **dünyada en yaygın kabul gören referans kitap**.

2. **Waterman, A. & Asanović, K.** (2019). *The RISC-V Instruction Set
   Manual, Volume I: Unprivileged ISA, Version 20191213*. RISC-V Foundation.
   — RISC-V ISA'nın **resmi tanımı**.

3. **RISC-V International**. (2024). *riscv-tests*: Resmi ISA test ve
   benchmark repository'si. https://github.com/riscv-software-src/riscv-tests
   — Endüstride RV32I/RV64I sentez doğrulamasında **fiili standart**.

4. **MIT 6.004** *Computation Structures* (2023). Massachusetts Institute
   of Technology. https://6004.mit.edu/
   — Üniversite seviyesinde RISC-V eğitimi için referans müfredat.

5. **RISC-V Application Binary Interface (psABI)** Specification.
   https://github.com/riscv-non-isa/riscv-elf-psabi-doc
   — Register kullanımı, calling convention için **standart**.

---

## Derleme ve Çalıştırma

```powershell
cd C:\Users\Yasin\Desktop\sunum3\sistem_proglamlama_proje_3

.\build.ps1 -Asm ..\tests\std_a_gauss_sum.asm
.\build.ps1 -Asm ..\tests\std_b_bubble_sort.asm
.\build.ps1 -Asm ..\tests\std_c_fib_recursive.asm
```

Üretilen `.mem` dosyaları `build/` klasöründedir. IDE üzerinden veya
`host_app/host_loader.py` ile FPGA'e yüklenir.
