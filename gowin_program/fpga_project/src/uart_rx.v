// UART Alıcı (Receiver) - 8N1, parametrik baud
// Tang Nano 9K 27 MHz, 115200 baud => CLK_DIV = 234
module uart_rx #(
    parameter CLK_FREQ = 27_000_000,
    parameter BAUD     = 115200
)(
    input  wire        clk,
    input  wire        resetn,
    input  wire        rx,
    output reg  [7:0]  data,
    output reg         valid
);
    localparam integer DIV   = CLK_FREQ / BAUD;
    localparam integer HALF  = DIV / 2;

    reg [15:0] cnt;
    reg [3:0]  bit_idx;
    reg [1:0]  state;
    reg        rx_s1, rx_s2;

    localparam S_IDLE  = 2'd0,
               S_START = 2'd1,
               S_DATA  = 2'd2,
               S_STOP  = 2'd3;

    // İki kademeli senkronizör
    always @(posedge clk) begin
        rx_s1 <= rx;
        rx_s2 <= rx_s1;
    end

    always @(posedge clk) begin
        if (!resetn) begin
            state   <= S_IDLE;
            cnt     <= 0;
            bit_idx <= 0;
            valid   <= 0;
            data    <= 0;
        end else begin
            valid <= 0;
            case (state)
                S_IDLE: begin
                    cnt <= 0; bit_idx <= 0;
                    if (rx_s2 == 1'b0) state <= S_START;
                end
                S_START: begin
                    if (cnt == HALF[15:0]) begin
                        if (rx_s2 == 1'b0) begin
                            cnt   <= 0;
                            state <= S_DATA;
                        end else state <= S_IDLE;
                    end else cnt <= cnt + 1'b1;
                end
                S_DATA: begin
                    if (cnt == DIV[15:0]-1) begin
                        cnt <= 0;
                        data[bit_idx] <= rx_s2;
                        if (bit_idx == 4'd7) state <= S_STOP;
                        else bit_idx <= bit_idx + 1'b1;
                    end else cnt <= cnt + 1'b1;
                end
                S_STOP: begin
                    if (cnt == DIV[15:0]-1) begin
                        valid <= 1'b1;
                        state <= S_IDLE;
                    end else cnt <= cnt + 1'b1;
                end
            endcase
        end
    end
endmodule
