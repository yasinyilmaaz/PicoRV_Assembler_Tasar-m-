#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#define MAX_OBJECTS 10
#define MAX_TEXT 1000
#define MAX_DATA 1000
#define MAX_SYMBOLS 200
#define MAX_RELOCS 200
#define MAX_LINE 256

typedef struct {
    char name[50];
    uint32_t offset;
    char scope[10];
    char section[10];
    uint32_t absolute_address;
} Symbol;

typedef struct {
    uint32_t offset;
    char type;
    char symbol[50];
} Reloc;

typedef struct {
    char filename[100];

    uint32_t text[MAX_TEXT];
    int text_count;

    uint32_t data[MAX_DATA];
    int data_count;

    Symbol symbols[MAX_SYMBOLS];
    int symbol_count;

    Reloc relocs[MAX_RELOCS];
    int reloc_count;

    uint32_t text_base_address;
    uint32_t data_base_address;
} ObjectFile;

/* ========================================================
   ESTAB (External Symbol Table) Veri Yapýsý
   Linker'ýn Pass 1 aþamasýnda doldurduðu ve tüm modüllerin
   ortaklaþa kullandýðý Dýþ Sembol Tablosudur.
   ======================================================== */
typedef struct {
    char name[50];
    uint32_t address;
} GlobalSymbol;

ObjectFile objects[MAX_OBJECTS];
int object_count = 0;

GlobalSymbol global_symbols[MAX_SYMBOLS]; // ESTAB Dizisi
int global_symbol_count = 0;

uint32_t final_text[MAX_TEXT * MAX_OBJECTS];
int final_text_count = 0;

uint32_t final_data[MAX_DATA * MAX_OBJECTS];
int final_data_count = 0;

void trim(char* s) {
    int len = strlen(s);
    while (len > 0 && (s[len - 1] == '\n' || s[len - 1] == '\r' || s[len - 1] == ' ' || s[len - 1] == '\t')) {
        s[len - 1] = '\0';
        len--;
    }
}

uint32_t encode_B_offset(uint32_t instruction, int offset) {
    instruction &= ~((1u << 31) | (0x3Fu << 25) | (0xFu << 8) | (1u << 7));
    instruction |= (((offset >> 12) & 0x1) << 31);
    instruction |= (((offset >> 5) & 0x3F) << 25);
    instruction |= (((offset >> 1) & 0xF) << 8);
    instruction |= (((offset >> 11) & 0x1) << 7);
    return instruction;
}

uint32_t encode_J_offset(uint32_t instruction, int offset) {
    instruction &= 0x00000FFF;
    instruction |= (((offset >> 20) & 0x1) << 31);
    instruction |= (((offset >> 1) & 0x3FF) << 21);
    instruction |= (((offset >> 11) & 0x1) << 20);
    instruction |= (((offset >> 12) & 0xFF) << 12);
    return instruction;
}

int find_global_symbol(char* name) {
    for (int i = 0; i < global_symbol_count; i++) {
        if (strcmp(global_symbols[i].name, name) == 0)
            return i;
    }
    return -1;
}

void add_global_symbol(char* name, uint32_t address) {
    if (find_global_symbol(name) != -1) {
        printf("HATA: Ayni global sembol iki kez tanimlandi: %s\n", name);
        exit(1);
    }
    strcpy(global_symbols[global_symbol_count].name, name);
    global_symbols[global_symbol_count].address = address;
    global_symbol_count++;
}

