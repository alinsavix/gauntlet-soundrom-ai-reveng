#!/usr/bin/env python3
"""Generate the consumer-led sound-NMI boot/normal protocol catalog."""

import argparse
import csv
from pathlib import Path


ROM_BASE = 0x4000

ANCHORS = {
    0x4018: bytes.fromhex("ad 30 10 29 10 f0 0d a9 00 95 00 e8 d0 fb"),
    0x4057: bytes.fromhex("a9 00 85 0e a9 00 85 02 e8 e0 10 d0 03 4c 8f 40"),
    0x408F: bytes.fromhex("a2 ff 9a a2 40 a9 80 20 5f 41 a9 40 20 5f 41"),
    0x40A7: bytes.fromhex("20 83 41 a9 00 85 00 85 0e 85 0f 58 a5 00 d0 11"),
    0x40C8: bytes.fromhex("78 a9 00 85 01 20 0b 5a a2 ff 8e 13 02"),
    0x44BD: bytes.fromhex("68 aa 68 a8 a9 ff 8d 13 02 68 40"),
    0x57B0: bytes.fromhex("48 2c 30 10 70 fb 98 48 ac 13 02 d0 22"),
    0x57BD: bytes.fromhex("18 ac 12 02 98 10 0e 49 80 a8 a5 04 49 80 85 04 30 02 e6 05"),
    0x57D1: bytes.fromhex("98 69 01 8d 12 02 ad 10 10 91 04 4c 20 58"),
    0x57DF: bytes.fromhex("c8 f0 06 ad 10 10 4c 20 58"),
}


def hx(value):
    return f"0x{value:04X}"


def find_direct_writes(rom, address):
    operand = address.to_bytes(2, "little")
    opcodes = {0x8D: "STA", 0x8C: "STY", 0x8E: "STX", 0xEE: "INC", 0xCE: "DEC"}
    rows = []
    for offset in range(len(rom) - 2):
        if rom[offset] in opcodes and rom[offset + 1:offset + 3] == operand:
            rows.append((ROM_BASE + offset, opcodes[rom[offset]]))
    return rows


def rows():
    return [
        {
            "start": hx(0x57B0), "end_inclusive": hx(0x57BC),
            "phase": "nmi_entry_mode_select", "mode": "$0213 selects path",
            "state_in": "NMI vector; A/Y not yet saved completely",
            "effect": "wait for output latch availability, save Y, branch on mode byte",
            "exit": "$57BD mode 0; $57DF modes 1..$FF", "confidence": "Verified",
        },
        {
            "start": hx(0x4018), "end_inclusive": hx(0x4029),
            "phase": "fast_init_branch", "mode": "$1030 bit 4 set",
            "state_in": "RESET hardware-status sample",
            "effect": "zero page $00 only, run $4183 check, skip boot NMI window",
            "exit": "$40C8 normal-mode install", "confidence": "Verified",
        },
        {
            "start": hx(0x4057), "end_inclusive": hx(0x408D),
            "phase": "ram_test_zero_fill", "mode": "$1030 bit 4 clear",
            "state_in": "full RESET RAM-test branch; pages $00-$0F selected",
            "effect": ("walking-bit test finishes each byte with zero; therefore $04/$05, "
                       "$0212/$0213, and all other tested RAM are zero"),
            "exit": "$408F after all 16 pages", "confidence": "Verified",
        },
        {
            "start": hx(0x408F), "end_inclusive": hx(0x40C7),
            "phase": "diagnostic_irq_sync_window", "mode": "$01=$FF;$0213=$00",
            "state_in": "$00=$04=$05=$0212=$0213=0 after RAM/ROM tests",
            "effect": ("CLI enables the early IRQ path, which increments $00; an NMI arriving "
                       "first can also write $00 indirectly; timeout sets $02 bit 2"),
            "exit": "$40C8 on nonzero $00 or 65536-count timeout", "confidence": "Verified",
        },
        {
            "start": hx(0x57BD), "end_inclusive": hx(0x57DE),
            "phase": "boot_indirect_write", "mode": "$0213=$00",
            "state_in": "one main-CPU byte available at $1010",
            "effect": ("store byte through ($04),Y; increment $0212; for negative old $0212, "
                       "normalize Y with XOR $80 and add $80 to pointer $04/$05"),
            "exit": "RTI via $5820", "confidence": "Verified arithmetic; protocol intent Unknown",
        },
        {
            "start": hx(0x40C8), "end_inclusive": hx(0x4103),
            "phase": "normal_mode_install", "mode": "$0213=$FF",
            "state_in": "boot window exit with interrupts disabled",
            "effect": "write $FF to $0213, initialize ring indices/devices, then CLI",
            "exit": "$4104 main loop", "confidence": "Verified",
        },
        {
            "start": hx(0x57DF), "end_inclusive": hx(0x57E7),
            "phase": "nonqueue_drop", "mode": "$0213=$01-$FE",
            "state_in": "one main-CPU byte available",
            "effect": "read $1010 to acknowledge/drop byte without queueing",
            "exit": "RTI via $5820", "confidence": "Verified; no direct ROM writer selects this mode",
        },
        {
            "start": hx(0x57E8), "end_inclusive": hx(0x5832),
            "phase": "normal_command_queue", "mode": "$0213=$FF",
            "state_in": "normal initialized mode",
            "effect": "advance 16-byte ring, validate command, queue or synthesize direct dispatch",
            "exit": "RTI or synthesized handler dispatch", "confidence": "Verified",
        },
        {
            "start": hx(0x44BD), "end_inclusive": hx(0x44C7),
            "phase": "direct_dispatch_restore", "mode": "$0213=$FF",
            "state_in": "direct NMI handler completion",
            "effect": "restore X/Y, reassert normal mode $FF, restore A, RTI",
            "exit": "RTI", "confidence": "Verified",
        },
    ]


