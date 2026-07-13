#!/usr/bin/env python3
"""Validate and emit the consumer catalog for physical audio output code."""

import argparse
import csv
from collections import defaultdict, deque
from pathlib import Path

import gauntlet_disasm as gd
import rom_table_audit as audit

ROM_BASE = 0x4000


def hx(value):
    return f"0x{value:04X}"


ANCHORS = {
    0x4D02: bytes.fromhex("98 48 c8 a9 00 8d 14 08"),
    0x4D36: bytes.fromhex("20 51 46"),
    0x4D84: bytes.fromhex("20 51 46"),
    0x4DFC: bytes.fromhex("a9 00 8d 21 08 a9 ff 8d 25 08"),
    0x4E0F: bytes.fromhex("20 02 4d"),
    0x4E08: bytes.fromhex("bd ae 57 48 a8 c8 c8"),
    0x4E36: bytes.fromhex("20 02 4d"),
    0x4E68: bytes.fromhex("be e6 07 d0 01 60"),
    0x4E7A: bytes.fromhex("20 51 46"),
    0x4E89: bytes.fromhex("20 f0 4f"),
    0x4EBB: bytes.fromhex("4e 2f 08 90 0e a0 08 20 f0 4f"),
    0x4ED5: bytes.fromhex("4e 2f 08 90 93 ae 19 08 f0 8e"),
    0x4F0E: bytes.fromhex("ad 2f 08 4a 4a aa bd 5b 5c"),
    0x4F51: bytes.fromhex("b9 dc 72"),
    0x4F5D: bytes.fromhex("b9 5b 5b"),
    0x4F6F: bytes.fromhex("b9 5b 5b"),
    0x4FD6: bytes.fromhex("a9 07 8d 3c 08"),
    0x4FDC: bytes.fromhex("bd ae 57 69 07 a8"),
    0x4FE4: bytes.fromhex("20 68 4e"),
    0x4FF0: bytes.fromhex("24 0d 30 18 48 a9 00 18"),
    0x500D: bytes.fromhex("bd a8 57 85 08 bd aa 57 85 09"),
    0x51B7: bytes.fromhex("ac 1d 08 f0 08 4d 1e 08 29 09 4d 1e 08"),
    0x51CB: bytes.fromhex("49 ff ac 1d 08 d0 07 3d cc 03 9d cc 03 60"),
    0x5C5B: bytes.fromhex("00 00 24 58"),
    0x57AE: bytes.fromhex("1e 22"),
    0x57B0: bytes.fromhex("48 2c"),
}