void read_object_file(char* filename, ObjectFile* obj) {
    FILE* f = fopen(filename, "r");
    if (!f) { printf("HATA: Object dosyasi acilamadi: %s\n", filename); exit(1); }

    strcpy(obj->filename, filename);
    obj->text_count = 0; obj->data_count = 0;
    obj->symbol_count = 0; obj->reloc_count = 0;

    char line[MAX_LINE];
    char section[30] = "";

    while (fgets(line, sizeof(line), f)) {
        trim(line);
        if (strlen(line) == 0) continue;

        if (line[0] == '.') { strcpy(section, line); continue; }

        if (strcmp(section, ".text") == 0) obj->text[obj->text_count++] = (uint32_t)strtoul(line, NULL, 16);
        else if (strcmp(section, ".data") == 0) obj->data[obj->data_count++] = (uint32_t)strtoul(line, NULL, 16);
        else if (strcmp(section, ".symbols") == 0) {
            Symbol* s = &obj->symbols[obj->symbol_count];
            sscanf(line, "%s %u %s %s", s->name, &s->offset, s->scope, s->section);
            s->absolute_address = 0;
            obj->symbol_count++;
        }
        else if (strcmp(section, ".relocs") == 0) {
            Reloc* r = &obj->relocs[obj->reloc_count];
            sscanf(line, "%u %c %s", &r->offset, &r->type, r->symbol);
            obj->reloc_count++;
        }
    }
    fclose(f);
}

/* ========================================================
   PASS 1 ADIMI: Bellek Haritasý (Memory Map) Çýkarma
   Nesne dosyalarýnýn bellekte art arda nasýl dizileceði hesaplanýr.
   ======================================================== */
void assign_base_addresses(uint32_t start_text, uint32_t start_data) {
    uint32_t current_text_base = start_text;
    uint32_t current_data_base = start_data;

    for (int i = 0; i < object_count; i++) {
        objects[i].text_base_address = current_text_base;
        objects[i].data_base_address = current_data_base;

        current_text_base += objects[i].text_count * 4;
        current_data_base += objects[i].data_count * 4;
    }
}

/* ========================================================
   PASS 1 ADIMI: ESTAB (External Symbol Table) Oluþturma
   Pass 1'in asýl amacýdýr. Her modüldeki GLOBAL semboller alýnýp,
   kesin(mutlak) adresleri hesaplanarak ESTAB'a kaydedilir.
   ======================================================== */
void build_global_symbol_table() {
    for (int i = 0; i < object_count; i++) {
        ObjectFile* obj = &objects[i];
        for (int j = 0; j < obj->symbol_count; j++) {
            Symbol* s = &obj->symbols[j];

            if (strcmp(s->section, "TEXT") == 0) {
                s->absolute_address = obj->text_base_address + s->offset;
            }
            else {
                s->absolute_address = obj->data_base_address + s->offset;
            }

            // Sadece GLOBAL (dýþa açýk) semboller ESTAB'a eklenir
            if (strcmp(s->scope, "GLOBAL") == 0) {
                add_global_symbol(s->name, s->absolute_address);
            }
        }
    }
}

/* ========================================================
   PASS 2 ADIMI: Bölümleri Birleþtirme (Merging)
   Tüm .o dosyalarýndaki text ve data bölümleri tek bir blok haline getirilir.
   ======================================================== */
void merge_sections() {
    final_text_count = 0; final_data_count = 0;

    for (int i = 0; i < object_count; i++) {
        for (int j = 0; j < objects[i].text_count; j++) final_text[final_text_count++] = objects[i].text[j];
        for (int j = 0; j < objects[i].data_count; j++) final_data[final_data_count++] = objects[i].data[j];
    }
}

/* ========================================================
   PASS 2 ADIMI: Relocation (Adres Düzeltme)
   Bu aþamada makine kodu doðrudan deðiþtirilir. .relocs tablosundaki
   istekler okunur, ESTAB'dan (global_symbols) adresi çekilir ve
   ilgili instruction'ýn içine offset olarak gömülür.
   ======================================================== */
