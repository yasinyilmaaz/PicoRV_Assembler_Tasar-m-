
module memory (
    input clk,
    input mem_valid,
    output reg mem_ready,
    input [31:0] mem_addr,
    input [31:0] mem_wdata,
    input [3:0] mem_wstrb,
    output reg [31:0] mem_rdata // Veri çıkış hattı burası olmalı
);
    // Hafıza modülün içinde tanımlanır, port listesinde değil
    // Boyutu 2048 hücreye (8KB) çıkardık
    reg [31:0] ram [0:2047]; 

    initial begin
        // firmware.mem dosyasını ram dizisine yükle
        $readmemh("firmware.mem", ram);
    end

    always @(posedge clk) begin
        mem_ready <= 0;
        if (mem_valid && !mem_ready) begin
            mem_ready <= 1;
            
            // Yazma İşlemleri
            if (mem_wstrb[0]) ram[mem_addr[31:2]][7:0]   <= mem_wdata[7:0];
            if (mem_wstrb[1]) ram[mem_addr[31:2]][15:8]  <= mem_wdata[15:8];
            if (mem_wstrb[2]) ram[mem_addr[31:2]][23:16] <= mem_wdata[23:16];
            if (mem_wstrb[3]) ram[mem_addr[31:2]][31:24] <= mem_wdata[31:24];
            
            // Okuma İşlemi
            mem_rdata <= ram[mem_addr[31:2]];
        end
    end
endmodule