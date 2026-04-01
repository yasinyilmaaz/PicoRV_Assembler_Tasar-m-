#include <stdio.h>
#include <stdlib.h>
#include <string.h>  
#include <stdint.h>

#ifdef _WIN32
#include <io.h>
#define F_OK 0
#define access _access
#else
#include <unistd.h>
#endif

#define MAX_LINE_LEN 256
#define MAX_SYMBOLS 100 // Raporundaki S degeri

// --- VERI YAPILARI (Dizi Tabanli SYMTAB) ---
typedef struct {
    char name[32];
    uint32_t address;
} Symbol;

Symbol symbol_table[MAX_SYMBOLS];
int symbol_count = 0;

typedef struct {
    char name[16];
    char type;
    uint8_t opcode, funct3, funct7;
} InstructionInfo;

InstructionInfo opcode_table[] = {
    {"add",  'R', 0x33, 0x0, 0x00},
    {"sub",  'R', 0x33, 0x0, 0x20},
    {"addi", 'I', 0x13, 0x0, 0x00},
    {"beq",  'B', 0x63, 0x0, 0x00},
    {"lw",   'I', 0x03, 0x2, 0x00},
    {"sw",   'S', 0x23, 0x2, 0x00}
};

// --- SEMBOL TABLOSU FONKSIYONLARI (Linear Search - O(N)) ---

int get_label_address(char* label) {
    for (int i = 0; i < symbol_count; i++) {
        if (strcmp(symbol_table[i].name, label) == 0) return symbol_table[i].address;
    }
    return -1;
}

// --- DIGER YARDIMCI FONKSIYONLAR ---

int get_register_num(char* reg) {
    if (reg == NULL || reg[0] != 'x') return -1;   // pass2 de  reg var mı ve format gereği x ile başlıyor mu ?
    return atoi(reg + 1);
}

void generate_output_filename(const char* input_path, char* output_name) {
    char base_name[256]; //deneme_output.mem ismi işte bu değişken sayesinde oluşuyor.
    strcpy(base_name, input_path);
    char* last_dot = strrchr(base_name, '.');
    if (last_dot) *last_dot = '\0';
    sprintf(output_name, "%s_output.mem", base_name);
    int counter = 2;
    while (access(output_name, F_OK) != -1) {
        sprintf(output_name, "%s_output_%d.mem", base_name, counter++);
    }
}

// --- TWO-PASS ASSEMBLER MOTORU ---

