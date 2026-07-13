#!/usr/bin/env python3
"""Generate the consumer-led RESET/diagnostic/initialization/main-loop catalog."""

import argparse
import csv
from pathlib import Path


ROM_BASE = 0x4000

ANCHORS = {
    0x4002: bytes.fromhex("78 d8 a2 ff 9a a9 ff 8d 30 10 a9 00 8d 30 10"),
    0x4018: bytes.fromhex("ad 30 10 29 10 f0 0d a9 00 95 00 e8 d0 fb"),
    0x402C: bytes.fromhex("a0 00 a9 ff a9 01 99 00 00 d9 00 00 f0 03 4c 57 41"),
    0x4057: bytes.fromhex("a9 00 85 0e a9 00 85 02 e8 e0 10 d0 03 4c 8f 40"),
    0x408F: bytes.fromhex("a2 ff 9a a2 40 a9 80 20 5f 41 a9 40 20 5f 41"),
    0x40A3: bytes.fromhex("a9 ff 85 01 20 83 41 a9 00 85 00 85 0e 85 0f 58"),
    0x40C8: bytes.fromhex("78 a9 00 85 01 20 0b 5a a2 ff 8e 13 02"),
    0x4104: bytes.fromhex("a5 02 29 fe 85 02 2c 30 10 70 18 ac 24 02"),
    0x4127: bytes.fromhex("ae 10 02 ec 11 02 f0 10 e8 e0 10 90 02 a2 00"),
    0x4142: bytes.fromhex("e0 01 f0 11 48 e0 08 b0 04 a9 10 d0 04 a5 02 09 08"),
    0x4157: bytes.fromhex("a9 10 8d 00 10 4c 5c 41"),
    0x415F: bytes.fromhex("85 11 a9 3f 85 10 a9 00 85 0e a0 00 86 0f 18"),
    0x4183: bytes.fromhex("8d 30 18 60"),
    0x4194: bytes.fromhex("a5 01 f0 05 e6 00 4c c4 41"),
    0x5A0B: bytes.fromhex("a9 ff 8d 03 10 a9 33 8d 02 10 a9 00 8d 0b 10"),
    0x5A25: bytes.fromhex("ad 30 10 29 c0 c9 80 d0 fe 4c 02 40"),
}


def hx(value):
    return f"0x{value:04X}"


def checksum(values):
    accumulator = 0
    for value in values:
        # $416D clears carry before every ADC.
        accumulator = (accumulator + value) & 0xFF
    return accumulator


