#!/usr/bin/env python3
"""Generate fade/ramp and YM winner/KC/KF staging catalogs."""

import argparse
import csv
from collections import Counter, defaultdict, deque
from pathlib import Path

import gauntlet_disasm as gd
import rom_table_audit as audit


ROM_BASE = 0x4000

ANCHORS = {
    0x4B6B: bytes.fromhex("bd 50 07 85 0e bd 6e 07 85 0f a5 11 48 bd ac 05"),
    0x4B8D: bytes.fromhex("a5 11 29 0f a8 b9 7f 5c 85 11 c9 ff d0 12 bd 32"),
    0x4BAD: bytes.fromhex("bd 14 07 38 e5 11 9d 14 07 b0 0d de 32 07 10 08"),
    0x4BC5: bytes.fromhex("a0 07 a5 0f c9 80 6a 66 0e 88 30 04 06 11 90 f4"),
    0x4BF2: bytes.fromhex("bd 8c 07 18 65 0e 9d 8c 07 90 02 e6 0f a5 0f a8"),
    0x4C16: bytes.fromhex("a4 17 d0 4f 29 30 f0 05 0d 2f 08 d0 03 ad 2f 08"),
    0x4C58: bytes.fromhex("a0 08 bd 9e 04 99 26 08 88 b1 0e 99 26 08 88 d0"),
    0x4C69: bytes.fromhex("bd 60 06 f0 4f bd 9c 06 1d 7e 06 f0 47 a5 00 29"),
    0x4CBD: bytes.fromhex("a5 17 d0 40 bd 7e 06 8d 1b 08 bd 9c 06 8d 1a 08"),
    0x5C73: bytes.fromhex("f0 00 78 00 3c 00 40 01 a0 00 00 03 00 ff 80 40"),
    0x5C7F: bytes.fromhex("00 ff 80 40 20 40 20 10 40 10 08 04 02 08 04 20"),
    0x5C8F: bytes.fromhex("00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"),
}

EXPECTED_POKEY_SHAPE_COUNTS = {0: 6, 1: 2, 4: 4, 5: 2, 7: 4}
EXPECTED_YM_NOTE_GROUPS = {0x00, 0x10, 0x20, 0x30}


def hx(value):
    return f"0x{value:04X}"


def code_rows():
    return [
        {
            "start": hx(0x4B6B), "end_inclusive": hx(0x4B8C),
            "kind": "ramp_setup", "role": "load signed ramp and choose default or event-derived service rate",
            "entry_contract": "X=logical channel; $11=current event/control byte",
            "exits": "fall $4B8D", "clobbers": "A,Y,P;$0E-$0F; saves original $11 on stack",
            "reads": "$0750/$076E;$05AC;$5C73-$5C74", "writes": "$0516/$0534 conditionally",
            "configured_reachability": "fade commands $3C/$41 and active ramp states", "confidence": "Verified",
        },
        {
            "start": hx(0x4B8D), "end_inclusive": hx(0x4BC4),
            "kind": "ramp_rate_countdown", "role": "decode 16-entry shift/control table and saturating 16-bit fade remainder",
            "entry_contract": "$0E/$0F=signed ramp; selected index in A/$11",
            "exits": "special $FF joins apply; ordinary path falls $4BC5",
            "clobbers": "A,Y,P;$11", "reads": "$5C7F-$5C8E;$0714/$0732",
            "writes": "$0714/$0732", "configured_reachability": "active fade/ramp",
            "confidence": "Verified",
        },
        {
            "start": hx(0x4BC5), "end_inclusive": hx(0x4C15),
            "kind": "signed_ramp_apply", "role": "arithmetic-shift signed ramp, accumulate fraction, apply integer volume/TL delta",
            "entry_contract": "$0F:$0E signed ramp; $11 shift bit/control",
            "exits": "RTS with original $11 restored; Y=0 no integer delta or $FF after apply",
            "clobbers": "A,Y,P;$0E-$0F; X preserved", "reads": "$078C;$081D;$0408 plus $5181/$5715 state",
            "writes": "$078C;POKEY base volume or YM operator TL reload via callee",
            "configured_reachability": "active fade/ramp", "confidence": "Verified",
        },
        {
            "start": hx(0x4C16), "end_inclusive": hx(0x4C68),
            "kind": "ym_winner_voice_stage", "role": "for final physical-list winner, stage control, four base TLs, and live TL-transform bytes",
            "entry_contract": "X=YM logical channel; A=event flags; $17=0 only for final/winning list member",
            "exits": "fall $4C69", "clobbers": "A,Y,P;$0E-$0F; X preserved",
            "reads": "$0426/$0444/$0462/$0480 as M1/M2/C1/C2 TL;$03CC/$03EA;$049E;voice+$1D..+$23",
            "writes": "$0826-$082F;$083D registers $60/$68/$70/$78+channel",
            "configured_reachability": "winning YM channel; suppressed for preceding list members", "confidence": "Verified",
        },
        {
            "start": hx(0x4C69), "end_inclusive": hx(0x4CBC),
            "kind": "ym_vibrato_delta_converge", "role": "periodically step signed 16-bit KC/KF delta toward zero by 2*vibrato depth",
            "entry_contract": "X=YM logical channel", "exits": "join $4CBD; clamp on sign crossing",
            "clobbers": "A,P;$0E-$0F", "reads": "$0660;$067E/$069C;$00",
            "writes": "$067E/$069C", "configured_reachability": "dormant: no configured SET_VIBRATO $8C",
            "confidence": "Verified code and configured dormancy",
        },
        {
            "start": hx(0x4CBD), "end_inclusive": hx(0x4D01),
            "kind": "ym_kc_kf_stage", "role": "winner-only split of signed delta across base KF and note/KC index",
            "entry_contract": "$17=0 winner; X=YM logical channel; $0819=current note index",
            "exits": "RTS", "clobbers": "A,Y,P;$081A-$081B",
            "reads": "$0408 base KF;$067E/$069C delta;$0819;$083C channel",
            "writes": "$083D at $30+channel;$0819 adjusted KC index",
            "configured_reachability": "winning YM channel; configured delta is zero",
            "confidence": "Verified",
        },
    ]