int process_passes(int pass_num, FILE* in, FILE* out) {
    char line[MAX_LINE_LEN];
    uint32_t current_pc = 0;
    int line_number = 0; //o an okunan satırın kaçıncı satır olduğunu takip etmek için kullanılır.
    int has_error = 0;  //Eğer tek bir satırda bile hata varsa, tüm derleme işlemini "başarısız" olarak işaretlemek.

    fseek(in, 0, SEEK_SET);  //Hocam, eğer bu satırı silersen Pass 1 dosyayı okur bitirir, ancak Pass 2 başladığında dosyanın sonunda olduğu için hiçbir şey okuyamaz.

    while (fgets(line, sizeof(line), in)) {
        line_number++;
        char* comment = strchr(line, ';'); if (comment) *comment = '\0';
        char* label_ptr = strchr(line, ':');
        char* content = line;

        // Pass 1: Etiket Kaydi
        if (label_ptr) {
            *label_ptr = '\0';
            char* l_name = strtok(line, " \t\r\n");
            if (pass_num == 1 && l_name) {
                if (symbol_count < MAX_SYMBOLS) {
                    strcpy(symbol_table[symbol_count].name, l_name);
                    symbol_table[symbol_count].address = current_pc;
                    symbol_count++;
                }
            }
            content = label_ptr + 1;
        }

        char* mnemonic = strtok(content, " ,()\t\r\n");
        if (!mnemonic) continue;

        // Direktifler
        if (mnemonic[0] == '.') {  //Başındaki . işaretini görünce program bu derektif der
            if (strcmp(mnemonic, ".org") == 0) {
                char* addr_str = strtok(NULL, " \t\r\n");
                if (addr_str) current_pc = (uint32_t)strtol(addr_str, NULL, 0);
            }
            else if (strcmp(mnemonic, ".word") == 0) {
                if (pass_num == 2) {
                    char* v = strtok(NULL, " \t\r\n");
                    if (v) fprintf(out, "%08X\n", (uint32_t)strtol(v, NULL, 0));
                    if (v) fprintf(out, "%08X\n", (uint32_t)strtol(v, NULL, 0));
                }
                current_pc += 4;
            }
            else if (strcmp(mnemonic, ".end") == 0) break;
            continue;
        }

        // Pass 2: Makine Kodu Uretimi
        if (pass_num == 2) {
            int found = 0;  // komutun var olup olmadığını her dongüde 1 olarak gösteriri.(add)
            for (int i = 0; i < 6; i++) {
                if (strcmp(mnemonic, opcode_table[i].name) == 0) {
                    found = 1;
                    uint32_t mc = 0;
                    if (opcode_table[i].type == 'R') {
                        int rd = get_register_num(strtok(NULL, " ,()"));  // İşlemin sonucu hangi register'a yazılacak?(x1)
                        int rs1 = get_register_num(strtok(NULL, " ,()")); // Birinci sayı hangi register'dan alınacak? (x2)
                        int rs2 = get_register_num(strtok(NULL, " ,()")); // İkinci sayı hangi register'dan alınacak?
                        if (rd == -1 || rs1 == -1 || rs2 == -1) { printf("HATA (Satir %d): Gecersiz register!\n", line_number); has_error = 1; break; }
                        mc = (opcode_table[i].funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (opcode_table[i].funct3 << 12) | (rd << 7) | opcode_table[i].opcode;  // bayneri kısmını bura 
                    }
                    else if (opcode_table[i].type == 'I') {
                        int rd = get_register_num(strtok(NULL, " ,()"));
                        int imm = atoi(strtok(NULL, " ,()"));
                        int rs1 = get_register_num(strtok(NULL, " ,()"));
                        if (rd == -1 || rs1 == -1) { printf("HATA (Satir %d): Gecersiz register!\n", line_number); has_error = 1; break; }
                        mc = ((imm & 0xFFF) << 20) | (rs1 << 15) | (opcode_table[i].funct3 << 12) | (rd << 7) | opcode_table[i].opcode;
                    }
                    else if (opcode_table[i].type == 'S') {
                        int rs2 = get_register_num(strtok(NULL, " ,()"));
                        int imm = atoi(strtok(NULL, " ,()"));
                        int rs1 = get_register_num(strtok(NULL, " ,()"));
                        mc = (((imm >> 5) & 0x7F) << 25) | (rs2 << 20) | (rs1 << 15) | (opcode_table[i].funct3 << 12) | ((imm & 0x1F) << 7) | opcode_table[i].opcode;
                    }
                    else if (opcode_table[i].type == 'B') {
                        int rs1 = get_register_num(strtok(NULL, " ,()"));
                        int rs2 = get_register_num(strtok(NULL, " ,()"));
                        char* lbl = strtok(NULL, " ,()");
                        int target = get_label_address(lbl);
                        if (target == -1) { printf("HATA (Satir %d): Tanimsiz etiket: %s\n", line_number, lbl); has_error = 1; break; }
                        int off = target - (int)current_pc;
                        mc = (((off >> 12) & 1) << 31) | (((off >> 5) & 0x3F) << 25) | (rs2 << 20) | (rs1 << 15) | (opcode_table[i].funct3 << 12) | (((off >> 1) & 0xF) << 8) | (((off >> 11) & 1) << 7) | opcode_table[i].opcode;
                    }
                    fprintf(out, "%08X\n", mc);   // hex kodunun üretildiği yer 
                    break;
                }
            }
            if (!found) { printf("HATA (Satir %d): Gecersiz komut: %s\n", line_number, mnemonic); has_error = 1; }
        }
        current_pc += 4;
    }
    return has_error;
}

int main(int argc, char* argv[]) {
    if (argc < 2) return printf("Kullanim: ./assembler test.asm\n"), 1;
    FILE* f = fopen(argv[1], "r"); if (!f) return perror("Dosya acilamadi"), 1;
    char out_fn[512]; generate_output_filename(argv[1], out_fn);
    process_passes(1, f, NULL);
    FILE* out = fopen(out_fn, "w");
    if (process_passes(2, f, out)) printf("\nHATA: Derleme basarisiz!\n");
    else printf("Basarili! Cikti: %s\n", out_fn);
    fclose(f); fclose(out);
    return 0;
}