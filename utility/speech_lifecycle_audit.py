#!/usr/bin/env python3
"""Validate and emit the TMS5220 speech lifecycle consumer catalog."""

import argparse
import csv
from pathlib import Path

ROM_BASE = 0x4000


def hx(v):
    return f"0x{v:04X}"


ANCHORS = {
    0x5833: bytes.fromhex("08 78 a0 00 8c 32 08 8c 33 08"),
    0x5894: bytes.fromhex("a5 33 f0 13 38 ed 00 00"),
    0x58AB: bytes.fromhex("ad 30 10 29 20 f0 17"),
    0x58C9: bytes.fromhex("a9 ff 85 30 ad 31 10 09 80"),
    0x58D7: bytes.fromhex("a4 2f d0 1e ac 32 08 cc 33 08"),
    0x58FC: bytes.fromhex("b1 2b e6 2b d0 02 e6 2c"),
    0x591A: bytes.fromhex("a9 ff 85 2f a9 60"),
    0x5926: bytes.fromhex("8d 20 18 ad 31 10 29 7f 8d 31 10"),
    0x5932: bytes.fromhex("a4 2f f0 03 4c e2 59"),
    0x5939: bytes.fromhex("08 78 48 a8 b9 3f 64"),
    0x595D: bytes.fromhex("b9 b2 63 0a 85 31"),
    0x5978: bytes.fromhex("b1 31 85 2b c8 b1 31 85 2c"),
    0x5995: bytes.fromhex("b1 31 85 2d c8 b1 31 85 2e"),
    0x59A8: bytes.fromhex("b9 3f 64 29 0f 85 32"),
    0x59E2: bytes.fromhex("08 78 ac 33 08 c8 c0 08"),
    0x59F3: bytes.fromhex("e4 35 90 12 f0 08"),
}


ROWS = [
    (0x5833, 0x5873, "callable_subroutine", "initialize/reset speech state with dummy stream", "boot;$58BE watchdog tail-jump", "interrupt state preserved with PHP/SEI/PLP", "RTS $5873", "A,Y,P", "$34;$1031;$00", "$0832-$0833;$34;$1031-$1033;$30;$2B-$2F;$33", "Verified", "Determine oscillator base bits in $34"),
    (0x5894, 0x58AA, "callable_prefix", "scheduled TMS5220 reset pulse", "IRQ audio update calls four times", "$33 nonzero is frame deadline", "RTS $58AA or continue $58AB", "A,P", "$33;$00", "$1032 at deadline-minus-8;$33 at deadline", "Verified", "Convert frame deltas to time after IRQ timing proof"),
    (0x58AB, 0x58C8, "internal_block", "active-low ready watchdog", "$5894", "$1030 bit 5 is TMS ready active low", "tail $5833 after 32/33 IRQ intervals; RTS $5931 otherwise", "A,P", "$1030;$00;$30", "$30", "Verified", "Confirm parity-dependent reset in MAME/cabinet trace"),
    (0x58C9, 0x58F8, "internal_block", "ready service, idle dequeue, and state dispatch", "$5894 ready path", "TMS ready; write strobe first deasserted", "start command $5939; stream $58F9; write $5926", "A,Y,P", "$1031;$2F;$0832-$0834;$0833", "$30;$1031;$0832;$35", "Verified", "Trace queue empty/current-priority interaction"),
    (0x58F9, 0x5915, "internal_block", "FIFO payload stream and length exhaustion", "$58C9 with $2F=$FF", "TMS ready; $2B-$2E current stream", "write byte $5926; enter drain state $11", "A,Y,P", "($2B),Y;$2D-$2E", "$2B-$2F;$2A", "Verified", "Confirm final payload byte acceptance in hardware trace"),
    (0x5916, 0x5931, "internal_block", "Speak External kickoff and 17-write zero drain", "$58C9 non-idle states", "$80 kickoff or $11..1 drain; TMS FIFO size 16", "RTS $5931", "A,Y,P", "$2F;$1031", "$2F;$1820;$1031", "Verified ROM; MAME FIFO rationale Strong inference", "Confirm stop-frame/zero-padding sequence in runtime trace"),
    (0x5932, 0x5938, "callable_dispatch", "start immediately if idle, otherwise enqueue", "type-11 handler $4439; opcode $9A", "A=parameter; X=priority from $64CC for command path", "fallthrough $5939 or tail $59E2", "Y,P", "$2F", "none", "Verified", "Verify opcode-$9A X priority provenance"),
    (0x5939, 0x59E1, "internal_block", "load metadata, clock, mixer, and arm kickoff", "$5932;$58F6 dequeue", "A=speech parameter; interrupts atomically disabled", "RTS $59E1", "A,Y,P", "$643F;$64CC;$63B2;$8449-$85C2;$85C3-$873C;$28-$29;$34", "$31-$35;$2A-$2F;$1033;$1020", "Verified", "Assign exact mixer subfields for clock-flag low nibble"),
    (0x59E2, 0x5A0A, "callable_subroutine", "atomic priority queue insertion", "$5936 and busy speech requests", "A=parameter; X=incoming priority", "RTS $5A0A; reject on full/lower priority", "A,Y,P", "$0832-$0833;$35", "$0832 on higher-priority flush;$0833;$0834-$083B;$35", "Verified", "Runtime trace full-ring rejection and flush ordering"),
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("rom", type=Path)
    p.add_argument("--csv", required=True, type=Path)
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
        for row in ROWS:
            w.writerow([hx(row[0]), hx(row[1]), *row[2:]])
    print(f"speech lifecycle: {len(ROWS)} blocks, {len(ANCHORS)} anchors validated")


if __name__ == "__main__":
    main()
