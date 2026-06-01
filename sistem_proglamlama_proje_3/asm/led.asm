.text
.global led_yak

led_yak:
    ; LED adresini (0x10000000) hazýrla
    lui x5, 0x10000    // hedef adresimiz olan 0x10000 x5 registrýna veridik     
    
    ; x10'dan gelen deðeri (0) o adrese KELÝME (32-bit) olarak yaz
    ; top.v içindeki mem_wdata[0] bunu bu sayede yakalayacak
    sw x10, 0(x5)         //   X10 registrýndaki 0 deðerini hedef adres olan x5 in tututðu adrese göturup yazýcaz
    
    ; Ana programa geri dön
    jr x1