ROWS = [
    (0x4D02, 0x4DFB, "callable_subroutine", "POKEY pair arbitration and scratch selection", "$4E0F;$4E36", "Y=first physical-list head minus one; $08-$09=POKEY base", "RTS $4DD3 or $4DFB; carry/result consumed by caller", "A,X,Y,P", "$07E6,Y;$13;$0811-$0825;logical lists via $4651", "$0811-$0825;$081C;channel arrays through $4651", "Verified", "Add representative active $4651 costs before the arbitration suffix"),
    (0x4DFC, 0x4E67, "tail_dispatch_entry", "POKEY four-channel update and register writes", "$500D for hardware type 0", "X=dispatcher index 0; $08-$09=$1800; $57AE=$1E", "RTS $4E67", "A,X,Y,P", "$57AE,X;$0817-$0825", "POKEY AUDF/AUDC pairs and AUDCTL through ($08),Y", "Verified", "Compose whole-pass bounds from active channel-engine paths"),
    (0x4E68, 0x4FD5, "callable_subroutine", "one YM2151 channel update", "$4FE4", "Y=physical-list head 34..41; $083C=YM channel 0..7", "early RTS $4E6D/$4E81/$4ED3/$4ED8; RTS $4FD5", "A,X,Y,P", "$07E6,Y;$17;$0812;$0819;$0826-$082F;$083C-$089F;$57A0-$57A7;$72DC-$73DB;$5B5B-$5C5A", "YM registers $08,$20-$3F,$60-$7F; shadows $083D+Y;$0810-$0813;$0C-$0F;$10-$11", "Verified", "Derive exact KC/KF/detune formula and operator mask meaning"),
    (0x4E82, 0x4ECE, "internal_block", "YM voice/control register flush", "$4E68 after active channel", "$083C=channel; prepared shadow bytes", "continue filter/pitch gate $4ECE", "A,Y,P plus $4FF0", "$083C;$083D+Y;$082F", "YM $20/$30/$38 and optional key register $08", "Verified", "Map each shadow byte to documented YM2151 bit fields"),
    (0x4ECE, 0x4EFE, "internal_block", "YM filter gate and base key-code lookup", "$4E68", "$0812=status/filter value; $0819=note index", "early RTS or continue conversion $4EFF", "A,X,Y,P plus $4FF0", "$13;$082F;$0812;$0819;$083C;$5AF9,X", "YM $28+channel; shadow; $0819", "Verified", "Prove $5AF9 index domain and note-to-KC mapping"),
    (0x4EFF, 0x4FBD, "internal_block", "YM operator total-level correction", "$4E68", "X points to shadow register $20+channel; $082F already shifted twice", "four-operator loop then $4FBD", "A,X,Y,P plus $4FF0", "$083D,X;$57A0-$57A7;$5C5B-$5C5E event/control bias;$0826-$082F;$72DC-$73DB;$5B5B-$5C5A", "YM total-level registers $60/$64/$68/$6C + channel; $0C-$0F;$10-$11;$0810/$0813", "Verified", "Configured bias indices 0..3 resolved in ym_tl_bias_catalog.csv"),
    (0x4FBD, 0x4FD5, "internal_block", "optional YM key-on write", "$4E68 after operator loop", "$082F shift state", "RTS $4FD5", "A,Y,P plus $4FF0", "$082F;$083C", "YM key register $08 and shadow", "Verified", "Correlate flag bit with note/retrigger paths"),
    (0x4FD6, 0x4FEF, "tail_dispatch_entry", "iterate eight YM2151 channels", "$500D for hardware type 2", "X=dispatcher index 1; $57AF=$22", "RTS $4FEF", "A,Y,P; X clobbered transitively", "$57AE,X", "$083C and per-channel effects from $4E68", "Verified", "Cycle-count worst and best active-channel paths"),
    (0x4FF0, 0x500C, "callable_subroutine", "YM2151 busy wait with sticky timeout", "all YM register writers", "Y=YM register number; A preserved unless timeout already sticky", "RTS $500C", "P; A preserved on normal first call", "$0D;$1811;$02", "$0D on timeout;$02 bit 1", "Verified", "Prove initialization/reset of sticky $0D across all paths"),
    (0x500D, 0x5028, "callable_dispatcher", "select hardware base/type and tail-dispatch", "$41D8;$41E0", "X=phase index 0 or 1", "tail $4DFC for type 0; tail $4FD6 otherwise", "A,Y,P; X passed/clobbered", "$57A8-$57AD,X", "$08-$09;$081D", "Verified", "Confirm only X=0/1 is configured at every caller"),
]


TABLES = [
    (0x57A0, 0x57A7, 1, 8, "YM algorithm/operator scaling masks", "$4F05", "index = YM algorithm bits 2..0", "Verified"),
    (0x57A8, 0x57AD, 1, 2, "overlapping hardware pointer/type views", "$500D", "X=0 POKEY or 1 YM2151", "Verified"),
    (0x57AE, 0x57AF, 1, 2, "physical-list-head base by hardware dispatcher", "$4E08;$4FDC", "X=0 -> $1E POKEY; X=1 -> $22 YM; next byte $57B0 is NMI entry", "Verified exact extent"),
    (0x5AF9, 0x5B78, 1, 128, "YM base key-code lookup view", "$4EEC", "configured note index 13..95; indices 98..127 structurally alias total-level table but are dormant", "Verified"),
    (0x5B5B, 0x5C5A, 1, 256, "YM operator total-level scaling lookup", "$4F5D;$4F6F", "Y is eight-bit combined nibble index", "Verified"),
    (0x5C5B, 0x5C5E, 1, 4, "YM total-level event/control bias table", "$4EBB;$4ED5;$4F14", "X=original $082F>>4 after two destructive memory shifts and two A shifts; configured indices 0..3", "Verified exact extent"),
    (0x72DC, 0x73DB, 1, 256, "YM operator total-level nonlinear lookup", "$4F51", "Y is eight-bit combined index", "Verified"),
]


