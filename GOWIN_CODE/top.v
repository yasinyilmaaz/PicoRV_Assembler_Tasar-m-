
module top (
    input clk,
    input resetn,
    output reg led_out // 5. LED (Pin 14)
);
    wire mem_valid;
    wire mem_ready;
    wire [31:0] mem_addr;
    wire [31:0] mem_wdata;
    wire [3:0] mem_wstrb;
    wire [31:0] mem_rdata;

    // --- İŞLEMCİ KONTROLÜ ---
    always @(posedge clk) begin
        if (!resetn) begin
            led_out <= 1'b1; // Reset anında LED söner
        end else begin
            // İşlemci 0x10000000 adresine yazdığında LED durumunu güncelle
            if (mem_valid && mem_wstrb && mem_addr == 32'h10000000) begin
                led_out <= mem_wdata[0]; 
            end
        end
    end

    picorv32 cpu (
        .clk         (clk        ),
        .resetn      (resetn     ),
        .mem_valid   (mem_valid  ),
        .mem_ready   (mem_ready  ),
        .mem_addr    (mem_addr   ),
        .mem_wdata   (mem_wdata  ),
        .mem_wstrb   (mem_wstrb  ),
        .mem_rdata   (mem_rdata  )
    );

    memory ram_inst (
        .clk         (clk        ),
        .mem_valid   (mem_valid  ),
        .mem_ready   (mem_ready  ),
        .mem_addr    (mem_addr   ),
        .mem_wdata   (mem_wdata  ),
        .mem_wstrb   (mem_wstrb  ),
        .mem_rdata   (mem_rdata  )
    );
endmodule