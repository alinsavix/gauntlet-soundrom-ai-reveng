#!/usr/bin/env python3
"""Linearly decode owned 6502 ranges and audit unresolved RAM-state references."""

import argparse
import csv
from pathlib import Path


ROM_BASE = 0x4000
UNRESOLVED_ZP = set(range(0x3A, 0x3E)) | {0x43}
EXPECTED_082F_REFS = {0x4681, 0x46B0, 0x481D, 0x48E9, 0x4C1E, 0x4C23,
                      0x4C28, 0x4EBB, 0x4ED5, 0x4F0E, 0x4FBD}
EXPECTED_INDEXED_WORKSPACE = {0x83B3, 0x83CB, 0x83D4, 0x83DF, 0x83F2,
                              0x840F, 0x8419, 0x8422, 0x8429}


READ = {
    0x05: ("ORA", "zp"), 0x15: ("ORA", "zpx"), 0x0D: ("ORA", "abs"), 0x1D: ("ORA", "absx"), 0x19: ("ORA", "absy"), 0x01: ("ORA", "indx"), 0x11: ("ORA", "indy"),
    0x25: ("AND", "zp"), 0x35: ("AND", "zpx"), 0x2D: ("AND", "abs"), 0x3D: ("AND", "absx"), 0x39: ("AND", "absy"), 0x21: ("AND", "indx"), 0x31: ("AND", "indy"),
    0x45: ("EOR", "zp"), 0x55: ("EOR", "zpx"), 0x4D: ("EOR", "abs"), 0x5D: ("EOR", "absx"), 0x59: ("EOR", "absy"), 0x41: ("EOR", "indx"), 0x51: ("EOR", "indy"),
    0x65: ("ADC", "zp"), 0x75: ("ADC", "zpx"), 0x6D: ("ADC", "abs"), 0x7D: ("ADC", "absx"), 0x79: ("ADC", "absy"), 0x61: ("ADC", "indx"), 0x71: ("ADC", "indy"),
    0xE5: ("SBC", "zp"), 0xF5: ("SBC", "zpx"), 0xED: ("SBC", "abs"), 0xFD: ("SBC", "absx"), 0xF9: ("SBC", "absy"), 0xE1: ("SBC", "indx"), 0xF1: ("SBC", "indy"),
    0xA5: ("LDA", "zp"), 0xB5: ("LDA", "zpx"), 0xAD: ("LDA", "abs"), 0xBD: ("LDA", "absx"), 0xB9: ("LDA", "absy"), 0xA1: ("LDA", "indx"), 0xB1: ("LDA", "indy"),
    0xA6: ("LDX", "zp"), 0xB6: ("LDX", "zpy"), 0xAE: ("LDX", "abs"), 0xBE: ("LDX", "absy"),
    0xA4: ("LDY", "zp"), 0xB4: ("LDY", "zpx"), 0xAC: ("LDY", "abs"), 0xBC: ("LDY", "absx"),
    0xC5: ("CMP", "zp"), 0xD5: ("CMP", "zpx"), 0xCD: ("CMP", "abs"), 0xDD: ("CMP", "absx"), 0xD9: ("CMP", "absy"), 0xC1: ("CMP", "indx"), 0xD1: ("CMP", "indy"),
    0xE4: ("CPX", "zp"), 0xEC: ("CPX", "abs"), 0xC4: ("CPY", "zp"), 0xCC: ("CPY", "abs"),
    0x24: ("BIT", "zp"), 0x2C: ("BIT", "abs"),
}
STORE = {
    0x85: ("STA", "zp"), 0x95: ("STA", "zpx"), 0x8D: ("STA", "abs"), 0x9D: ("STA", "absx"), 0x99: ("STA", "absy"), 0x81: ("STA", "indx"), 0x91: ("STA", "indy"),
    0x86: ("STX", "zp"), 0x96: ("STX", "zpy"), 0x8E: ("STX", "abs"),
    0x84: ("STY", "zp"), 0x94: ("STY", "zpx"), 0x8C: ("STY", "abs"),
}
RMW = {
    0x06: ("ASL", "zp"), 0x16: ("ASL", "zpx"), 0x0E: ("ASL", "abs"), 0x1E: ("ASL", "absx"),
    0x46: ("LSR", "zp"), 0x56: ("LSR", "zpx"), 0x4E: ("LSR", "abs"), 0x5E: ("LSR", "absx"),
    0x26: ("ROL", "zp"), 0x36: ("ROL", "zpx"), 0x2E: ("ROL", "abs"), 0x3E: ("ROL", "absx"),
    0x66: ("ROR", "zp"), 0x76: ("ROR", "zpx"), 0x6E: ("ROR", "abs"), 0x7E: ("ROR", "absx"),
    0xE6: ("INC", "zp"), 0xF6: ("INC", "zpx"), 0xEE: ("INC", "abs"), 0xFE: ("INC", "absx"),
    0xC6: ("DEC", "zp"), 0xD6: ("DEC", "zpx"), 0xCE: ("DEC", "abs"), 0xDE: ("DEC", "absx"),
}
DATA_OPS = {**{k: (*v, "read") for k, v in READ.items()},
            **{k: (*v, "write") for k, v in STORE.items()},
            **{k: (*v, "read_modify_write") for k, v in RMW.items()}}