POKEY_REFERENCE_DEFINES = {
    "POLY9": "0x80", "CH1_HICLK": "0x40", "CH3_HICLK": "0x20",
    "CH12_JOINED": "0x10", "CH34_JOINED": "0x08", "CH1_FILTER": "0x04",
    "CH2_FILTER": "0x02", "CLK_15KHZ": "0x01",
}


def configured_pokey_control_operands(rom):
    records = list(audit.type7_records(rom))
    rows, edges, _, errors = audit.type7_sequence_map(
        rom, [(f"record_{r['offset']}", r["sequence_pointer"]) for r in records])
    if errors:
        raise SystemExit(f"sequence errors: {errors}")
    by_address = {row["address"]: row for row in rows}
    computed_targets = defaultdict(list)
    for edge in edges:
        if edge["kind"].startswith("conditional"):
            computed_targets[edge["source"]].append(edge["target"])
    queue = deque((r["sequence_pointer"], r["chip"]) for r in records)
    seen = set()
    set_values = set()
    clear_values = set()
    while queue:
        address, mode = queue.popleft()
        if (address, mode) in seen or address not in by_address:
            continue
        seen.add((address, mode))
        row = by_address[address]
        opcode = row["opcode"]
        if opcode == 0x90:
            mode = "POKEY"
        elif opcode == 0x91:
            mode = "YM2151"
        raw = bytes.fromhex(row["raw_hex"])
        if mode == "POKEY" and opcode == 0x8B:
            set_values.add(raw[1])
        elif mode == "POKEY" and opcode == 0x9B:
            clear_values.add(raw[1])
        target = row["target"] if row["target"] != "" else None
        next_address = address + row["size"]
        if opcode == 0x99:
            queue.append((target, mode))
        elif opcode in (0xAE, 0xAF):
            for computed_target in computed_targets[address]:
                queue.append((computed_target, mode))
        elif row["mnemonic"] not in ("CHAIN", "END"):
            queue.append((next_address, mode))
            if target is not None:
                queue.append((target, mode))
    return set_values, clear_values, len(seen)


def validate(rom):
    if len(rom) != 0xC000:
        raise SystemExit(f"expected 0xC000-byte ROM, got {len(rom):#x}")
    for address, expected in ANCHORS.items():
        off = address - ROM_BASE
        actual = rom[off:off + len(expected)]
        if actual != expected:
            raise SystemExit(f"anchor mismatch at {hx(address)}")