def contract_rows():
    return [
        {
            "address": hx(0x57B0), "entry_kind": "vector_entry",
            "role": "sound-command NMI entry and mode dispatcher",
            "entry_contract": "NMI vector; CPU frame stacked; command interface may hold one byte at $1010",
            "exits": "all ordinary paths converge on $5820 RTI; direct queries synthesize a handler that also ends in RTI",
            "clobbers": "none architecturally after RTI; transient A/X/Y/P and stack",
            "reads": "$1030;$0212-$0213;$04-$05;$1010;$0210-$0211;$5D0F;$5FA2-$5FA7",
            "writes": "$04-$05;$0210-$0213;$0200-$020F;optional indirect RAM;stack;direct-handler effects",
            "interrupt_safety": "NMI context; command latch serializes delivery; normal queue path saves/restores A/X/Y",
            "configured_reachability": "boot mode 0 conditional; modes 1-$FE have no ROM writer; normal $FF always after initialization",
            "confidence": "Verified mechanics; boot sender intent Unknown",
        },
        {
            "address": hx(0x582D), "entry_kind": "nmi_indirect_dispatcher",
            "role": "synthesize direct NMI query-handler return",
            "entry_contract": "normal NMI path; Y=2*validation code for direct query 0..2; interrupted A/X/Y already saved",
            "exits": "push target-minus-one from $5FA2 and RTS into query handler; handler tail restores registers and RTI",
            "clobbers": "transient A,P and stack; interrupted registers restored by selected handler",
            "reads": "$5FA2-$5FA7,Y", "writes": "stack plus selected query effects",
            "interrupt_safety": "NMI-only synthesized dispatch; inherits serialized command-latch transaction",
            "configured_reachability": "commands $03/$06/$07 through validation codes 0/1/2",
            "confidence": "Verified",
        },
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("rom", type=Path)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--contract-csv", required=True, type=Path)
    args = parser.parse_args()
    rom = args.rom.read_bytes()
    if len(rom) != 0xC000:
        raise SystemExit(f"expected 0xC000-byte ROM, got {len(rom):#x}")
    for address, expected in ANCHORS.items():
        offset = address - ROM_BASE
        if rom[offset:offset + len(expected)] != expected:
            raise SystemExit(f"anchor mismatch at {hx(address)}")
    writes = find_direct_writes(rom, 0x0213)
    if writes != [(0x40D2, "STX"), (0x44C3, "STA")]:
        raise SystemExit(f"unexpected direct $0213 writes: {writes}")
    output = rows()
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)
    contracts = contract_rows()
    with args.contract_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=contracts[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(contracts)
    print(f"nmi protocol: {len(output)} phases, {len(contracts)} entry contracts, {len(ANCHORS)} anchors, "
          f"direct $0213 writes {','.join(hx(a) for a, _ in writes)}")


if __name__ == "__main__":
    main()