void apply_relocations() {
    for (int i = 0; i < object_count; i++) {
        ObjectFile* obj = &objects[i];

        for (int j = 0; j < obj->reloc_count; j++) {
            Reloc* r = &obj->relocs[j];

            // ESTAB üzerinden sembolün kesin adresini arýyoruz
            int sym_index = find_global_symbol(r->symbol);

            if (sym_index == -1) {
                printf("HATA: External sembol ESTAB'da bulunamadi: %s\n", r->symbol);
                exit(1);
            }

            uint32_t symbol_addr = global_symbols[sym_index].address;
            uint32_t instruction_addr = obj->text_base_address + r->offset;
            int offset = (int)symbol_addr - (int)instruction_addr;

            int final_index = (instruction_addr - objects[0].text_base_address) / 4;

            if (r->type == 'B') final_text[final_index] = encode_B_offset(final_text[final_index], offset);
            else if (r->type == 'J') final_text[final_index] = encode_J_offset(final_text[final_index], offset);
            else { printf("HATA: Desteklenmeyen relocation tipi: %c\n", r->type); exit(1); }
        }
    }
}

void write_output_mem(char* filename, uint32_t start_text, uint32_t start_data) {
    FILE* out = fopen(filename, "w");
    if (!out) { printf("HATA: Cikti dosyasi olusturulamadi!\n"); exit(1); }

    if (final_text_count > 0) {
        fprintf(out, "@%08X\n", start_text / 4);
        for (int i = 0; i < final_text_count; i++) fprintf(out, "%08X\n", final_text[i]);
    }
    if (final_data_count > 0) {
        fprintf(out, "@%08X\n", start_data / 4);
        for (int i = 0; i < final_data_count; i++) fprintf(out, "%08X\n", final_data[i]);
    }
    fclose(out);
}

void print_debug_info() {
    printf("\n--- Object Base Adresleri (Pass 1 Ciktisi) ---\n");
    for (int i = 0; i < object_count; i++) {
        printf("%s:\n  .text base = 0x%08X\n  .data base = 0x%08X\n", objects[i].filename, objects[i].text_base_address, objects[i].data_base_address);
    }

    printf("\n--- ESTAB: Global Symbol Table (Pass 1 Ciktisi) ---\n");
    for (int i = 0; i < global_symbol_count; i++) {
        printf("%s -> 0x%08X\n", global_symbols[i].name, global_symbols[i].address);
    }
    printf("\nLinkleme (Pass 2 Relocation) tamamlandi.\n");
}

int main(int argc, char* argv[]) {
    uint32_t start_text = 0x00000000;
    uint32_t start_data = 0x00001000;
    char* output_name = "output.mem";
    int arg_idx = 1;

    while (arg_idx < argc) {
        if (strcmp(argv[arg_idx], "-Ttext") == 0 && arg_idx + 1 < argc) { start_text = (uint32_t)strtoul(argv[arg_idx + 1], NULL, 16); arg_idx += 2; }
        else if (strcmp(argv[arg_idx], "-Tdata") == 0 && arg_idx + 1 < argc) { start_data = (uint32_t)strtoul(argv[arg_idx + 1], NULL, 16); arg_idx += 2; }
        else if (strcmp(argv[arg_idx], "-o") == 0 && arg_idx + 1 < argc) { output_name = argv[arg_idx + 1]; arg_idx += 2; }
        else break;
    }

    object_count = argc - arg_idx;

    if (object_count == 0) {
        printf("Kullanim: %s [-Ttext adres] [-Tdata adres] [-o output.mem] input1.o input2.o ...\n", argv[0]);
        return 1;
    }

    // Dosyalarýn okunmasý
    for (int i = 0; i < object_count; i++) read_object_file(argv[arg_idx + i], &objects[i]);

    // ========================================================
    // --- LINKER PASS 1 ---
    // Adresleme iþlemleri ve ESTAB tablosunun oluþturulmasý
    // ========================================================
    assign_base_addresses(start_text, start_data);
    build_global_symbol_table();

    // ========================================================
    // --- LINKER PASS 2 ---
    // Makine kodlarýnýn birleþtirilmesi ve ESTAB kullanýlarak 
    // bilinmeyen(external) adreslerin(relocations) düzeltilmesi
    // ========================================================
    merge_sections();
    apply_relocations();

    // Çýktý dosyasýnýn yazýlmasý
    write_output_mem(output_name, start_text, start_data);

    print_debug_info();
    printf("Cikti dosyasi: %s\n", output_name);

    return 0;
}