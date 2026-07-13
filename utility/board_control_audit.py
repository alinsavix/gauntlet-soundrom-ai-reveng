#!/usr/bin/env python3
"""Validate and emit board/coin control blocks and state transitions."""

import argparse
import csv
from pathlib import Path

ROM_BASE = 0x4000


def hx(v):
    return f"0x{v:04X}"


ANCHORS = {
    0x8381: bytes.fromhex("a9 10 2c 30 10 d0 24"),
    0x8388: bytes.fromhex("a2 03 ad 20 10 4a 48"),
    0x838F: bytes.fromhex("bd a4 83 90 02 a9 00"),
    0x83A4: bytes.fromhex("40 10 04 01 c0 30 0c 03"),
    0x83AC: bytes.fromhex("ad 20 10 a2 03 4a 48"),
    0x83B3: bytes.fromhex("b5 3e 29 1f b0 17"),
    0x83E3: bytes.fromhex("bd a4 83 18 65 44 45 44"),
    0x83F2: bytes.fromhex("f6 36 68 ca 10 b9"),
    0x83F8: bytes.fromhex("e6 42 a5 42 4a b0 31"),
    0x83FF: bytes.fromhex("a5 36 05 37 05 38 05 39"),
    0x840D: bytes.fromhex("a2 03 b5 36 f0 08 c9 10"),
    0x8420: bytes.fromhex("a2 03 b5 36 f0 07 18 69 ef"),
    0x8430: bytes.fromhex("a5 36 05 37 8d 35 10"),
    0x8437: bytes.fromhex("a5 38 05 39 8d 34 10 60"),
    0x843F: bytes.fromhex("a5 44 20 c8 44 4c 1e 58"),
}


BLOCKS = [
    (0x8381, 0x8387, "callable_entry", "select active-low self-test input state", "IRQ $41C4", "called once per normal IRQ", "self-test-active $8388 or normal/inactive $83AC", "A,P", "$1030 bit 4", "none", "Verified", "Confirm reset-time initial values of $36-$42/$44"),
    (0x8388, 0x83A3, "internal_block", "self-test-active direct four-input cache encoding", "$8381 with $1030 bit 4 low", "$1020 bits 3..0 active low", "RTS $83A3", "A,X,P", "$1020;$44;$83A4-$83AB", "$44", "Verified", "Map four input positions to cabinet player/slot labels"),
    (0x83AC, 0x83F7, "internal_block", "normal/inactive input filter and event generation", "$8381 with $1030 bit 4 high", "$3E-$41 four filter accumulators", "continue pulse service $83F8", "A,X,P", "$1020;$3E-$42;$44;$83A4-$83AB", "$3E-$42;$44;$36-$39", "Verified algorithm; Strong inference debounce role", "Relate filter threshold latency to cabinet expectations"),
    (0x83F8, 0x843E, "internal_block", "alternate-phase pulse stretcher and counter writes", "$83AC", "$36-$39 four pending/pulse states; $42 phase", "RTS $843E", "A,X,P", "$36-$42", "$36-$39;$1034-$1035", "Verified algorithm; Strong inference pulse-width role", "Measure solenoid active polarity and pulse duration on hardware trace"),
    (0x843F, 0x8446, "nmi_table_entry", "return cached input/event byte to main CPU", "NMI direct-dispatch table query 3", "$44 is the four-field board-input/event cache", "JSR $44C8 then tail $581E NMI restore", "A,P plus $44C8", "$44;$1030", "$1000;$02", "Verified", "Map four cached fields to cabinet player/slot labels"),
]


TRANSITIONS = [
    ("self-test-active direct input inactive", "$1020 bit=1", "$44 field", "00", "replace selected two-bit field with 00"),
    ("self-test-active direct input active", "$1020 bit=0", "$44 field", "01 at field position", "replace selected field using $40/$10/$04/$01"),
    ("normal filtered input active", "filter low5=1..26 and phase&7=7", "$3E-$41", "low5 minus 1", "slow decay; 27..31 decay every call"),
    ("normal filtered input inactive", "filter below saturation", "$3E-$41", "add $21", "8-bit accumulator rise"),
    ("filter threshold crossing", "add $21 carries with nonzero result", "$3E-$41 and $36-$39", "filter=$1F; pulse state incremented", "also updates corresponding $44 field"),
    ("pulse start", "even phase and aggregate 1..15", "$36-$39", "first nonzero becomes $F0", "begins stretched solenoid pulse"),
    ("pulse decay", "even phase and state >=$10", "$36-$39", "subtract $10", "$F0,$E0,...,$10,0"),
    ("physical outputs", "every call", "$1035/$1034", "OR($36,$37) / OR($38,$39)", "left/right mechanical counter solenoids"),
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("rom", type=Path)
    p.add_argument("--csv", required=True, type=Path)
    p.add_argument("--transition-csv", required=True, type=Path)
    args = p.parse_args()
    rom = args.rom.read_bytes()
    if len(rom) != 0xC000:
        raise SystemExit("unexpected ROM size")
    for addr, expected in ANCHORS.items():
        off = addr - ROM_BASE
        if rom[off:off + len(expected)] != expected:
            raise SystemExit(f"anchor mismatch at {hx(addr)}")
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["start", "end_inclusive", "entry_kind", "role", "incoming", "entry_assumptions", "exits", "clobbers", "reads", "writes", "confidence", "next_test"])
        for row in BLOCKS:
            w.writerow([hx(row[0]), hx(row[1]), *row[2:]])
    with args.transition_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["transition", "condition", "state", "result", "interpretation"])
        w.writerows(TRANSITIONS)
    print(f"board control: {len(BLOCKS)} blocks, {len(TRANSITIONS)} transitions, {len(ANCHORS)} anchors validated")


if __name__ == "__main__":
    main()
