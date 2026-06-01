// UART Verici (Transmitter) - ACK/NAK göndermek için
module uart_tx #(
    parameter CLK_FREQ = 27_000_000,
    parameter BAUD     = 115200
)(
    input  wire        clk,
    input  wire        resetn,
    input  wire [7:0]  data,
    input  wire        start,
    output reg         tx,
    output reg         busy
);
    localparam integer DIV = CLK_FREQ / BAUD;
    reg [15:0] cnt;
    reg [3:0]  bit_idx;
    reg [9:0]  shift; // start + 8 data + stop

    always @(posedge clk) begin
        if (!resetn) begin
            tx <= 1'b1; busy <= 0; cnt <= 0; bit_idx <= 0; shift <= 10'h3FF;
        end else begin
            if (!busy) begin
                tx <= 1'b1;
                if (start) begin
                    shift   <= {1'b1, data, 1'b0}; // stop, data, start
                    busy    <= 1'b1;
                    cnt     <= 0;
                    bit_idx <= 0;
                end
            end else begin
                if (cnt == DIV[15:0]-1) begin
                    cnt <= 0;
                    tx  <= shift[0];
                    shift <= {1'b1, shift[9:1]};
                    if (bit_idx == 4'd9) busy <= 0;
                    else bit_idx <= bit_idx + 1'b1;
                end else cnt <= cnt + 1'b1;
            end
        end
    end
endmodule
