#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <ctype.h>

#define MAX_LINE_LEN 256
#define MAX_TEXT 1000
#define MAX_DATA 1000
#define MAX_RELOCS 100
#define MAX_EXTERNS 100
#define HASH_SIZE 256  // Hash tablosu boyutu

typedef struct {
    char name[50];
    uint32_t address;
    char scope[10];
    char section[10];
} Symbol;

// Hash Table icin Bagli Liste Dugumu
typedef struct SymbolNode {
    Symbol info;
    struct SymbolNode* next;
} SymbolNode;

typedef struct {
    uint32_t offset;
    char type;
    char symbol[50];
} Reloc;

typedef struct {
    char name[10];
    char type;
    uint8_t opcode, funct3, funct7;
} InstructionInfo;

// Hash Tablosu (Global Dizi)
SymbolNode* hash_table[HASH_SIZE] = { NULL };
int symbol_count = 0;

uint32_t text_section[MAX_TEXT];
int text_count = 0;

uint32_t data_section[MAX_DATA];
int data_count = 0;

Reloc reloc_table[MAX_RELOCS];
int reloc_count = 0;

char extern_table[MAX_EXTERNS][50];
int extern_count = 0;

// Genisletilmis RV32I Komut Seti
InstructionInfo opcode_table[] = {
    // R-Type
    {"add",  'R', 0x33, 0x0, 0x00},
    {"sub",  'R', 0x33, 0x0, 0x20},
    {"sll",  'R', 0x33, 0x1, 0x00},
    {"xor",  'R', 0x33, 0x4, 0x00},
    {"srl",  'R', 0x33, 0x5, 0x00},
    {"sra",  'R', 0x33, 0x5, 0x20},
    {"or",   'R', 0x33, 0x6, 0x00},
    {"and",  'R', 0x33, 0x7, 0x00},

    // I-Type
    {"addi", 'I', 0x13, 0x0, 0x00},
    {"xori", 'I', 0x13, 0x4, 0x00},
    {"ori",  'I', 0x13, 0x6, 0x00},
    {"andi", 'I', 0x13, 0x7, 0x00},

    // I-Type (Load)
    {"lb",   'I', 0x03, 0x0, 0x00},
    {"lh",   'I', 0x03, 0x1, 0x00},
    {"lw",   'I', 0x03, 0x2, 0x00},

    // S-Type (Store)
    {"sb",   'S', 0x23, 0x0, 0x00},
    {"sh",   'S', 0x23, 0x1, 0x00},
    {"sw",   'S', 0x23, 0x2, 0x00},

    // B-Type (Branch)
    {"beq",  'B', 0x63, 0x0, 0x00},
    {"bne",  'B', 0x63, 0x1, 0x00},
    {"blt",  'B', 0x63, 0x4, 0x00},
    {"bge",  'B', 0x63, 0x5, 0x00},

    // J-Type & Jump Register
    {"jal",  'J', 0x6F, 0x0, 0x00},
    {"jalr", 'I', 0x67, 0x0, 0x00}, // jalr I-Type encoding kullanir

    // U-Type
    {"lui",   'U', 0x37, 0x0, 0x00},
    {"auipc", 'U', 0x17, 0x0, 0x00}
};

int opcode_count = sizeof(opcode_table) / sizeof(opcode_table[0]);

// --- HASH TABLE FONKSIYONLARI ---

// Basit ve hizli bir String Hashing Algoritmasi (djb2)
unsigned int hash(char* str) {
    unsigned int hash = 5381;
    int c;
    while ((c = *str++)) {
        hash = ((hash << 5) + hash) + c;
    }
    return hash % HASH_SIZE;
}

// Sembol Arama (Bulunamazsa NULL doner)
Symbol* find_symbol(char* name) {
    unsigned int index = hash(name);
    SymbolNode* current = hash_table[index];

    while (current != NULL) {
        if (strcmp(current->info.name, name) == 0) {
            return &(current->info);
        }
        current = current->next;
    }
    return NULL;
}

// Sembol Ekleme (Basa Ekleme / Chaining)
void insert_symbol(char* name, uint32_t address, char* scope, char* section) {
    if (find_symbol(name) != NULL) return; // Zaten varsa ekleme

    unsigned int index = hash(name);
    SymbolNode* new_node = (SymbolNode*)malloc(sizeof(SymbolNode));

    strcpy(new_node->info.name, name);
    new_node->info.address = address;
    strcpy(new_node->info.scope, scope);
    strcpy(new_node->info.section, section);

    new_node->next = hash_table[index];
    hash_table[index] = new_node;
    symbol_count++;
}

