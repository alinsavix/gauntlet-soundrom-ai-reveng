#!/usr/bin/env python3
"""Validate pitch-table aliases and configured note-mode reachability."""

import argparse
import csv
import math
import re
from collections import defaultdict, deque
from pathlib import Path

import gauntlet_disasm as gd
import rom_table_audit as audit


def walk_modes(rom):
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
    notes = defaultdict(set)
    operations = defaultdict(set)
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
        operations[mode].add(opcode)
        if row["mnemonic"] == "NOTE":
            notes[mode].add(opcode)
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
    return notes, operations, len(seen)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("rom", type=Path)
    p.add_argument("--csv", required=True, type=Path)
    p.add_argument("--consumer-validation-csv", required=True, type=Path)
    p.add_argument("--ym-pitch-csv", required=True, type=Path)
    p.add_argument("--ymfm-ref", required=True, type=Path)
    p.add_argument("--ymfm-opm-ref", required=True, type=Path)
    p.add_argument("--ymfm-engine-ref", required=True, type=Path)
    args = p.parse_args()
    rom = gd.GauntletROM(str(args.rom))
    notes, operations, states = walk_modes(rom)
    if notes.get("POKEY"):
        raise SystemExit("configured POKEY NOTE path unexpectedly reachable")
    ym_notes = notes["YM2151"]
    if min(ym_notes) != 13 or max(ym_notes) != 95:
        raise SystemExit("unexpected configured YM note domain")
    if 0x8C in operations.get("POKEY", set()) | operations.get("YM2151", set()):
        raise SystemExit("configured SET_VIBRATO unexpectedly reachable")
    if 0x86 not in operations.get("POKEY", set()) or 0x86 in operations.get("YM2151", set()):
        raise SystemExit("configured frequency-envelope mode domain changed")
    pitch_state_anchors = {
        0x4557: "99 60 06 99 f6 06 99 7e 06 99 9c 06",
        0x48CA: "bd 60 06 d0 4d 9d 7e 06 9d 9c 06",
        0x51E2: "9d 60 06 60",
    }
    for address, expected_hex in pitch_state_anchors.items():
        expected = bytes.fromhex(expected_hex)
        actual = bytes(rom.read_byte(address + i) for i in range(len(expected)))
        if actual != expected:
            raise SystemExit(f"pitch-state anchor mismatch at ${address:04X}")

    words = [rom.read_word(0x5A35 + 2 * i) for i in range(128)]
    for note in range(1, 98):
        midi = note + 11
        hz = 440.0 * 2.0 ** ((midi - 69) / 12.0)
        expected = round(1_790_000.0 / (2.0 * hz) - 7.0)
        if words[note] != expected:
            raise SystemExit(f"nominal POKEY prefix mismatch at note {note}")

    kc = [rom.read_byte(0x5AF9 + i) for i in range(128)]
    scale = [rom.read_byte(0x5B5B + i) for i in range(256)]
    mismatches = sum(
        scale[16 * r + c] != ((2 * r + 1) * c) // 16
        for r in range(16) for c in range(16))
    if mismatches != 1:
        raise SystemExit("unexpected total-level scaling-table shape")

    ymfm_source = args.ymfm_ref.read_text()
    opm_source = args.ymfm_opm_ref.read_text()
    engine_source = args.ymfm_engine_ref.read_text()
    marker = "static const uint32_t s_phase_step[12*64]"
    table_start = ymfm_source.index(marker)
    brace = ymfm_source.index("{", table_start)
    table_end = ymfm_source.index("};", brace)
    phase_steps = [int(value) for value in re.findall(
        r"\b\d+\b", ymfm_source[brace:table_end])]
    if len(phase_steps) != 768:
        raise SystemExit(f"unexpected YMFM phase-step length {len(phase_steps)}")
    if "uint32_t block = bitfield(block_freq, 10, 3);" not in ymfm_source:
        raise SystemExit("YMFM OPM block extraction formula missing")
    if "word(0x28, 0, 7, 0x30, 2, 6, choffs)" not in opm_source:
        raise SystemExit("YMFM KC/KF register composition missing")
    if ("DEFAULT_PRESCALE = 2" not in opm_source
            or "CHANNELS = 8" not in opm_source
            or "OPERATORS = CHANNELS * 4" not in opm_source):
        raise SystemExit("YMFM OPM prescale/operator constants missing")
    if "return baseclock / (m_clock_prescale * OPERATORS);" not in engine_source:
        raise SystemExit("YMFM sample-rate formula missing")

    ym_clock = 14_318_181.0 / 4.0
    ym_sample_rate = ym_clock / (2.0 * 32.0)

    def ym_base_pitch(note, kf=0):
        key_code = kc[note]
        block = (key_code >> 4) & 7
        code = key_code & 15
        adjusted = code - (code >> 2)
        fraction = (kf >> 2) & 63
        effective = adjusted * 64 + fraction
        phase_step = phase_steps[effective] >> (block ^ 7)
        hz = phase_step * ym_sample_rate / (1 << 20)
        midi = note + 11
        target = 440.0 * 2.0 ** ((midi - 69) / 12.0)
        cents = 1200.0 * math.log2(hz / target)
        return key_code, block, adjusted, fraction, phase_step, hz, midi, target, cents

    chromatic_errors = [ym_base_pitch(note)[-1] for note in range(13, 98)]
    if min(chromatic_errors) < -1.53 or max(chromatic_errors) > 0.19:
        raise SystemExit("unexpected YM chromatic error range")

    selected_notes = [49, 51, 53, 54, 56, 58, 60, 61]
    ym_rows = []
    for note in selected_notes:
        key_code, block, adjusted, fraction, phase_step, hz, midi, target, cents = \
            ym_base_pitch(note)
        if abs(cents) > 0.51:
            raise SystemExit(f"selected YM pitch mismatch at note {note}: {cents}")
        ym_rows.append([
            "command_04_stable", note, midi, gd.note_name(note),
            f"0x{key_code:02X}", "0x00", block, adjusted, fraction, phase_step,
            hz, midi, gd.note_name(note), target, cents,
            "command $04 steady state; voice $6F94 byte +2 = 0; operator multiple 1",
            "Verified ROM/YMFM formula and clock"])

    rows = [
        ["POKEY_note_lookup_view", "0x5A35", "0x5B34", 128, "16-bit LE indexed by note*2 at $4786/$4795", "No NOTE instruction is configured in POKEY mode", "Verified reachability; tail semantics Unknown"],
        ["POKEY_chromatic_prefix", "0x5A37", "0x5AF8", 97, "notes 1..97 exactly match rounded 1.790 MHz joined-divider targets", "Assumes MIDI=note+11 and divisor+7 hardware rule", "Strong inference tuning model; Verified bytes and clock"],
        ["YM_key_code_view", "0x5AF9", "0x5B78", 128, "note byte indexes gappy YM KC value written to register $28+channel", "Configured YM notes span 13..95", "Verified"],
        ["YM_key_code_alias", "0x5B5B", "0x5B78", 30, "KC indices 98..127 alias total-level scaling bytes 0..29", "No configured note reaches the aliased tail", "Verified structural alias; configured dormant"],
        ["YM_total_level_nonlinear", "0x72DC", "0x73DB", 256, "nonlinear value consumed only by $4F51 total-level path", "Result ultimately written to registers $60-$7F", "Verified; prior frequency label Contradicted"],
        ["YM_total_level_scale", "0x5B5B", "0x5C5A", 256, "16x16 scale approximates floor((2*r+1)*c/16), one byte differs", "Consumed at $4F5D/$4F6F for total-level correction", "Verified; prior frequency label Contradicted"],
        ["YM_vibrato_delta_convergence", "0x4C69", "0x4CBD", 0, "$0660 nonzero would step $067E/$069C toward zero before KC/KF staging", "No configured SET_VIBRATO $8C; allocation and zero-depth note path clear state", "Verified dormant under configured sequences"],
        ["POKEY_frequency_envelope_domain", "0x655F", "0x69FF", 13, "all configured SET_FREQ_ENV $86 operands reached mode-aware", "All 13 operations are POKEY mode; none YM2151", "Verified configured reachability; individual packing varies"],
    ]
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["view", "start", "end_inclusive", "entries", "consumer", "configured_domain_or_formula", "confidence"])
        w.writerows(rows)
    with args.consumer_validation_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["batch", "address", "instructions", "consumer", "evidence", "confidence"])
        w.writerows([
            [1, "0x49C5", 32, "frequency_envelope", "pointer reload, countdown decrement, FF loop control, pointer rewind", "Verified"],
            [2, "0x4A90", 32, "volume_envelope", "pointer reload, countdown decrement, FF loop control, pointer rewind", "Verified"],
            [3, "0x4F3E", 24, "ym_total_level_nonlinear_lookup", "Y = $0819 OR $0826[index]; indexed read from $72DC,Y; result writes $60-$7F", "Verified"],
        ])
    with args.ym_pitch_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["context", "rom_note", "interpreted_midi", "label", "kc",
                    "kf", "block", "adjusted_code", "fraction", "ymfm_phase_step",
                    "frequency_hz", "comparison_midi", "comparison_label",
                    "equal_tempered_hz", "error_cents", "state_assumptions",
                    "confidence"])
        w.writerows(ym_rows)
    print(f"pitch conversion: {len(rows)} views, {len(ym_rows)} YMFM rows, "
          f"{states} mode states, YM notes {min(ym_notes)}..{max(ym_notes)}, POKEY notes 0, "
          f"chromatic error {min(chromatic_errors):.3f}..{max(chromatic_errors):.3f} cents")


if __name__ == "__main__":
    main()