def write_csv(path, header, rows, address_columns=2):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for row in rows:
            writer.writerow([*(hx(v) for v in row[:address_columns]), *row[address_columns:]])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("rom", type=Path)
    p.add_argument("--csv", required=True, type=Path)
    p.add_argument("--table-csv", required=True, type=Path)
    p.add_argument("--pokey-control-csv", required=True, type=Path)
    p.add_argument("--pokey-ref", required=True, type=Path)
    args = p.parse_args()
    raw_rom = args.rom.read_bytes()
    validate(raw_rom)
    rom = gd.GauntletROM(str(args.rom))
    set_values, clear_values, mode_states = configured_pokey_control_operands(rom)
    if set_values != {0x20} or clear_values:
        raise SystemExit(
            f"unexpected configured POKEY control operands: set={set_values}, clear={clear_values}")
    reference = args.pokey_ref.read_text()
    for name, value in POKEY_REFERENCE_DEFINES.items():
        if f"#define {name}" not in reference or value not in reference:
            raise SystemExit(f"missing POKEY reference definition {name}={value}")
    write_csv(args.csv, ["start", "end_inclusive", "entry_kind", "role", "incoming", "entry_assumptions", "exits", "clobbers", "reads", "writes", "confidence", "next_test"], ROWS)
    write_csv(args.table_csv, ["start", "end_inclusive", "record_width", "count", "role", "consumers", "index_domain", "confidence"], TABLES)
    control_rows = [
        ("AUDCTL_bit", "0x80", "refs/pokey.cpp", "POLY9: select 9-bit rather than 17-bit polynomial", "No configured POKEY $8B/$9B operand selects it", "Verified supplied implementation meaning/reachability"),
        ("AUDCTL_bit", "0x40", "refs/pokey.cpp", "CH1_HICLK: channel 1 uses 1.79 MHz clock", "Forced with $10 by $4E3B when channel-2 member wins/ties", "Verified"),
        ("AUDCTL_bit", "0x20", "refs/pokey.cpp", "CH3_HICLK: channel 3 uses 1.79 MHz clock", "Only configured POKEY SET_CTRL_BITS operand; also forced for joined channel 3/4", "Verified"),
        ("AUDCTL_bit", "0x10", "refs/pokey.cpp", "CH12_JOINED: channel 1/2 form 16-bit divider", "Forced with $40 by $4E3B when channel-2 member wins/ties", "Verified"),
        ("AUDCTL_bit", "0x08", "refs/pokey.cpp", "CH34_JOINED: channel 3/4 form 16-bit divider", "Forced with $20 by $4E14 when channel-4 member wins/ties", "Verified"),
        ("AUDCTL_bit", "0x04", "refs/pokey.cpp", "CH1_FILTER: channel 3 clocks channel-1 high-pass sample", "No configured POKEY $8B/$9B operand selects it", "Verified supplied implementation meaning/reachability"),
        ("AUDCTL_bit", "0x02", "refs/pokey.cpp", "CH2_FILTER: channel 4 clocks channel-2 high-pass sample", "No configured POKEY $8B/$9B operand selects it", "Verified supplied implementation meaning/reachability"),
        ("AUDCTL_bit", "0x01", "refs/pokey.cpp", "CLK_15KHZ: base clock 15.7 rather than 63.9 kHz", "No configured POKEY $8B/$9B operand selects it", "Verified supplied implementation meaning/reachability"),
        ("configured_operand", "0x20", "$51B7 and mode-aware traversal", "OR CH3_HICLK into per-logical-channel $03EA mask", "Commands $43-$49; chip-test $05 retains reset mask 0/$FF", "Verified"),
        ("forced_pair_mode", "0x28", "$4D02 carry -> $4E14", "CH3_HICLK | CH34_JOINED", "Second member priority >= first; ties select joined mode", "Verified"),
        ("forced_pair_mode", "0x50", "$4D02 carry -> $4E3B", "CH1_HICLK | CH12_JOINED", "Second member priority >= first; ties select joined mode", "Verified"),
        ("final_combine", "formula", "$4DC4-$4DF8;$4E42-$4E4A", "AUDCTL = accumulated OR masks AND accumulated AND masks", "$03EA starts 0; $03CC starts $FF; $8B ORs and $9B clears", "Verified"),
    ]
    write_csv(args.pokey_control_csv,
              ["kind", "value", "source", "meaning", "configured_use", "confidence"],
              control_rows, address_columns=0)
    print(f"physical output: {len(ROWS)} blocks, {len(TABLES)} tables, "
          f"{len(control_rows)} POKEY control rows, {len(ANCHORS)} anchors, "
          f"{mode_states} mode states validated")


if __name__ == "__main__":
    main()
