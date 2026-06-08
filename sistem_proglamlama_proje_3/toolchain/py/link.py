#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RV32I Linker (Python implementation)
=====================================
.o dosyalarini birlestirip relocation uygulayarak Verilog $readmemh
uyumlu .mem dosyasi uretir.

Kullanim:
    python link.py [-Ttext 0x0] [-Tdata 0x1000] [-o out.mem] file1.o [file2.o...]
"""

import sys, os, re

# =====================================================================
# .o dosyasini oku
# =====================================================================
class ObjectFile:
    def __init__(self, path):
        self.path = path
        self.text_offsets = []   # [(offset, word32)]
        self.data_offsets = []   # [(offset, word32)]
        self.symbols = {}        # name -> (addr, scope, section)
        self.externs = []        # list of names
        self.relocs = []         # list of (offset, type, symbol)
        self.text_size = 0
        self.data_size = 0
        self._parse()

    def _parse(self):
        with open(self.path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        section = None
        for line in lines:
            line = line.rstrip()
            if not line:
                continue
            if line in (".text", ".data", ".symbols", ".externs", ".relocs"):
                section = line[1:]
                continue
            parts = line.split()
            if section in ("text", "data"):
                if len(parts) == 2:
                    off = int(parts[0], 16)
                    word = int(parts[1], 16)
                    if section == "text":
                        self.text_offsets.append((off, word))
                    else:
                        self.data_offsets.append((off, word))
            elif section == "symbols":
                if len(parts) >= 4:
                    name = parts[0]
                    addr = int(parts[1], 16)
                    scope = parts[2]
                    sec = parts[3]
                    self.symbols[name] = (addr, scope, sec)
            elif section == "externs":
                if parts:
                    self.externs.append(parts[0])
            elif section == "relocs":
                if len(parts) >= 3:
                    off = int(parts[0])
                    typ = parts[1]
                    sym = parts[2]
                    self.relocs.append((off, typ, sym))
        self.text_size = max((o for o,_ in self.text_offsets), default=-4) + 4
        self.data_size = max((o for o,_ in self.data_offsets), default=-4) + 4

# =====================================================================
# Encoder yardimcilari (B-type ve J-type patching icin)
# =====================================================================
def patch_b_offset(inst, offset):
    """B-type komutta imm bitlerini yeniden yerlestir."""
    if offset < 0:
        ou = offset & 0xFFFFFFFF
    else:
        ou = offset
    b12   = (ou >> 12) & 0x1
    b11   = (ou >> 11) & 0x1
    b10_5 = (ou >> 5)  & 0x3F
    b4_1  = (ou >> 1)  & 0xF
    # Imm bitlerini sifirla
    mask = 0xFE000F80   # bit 31 + bits 30:25 + bits 11:8 + bit 7
    inst &= ~mask & 0xFFFFFFFF
    inst |= (b12 << 31) | (b10_5 << 25) | (b4_1 << 8) | (b11 << 7)
    return inst & 0xFFFFFFFF

def patch_j_offset(inst, offset):
    """J-type komutta imm bitlerini yeniden yerlestir."""
    if offset < 0:
        ou = offset & 0xFFFFFFFF
    else:
        ou = offset
    j20    = (ou >> 20) & 0x1
    j10_1  = (ou >> 1)  & 0x3FF
    j11    = (ou >> 11) & 0x1
    j19_12 = (ou >> 12) & 0xFF
    mask = 0xFFFFF000
    inst &= ~mask & 0xFFFFFFFF
    inst |= (j20 << 31) | (j10_1 << 21) | (j11 << 20) | (j19_12 << 12)
    return inst & 0xFFFFFFFF

# =====================================================================
# Linker ana mantik
# =====================================================================
def link(objects, start_text, start_data, out_path):
    # 1) Base adreslerini hesapla (objelerin sirasi: ilki sifirdan baslar)
    text_base = {}
    data_base = {}
    cur_text = start_text
    cur_data = start_data
    print("\n--- Object Base Adresleri (Pass 1 Ciktisi) ---")
    for obj in objects:
        text_base[obj.path] = cur_text
        data_base[obj.path] = cur_data
        print(f"{obj.path}:")
        print(f"  .text base = 0x{cur_text:08X}")
        print(f"  .data base = 0x{cur_data:08X}")
        cur_text += obj.text_size
        cur_data += obj.data_size

    # 2) ESTAB
    estab = {}
    for obj in objects:
        for name, (addr, scope, sec) in obj.symbols.items():
            if scope == "GLOBAL":
                base = text_base[obj.path] if sec == "TEXT" else data_base[obj.path]
                estab[name] = base + addr
    print("\n--- ESTAB: Global Symbol Table (Pass 1 Ciktisi) ---")
    for name, addr in estab.items():
        print(f"  {name} -> 0x{addr:08X}")

    # 3) Relocation uygula
    # Her objenin text'ini birlestirilmis bir lineer diziye koyalim
    merged_text = {}  # absolute_addr -> word
    merged_data = {}  # absolute_addr -> word
    for obj in objects:
        tb = text_base[obj.path]
        db = data_base[obj.path]
        for off, word in obj.text_offsets:
            merged_text[tb + off] = word
        for off, word in obj.data_offsets:
            merged_data[db + off] = word

        # Relocation
        for off, typ, symname in obj.relocs:
            abs_off = tb + off
            if symname in estab:
                target_addr = estab[symname]
            elif symname in obj.symbols:
                addr, scope, sec = obj.symbols[symname]
                base = tb if sec == "TEXT" else db
                target_addr = base + addr
            else:
                sys.stderr.write(f"[LINK ERR] Undefined symbol: {symname} (in {obj.path})\n")
                continue
            pc_off = target_addr - abs_off
            inst = merged_text[abs_off]
            if typ == 'B':
                inst = patch_b_offset(inst, pc_off)
            elif typ == 'J':
                inst = patch_j_offset(inst, pc_off)
            merged_text[abs_off] = inst

    print("\nLinkleme (Pass 2 Relocation) tamamlandi.")

    # 4) .mem dosyasi yaz
    with open(out_path, "w", encoding="utf-8") as f:
        # text
        if merged_text:
            sorted_keys = sorted(merged_text.keys())
            first = sorted_keys[0]
            f.write(f"@{first:08X}\n")
            prev_addr = first - 4
            for addr in sorted_keys:
                if addr != prev_addr + 4:
                    # Bosluk var, yeni @ tag yaz
                    f.write(f"@{addr:08X}\n")
                f.write(f"{merged_text[addr]:08X}\n")
                prev_addr = addr
        # data
        if merged_data:
            sorted_keys = sorted(merged_data.keys())
            first = sorted_keys[0]
            f.write(f"@{first:08X}\n")
            prev_addr = first - 4
            for addr in sorted_keys:
                if addr != prev_addr + 4:
                    f.write(f"@{addr:08X}\n")
                f.write(f"{merged_data[addr]:08X}\n")
                prev_addr = addr
    print(f"Cikti dosyasi: {out_path}")

# =====================================================================
# CLI
# =====================================================================
def main():
    args = sys.argv[1:]
    if not args:
        print("Kullanim: python link.py [-Ttext 0x0] [-Tdata 0x1000] "
              "[-o out.mem] file1.o [file2.o...]")
        sys.exit(1)

    start_text = 0
    start_data = 0
    out_path = "out.mem"
    files = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "-Ttext":
            start_text = int(args[i+1], 0); i += 2
        elif a == "-Tdata":
            start_data = int(args[i+1], 0); i += 2
        elif a == "-o":
            out_path = args[i+1]; i += 2
        else:
            files.append(a); i += 1

    if not files:
        print("Hata: en az 1 .o dosyasi gerekli")
        sys.exit(1)

    objects = [ObjectFile(p) for p in files]
    link(objects, start_text, start_data, out_path)

if __name__ == "__main__":
    main()