ONE_BYTE = {0x00, 0x08, 0x0A, 0x18, 0x28, 0x2A, 0x38, 0x40, 0x48, 0x4A,
            0x58, 0x60, 0x68, 0x6A, 0x78, 0x88, 0x8A, 0x98, 0x9A, 0xA8,
            0xAA, 0xB8, 0xBA, 0xC8, 0xCA, 0xD8, 0xE8, 0xEA, 0xF8}
BRANCH = {0x10, 0x30, 0x50, 0x70, 0x90, 0xB0, 0xD0, 0xF0}
IMMEDIATE = {0x09, 0x29, 0x49, 0x69, 0xA0, 0xA2, 0xA9, 0xC0, 0xC9, 0xE0, 0xE9}
CONTROL_3 = {0x20, 0x4C, 0x6C}


def instruction_length(opcode):
    if opcode in ONE_BYTE:
        return 1
    if opcode in BRANCH or opcode in IMMEDIATE:
        return 2
    if opcode in CONTROL_3:
        return 3
    if opcode in DATA_OPS:
        mode = DATA_OPS[opcode][1]
        return 2 if mode in {"zp", "zpx", "zpy", "indx", "indy"} else 3
    raise KeyError(opcode)


def hx(value, width=4):
    return f"0x{value:0{width}X}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("rom", type=Path)
    p.add_argument("--semantic-coverage", required=True, type=Path)
    p.add_argument("--csv", required=True, type=Path)
    p.add_argument("--summary-csv", required=True, type=Path)
    args = p.parse_args()
    rom = args.rom.read_bytes()
    with args.semantic_coverage.open(newline="") as f:
        owned_rows = [(int(row["start"], 16), int(row["end_inclusive"], 16))
                      for row in csv.DictReader(f) if row["classification"] == "semantic_owned"]
    intervals = []
    for start, end in owned_rows:
        if intervals and intervals[-1][1] + 1 == start:
            intervals[-1] = (intervals[-1][0], end)
        else:
            intervals.append((start, end))

    decoded = []
    for start, end in intervals:
        address = start
        while address <= end:
            opcode = rom[address - ROM_BASE]
            try:
                length = instruction_length(opcode)
            except KeyError:
                raise SystemExit(f"unsupported/non-code byte {hx(opcode, 2)} at {hx(address)}")
            if address + length - 1 > end:
                raise SystemExit(f"semantic interval ends inside instruction at {hx(address)}")
            decoded.append((address, opcode, length))
            address += length

    rows = []
    direct_unknown = []
    refs_082f = []
    for address, opcode, length in decoded:
        if opcode not in DATA_OPS:
            continue
        mnemonic, mode, access = DATA_OPS[opcode]
        operand_offset = address - ROM_BASE + 1
        operand = rom[operand_offset]
        if length == 3:
            operand |= rom[operand_offset + 1] << 8
        category = None
        if mode in {"zp", "indx", "indy"} and operand in UNRESOLVED_ZP:
            category = "direct_or_pointer_unknown_zp"
            direct_unknown.append(address)
        elif mode in {"zpx", "zpy"} and 0x30 <= operand <= 0x44:
            category = "indexed_board_workspace_candidate"
        elif operand == 0x082F:
            category = "control_082f"
            refs_082f.append(address)
        if category:
            rows.append({"instruction": hx(address), "opcode": hx(opcode, 2),
                         "mnemonic": mnemonic, "mode": mode, "access": access,
                         "encoded_operand": hx(operand, 2 if length == 2 else 4),
                         "category": category, "confidence": "Verified aligned decode"})

    if direct_unknown:
        raise SystemExit(f"direct references to unresolved zero-page bytes: {[hx(a) for a in direct_unknown]}")
    if set(refs_082f) != EXPECTED_082F_REFS:
        raise SystemExit(f"$082F reference set changed: {[hx(a) for a in refs_082f]}")
    indexed = {int(row["instruction"], 16) for row in rows
               if row["category"] == "indexed_board_workspace_candidate"}
    if indexed != EXPECTED_INDEXED_WORKSPACE:
        raise SystemExit(f"indexed board-workspace set changed: {[hx(a) for a in sorted(indexed)]}")
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    summary = [
        {"state": "$3A-$3D/$43", "producer": "blanket RAM clear; optional boot indirect write only",
         "consumer": "none in 3,199 aligned executable instructions",
         "semantics": "unused zero-page storage in the current ROM",
         "configured_domain": "$36,X and $3E,X candidates have X=3..0 and stop at $39/$41",
         "confidence": "Verified current-image nonuse"},
        {"state": "$082F bit 0", "producer": "$46B0 secondary expiry; $481D stop; preserved by $4C28",
         "consumer": "$4EBB destructive LSR carry", "semantics": "YM key-off request",
         "configured_domain": "0/1", "confidence": "Verified"},
        {"state": "$082F bit 1", "producer": "$4C28 OR #$02",
         "consumer": "$4ED5 destructive LSR carry", "semantics": "KC/TL refresh gate",
         "configured_domain": "always set for staged YM winner", "confidence": "Verified"},
        {"state": "$082F bit 2", "producer": "$48E9 new-note value $04; preserved by $4C28",
         "consumer": "$4FBD destructive LSR carry after bits 0/1 consumed",
         "semantics": "YM key-on request", "configured_domain": "0/1", "confidence": "Verified"},
        {"state": "$082F bits 5..4", "producer": "$4C1A masks event/control A with $30 and $4C28 stages it",
         "consumer": "$4F0E two A shifts after two earlier memory shifts; $4F14 indexes $5C5B-$5C5E",
         "semantics": "four-state operator TL event/control bias selector",
         "configured_domain": "00/10/20/30 -> indices 0/1/2/3", "confidence": "Verified"},
        {"state": "$082F bits 7..6/3", "producer": "none",
         "consumer": "none (bit 3 is discarded; bits 7..6 never staged)",
         "semantics": "unused in current ROM", "configured_domain": "always zero",
         "confidence": "Verified current-image nonuse"},
    ]
    with args.summary_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=summary[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(summary)
    print(f"RAM-state references: {len(decoded)} aligned instructions, "
          f"0 direct unknown-ZP refs, {len(refs_082f)} direct $082F refs, "
          f"{sum(row['category']=='indexed_board_workspace_candidate' for row in rows)} indexed workspace candidates")


if __name__ == "__main__":
    main()