// --- YARDIMCI FONKSIYONLAR ---

void trim(char* s) {
    char* p = s;
    int len;
    while (isspace((unsigned char)*p)) p++;
    if (p != s) memmove(s, p, strlen(p) + 1);
    len = strlen(s);
    while (len > 0 && isspace((unsigned char)s[len - 1])) {
        s[len - 1] = '\0';
        len--;
    }
}

int get_register_num(char* reg) {
    if (reg == NULL || reg[0] != 'x') return 0;
    return atoi(reg + 1);
}

void add_extern_if_not_exists(char* name) {
    for (int i = 0; i < extern_count; i++) {
        if (strcmp(extern_table[i], name) == 0) return;
    }
    strcpy(extern_table[extern_count], name);
    extern_count++;
}

void add_reloc(uint32_t offset, char type, char* symbol) {
    reloc_table[reloc_count].offset = offset;
    reloc_table[reloc_count].type = type;
    strcpy(reloc_table[reloc_count].symbol, symbol);
    reloc_count++;
}

// --- ENCODING FONKSIYONLARI ---

uint32_t encode_R(InstructionInfo info, char* rd_s, char* rs1_s, char* rs2_s) {
    int rd = get_register_num(rd_s);
    int rs1 = get_register_num(rs1_s);
    int rs2 = get_register_num(rs2_s);
    return (info.funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (info.funct3 << 12) | (rd << 7) | info.opcode;
}

uint32_t encode_I(InstructionInfo info, char* rd_s, char* rs1_s, char* imm_s) {
    int rd = get_register_num(rd_s);
    int rs1 = get_register_num(rs1_s);
    int imm = atoi(imm_s);
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (info.funct3 << 12) | (rd << 7) | info.opcode;
}

uint32_t encode_B(InstructionInfo info, char* rs1_s, char* rs2_s, int offset) {
    int rs1 = get_register_num(rs1_s);
    int rs2 = get_register_num(rs2_s);
    return (((offset >> 12) & 0x1) << 31) | (((offset >> 5) & 0x3F) << 25) | (rs2 << 20) | (rs1 << 15) | (info.funct3 << 12) | (((offset >> 1) & 0xF) << 8) | (((offset >> 11) & 0x1) << 7) | info.opcode;
}

uint32_t encode_S(InstructionInfo info, char* rs2_s, char* imm_rs1_s) {
    char temp[50];
    strcpy(temp, imm_rs1_s);
    char* imm_str = strtok(temp, "(");
    char* rs1_str = strtok(NULL, ")");
    int imm = atoi(imm_str);
    int rs1 = get_register_num(rs1_str);
    int rs2 = get_register_num(rs2_s);
    return (((imm >> 5) & 0x7F) << 25) | (rs2 << 20) | (rs1 << 15) | (info.funct3 << 12) | ((imm & 0x1F) << 7) | info.opcode;
}

uint32_t encode_LW_SW(InstructionInfo info, char* rd_s, char* imm_rs1_s) {
    char temp[50];
    strcpy(temp, imm_rs1_s);
    char* imm_str = strtok(temp, "(");
    char* rs1_str = strtok(NULL, ")");
    int imm = atoi(imm_str);
    int rd = get_register_num(rd_s);
    int rs1 = get_register_num(rs1_str);
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (info.funct3 << 12) | (rd << 7) | info.opcode;
}

uint32_t encode_J(InstructionInfo info, char* rd_s, int offset) {
    int rd = get_register_num(rd_s);
    return (((offset >> 20) & 0x1) << 31) | (((offset >> 1) & 0x3FF) << 21) | (((offset >> 11) & 0x1) << 20) | (((offset >> 12) & 0xFF) << 12) | (rd << 7) | info.opcode;
}

// U-Type Encoder (lui, auipc) eklendi
uint32_t encode_U(InstructionInfo info, char* rd_s, char* imm_s) {
    int rd = get_register_num(rd_s);
    uint32_t imm = (uint32_t)strtoul(imm_s, NULL, 0); // Hex veya Dec alabilir
    // U-Type komutlarinda immediate degeri ust 20 bite yerlesir (12 bit shift)
    return ((imm & 0xFFFFF) << 12) | (rd << 7) | info.opcode;
}

void pass1(FILE* in) {
    char line[MAX_LINE_LEN];
    uint32_t current_text_pc = 0;
    uint32_t current_data_pc = 0;
    char current_section[10] = "TEXT";

    while (fgets(line, sizeof(line), in)) {
        char* comment = strchr(line, ';');
        if (comment) *comment = '\0';

        trim(line);
        if (strlen(line) == 0) continue;

        char* label_ptr = strchr(line, ':');

        if (label_ptr) {
            *label_ptr = '\0';
            trim(line);

            uint32_t addr = (strcmp(current_section, "TEXT") == 0) ? current_text_pc : current_data_pc;

            // Hash Table'a Ekleme
            insert_symbol(line, addr, "LOCAL", current_section);

            char* rest = label_ptr + 1;
            trim(rest);
            if (strlen(rest) == 0) continue;
            strcpy(line, rest);
        }

        char temp[MAX_LINE_LEN];
        strcpy(temp, line);
        char* mnemonic = strtok(temp, " ,\t\r\n");
        if (!mnemonic) continue;

        if (strcmp(mnemonic, ".text") == 0) { strcpy(current_section, "TEXT"); continue; }
        if (strcmp(mnemonic, ".data") == 0) { strcpy(current_section, "DATA"); continue; }
        if (strcmp(mnemonic, ".global") == 0) continue;
        if (strcmp(mnemonic, ".extern") == 0) continue;

        if (mnemonic[0] == '.') {
            if (strcmp(mnemonic, ".word") == 0) {
                if (strcmp(current_section, "TEXT") == 0) current_text_pc += 4;
                else current_data_pc += 4;
            }
            continue;
        }

        if (strcmp(current_section, "TEXT") == 0) current_text_pc += 4;
    }
}

void pass2(FILE* in) {
    char line[MAX_LINE_LEN];
    uint32_t current_text_pc = 0;
    uint32_t current_data_pc = 0;
    char current_section[10] = "TEXT";

    while (fgets(line, sizeof(line), in)) {
        char* comment = strchr(line, ';');
        if (comment) *comment = '\0';

        trim(line);
        if (strlen(line) == 0) continue;

        char* label_ptr = strchr(line, ':');
        if (label_ptr) {
            char* rest = label_ptr + 1;
            trim(rest);
            if (strlen(rest) == 0) continue;
            strcpy(line, rest);
        }

        char* mnemonic = strtok(line, " ,\t\r\n");
        if (!mnemonic) continue;

        if (strcmp(mnemonic, ".text") == 0) { strcpy(current_section, "TEXT"); continue; }
        if (strcmp(mnemonic, ".data") == 0) { strcpy(current_section, "DATA"); continue; }

        if (strcmp(mnemonic, ".global") == 0) {
            char* sym = strtok(NULL, " ,\t\r\n");
            Symbol* s = find_symbol(sym);
            if (s != NULL) strcpy(s->scope, "GLOBAL");
            continue;
        }

        if (strcmp(mnemonic, ".extern") == 0) {
            char* sym = strtok(NULL, " ,\t\r\n");
            if (sym) add_extern_if_not_exists(sym);
            continue;
        }

        if (mnemonic[0] == '.') {
            if (strcmp(mnemonic, ".word") == 0) {
                char* val_s = strtok(NULL, " ,\t\r\n");
                uint32_t val = (uint32_t)strtol(val_s, NULL, 0);
                if (strcmp(current_section, "TEXT") == 0) {
                    text_section[text_count++] = val;
                    current_text_pc += 4;
                }
                else {
                    data_section[data_count++] = val;
                    current_data_pc += 4;
                }
            }
            continue;
        }

        for (int i = 0; i < opcode_count; i++) {
            if (strcmp(mnemonic, opcode_table[i].name) == 0) {
                uint32_t mc = 0;

                if (opcode_table[i].type == 'R') {
                    char* rd = strtok(NULL, " ,\t\r\n");
                    char* rs1 = strtok(NULL, " ,\t\r\n");
                    char* rs2 = strtok(NULL, " ,\t\r\n");
                    mc = encode_R(opcode_table[i], rd, rs1, rs2);
                }
                else if (opcode_table[i].type == 'I') {
                    // Load komutlari (lw, lh, lb vb) veya jalr offset(rs1) formatinda olabilir
                    if (strcmp(mnemonic, "lw") == 0 || strcmp(mnemonic, "lh") == 0 || strcmp(mnemonic, "lb") == 0 || strcmp(mnemonic, "jalr") == 0) {
                        char* rd = strtok(NULL, " ,\t\r\n");
                        char* imm_rs1 = strtok(NULL, " ,\t\r\n");
                        mc = encode_LW_SW(opcode_table[i], rd, imm_rs1);
                    }
                    else { // addi, andi, ori, vb.
                        char* rd = strtok(NULL, " ,\t\r\n");
                        char* rs1 = strtok(NULL, " ,\t\r\n");
                        char* imm = strtok(NULL, " ,\t\r\n");
                        mc = encode_I(opcode_table[i], rd, rs1, imm);
                    }
                }
                else if (opcode_table[i].type == 'S') {
                    char* rs2 = strtok(NULL, " ,\t\r\n");
                    char* imm_rs1 = strtok(NULL, " ,\t\r\n");
                    mc = encode_S(opcode_table[i], rs2, imm_rs1);
                }
                else if (opcode_table[i].type == 'U') { // lui, auipc
                    char* rd = strtok(NULL, " ,\t\r\n");
                    char* imm = strtok(NULL, " ,\t\r\n");
                    mc = encode_U(opcode_table[i], rd, imm);
                }
                else if (opcode_table[i].type == 'B') {
                    char* rs1 = strtok(NULL, " ,\t\r\n");
                    char* rs2 = strtok(NULL, " ,\t\r\n");
                    char* target = strtok(NULL, " ,\t\r\n");

                    Symbol* s = find_symbol(target); // HASH ARAMASI
                    if (s != NULL && strcmp(s->section, "TEXT") == 0) {
                        int offset = s->address - current_text_pc;
                        mc = encode_B(opcode_table[i], rs1, rs2, offset);
                    }
                    else {
                        mc = encode_B(opcode_table[i], rs1, rs2, 0);
                        add_extern_if_not_exists(target);
                        add_reloc(current_text_pc, 'B', target);
                    }
                }
                else if (opcode_table[i].type == 'J') {
                    char* rd = strtok(NULL, " ,\t\r\n");
                    char* target = strtok(NULL, " ,\t\r\n");

                    Symbol* s = find_symbol(target); // HASH ARAMASI
                    if (s != NULL && strcmp(s->section, "TEXT") == 0) {
                        int offset = s->address - current_text_pc;
                        mc = encode_J(opcode_table[i], rd, offset);
                    }
                    else {
                        mc = encode_J(opcode_table[i], rd, 0);
                        add_extern_if_not_exists(target);
                        add_reloc(current_text_pc, 'J', target);
                    }
                }

                if (strcmp(current_section, "TEXT") == 0) {
                    text_section[text_count++] = mc;
                    current_text_pc += 4;
                }
                break;
            }
        }
    }
}

void write_object_file(char* out_name) {
    FILE* out = fopen(out_name, "w");

    fprintf(out, ".text\n");
    for (int i = 0; i < text_count; i++) fprintf(out, "%08X\n", text_section[i]);

    fprintf(out, ".data\n");
    for (int i = 0; i < data_count; i++) fprintf(out, "%08X\n", data_section[i]);

    fprintf(out, ".symbols\n");
    // Hash tablosu uzerinde dolasarak sembolleri dosyaya yazdirma
    for (int i = 0; i < HASH_SIZE; i++) {
        SymbolNode* current = hash_table[i];
        while (current != NULL) {
            fprintf(out, "%s %u %s %s\n",
                current->info.name,
                current->info.address,
                current->info.scope,
                current->info.section);
            current = current->next;
        }
    }

    fprintf(out, ".externs\n");
    for (int i = 0; i < extern_count; i++) fprintf(out, "%s\n", extern_table[i]);

    fprintf(out, ".relocs\n");
    for (int i = 0; i < reloc_count; i++) {
        fprintf(out, "%u %c %s\n", reloc_table[i].offset, reloc_table[i].type, reloc_table[i].symbol);
    }

    fclose(out);
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        printf("Kullanim: %s input.asm output.o\n", argv[0]);
        return 1;
    }

    FILE* f = fopen(argv[1], "r");
    if (!f) { printf("Hata: %s acilamadi!\n", argv[1]); return 1; }
    pass1(f);
    fclose(f);

    f = fopen(argv[1], "r");
    pass2(f);
    fclose(f);

    write_object_file(argv[2]);
    printf("Object dosyasi olusturuldu: %s\n", argv[2]);

    return 0;
}