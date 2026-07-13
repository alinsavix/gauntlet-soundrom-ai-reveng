#!/usr/bin/env python3
"""Validate dormant command-handler entries and generate their semantic catalog."""

import argparse
import csv
from pathlib import Path


ROM_BASE = 0x4000
RESERVED_TYPES = (1, 2, 4, 6, 12, 14)
EXPECTED_ENTRIES = {
    1: 0x434C, 2: 0x4359, 4: 0x4374,
    6: 0x43AF, 12: 0x4461, 14: 0x4618,
}
ANCHORS = {
    0x4633: "46 43 4b 43 58 43 68 43 73 43 8c 43 ae 43 dd 44 44 44 d3 43 0a 44 38 44 60 44 18 46 17 46",
    0x434C: "a8 b9 59 65 29 0f aa b9 5a 65 95 18 60",
    0x4359: "a8 b9 59 65 29 0f aa b9 5a 65 18 75 18 95 18 60",
    0x4374: "08 78 85 11 a0 1d b9 90 03 4a 4a 45 11 d0 05 a9 ff 99 28 02 88 10 ef 28",
    0x43AF: "85 11 4a 4a 4a 4a a8 a5 11 29 0f 18 79 ae 57 a8 08 78 b9 e6 07 f0 0c a8 88 a9 ff 99 28 02 b9 e6 07 d0 f4 28 60",
    0x4461: "aa bd 5b 65 c9 3b b0 3e c9 08 90 14 c9 0a 90 36 c9 0d 90 0c c9 12 90 2e c9 16 90 04 c9 19 90 26 0a a8",
    0x4618: "60",
    0x5059: "08 78 bd e6 07 f0 0d aa ca bd 28 02 cd 30 08 d0 f1 20 6f 50 28 60",
    0x6559: "00 00 00 00 00 00",
}


ROWS = {
    1: (
        "set workspace variable from sliding support pair",
        "A=handler parameter; Y=A",
        "$6559,Y selector low nibble; $655A,Y value",
        "$18+(selector&$0F) = value",
        "RTS",
        "No configured command; support bytes $6559-$655E are all zero",
    ),
    2: (
        "add sliding support-pair value to workspace variable",
        "A=handler parameter; Y=A",
        "$6559,Y selector low nibble; $655A,Y value; selected $18-$27 byte",
        "$18+(selector&$0F) += value modulo 256",
        "RTS",
        "No configured command; support bytes $6559-$655E are all zero",
    ),
    4: (
        "soft-kill logical channels by encoded status class",
        "A=status-class selector",
        "$0390,Y for Y=29..0",
        "$0228,Y=$FF where (($0390,Y>>2) XOR A)==0; interrupt-atomic",
        "RTS",
        "No configured command; no support table",
    ),
    6: (
        "soft-kill every node in a selected physical-list chain",
        "A high nibble selects $57AE index; low nibble offsets returned list head",
        "$57AE,A>>4; $07E6 list links",
        "$0228,node=$FF for every linked logical channel; interrupt-atomic",
        "RTS",
        "No configured command, so $57AE index/offset domain is empty",
    ),
    12: (
        "apply a safe bytecode operation to matching active channels",
        "A indexes sliding $655B-$655E fields",
        "$655B opcode offset; $655C argument; $655D target command; $655E physical offset",
        "validate target is type 7; traverse head $1E+offset; dispatch opcode $80-$87/$8A-$8C/$92-$95/$99-$BA with A=argument",
        "tail $5059/$506F then RTS",
        "No configured command; zero support bytes fail target-type validation",
    ),
    14: (
        "null handler",
        "none",
        "none",
        "none",
        "RTS",
        "No configured command; deliberately inert",
    ),
}


def require_bytes(rom, address, expected_hex):
    expected = bytes.fromhex(expected_hex)
    offset = address - ROM_BASE
    if rom[offset:offset + len(expected)] != expected:
        raise SystemExit(f"anchor mismatch at ${address:04X}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("rom", type=Path)
    parser.add_argument("--command-csv", required=True, type=Path)
    parser.add_argument("--cpu-entry-csv", required=True, type=Path)
    parser.add_argument("--csv", required=True, type=Path)
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    if len(rom) != 0xC000:
        raise SystemExit(f"expected 0xC000-byte ROM, got {len(rom):#x}")
    for address, expected in ANCHORS.items():
        require_bytes(rom, address, expected)

    table = rom[0x4633 - ROM_BASE:0x4651 - ROM_BASE]
    entries = [int.from_bytes(table[2 * i:2 * i + 2], "little") + 1
               for i in range(15)]
    for handler_type, expected in EXPECTED_ENTRIES.items():
        if entries[handler_type] != expected:
            raise SystemExit(f"type {handler_type} entry changed")

    command_counts = {handler_type: 0 for handler_type in RESERVED_TYPES}
    with args.command_csv.open(newline="") as f:
        for row in csv.DictReader(f):
            handler_type = int(row["handler_type"])
            if handler_type in command_counts:
                command_counts[handler_type] += 1
    if any(command_counts.values()):
        raise SystemExit(f"reserved handler acquired configured command: {command_counts}")

    entry_sources = {}
    with args.cpu_entry_csv.open(newline="") as f:
        for row in csv.DictReader(f):
            address = int(row["address"], 16)
            if address in EXPECTED_ENTRIES.values():
                entry_sources[address] = (row["entry_kind"], row["source"], row["confidence"])
    for handler_type, address in EXPECTED_ENTRIES.items():
        expected_source = f"handler_table_type_{handler_type}"
        if entry_sources.get(address) != ("table_dispatch_entry", expected_source, "Verified"):
            raise SystemExit(f"unexpected fixed-point source for type {handler_type}")

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow([
            "handler_type", "entry", "semantic_role", "input_contract",
            "reads", "writes_or_effect", "exit", "configured_command_count",
            "fixed_point_source", "configured_status", "confidence",
        ])
        for handler_type in RESERVED_TYPES:
            role, inputs, reads, writes, exit_kind, status = ROWS[handler_type]
            writer.writerow([
                handler_type, f"0x{EXPECTED_ENTRIES[handler_type]:04X}", role,
                inputs, reads, writes, exit_kind, command_counts[handler_type],
                entry_sources[EXPECTED_ENTRIES[handler_type]][1], status,
                "Verified semantics and configured dormancy; original provenance Unknown",
            ])
    print(f"reserved handlers: {len(RESERVED_TYPES)} entries, "
          f"{len(ANCHORS)} anchors, zero configured commands")


if __name__ == "__main__":
    main()