def mode_shape_counts(rom):
    records = list(audit.type7_records(rom))
    rows, edges, _, errors = audit.type7_sequence_map(
        rom, [(f"record_{r['offset']}", r["sequence_pointer"]) for r in records])
    if errors:
        raise SystemExit(f"sequence errors: {errors}")
    by_address = {r["address"]: r for r in rows}
    computed_targets = defaultdict(list)
    for edge in edges:
        if edge["kind"].startswith("conditional"):
            computed_targets[edge["source"]].append(edge["target"])
    queue = deque((r["sequence_pointer"], r["chip"]) for r in records)
    seen = set()
    counts = Counter()
    ym_note_groups = set()
    operations = defaultdict(set)
    while queue:
        address, mode = queue.popleft()
        if (address, mode) in seen or address not in by_address:
            continue
        seen.add((address, mode))
        item = by_address[address]
        opcode = item["opcode"]
        if opcode == 0x90:
            mode = "POKEY"
        elif opcode == 0x91:
            mode = "YM2151"
        operations[mode].add(opcode)
        if mode == "POKEY" and item["mnemonic"] in ("NOTE", "REST"):
            raw = bytes.fromhex(item["raw_hex"])
            if len(raw) > 1 and raw[1]:
                counts[(raw[1] & 0x38) >> 3] += 1
        if mode == "YM2151" and item["mnemonic"] == "NOTE":
            ym_note_groups.add(item["opcode"] & 0x30)
        target = item["target"] if item["target"] != "" else None
        next_address = address + item["size"]
        if opcode == 0x99:
            queue.append((target, mode))
        elif opcode in (0xAE, 0xAF):
            for computed_target in computed_targets[address]:
                queue.append((computed_target, mode))
        elif item["mnemonic"] not in ("CHAIN", "END"):
            queue.append((next_address, mode))
            if target is not None:
                queue.append((target, mode))
    if dict(counts) != EXPECTED_POKEY_SHAPE_COUNTS:
        raise SystemExit(f"POKEY shape domain changed: {dict(counts)}")
    if 0x8C in operations["POKEY"] | operations["YM2151"]:
        raise SystemExit("configured SET_VIBRATO unexpectedly reachable")
    if ym_note_groups != EXPECTED_YM_NOTE_GROUPS:
        raise SystemExit(f"YM note high-bit groups changed: {ym_note_groups}")
    return counts, ym_note_groups, len(seen)


def fade_rate_rows(rom):
    values = [rom.read_byte(0x5C7F + index) for index in range(16)]
    for index, value in enumerate(values):
        if value == 0xFF:
            shift = "special"
            behavior = "fade remainder high-byte countdown/clear control"
        elif value == 0:
            shift = 8
            behavior = "signed ramp divided by 256"
        else:
            if value & (value - 1):
                raise SystemExit(f"fade-rate value ${value:02X} is not a power of two")
            shift = 8 - (value.bit_length() - 1)
            behavior = f"signed ramp divided by {1 << shift}"
        yield {
            "index": index, "address": hx(0x5C7F + index), "value_hex": f"0x{value:02X}",
            "arithmetic_right_shifts": shift, "behavior": behavior, "confidence": "Verified",
        }