def catalog_rows(checksums):
    checksum_text = "; ".join(
        f"${start:04X}-${start + 0x3FFF:04X}=${value:02X}"
        for start, value in checksums)
    return [
        {
            "start": hx(0x4002), "end_inclusive": hx(0x401D),
            "kind": "reset_entry", "role": "CPU and YM reset sequencing; sample self-test",
            "entry_contract": "RESET tail from $5A2E; interrupts masked",
            "exits": "$401F self-test inactive/high; $402C active/low",
            "clobbers": "A,X,P,SP", "reads": "$1030", "writes": "$1030,SP",
            "confidence": "Verified",
        },
        {
            "start": hx(0x401F), "end_inclusive": hx(0x402B),
            "kind": "fast_init", "role": "normal boot: clear zero page and skip diagnostics",
            "entry_contract": "$1030 bit 4 set (self-test inactive)",
            "exits": "tail $40C8 after JSR $4183",
            "clobbers": "A,X,P", "reads": "none", "writes": "$0000-$00FF;$1830",
            "confidence": "Verified",
        },
        {
            "start": hx(0x402C), "end_inclusive": hx(0x4056),
            "kind": "zero_page_ram_test", "role": "walking one/complement test; leave page zeroed",
            "entry_contract": "$1030 bit 4 clear; X=0",
            "exits": "$4057 success; tail $4157 first mismatch",
            "clobbers": "A,Y,P", "reads": "$0000-$00FF", "writes": "$0000-$00FF",
            "confidence": "Verified",
        },
        {
            "start": hx(0x4057), "end_inclusive": hx(0x408E),
            "kind": "paged_ram_test", "role": "walking one/complement test pages $01-$0F; leave zeroed",
            "entry_contract": "page-zero test succeeded; X=0",
            "exits": "$408F after page $0F; $4157 fatal for page $01; continue after logged errors pages $02-$0F",
            "clobbers": "A,X,Y,P", "reads": "$0100-$0FFF",
            "writes": "$0100-$0FFF;$02;$0E-$0F",
            "confidence": "Verified",
        },
        {
            "start": hx(0x408F), "end_inclusive": hx(0x40C7),
            "kind": "rom_test_irq_sync", "role": "three ROM checksums then wait for first initialization IRQ",
            "entry_contract": "self-test RAM diagnostics complete",
            "exits": "$40C8 when early IRQ/NMI makes $00 nonzero or 65536-count timeout sets $02 bit 2",
            "clobbers": "A,X,Y,P,SP", "reads": "$4000-$FFFF;$00;$02",
            "writes": "$00-$01;$02;$0E-$0F;$10-$11;$1830",
            "confidence": f"Verified; checksum results {checksum_text}",
        },
        {
            "start": hx(0x40C8), "end_inclusive": hx(0x4103),
            "kind": "common_initialization", "role": "install normal NMI/ring/mixer state and initialize devices",
            "entry_contract": "fast boot or diagnostic/IRQ-sync exit",
            "exits": "$4104 with IRQ enabled",
            "clobbers": "A,X,Y,P plus callees", "reads": "$1010",
            "writes": "$01;$13;$28-$29;$0210-$0211;$0213;$0224-$0225;$1000;$1020 plus $5833/$41E6 effects",
            "confidence": "Verified",
        },
        {
            "start": hx(0x4104), "end_inclusive": hx(0x4126),
            "kind": "main_output_drain", "role": "clear main heartbeat and send at most one queued output byte",
            "entry_contract": "normal main loop",
            "exits": "fall $4127 whether latch busy, queue empty, or one byte sent",
            "clobbers": "A,Y,P", "reads": "$02;$1030;$0224-$0225;$0214-$0223",
            "writes": "$02;$0224;$1000", "confidence": "Verified",
        },
        {
            "start": hx(0x4127), "end_inclusive": hx(0x4141),
            "kind": "main_input_dispatch", "role": "consume and dispatch at most one command-ring byte",
            "entry_contract": "output phase complete",
            "exits": "tail $4104 after optional JSR $432E",
            "clobbers": "A,X,Y,P plus dispatcher", "reads": "$0210-$0211;$0200-$020F",
            "writes": "$0210 plus dispatcher effects", "confidence": "Verified",
        },
        {
            "start": hx(0x4142), "end_inclusive": hx(0x4156),
            "kind": "ram_error_classifier", "role": "classify failing RAM page while preserving test A",
            "entry_contract": "X=failing page; A=current test pattern",
            "exits": "$4157 fatal for page $01; RTS with $02=$10 for pages $02-$07 or $02|=$08 for $08-$0F",
            "clobbers": "P; A preserved on returning paths", "reads": "$02", "writes": "$02;stack",
            "confidence": "Verified",
        },
        {
            "start": hx(0x4157), "end_inclusive": hx(0x415E),
            "kind": "fatal_ram_failure", "role": "send error byte $10 and halt",
            "entry_contract": "page-zero/page-one RAM mismatch",
            "exits": "infinite loop $415C", "clobbers": "A,P", "reads": "none", "writes": "$1000",
            "confidence": "Verified",
        },
        {
            "start": hx(0x415F), "end_inclusive": hx(0x4182),
            "kind": "rom_checksum_helper", "role": "16 KiB modulo-256 checksum; flag result if not $FF",
            "entry_contract": "X=start page; A=error mask",
            "exits": "RTS; X advanced by $40 pages",
            "clobbers": "A,X,Y,P", "reads": "64 pages through ($0E),Y;$02",
            "writes": "$02;$0E-$0F;$10-$11", "confidence": "Verified",
        },
        {
            "start": hx(0x4183), "end_inclusive": hx(0x4186),
            "kind": "irq_ack_helper", "role": "acknowledge/clear sound IRQ source",
            "entry_contract": "callable; A is value written but otherwise preserved",
            "exits": "RTS", "clobbers": "none", "reads": "none", "writes": "$1830",
            "confidence": "Verified",
        },
        {
            "start": hx(0x5A0B), "end_inclusive": hx(0x5A24),
            "kind": "boot_board_handshake", "role": "write fixed board-interface startup sequence",
            "entry_contract": "called once by common initialization at $40CD",
            "exits": "RTS",
            "clobbers": "A,P", "reads": "none",
            "writes": "$1003=$FF;$1002=$33;$100B=$00;$100C=$22;$1000=$0F",
            "confidence": "Verified writes; board-level purpose Unknown",
        },
        {
            "start": hx(0x5A25), "end_inclusive": hx(0x5A30),
            "kind": "reset_vector_gate", "role": "wait for board status bits 7..6 to equal $80, then enter RESET body",
            "entry_contract": "RESET vector",
            "exits": "tail $4002 once ($1030 & $C0)==$80; otherwise spin at $5A2C",
            "clobbers": "A,P", "reads": "$1030", "writes": "none",
            "confidence": "Verified",
        },
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("rom", type=Path)
    parser.add_argument("--csv", required=True, type=Path)
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    if len(rom) != 0xC000:
        raise SystemExit(f"expected 0xC000-byte ROM, got {len(rom):#x}")
    for address, expected in ANCHORS.items():
        offset = address - ROM_BASE
        if rom[offset:offset + len(expected)] != expected:
            raise SystemExit(f"anchor mismatch at {hx(address)}")
    checksums = []
    for start in (0x4000, 0x8000, 0xC000):
        offset = start - ROM_BASE
        value = checksum(rom[offset:offset + 0x4000])
        checksums.append((start, value))
    if [value for _, value in checksums] != [0xFF, 0xFF, 0xFF]:
        raise SystemExit(f"ROM checksum mismatch: {checksums}")
    output = catalog_rows(checksums)
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)
    print(f"initialization/main: {len(output)} blocks, {len(ANCHORS)} anchors, "
          "three 16-KiB checksums=$FF")


if __name__ == "__main__":
    main()
