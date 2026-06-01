// Tang Nano 9K - PicoRV32 + UART XMODEM Loader
//
// Bellek haritası (CPU tarafı):
//   0x0000_0000 - 0x0000_7FFF : RAM (32KB, kod + veri)
//   0x1000_0000               : LED bank yazma (alt 6 bit -> 6 LED)
//   0x1000_0010               : Buton okuma  (alt 2 bit S1, S2)
//
module top (
    input  wire       clk,        // 27 MHz
    input  wire       resetn,     // S1 buton (aktif düşük)
    input  wire       uart_rx,    // PC -> FPGA
    output wire       uart_tx,    // FPGA -> PC
    input  wire       btn_user,   // S2 buton (kullanıcı testleri için)
    output reg  [5:0] led         // 6 LED (aktif düşük: 0 = yanık)
);
    // --- UART RX/TX ---
    wire [7:0] rx_byte;
    wire       rx_valid;
    wire [7:0] tx_byte;
    wire       tx_start;
    wire       tx_busy;

    uart_rx #(.CLK_FREQ(27_000_000), .BAUD(115200)) u_rx (
        .clk(clk), .resetn(resetn), .rx(uart_rx),
        .data(rx_byte), .valid(rx_valid)
    );
    uart_tx #(.CLK_FREQ(27_000_000), .BAUD(115200)) u_tx (
        .clk(clk), .resetn(resetn),
        .data(tx_byte), .start(tx_start),
        .tx(uart_tx), .busy(tx_busy)
    );

    // --- Loader FSM ---
    wire        ld_we;
    wire [12:0] ld_addr;
    wire [31:0] ld_wdata;
    wire        cpu_resetn;
    wire        loading, done;

    loader_fsm #(.CLK_FREQ(27_000_000), .BAUD(115200)) u_loader (
        .clk(clk), .resetn(resetn),
        .rx_data(rx_byte), .rx_valid(rx_valid),
        .tx_data(tx_byte), .tx_start(tx_start), .tx_busy(tx_busy),
        .mem_we(ld_we), .mem_waddr(ld_addr), .mem_wdata(ld_wdata),
        .cpu_resetn(cpu_resetn),
        .loading(loading), .done(done)
    );

    // --- PicoRV32 ---
    wire        mem_valid;
    wire        mem_ready;
    wire [31:0] mem_addr;
    wire [31:0] mem_wdata;
    wire [3:0]  mem_wstrb;
    wire [31:0] mem_rdata;

    wire        cpu_mem_valid;
    wire        cpu_mem_ready;
    wire [31:0] cpu_mem_rdata;

    picorv32 #(
        .ENABLE_COUNTERS(0),
        .ENABLE_MUL(0),
        .ENABLE_DIV(0),
        .COMPRESSED_ISA(0),
        .BARREL_SHIFTER(0)
    ) cpu (
        .clk         (clk        ),
        .resetn      (cpu_resetn ),
        .mem_valid   (mem_valid  ),
        .mem_ready   (mem_ready  ),
        .mem_addr    (mem_addr   ),
        .mem_wdata   (mem_wdata  ),
        .mem_wstrb   (mem_wstrb  ),
        .mem_rdata   (mem_rdata  )
    );

    // --- Bellek + GPIO çoklayıcı ---
    wire is_ram  = (mem_addr[31:28] == 4'h0);
    wire is_gpio = (mem_addr[31:28] == 4'h1);

    wire        ram_valid = mem_valid & is_ram;
    wire [31:0] ram_rdata;
    wire        ram_ready;

    memory u_mem (
        .clk(clk),
        .ld_we(ld_we), .ld_addr(ld_addr), .ld_wdata(ld_wdata),
        .mem_valid(ram_valid), .mem_ready(ram_ready),
        .mem_addr(mem_addr), .mem_wdata(mem_wdata),
        .mem_wstrb(mem_wstrb), .mem_rdata(ram_rdata)
    );

    // GPIO bloğu
    reg [31:0] gpio_rdata;
    reg        gpio_ready;
    reg [5:0]  led_reg;

    always @(posedge clk) begin
        gpio_ready <= 1'b0;
        if (!cpu_resetn) begin
            led_reg <= 6'b111111; // sönük
        end else if (mem_valid && is_gpio && !gpio_ready) begin
            gpio_ready <= 1'b1;
            case (mem_addr[7:0])
                8'h00: begin
                    if (mem_wstrb != 0) led_reg <= ~mem_wdata[5:0]; // 1 yaz = LED yansın
                    gpio_rdata <= {26'b0, ~led_reg};
                end
                8'h10: begin
                    gpio_rdata <= {30'b0, ~btn_user, ~resetn};
                end
                default: gpio_rdata <= 32'h0;
            endcase
        end
    end

    assign mem_ready = is_ram ? ram_ready : (is_gpio ? gpio_ready : 1'b0);
    assign mem_rdata = is_ram ? ram_rdata : gpio_rdata;

    // LED çıkışı: yükleme sırasında "loading" göster, sonra CPU LED'leri
    always @(posedge clk) begin
        if (loading)      led <= ~6'b000001;       // tek LED yanar
        else if (done)    led <= led_reg;          // CPU kontrolü
        else              led <= 6'b111111;
    end
endmodule