def volume_shape_rows(rom, configured_counts):
    for shape in range(8):
        start = 0x5C8F + 16 * shape
        values = [rom.read_byte(start + phase) for phase in range(16)]
        signed = [value - 256 if value >= 128 else value for value in values]
        if not any(signed):
            behavior = "neutral"
        elif max(signed) <= 0:
            behavior = "negative attenuation trajectory"
        elif min(signed) >= 0:
            behavior = "positive trajectory decaying to zero"
        else:
            behavior = "mixed signed trajectory"
        yield {
            "shape": shape, "start": hx(start), "end_inclusive": hx(start + 15),
            "values_hex": " ".join(f"{value:02X}" for value in values),
            "signed_values": " ".join(str(value) for value in signed),
            "configured_pokey_instruction_states": configured_counts[shape],
            "configured_pokey_reachable": bool(configured_counts[shape]),
            "behavior": behavior,
            "confidence": "Verified consumer/index domain",
        }


def ym_tl_bias_rows(rom, note_groups):
    rows = []
    for source_kind, low_bits in (("refresh", 0x02), ("new_note", 0x06)):
        for note_group in sorted(note_groups):
            control = note_group | low_bits
            # $4EBB and $4ED5 destructively shift bits 0/1 from $082F before
            # $4F0E performs two more shifts in A.  The lookup therefore sees
            # original control bits 5..4, not original >> 2.
            index = control >> 4
            address = 0x5C5B + index
            rows.append({
                "source_kind": source_kind,
                "note_group_hex": f"0x{note_group:02X}",
                "control_082f_hex": f"0x{control:02X}",
                "post_two_memory_shifts_hex": f"0x{control >> 2:02X}",
                "index": index,
                "address": hx(address),
                "bias_value_hex": f"0x{rom.read_byte(address):02X}",
                "consumer": "$4F14 subtracts this value from live operator TL input",
                "confidence": "Verified producer/consumer domain",
            })
    return rows


def write_csv(path, rows):
    rows = list(rows)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("rom", type=Path)
    parser.add_argument("--code-csv", required=True, type=Path)
    parser.add_argument("--fade-rate-csv", required=True, type=Path)
    parser.add_argument("--volume-shape-csv", required=True, type=Path)
    parser.add_argument("--ym-tl-bias-csv", required=True, type=Path)
    args = parser.parse_args()
    raw = args.rom.read_bytes()
    if len(raw) != 0xC000:
        raise SystemExit(f"expected 0xC000-byte ROM, got {len(raw):#x}")
    for address, expected in ANCHORS.items():
        offset = address - ROM_BASE
        if raw[offset:offset + len(expected)] != expected:
            raise SystemExit(f"anchor mismatch at {hx(address)}")
    # $4658 is the only direct write to the winner/suppression flag $17.
    writes17 = [ROM_BASE + offset for offset in range(len(raw) - 1)
                if raw[offset:offset + 2] == bytes.fromhex("85 17")]
    if writes17 != [0x4658]:
        raise SystemExit(f"unexpected direct $17 writes: {[hx(v) for v in writes17]}")
    rom = gd.GauntletROM(str(args.rom))
    shape_counts, ym_note_groups, mode_states = mode_shape_counts(rom)
    code = code_rows()
    if code[0]["start"] != "0x4B6B" or code[-1]["end_inclusive"] != "0x4D01":
        raise SystemExit("support code coverage endpoints changed")
    for left, right in zip(code, code[1:]):
        if int(right["start"], 16) != int(left["end_inclusive"], 16) + 1:
            raise SystemExit("support code coverage is not contiguous")
    for path in (args.code_csv, args.fade_rate_csv, args.volume_shape_csv,
                 args.ym_tl_bias_csv):
        path.parent.mkdir(parents=True, exist_ok=True)
    write_csv(args.code_csv, code)
    write_csv(args.fade_rate_csv, fade_rate_rows(rom))
    write_csv(args.volume_shape_csv, volume_shape_rows(rom, shape_counts))
    write_csv(args.ym_tl_bias_csv, ym_tl_bias_rows(rom, ym_note_groups))
    print(f"support staging: {len(code)} blocks, {len(ANCHORS)} anchors, "
          f"16 fade rates, 8x16 volume shapes, 8 YM TL-bias states, "
          f"{mode_states} mode states")


if __name__ == "__main__":
    main()
