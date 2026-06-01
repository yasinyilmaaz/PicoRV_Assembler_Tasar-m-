// XMODEM-CRC Loader FSM
// Paket formatı: [SOH=0x01][SEQ][~SEQ][128 bayt veri][CRC HI][CRC LO]
// EOT = 0x04 yükleme bitti.
// Sırasında CPU resetn'i 0 tutulur. Bitince cpu_resetn = 1.
//
// Veri belleğe 0x0000'dan itibaren 32-bit kelime hizalı yazılır (little-endian).
module loader_fsm #(
    parameter CLK_FREQ = 27_000_000,
    parameter BAUD     = 115200
)(
    input  wire        clk,
    input  wire        resetn,        // sistem reset (buton)
    // UART
    input  wire [7:0]  rx_data,
    input  wire        rx_valid,
    output reg  [7:0]  tx_data,
    output reg         tx_start,
    input  wire        tx_busy,
    // Bellek yazma portu
    output reg         mem_we,
    output reg  [12:0] mem_waddr,     // kelime adresi (8K kelime = 32KB)
    output reg  [31:0] mem_wdata,
    // CPU kontrol
    output reg         cpu_resetn,
    output reg         loading,       // gösterge LED
    output reg         done           // gösterge LED
);
    // XMODEM byte değerleri
    localparam SOH = 8'h01;
    localparam EOT = 8'h04;
    localparam ACK = 8'h06;
    localparam NAK = 8'h15;
    localparam C_C = 8'h43; // 'C' - CRC modunda başlat

    // CRC
    reg crc_clear, crc_en;
    reg [7:0] crc_in;
    wire [15:0] crc_out;
    crc16 u_crc (
        .clk(clk), .resetn(resetn),
        .clear(crc_clear), .en(crc_en),
        .data(crc_in), .crc(crc_out)
    );

    // FSM
    localparam S_INIT     = 4'd0,
               S_SEND_C   = 4'd1,
               S_WAIT_HDR = 4'd2,
               S_SEQ      = 4'd3,
               S_NSEQ     = 4'd4,
               S_DATA     = 4'd5,
               S_CRC_HI   = 4'd6,
               S_CRC_LO   = 4'd7,
               S_SEND_ACK = 4'd8,
               S_SEND_NAK = 4'd9,
               S_DONE     = 4'd10,
               S_WAIT_TX  = 4'd11;

    reg [3:0]  state, ret_state;
    reg [7:0]  expected_seq;
    reg [7:0]  rx_seq, rx_nseq;
    reg [7:0]  byte_cnt;        // 0..127
    reg [15:0] rx_crc;
    reg [1:0]  byte_lane;       // 32-bit kelime için bayt indeksi
    reg [31:0] word_buf;
    reg [12:0] cur_waddr;       // toplam yazma adresi
    reg [23:0] timeout_cnt;     // C gönderme periyodu
    reg [7:0]  tx_next;         // gönderilecek karakter

    // 1 saniyelik timeout sayacı (init aşamasında C tekrar gönder)
    localparam ONE_SEC = CLK_FREQ;

    always @(posedge clk) begin
        if (!resetn) begin
            state        <= S_INIT;
            ret_state    <= S_INIT;
            cpu_resetn   <= 1'b0;
            loading      <= 1'b0;
            done         <= 1'b0;
            mem_we       <= 1'b0;
            mem_waddr    <= 0;
            mem_wdata    <= 0;
            tx_start     <= 0;
            tx_data      <= 0;
            crc_clear    <= 0;
            crc_en       <= 0;
            crc_in       <= 0;
            expected_seq <= 8'd1;
            byte_cnt     <= 0;
            byte_lane    <= 0;
            word_buf     <= 0;
            cur_waddr    <= 0;
            timeout_cnt  <= 0;
            rx_seq       <= 0; rx_nseq <= 0; rx_crc <= 0;
            tx_next      <= 0;
        end else begin
            // varsayılanlar
            mem_we    <= 0;
            tx_start  <= 0;
            crc_clear <= 0;
            crc_en    <= 0;

            case (state)
                // Başlangıç: hosta "ben CRC modundayım" demek için 'C' gönder
                S_INIT: begin
                    cpu_resetn  <= 0;
                    loading     <= 1;
                    done        <= 0;
                    timeout_cnt <= 0;
                    tx_next     <= C_C;
                    state       <= S_SEND_C;
                end
                S_SEND_C: begin
                    if (!tx_busy) begin
                        tx_data  <= tx_next;
                        tx_start <= 1'b1;
                        state    <= S_WAIT_HDR;
                    end
                end

                // Paket başlığı bekle
                S_WAIT_HDR: begin
                    timeout_cnt <= timeout_cnt + 1'b1;
                    if (timeout_cnt == ONE_SEC[23:0]) begin
                        // 1 sn cevap yoksa tekrar 'C' gönder
                        timeout_cnt <= 0;
                        tx_next     <= C_C;
                        state       <= S_SEND_C;
                    end
                    if (rx_valid) begin
                        if (rx_data == SOH) begin
                            crc_clear <= 1'b1;
                            byte_cnt  <= 0;
                            byte_lane <= 0;
                            word_buf  <= 0;
                            state     <= S_SEQ;
                        end else if (rx_data == EOT) begin
                            tx_next <= ACK;
                            ret_state <= S_DONE;
                            state   <= S_WAIT_TX;
                        end
                    end
                end

                S_SEQ:  if (rx_valid) begin rx_seq  <= rx_data; state <= S_NSEQ; end
                S_NSEQ: if (rx_valid) begin rx_nseq <= rx_data; state <= S_DATA;  end

                S_DATA: if (rx_valid) begin
                    crc_in <= rx_data; crc_en <= 1'b1;
                    case (byte_lane)
                        2'd0: word_buf[7:0]   <= rx_data;
                        2'd1: word_buf[15:8]  <= rx_data;
                        2'd2: word_buf[23:16] <= rx_data;
                        2'd3: word_buf[31:24] <= rx_data;
                    endcase
                    if (byte_lane == 2'd3) begin
                        // sadece sıra doğruysa belleğe yaz; ama yine de toplayalım
                        // (yanlış paket sonunda NAK ile reddedilirse adres geri alınmaz)
                        // Güvenlik için: yazmayı paket sonunda CRC OK olunca yapacağız.
                        // Bu nedenle word_buf'ı geçici tutup CRC kontrolünde yazacağız.
                        byte_lane <= 0;
                    end else byte_lane <= byte_lane + 1'b1;

                    if (byte_cnt == 8'd127) state <= S_CRC_HI;
                    else byte_cnt <= byte_cnt + 1'b1;
                end

                S_CRC_HI: if (rx_valid) begin rx_crc[15:8] <= rx_data; state <= S_CRC_LO; end
                S_CRC_LO: if (rx_valid) begin
                    rx_crc[7:0] <= rx_data;
                    // 1 saat sonra CRC karşılaştır
                    state <= S_SEND_ACK;
                end

                S_SEND_ACK: begin
                    // CRC ve seq kontrolü
                    if ((rx_seq == expected_seq) &&
                        (rx_nseq == (8'hFF - expected_seq)) &&
                        ({rx_crc[15:8], rx_crc[7:0]} == crc_out)) begin
                        // Paket OK -> ACK + belleğe taşı
                        expected_seq <= expected_seq + 8'd1;
                        tx_next      <= ACK;
                        // 128 bayt = 32 kelime; bunlar zaten geçici word_buf'a tek tek
                        // yazıldı ama biz onları belleğe paket sonrası tek tek yazmak
                        // yerine, S_DATA içinde bellek portuna her 4 bayt için 1 yazma
                        // yapsaydık daha verimli olurdu. Burada basitlik için:
                        // word_buf en son kelimeyi tutuyor; ancak tüm paketi yazmak
                        // gerekir. Çözüm: S_DATA içinde her tam kelimede mem_we ile yaz.
                        // (Bunu aşağıda hallediyoruz — ACK gönderirken yalnızca cur_waddr'i ileri al.)
                        cur_waddr <= cur_waddr; // already advanced in S_DATA
                        ret_state <= S_WAIT_HDR;
                    end else begin
                        // Hatalı paket: NAK ve belleği bir önceki kelime adresine geri al
                        tx_next   <= NAK;
                        cur_waddr <= cur_waddr - 13'd32; // 32 kelime geri
                        ret_state <= S_WAIT_HDR;
                    end
                    state <= S_WAIT_TX;
                end

                S_WAIT_TX: begin
                    if (!tx_busy) begin
                        tx_data  <= tx_next;
                        tx_start <= 1'b1;
                        timeout_cnt <= 0;
                        state    <= ret_state;
                    end
                end

                S_DONE: begin
                    loading    <= 0;
                    done       <= 1;
                    cpu_resetn <= 1'b1;   // İŞLEMCİYİ ÇALIŞTIR
                end

                default: state <= S_INIT;
            endcase

            // S_DATA içinde her 4. bayttan sonra belleğe doğrudan yaz
            // (mem_we yukarıda varsayılan 0 idi; burada override ediyoruz)
            if (state == S_DATA && rx_valid && byte_lane == 2'd3) begin
                mem_we    <= 1'b1;
                mem_waddr <= cur_waddr;
                mem_wdata <= {rx_data, word_buf[23:16], word_buf[15:8], word_buf[7:0]};
                cur_waddr <= cur_waddr + 1'b1;
            end
        end
    end
endmodule
