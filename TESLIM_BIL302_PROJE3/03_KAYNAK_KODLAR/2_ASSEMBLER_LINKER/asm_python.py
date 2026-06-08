#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RV32I Assembler (Python implementation)
========================================
Mevcut C assembler'in tam replikasi. Iki gecisli mimari, hash table
sembol tablosu, RISC-V psABI uyumlu register isimleri, hex/dec/bin/oct
literal'ler. WDAC engelinden bagimsiz calismasi icin Python ile yazildi.

Kullanim:
    python asm.py <input.asm> <output.o>
"""

import sys, os, re

# =====================================================================
# RV32I komut tablosu (C'deki opcode_table ile birebir)
# =====================================================================
OPCODES = {
    # R-Type
    "add":  ('R', 0x33, 0x0, 0x00),
    "sub":  ('R', 0x33, 0x0, 0x20),
    "sll":  ('R', 0x33, 0x1, 0x00),
    "xor":  ('R', 0x33, 0x4, 0x00),
    "srl":  ('R', 0x33, 0x5, 0x00),
    "sra":  ('R', 0x33, 0x5, 0x20),
    "or":   ('R', 0x33, 0x6, 0x00),
    "and":  ('R', 0x33, 0x7, 0x00),
    "slt":  ('R', 0x33, 0x2, 0x00),
    "sltu": ('R', 0x33, 0x3, 0x00),

    # I-Type (ALU immediate)
    "addi": ('I', 0x13, 0x0, 0x00),
    "xori": ('I', 0x13, 0x4, 0x00),
    "ori":  ('I', 0x13, 0x6, 0x00),
    "andi": ('I', 0x13, 0x7, 0x00),
    "slti": ('I', 0x13, 0x2, 0x00),
    # I-Type Shift (shamt 5-bit, funct7 imm[11:5]'e yerlesir)
    "slli": ('I', 0x13, 0x1, 0x00),
    "srli": ('I', 0x13, 0x5, 0x00),
    "srai": ('I', 0x13, 0x5, 0x20),

    # I-Type (Load)
    "lb":  ('I', 0x03, 0x0, 0x00),
    "lh":  ('I', 0x03, 0x1, 0x00),
    "lw":  ('I', 0x03, 0x2, 0x00),
    "lbu": ('I', 0x03, 0x4, 0x00),
    "lhu": ('I', 0x03, 0x5, 0x00),

    # S-Type (Store)
    "sb": ('S', 0x23, 0x0, 0x00),
    "sh": ('S', 0x23, 0x1, 0x00),
    "sw": ('S', 0x23, 0x2, 0x00),

    # B-Type (Branch)
    "beq":  ('B', 0x63, 0x0, 0x00),
    "bne":  ('B', 0x63, 0x1, 0x00),
    "blt":  ('B', 0x63, 0x4, 0x00),
    "bge":  ('B', 0x63, 0x5, 0x00),
    "bltu": ('B', 0x63, 0x6, 0x00),
    "bgeu": ('B', 0x63, 0x7, 0x00),

    # J-Type & Jump Register
    "jal":  ('J', 0x6F, 0x0, 0x00),
    "jalr": ('I', 0x67, 0x0, 0x00),

    # U-Type
    "lui":   ('U', 0x37, 0x0, 0x00),
    "auipc": ('U', 0x17, 0x0, 0x00),
}

# =====================================================================
# RISC-V psABI register isimleri (Specification §2)
# =====================================================================
ABI_ALIASES = {
    "zero":0, "ra":1,  "sp":2,  "gp":3,  "tp":4,
    "t0":5,   "t1":6,  "t2":7,
    "s0":8,   "fp":8,  "s1":9,
    "a0":10,  "a1":11, "a2":12, "a3":13,
    "a4":14,  "a5":15, "a6":16, "a7":17,
    "s2":18,  "s3":19, "s4":20, "s5":21,
    "s6":22,  "s7":23, "s8":24, "s9":25,
    "s10":26, "s11":27,
    "t3":28,  "t4":29, "t5":30, "t6":31,
}

def get_register_num(reg, lineno=0):
    """Hem mimari (x0..x31) hem ABI takma adlarini kabul eder."""
    if reg is None or reg == "":
        sys.stderr.write(f"[ASM ERR L{lineno}] Register beklendi, bos.\n")
        return 0
    r = reg.strip().lower().lstrip(',').rstrip(',').strip()
    if r.startswith("x") and r[1:].isdigit():
        n = int(r[1:])
        if n < 0 or n > 31:
            sys.stderr.write(f"[ASM ERR L{lineno}] Gecersiz register: {reg}\n")
            return 0
        return n
    if r in ABI_ALIASES:
        return ABI_ALIASES[r]
    sys.stderr.write(f"[ASM ERR L{lineno}] Bilinmeyen register: '{reg}'\n")
    return 0

def parse_imm(s, lineno=0):
    """Ondalik, hex (0x), oktal (0), binary (0b) ve isaretli sayilar."""
    if s is None:
        return 0
    s = s.strip()
    if not s:
        return 0
    neg = 1
    if s.startswith('-'):
        neg = -1
        s = s[1:]
    elif s.startswith('+'):
        s = s[1:]
    try:
        if s.lower().startswith("0b"):
            return neg * int(s[2:], 2)
        if s.lower().startswith("0x"):
            return neg * int(s[2:], 16)
        if s.startswith("0") and len(s) > 1 and s[1].isdigit():
            return neg * int(s, 8)
        return neg * int(s, 10)
    except ValueError:
        sys.stderr.write(f"[ASM ERR L{lineno}] Gecersiz immediate: '{s}'\n")
        return 0

# =====================================================================
# Yorum ve trim yardimcilari
# =====================================================================
def strip_comment(line):
    """RISC-V GNU as standardi: '#' yorum karakteri.
    Ek olarak ';' ve '//' de desteklenir (geriye uyumluluk)."""
    for ch in ("#", ";"):
        i = line.find(ch)
        if i >= 0:
            line = line[:i]
    i = line.find("//")
    if i >= 0:
        line = line[:i]
    return line

def is_real_opcode(mnemonic):
    return mnemonic in OPCODES

# =====================================================================
# Encoder fonksiyonlari
# =====================================================================
def encode_R(info, rd, rs1, rs2, lineno=0):
    _, op, f3, f7 = info
    return ((f7 & 0x7F) << 25) | ((rs2 & 0x1F) << 20) | ((rs1 & 0x1F) << 15) \
         | ((f3 & 0x7) << 12) | ((rd & 0x1F) << 7) | (op & 0x7F)

def encode_I(info, rd, rs1, imm, lineno=0):
    _, op, f3, f7 = info
    if imm < -2048 or imm > 2047:
        sys.stderr.write(f"[ASM WRN L{lineno}] I-type imm araligi disinda: {imm}\n")
    enc = ((imm & 0xFFF) << 20) | ((rs1 & 0x1F) << 15) \
        | ((f3 & 0x7) << 12) | ((rd & 0x1F) << 7) | (op & 0x7F)
    # Shift I-type: funct7 imm[11:5]'e yerlesir
    enc |= ((f7 & 0x7F) << 25)
    return enc & 0xFFFFFFFF

def encode_S(info, rs1, rs2, imm, lineno=0):
    _, op, f3, _ = info
    if imm < -2048 or imm > 2047:
        sys.stderr.write(f"[ASM WRN L{lineno}] S-type imm araligi disinda: {imm}\n")
    return (((imm >> 5) & 0x7F) << 25) | ((rs2 & 0x1F) << 20) | ((rs1 & 0x1F) << 15) \
         | ((f3 & 0x7) << 12) | ((imm & 0x1F) << 7) | (op & 0x7F)

def encode_B(info, rs1, rs2, offset, lineno=0):
    _, op, f3, _ = info
    o = offset & 0x1FFF  # 13-bit signed range
    if offset < -4096 or offset > 4095:
        sys.stderr.write(f"[ASM WRN L{lineno}] B-type offset araligi disinda: {offset}\n")
    # offset signed; bit mosaicing
    if offset < 0:
        # Python int -> sign extend for shifts
        offset_u = offset & 0xFFFFFFFF
    else:
        offset_u = offset
    b12   = (offset_u >> 12) & 0x1
    b11   = (offset_u >> 11) & 0x1
    b10_5 = (offset_u >> 5)  & 0x3F
    b4_1  = (offset_u >> 1)  & 0xF
    return (b12 << 31) | (b10_5 << 25) | ((rs2 & 0x1F) << 20) \
         | ((rs1 & 0x1F) << 15) | ((f3 & 0x7) << 12) \
         | (b4_1 << 8) | (b11 << 7) | (op & 0x7F)

def encode_U(info, rd, imm, lineno=0):
    _, op, _, _ = info
    return ((imm & 0xFFFFF) << 12) | ((rd & 0x1F) << 7) | (op & 0x7F)

def encode_J(info, rd, offset, lineno=0):
    _, op, _, _ = info
    if offset < -1048576 or offset > 1048575:
        sys.stderr.write(f"[ASM WRN L{lineno}] J-type offset araligi disinda: {offset}\n")
    if offset < 0:
        offset_u = offset & 0xFFFFFFFF
    else:
        offset_u = offset
    j20    = (offset_u >> 20) & 0x1
    j10_1  = (offset_u >> 1)  & 0x3FF
    j11    = (offset_u >> 11) & 0x1
    j19_12 = (offset_u >> 12) & 0xFF
    return (j20 << 31) | (j10_1 << 21) | (j11 << 20) | (j19_12 << 12) \
         | ((rd & 0x1F) << 7) | (op & 0x7F)

# =====================================================================
# Operand ayristirma yardimcilari
# =====================================================================
def parse_offset_rs1(s, lineno=0):
    """'imm(rs1)' veya '0(t0)' gibi load/store/jalr formatini ayristirir."""
    m = re.match(r"^\s*(-?\w+)\s*\(\s*([\w]+)\s*\)\s*$", s)
    if not m:
        # Belki sadece imm verildi (jalr offset, register)
        return 0, "x0"
    return parse_imm(m.group(1), lineno), m.group(2)

def split_operands(rest):
    """'a0, zero, 0x3F' veya 'a0,zero,63' gibi operand listesini ayirir."""
    # Virgul ile bol, sonra her elemani trim et
    parts = [p.strip() for p in rest.split(",")]
    # Bos elemanlari ele
    return [p for p in parts if p]

# =====================================================================
# Sembol tablosu
# =====================================================================
class Symbol:
    __slots__ = ("name","address","scope","section")
    def __init__(self, name, address, scope, section):
        self.name, self.address = name, address
        self.scope, self.section = scope, section

class Relocation:
    __slots__ = ("offset","type","symbol")
    def __init__(self, offset, type_, symbol):
        self.offset, self.type, self.symbol = offset, type_, symbol

# =====================================================================
# PASS 1: Etiket adreslerini topla
# =====================================================================
def pass1(lines):
    symbols = {}    # name -> Symbol
    current_text_pc = 0
    current_data_pc = 0
    current_section = "TEXT"

    for lineno, raw in enumerate(lines, 1):
        line = strip_comment(raw).strip()
        if not line:
            continue

        # Etiket?
        if ':' in line:
            idx = line.index(':')
            label = line[:idx].strip()
            rest  = line[idx+1:].strip()
            if label:
                addr = current_text_pc if current_section == "TEXT" else current_data_pc
                if label not in symbols:
                    symbols[label] = Symbol(label, addr, "LOCAL", current_section)
            line = rest
            if not line:
                continue

        # Direktif veya mnemonic?
        parts = line.split(None, 1)
        if not parts:
            continue
        mn = parts[0].lower()

        if mn == ".text":
            current_section = "TEXT"; continue
        if mn == ".data":
            current_section = "DATA"; continue
        if mn in (".globl", ".global", ".extern"):
            continue
        if mn == ".word":
            if current_section == "TEXT":
                current_text_pc += 4
            else:
                current_data_pc += 4
            continue
        if mn == ".space":
            # .space N  -  N bayt rezerv (word'e yukari yuvarla)
            rest = parts[1] if len(parts) > 1 else "0"
            n = parse_imm(rest.split()[0] if rest.split() else "0", lineno)
            bytes_ = ((n + 3) // 4) * 4
            if current_section == "TEXT":
                current_text_pc += bytes_
            else:
                current_data_pc += bytes_
            continue
        if mn.startswith("."):
            continue

        # Gercek opcode mu?
        if is_real_opcode(mn):
            if current_section == "TEXT":
                current_text_pc += 4
            # .data icinde komut hata; ama PC artirmayalim

    return symbols

# =====================================================================
# PASS 2: Makine kodu uret
# =====================================================================
def pass2(lines, symbols):
    text_section = []
    data_section = []
    relocs = []
    externs = set()
    globals_set = set()

    current_text_pc = 0
    current_data_pc = 0
    current_section = "TEXT"

    for lineno, raw in enumerate(lines, 1):
        line = strip_comment(raw).strip()
        if not line:
            continue

        if ':' in line:
            idx = line.index(':')
            line = line[idx+1:].strip()
            if not line:
                continue

        parts = line.split(None, 1)
        if not parts:
            continue
        mn = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""

        # Direktifler
        if mn == ".text":
            current_section = "TEXT"; continue
        if mn == ".data":
            current_section = "DATA"; continue
        if mn in (".globl", ".global"):
            sym = rest.strip()
            globals_set.add(sym)
            if sym in symbols:
                symbols[sym].scope = "GLOBAL"
            continue
        if mn == ".extern":
            externs.add(rest.strip()); continue
        if mn == ".word":
            ops = split_operands(rest)
            for o in ops:
                val = parse_imm(o, lineno) & 0xFFFFFFFF
                if current_section == "TEXT":
                    text_section.append(val)
                    current_text_pc += 4
                else:
                    data_section.append(val)
                    current_data_pc += 4
            continue
        if mn == ".space":
            n = parse_imm(rest.split()[0] if rest.split() else "0", lineno)
            words = (n + 3) // 4
            for _ in range(words):
                if current_section == "TEXT":
                    text_section.append(0)
                    current_text_pc += 4
                else:
                    data_section.append(0)
                    current_data_pc += 4
            continue
        if mn.startswith("."):
            continue

        # Opcode
        if not is_real_opcode(mn):
            sys.stderr.write(f"[ASM ERR L{lineno}] Bilinmeyen komut: '{mn}'\n")
            continue

        info = OPCODES[mn]
        kind = info[0]
        ops = split_operands(rest)
        mc = 0

        try:
            if kind == 'R':
                if len(ops) != 3:
                    sys.stderr.write(f"[ASM ERR L{lineno}] {mn}: 3 operand bekleniyor\n")
                    continue
                rd  = get_register_num(ops[0], lineno)
                rs1 = get_register_num(ops[1], lineno)
                rs2 = get_register_num(ops[2], lineno)
                mc = encode_R(info, rd, rs1, rs2, lineno)

            elif kind == 'I':
                # Load veya jalr: 'rd, imm(rs1)' formati
                if mn in ("lb","lh","lw","lbu","lhu","jalr"):
                    if len(ops) == 2:
                        rd = get_register_num(ops[0], lineno)
                        imm, rs1_s = parse_offset_rs1(ops[1], lineno)
                        rs1 = get_register_num(rs1_s, lineno)
                        mc = encode_I(info, rd, rs1, imm, lineno)
                    elif len(ops) == 3:
                        # jalr alternatif: 'rd, rs1, imm'
                        rd  = get_register_num(ops[0], lineno)
                        rs1 = get_register_num(ops[1], lineno)
                        imm = parse_imm(ops[2], lineno)
                        mc = encode_I(info, rd, rs1, imm, lineno)
                    else:
                        sys.stderr.write(f"[ASM ERR L{lineno}] {mn}: operand sayisi yanlis\n")
                else:
                    if len(ops) != 3:
                        sys.stderr.write(f"[ASM ERR L{lineno}] {mn}: 3 operand bekleniyor\n")
                        continue
                    rd  = get_register_num(ops[0], lineno)
                    rs1 = get_register_num(ops[1], lineno)
                    imm = parse_imm(ops[2], lineno)
                    mc = encode_I(info, rd, rs1, imm, lineno)

            elif kind == 'S':
                # sw rs2, imm(rs1)
                if len(ops) != 2:
                    sys.stderr.write(f"[ASM ERR L{lineno}] {mn}: 2 operand bekleniyor\n")
                    continue
                rs2 = get_register_num(ops[0], lineno)
                imm, rs1_s = parse_offset_rs1(ops[1], lineno)
                rs1 = get_register_num(rs1_s, lineno)
                mc = encode_S(info, rs1, rs2, imm, lineno)

            elif kind == 'B':
                if len(ops) != 3:
                    sys.stderr.write(f"[ASM ERR L{lineno}] {mn}: 3 operand bekleniyor\n")
                    continue
                rs1 = get_register_num(ops[0], lineno)
                rs2 = get_register_num(ops[1], lineno)
                target = ops[2].strip()
                if target in symbols and symbols[target].section == "TEXT":
                    offset = symbols[target].address - current_text_pc
                else:
                    # Extern olabilir
                    externs.add(target)
                    relocs.append(Relocation(current_text_pc, 'B', target))
                    offset = 0
                mc = encode_B(info, rs1, rs2, offset, lineno)

            elif kind == 'U':
                if len(ops) != 2:
                    sys.stderr.write(f"[ASM ERR L{lineno}] {mn}: 2 operand bekleniyor\n")
                    continue
                rd  = get_register_num(ops[0], lineno)
                imm = parse_imm(ops[1], lineno)
                mc = encode_U(info, rd, imm, lineno)

            elif kind == 'J':
                if len(ops) != 2:
                    sys.stderr.write(f"[ASM ERR L{lineno}] {mn}: 2 operand bekleniyor\n")
                    continue
                rd = get_register_num(ops[0], lineno)
                target = ops[1].strip()
                if target in symbols and symbols[target].section == "TEXT":
                    offset = symbols[target].address - current_text_pc
                else:
                    externs.add(target)
                    relocs.append(Relocation(current_text_pc, 'J', target))
                    offset = 0
                mc = encode_J(info, rd, offset, lineno)
        except Exception as e:
            sys.stderr.write(f"[ASM ERR L{lineno}] Encode exception: {e}\n")
            mc = 0

        if current_section == "TEXT":
            text_section.append(mc & 0xFFFFFFFF)
            current_text_pc += 4

    return text_section, data_section, symbols, relocs, externs, globals_set

# =====================================================================
# .o dosyasi yaz
# =====================================================================
def write_object_file(path, text_section, data_section, symbols, relocs, externs):
    with open(path, "w", encoding="utf-8") as f:
        f.write(".text\n")
        for i, w in enumerate(text_section):
            f.write(f"{i*4:08X} {w:08X}\n")
        f.write(".data\n")
        base = 0
        for i, w in enumerate(data_section):
            f.write(f"{(base+i*4):08X} {w:08X}\n")
        f.write(".symbols\n")
        for name, sym in symbols.items():
            f.write(f"{sym.name} {sym.address:08X} {sym.scope} {sym.section}\n")
        f.write(".externs\n")
        for e in externs:
            f.write(f"{e}\n")
        f.write(".relocs\n")
        for r in relocs:
            f.write(f"{r.offset} {r.type} {r.symbol}\n")

# =====================================================================
# CLI
# =====================================================================
def main():
    if len(sys.argv) < 3:
        print(f"Kullanim: python {os.path.basename(sys.argv[0])} <input.asm> <output.o>")
        sys.exit(1)
    in_path, out_path = sys.argv[1], sys.argv[2]
    if not os.path.exists(in_path):
        print(f"Hata: {in_path} acilamadi!")
        sys.exit(1)

    with open(in_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    symbols = pass1(lines)
    text, data, syms, relocs, externs, globals_set = pass2(lines, symbols)

    write_object_file(out_path, text, data, syms, relocs, externs)
    print(f"Object dosyasi olusturuldu: {out_path}")

if __name__ == "__main__":
    main()
