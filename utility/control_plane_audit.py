#!/usr/bin/env python3
"""Generate the IRQ/reset/command-dispatch/type-7-allocation semantic catalog."""

import argparse
import csv
from collections import Counter
from pathlib import Path


ROM_BASE = 0x4000

ANCHORS = {
    0x4187: bytes.fromhex("48 8a 48 d8 8d 30 18 a5 02 29 fb 85"),
    0x4194: bytes.fromhex("a5 01 f0 05 e6 00 4c c4 41 ba bd 03"),
    0x41C8: bytes.fromhex("20 94 58 20 94 58 20 94 58 a5 00 4a"),
    0x41E6: bytes.fromhex("08 78 20 95 42 a9 00 8d 24 02 8d 25"),
    0x4218: bytes.fromhex("a2 01 bd a8 57 85 08 bd aa 57 85 09"),
    0x4295: bytes.fromhex("a9 01 85 14 20 d7 42 a9 02 91 15 aa"),
    0x42C6: bytes.fromhex("a5 14 20 d7 42 48 b1 15 f0 04 85 14"),
    0x42D7: bytes.fromhex("48 a8 88 84 15 84 0e a0 00 84 16 06"),
    0x42F9: bytes.fromhex("98 48 bd d8 06 f0 13 20 d7 42 48 b1"),
    0x432E: bytes.fromhex("c0 db b0 14 b9 ea 5d c9 0f b0 0d 0a"),
    0x4347: bytes.fromhex("0a 0a 85 13 60"),
    0x4369: bytes.fromhex("0a a8 b9 a1 5f 48 b9 a0 5f 48 60"),
    0x438D: bytes.fromhex("08 78 a8 b9 ea 5d c9 07 d0 17 b9 c5"),
    0x43D4: bytes.fromhex("08 78 a8 b9 ea 5d c9 07 d0 2c b9 c5"),
    0x440B: bytes.fromhex("08 78 85 11 a0 1d b9 90 03 4a 4a 45"),
    0x4439: bytes.fromhex("a8 be cc 64 e4 13 90 03 4c 32 59 60"),
    0x4445: bytes.fromhex("ac 25 02 99 14 02 c8 c0 10 90 02 a0"),
    0x44A8: bytes.fromhex("a5 02 20 c8 44 a5 02 09 04 09 01 85 02 4c bd 44"),
    0x44B8: bytes.fromhex("a9 db 20 c8 44"),
    0x44C8: bytes.fromhex("48 a9 40 2d 30 10 d0 fb 68 48 8d 00 10"),
    0x44DE: bytes.fromhex("85 03 a8 be a8 5f b9 e6 5f d0 14 a5"),
    0x44FD: bytes.fromhex("8e 27 02 a0 1d b9 90 03 f0 2b 88 10"),
    0x4532: bytes.fromhex("a9 07 99 08 04 a9 10 99 ca 05 a9 a0"),
    0x45D2: bytes.fromhex("ae 10 08 08 78 8e 10 08 bd e6 07 f0"),
    0x460E: bytes.fromhex("27 02 be fc 62 f0 03 4c fd 44 60 48"),
    0x4619: bytes.fromhex("48 85 28 a9 e0 49 ff 25 28 85 29 68"),
    0x4633: bytes.fromhex("46 43 4b 43 58 43 68 43 73 43 8c 43"),
}

EXPECTED_HANDLER_TARGETS = [
    0x4347, 0x434C, 0x4359, 0x4369, 0x4374,
    0x438D, 0x43AF, 0x44DE, 0x4445, 0x43D4,
    0x440B, 0x4439, 0x4461, 0x4619, 0x4618,
]

EXPECTED_CONFIGURED_COUNTS = {
    0: 2, 3: 1, 5: 3, 7: 62, 8: 1,
    9: 1, 10: 1, 11: 141, 13: 4,
}


def hx(value):
    return f"0x{value:04X}"


