// CRC-16/XMODEM (polinom 0x1021, başlangıç 0x0000, no reflect)
// Seri LFSR mimarisi - alan-verimli, UART hızı için yeterli (1 saat/bit)
module crc16 (
    input  wire        clk,
    input  wire        resetn,
    input  wire        clear,      // CRC'yi 0x0000'a resetler
    input  wire        en,         // veri geçerliyse 1 saat darbesi
    input  wire [7:0]  data,
    output reg  [15:0] crc
);
    integer i;
    reg [15:0] tmp;
    always @(posedge clk) begin
        if (!resetn || clear) begin
            crc <= 16'h0000;
        end else if (en) begin
            tmp = crc ^ {data, 8'h00};
            for (i = 0; i < 8; i = i + 1) begin
                if (tmp[15]) tmp = (tmp << 1) ^ 16'h1021;
                else         tmp = (tmp << 1);
            end
            crc <= tmp;
        end
    end
endmodule
