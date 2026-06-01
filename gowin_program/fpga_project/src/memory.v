// 8K x 32-bit (32 KB) RAM - Gowin BSRAM olarak sentezlenecek şekilde
// ----------------------------------------------------------------------
// Mimari notu:
//   Loader FSM, CPU resetn=0 iken belleğe yazar; yükleme bittiğinde
//   cpu_resetn=1 olur ve artık yalnızca CPU yazar/okur. İki port aynı
//   anda asla aktif olmadığı için, fiziksel olarak TEK portlu BSRAM
//   yeterlidir. Bu nedenle giriş tarafında bir mux ile yazma kaynağını
//   seçiyoruz (loader vs CPU). 4 ayrı bayt-bellek dizisi kullanmak,
//   Gowin sentezleyicisinin (synplify) bu yapıyı 4 adet B-SRAM bloğuna
//   doğrudan eşlemesini sağlar; aksi halde "262144 DFF" hatası alınır.
// ----------------------------------------------------------------------
module memory (
    input  wire        clk,
    // Loader port (yalnızca yazma)
    input  wire        ld_we,
    input  wire [12:0] ld_addr,
    input  wire [31:0] ld_wdata,
    // CPU portu (PicoRV32 native bus)
    input  wire        mem_valid,
    output reg         mem_ready,
    input  wire [31:0] mem_addr,
    input  wire [31:0] mem_wdata,
    input  wire [3:0]  mem_wstrb,
    output reg  [31:0] mem_rdata
);
    // 4 x 8K x 8-bit BSRAM blokları (bayt strobe için ayrı diziler)
    reg [7:0] ram0 [0:8191];
    reg [7:0] ram1 [0:8191];
    reg [7:0] ram2 [0:8191];
    reg [7:0] ram3 [0:8191];

    // Yazma kaynağı mux'u
    wire        cpu_we   = mem_valid & (|mem_wstrb) & ~mem_ready;
    wire [12:0] waddr    = ld_we ? ld_addr        : mem_addr[14:2];
    wire [31:0] wdata    = ld_we ? ld_wdata       : mem_wdata;
    wire [3:0]  wstrb    = ld_we ? 4'b1111        : mem_wstrb;
    wire        we_any   = ld_we | cpu_we;

    // Okuma adresi her zaman CPU portundan
    wire [12:0] raddr    = mem_addr[14:2];

    always @(posedge clk) begin
        if (we_any) begin
            if (wstrb[0]) ram0[waddr] <= wdata[7:0];
            if (wstrb[1]) ram1[waddr] <= wdata[15:8];
            if (wstrb[2]) ram2[waddr] <= wdata[23:16];
            if (wstrb[3]) ram3[waddr] <= wdata[31:24];
        end
        // Senkron okuma (BSRAM kuralı)
        mem_rdata <= {ram3[raddr], ram2[raddr], ram1[raddr], ram0[raddr]};

        // Hazır sinyali
        mem_ready <= mem_valid & ~mem_ready;
    end
endmodule