def row(start, end, kind, role, entry, exits, clobbers, reads, writes,
        configured="", confidence="Verified"):
    return {
        "start": hx(start), "end_inclusive": hx(end), "kind": kind,
        "role": role, "entry_contract": entry, "exits": exits,
        "clobbers": clobbers, "reads": reads, "writes": writes,
        "configured_reachability": configured, "confidence": confidence,
    }


def catalog_rows():
    return [
        row(0x4187, 0x41C7, "irq_entry",
            "ack IRQ, clear heartbeat bit 2, handle initialization/BRK/normal service",
            "IRQ vector; CPU frame already stacked",
            "RTI early/normal; BRK tail-reinitializes at $40EC",
            "normal/early paths restore A,X,Y; P restored by RTI", "$01-$02;$00;$2A;$29;stacked P",
            "$1830;$00;$02;$2A;$1020 plus callees", "always"),
        row(0x41C8, 0x41E5, "irq_audio_service",
            "four speech services around alternating POKEY/YM device sweep",
            "normal IRQ after Y saved; parity in $00",
            "RTS via final $5894 tail jump", "A,X,Y,P plus callees", "$00",
            "speech/device state", "normal IRQ"),
        row(0x41E6, 0x4217, "global_reset_software",
            "atomically rebuild context pool and clear queues/channel arrays",
            "JSR from initialization or type-3 command $00", "continue $4218; RTS at $4294",
            "A,X,Y; P restored", "none",
            "$0224-$0226;$0832-$0833;$07E6-$080F and selected 30-entry channel arrays",
            "command $00 and boot"),
        row(0x4218, 0x425D, "pokey_reset",
            "select POKEY hardware, sequence SKCTL 0/1/2/3, clear AUDCTL and audio registers",
            "global reset X=1 then X=0 hardware loop", "join $428D",
            "A,X,Y,P;$08-$09;$11-$12", "$57A8-$57AD", "$1800-$180F", "boot/reset"),
        row(0x425E, 0x4294, "ym_reset",
            "wait for YM ready, address key-on register $08, key off channels 7..0, clear timeout bit",
            "global reset hardware type 2", "loop next hardware; then PLP/RTS",
            "A,X,Y,P;$0D", "$02;$57A8-$57AD", "$1810-$1811;$02", "boot/reset"),
        row(0x4295, 0x42C5, "context_pool_initialize",
            "build four-byte record free list at $093D with terminal sentinel",
            "global reset", "RTS with free-list head $14=1", "A,X,Y,P;$14-$16",
            "none", "$093D-$0C54;$14-$16", "boot/reset"),
        row(0x42C6, 0x42D6, "context_pool_allocate",
            "pop one nonterminal record ID from free list",
            "$14=head ID", "RTS A=allocated ID; A=0 if only terminal record remains",
            "A,Y,P;$0E;$15-$16", "$14;record next", "$14", "bytecode repeat/call contexts"),
        row(0x42D7, 0x42F8, "context_record_address",
            "map record ID A to $093D+4*(A-1)", "A=record ID",
            "RTS A preserved, Y=0, pointer in $15-$16", "Y,P;$0E;$15-$16", "none",
            "$0E;$15-$16", "pool helpers"),
        row(0x42F9, 0x432D, "channel_context_free",
            "splice both channel-owned context chains back onto free-list head",
            "X=logical channel", "RTS with $06D8,X=$06BA,X=0",
            "A,Y,P;$0E;$14-$16", "$06D8,X;$06BA,X;context links;$14",
            "$06D8,X;$06BA,X;context links;$14", "replacement/termination"),
        row(0x432E, 0x4346, "command_dispatch",
            "validate command/type and synthesize RTS dispatch through target-minus-one table",
            "Y=command", "invalid RTS; valid returns into one of 15 handlers with A=parameter",
            "A,X,P;Y preserved", "$5DEA,Y;$5EC5,Y;$4633-$4650", "stack",
            "all main-loop commands"),
        row(0x4347, 0x434B, "handler_type_0", "set global speech/filter threshold to parameter*4",
            "A=parameter", "RTS", "A,P", "none", "$13", "2 commands"),
        row(0x434C, 0x4368, "reserved_handlers_1_2", "set/add sliding workspace byte",
            "A=parameter", "RTS", "A,X,Y,P", "$6559-$655A;$18-$27", "$18-$27",
            "0 commands; see reserved_handler_catalog.csv"),
        row(0x4369, 0x4373, "handler_type_3", "secondary target-minus-one dispatch",
            "A=parameter", "returns into selected target", "A,Y,P", "$5FA0+2*A", "stack",
            "command $00 -> $41E6"),
        row(0x4374, 0x438C, "reserved_handler_4", "soft-kill logical channels by status class",
            "A=status class", "RTS", "A,Y,P", "$0390", "$0228",
            "0 commands; see reserved_handler_catalog.csv"),
        row(0x438D, 0x43AE, "handler_type_5", "stop active channels matching a target type-7 parameter",
            "A=target command", "RTS", "A,Y,P", "$5DEA;$5EC5;$0228", "$0228=$FF",
            "commands $21/$2F/$39"),
        row(0x43AF, 0x43D3, "reserved_handler_6", "walk selected physical list and soft-kill members",
            "A=encoded list selector", "RTS", "A,Y,P", "$57AE;$07E6", "$0228=$FF",
            "0 commands; see reserved_handler_catalog.csv"),
        row(0x43D4, 0x440A, "handler_type_9", "fade channels matching target type-7 parameter",
            "A=target command", "RTS", "A,Y,P", "$5DEA;$5EC5;$0228",
            "$0714/$0732/$0750/$076E/$078C;$0228=$FE", "command $3C"),
        row(0x440B, 0x4438, "handler_type_10", "fade logical channels matching status class",
            "A=status class", "RTS", "A,Y,P", "$0390",
            "$0714/$0732/$0750/$076E/$078C;$0228=$FE", "command $41"),
        row(0x4439, 0x4444, "handler_type_11", "priority-gate speech then tail to start/queue routine",
            "A=speech parameter", "$5932 if priority >= $13; otherwise RTS", "X,Y,P",
            "$64CC;$13", "speech state via $5932", "141 speech commands"),
        row(0x4445, 0x4460, "handler_type_8", "enqueue one byte to 16-byte sound-to-main ring",
            "A=output byte", "RTS; on full ring set overflow flag", "A,Y,P",
            "$0224-$0225", "$0214-$0223;$0225 or $0226=$80", "command $DA"),
        row(0x4461, 0x44A7, "reserved_handler_12", "validate and apply safe opcode to matching live channels",
            "A=support-record offset", "RTS or tail $5059", "A,X,Y,P",
            "$655B-$655E;$5DEA;$5EC5", "$0830-$0831 plus opcode effects",
            "0 commands; see reserved_handler_catalog.csv"),
        row(0x44A8, 0x44B7, "nmi_query_7",
            "send error byte, then arm bits 2 and 0 before common NMI restore",
            "synthesized NMI direct dispatch for command $07", "tail $44BD; RTI",
            "interrupted registers restored by tail", "$02;$1030", "$1000;$02|=$05",
            "NMI command $07"),
        row(0x44B8, 0x44BC, "nmi_query_6",
            "send fixed $DB response before common NMI restore",
            "synthesized NMI direct dispatch for command $06", "fall $44BD; RTI",
            "interrupted registers restored by fallthrough", "$1030", "$1000",
            "NMI command $06"),
        row(0x44BD, 0x44C7, "nmi_direct_restore",
            "restore interrupted X/Y/A and reinstall normal NMI mode",
            "tail/fallthrough from direct NMI handlers", "RTI", "none after RTI",
            "stack", "$0213=$FF;stack", "NMI commands $03/$06/$07"),
        row(0x44C8, 0x44DD, "main_output_latch_write",
            "wait for output latch empty, send A, then wait for main CPU acceptance",
            "JSR with A=response byte", "RTS with A preserved",
            "P(N/Z);A/X/Y preserved", "$1030 bit 6", "$1000", "NMI queries $03/$06/$07"),
        row(0x44DE, 0x44FC, "type7_admission",
            "load first record and optionally reject duplicate active parameter",
            "A=type-7 parameter", "continue $44FD; optional RTS duplicate guard",
            "A,X,Y,P;$03", "$5FA8;$5FE6;$0228;$0390", "$03",
            "62 type-7 parameters; all flags $FF bypass duplicate guard"),
        row(0x44FD, 0x4531, "type7_slot_reclaim",
            "find free logical slot or reclaim lowest-priority head on target physical list",
            "X=type-7 record offset", "continue $4532; SEC/RTS if no reclaimable slot",
            "A,X,Y,P;$0227", "$0390;$6024;$60DA;$07E6", "$0227;$07E6",
            "all type-7 allocations"),
        row(0x4532, 0x45D1, "type7_state_initialize",
            "initialize complete logical-channel state and sequence/support pointers",
            "Y=chosen logical slot; X=record offset", "continue $45D2",
            "A,X,P;$0810", "$6024;$60DA;$6190-$62FB",
            "logical channel arrays $0228-$07C8;$0810", "all type-7 allocations"),
        row(0x45D2, 0x4617, "type7_physical_insert_chain",
            "priority-sort physical list, replace equal priority, then allocate linked record chain",
            "Y=new logical slot; X=physical head index", "reenter $44FD for next record; RTS at $4618",
            "A,X,Y,P;$0810", "$0390;$07E6;$62FC", "$0390;$07E6;$0228",
            "all 182 reachable records"),
        row(0x4618, 0x4618, "reserved_handler_14", "null handler / shared type-7 completion RTS",
            "dispatch or type-7 chain complete", "RTS", "none", "none", "none",
            "0 type-14 commands; shared by type-7"),
        row(0x4619, 0x4632, "handler_type_13", "split mixer byte into speech/effects/music shadows",
            "A=mixer parameter", "RTS; defer $1020 write while speech state overlaps",
            "A,P", "$2F", "$28-$29;$1020 conditionally", "commands $D6-$D9"),
        row(0x4633, 0x4650, "handler_target_table", "15 little-endian target-minus-one entries",
            "indexed by doubled handler type", "data", "none", "none", "none",
            "types 0..14", "Verified exact table"),
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
    targets = []
    for index in range(15):
        offset = 0x4633 - ROM_BASE + 2 * index
        targets.append(int.from_bytes(rom[offset:offset + 2], "little") + 1)
    if targets != EXPECTED_HANDLER_TARGETS:
        raise SystemExit(f"handler target mismatch: {[hx(v) for v in targets]}")
    counts = Counter(rom[0x5DEA - ROM_BASE:0x5DEA - ROM_BASE + 219])
    configured = {kind: count for kind, count in counts.items() if kind < 15 and count}
    if configured != EXPECTED_CONFIGURED_COUNTS:
        raise SystemExit(f"configured handler counts changed: {configured}")
    flags = rom[0x5FE6 - ROM_BASE:0x5FE6 - ROM_BASE + 62]
    if set(flags) != {0xFF}:
        raise SystemExit("configured type-7 admission flags are no longer all $FF")
    output = catalog_rows()
    expected_start = 0x4187
    for item in output:
        start = int(item["start"], 16)
        end = int(item["end_inclusive"], 16)
        if start != expected_start or end < start:
            raise SystemExit(
                f"control-plane coverage break at {item['start']}, expected {hx(expected_start)}")
        expected_start = end + 1
    if expected_start != 0x4651:
        raise SystemExit(f"control-plane coverage ends at {hx(expected_start - 1)}")
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)
    print(f"control plane: {len(output)} blocks, {len(ANCHORS)} anchors, "
          "15 handler targets, 9 configured handler types, contiguous coverage")


if __name__ == "__main__":
    main()
