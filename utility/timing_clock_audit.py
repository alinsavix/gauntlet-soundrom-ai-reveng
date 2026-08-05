#!/usr/bin/env python3
"""Validate ROM scheduler anchors and generate clock/cycle evidence catalogs."""

import argparse
import csv
import math
from pathlib import Path

import gauntlet_disasm as gd
from mos6502_cycle import CPU6502


MASTER_HZ = 14_318_181.0
HTOTAL = 456
VTOTAL = 262


def require_bytes(rom, address, expected_hex):
    expected = bytes.fromhex(expected_hex)
    actual = bytes(rom.read_byte(address + i) for i in range(len(expected)))
    if actual != expected:
        raise SystemExit(
            f"anchor mismatch at ${address:04X}: {actual.hex(' ')} != {expected.hex(' ')}")


def require_text(path, snippets):
    text = path.read_text()
    for snippet in snippets:
        if snippet not in text:
            raise SystemExit(f"reference marker missing from {path}: {snippet}")


def write_csv(path, header, rows, lineterminator=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = (csv.writer(f) if lineterminator is None else
                  csv.writer(f, lineterminator=lineterminator))
        writer.writerow(header)
        writer.writerows(rows)


def command44_channel_service(rom_data, prior_services, phase):
    """Execute command $44's selected X=29 path through one $4651 service.

    Earlier services use a common scheduler phase; ``phase`` selects only the
    measured service.  The RAM seed is the state established by type-7
    allocation before the first device sweep.
    """
    cpu = CPU6502(rom_data)
    x = 29
    cpu.x = x
    cpu.mem[0x081C] = x
    cpu.mem[0x081D] = 0  # POKEY device sweep
    channel_seed = {
        0x07E6: 0x00, 0x0390: 0x67, 0x0228: 0x44,
        0x0246: 0x85, 0x0264: 0x65,
        0x02BE: 0x00, 0x02DC: 0x00, 0x02FA: 0x00, 0x0318: 0x00,
        0x03CC: 0xFF, 0x03EA: 0x00, 0x0408: 0x07,
        0x0426: 0x31, 0x0444: 0x5A, 0x0462: 0x31, 0x0480: 0x5A,
        0x05CA: 0x10, 0x0642: 0xA0,
    }
    for base, value in channel_seed.items():
        cpu.mem[base + x] = value

    def service(selected_phase):
        cpu.x = x
        cpu.mem[0x00] = selected_phase
        cpu.cycles = 0
        cpu.instructions = 0
        cpu.trace = []
        cpu.run(0x4651, stop_rts=0x4B6A)
        return cpu.cycles, cpu.instructions

    for _ in range(prior_services):
        service(3)
    cycles, instructions = service(phase)
    return cpu, cycles, instructions


def command05_ff_loop_service(rom_data, phase):
    """Execute channel 2's configured $68F3 `$FF FF 06` loop boundary."""
    cpu = CPU6502(rom_data)
    x = 28
    cpu.x = x
    cpu.mem[0x00] = phase
    cpu.mem[0x081D] = 0
    channel_seed = {
        0x07E6: 0x00, 0x0390: 0x11, 0x0228: 0x05,
        0x0246: 0x8D, 0x0264: 0x68,
        # Nonzero prepared pitch keeps the active-output branch selected.
        0x0282: 0x01, 0x02A0: 0x00,
        0x02BE: 0x30, 0x02DC: 0x01, 0x02FA: 0x30, 0x0318: 0x01,
        0x03CC: 0xFF, 0x03EA: 0x00, 0x0408: 0x07,
        0x0462: 0xF3, 0x0480: 0x68,
        0x049E: 0x00,
        # Prior $FC record is at its boundary; loop repeat state is fresh.
        0x0516: 0x05, 0x0534: 0x01, 0x05AC: 0x00,
        0x0552: 0x00, 0x0570: 0x00, 0x058E: 0x00,
        0x05CA: 0x10, 0x0642: 0xA0, 0x067E: 0x01, 0x069C: 0x00,
    }
    for base, value in channel_seed.items():
        cpu.mem[base + x] = value
    cpu.run(0x4651, stop_rts=0x4B6A)
    return cpu, cpu.cycles, cpu.instructions


def command05_full_consumer(rom_data):
    """Build the four-record allocation topology for command $05."""
    cpu = CPU6502(rom_data)
    cpu.mem[0x13] = 0
    sequences = (0x6838, 0x686D, 0x68A2, 0x68C2)
    for record, sequence in enumerate(sequences):
        x = 29 - record
        head = 30 + record
        # $4607-$4609 stores logical slot + 1 in physical head $1E..$21.
        cpu.mem[0x07E6 + head] = x + 1
        channel_seed = {
            0x07E6: 0x00, 0x0390: 0x11, 0x0228: 0x05,
            0x0246: sequence & 0xFF, 0x0264: sequence >> 8,
            0x03CC: 0xFF, 0x03EA: 0x00, 0x0408: 0x07,
            0x0426: 0x31, 0x0444: 0x5A, 0x0462: 0x31, 0x0480: 0x5A,
            0x05CA: 0x10, 0x0642: 0xA0,
        }
        for base, value in channel_seed.items():
            cpu.mem[base + x] = value
    return cpu


def command05_full_service(cpu, phase):
    """Execute one complete `$500D->$4DFC` POKEY service in-place."""
    cpu.x = 0
    cpu.mem[0x00] = phase
    cpu.cycles = 0
    cpu.instructions = 0
    cpu.trace = []
    cpu.run(0x500D, stop_rts=0x4E67)
    return cpu.cycles, cpu.instructions


def speech_service(rom_data, ready, state=0, phase=0, watchdog=0xFF,
                   stop_rts=0x5931):
    """Execute one selected `$5894` speech-service path."""
    cpu = CPU6502(rom_data)
    cpu.mem[0x33] = 0
    cpu.mem[0x1030] = 0 if ready else 0x20
    cpu.mem[0x00] = phase
    cpu.mem[0x30] = watchdog
    cpu.mem[0x2F] = state
    cpu.mem[0x1031] = 0x80
    if state == 0xFF:
        cpu.mem[0x2B] = 0x00
        cpu.mem[0x2C] = 0x02
        cpu.mem[0x0200] = 0x55
        cpu.mem[0x2D] = 2
        cpu.mem[0x2E] = 0
    cpu.run(0x5894, stop_rts=stop_rts)
    return cpu


def trace_duration(rom, start, service_hz, branch_decisions=None,
                   max_loop_jumps=None):
    """Trace a finite stream with carried residue and $8E/$8F repeats."""
    instructions = [i for i in gd.disassemble_sequence(rom, start)
                    if not i.is_marker]
    tempo = 0x10
    timer = -tempo  # first physical-device service subtracts the zeroed timer
    # Allocation ($45A3: LDA $6024,X / ASL A / SEC / ROL A / STA $0390,Y) leaves
    # status bit 0 set on every new channel, so the duration-table arm at $4854
    # is the default.  Only SWITCH_POKEY clears it.
    pokey_duration_rule = False
    update = 1
    waiting = False
    first_event_update = None
    notes = 0
    rests = 0
    end_kind = ""
    tempo_changes = 0
    repeated_body_executions = 0
    repeat_stack = []
    branch_decisions = branch_decisions or {}
    branch_count = 0
    loop_jumps = 0
    loop_boundaries = []
    index = 0
    executed = 0
    unsupported = {
        "COND_JUMP_INC", "COND_JUMP_EQ",
        "COND_JUMP_NE", "COND_JUMP_PL", "COND_JUMP_MI", "PUSH_SEQ",
    }
    while index < len(instructions):
        executed += 1
        if executed > 10000:
            raise SystemExit(f"duration trace execution limit at ${start:04X}")
        inst = instructions[index]
        if waiting:
            if tempo == 0:
                raise SystemExit(f"zero tempo while tracing ${start:04X}")
            steps = max(1, timer // tempo + 1)
            timer -= steps * tempo
            update += steps
            waiting = False
        if inst.mnemonic == "SET_TEMPO":
            tempo = inst.raw[1] >> 2
            tempo_changes += 1
        elif inst.mnemonic == "ADD_TEMPO":
            tempo = (tempo + inst.raw[1]) & 0xFF
            tempo_changes += 1
        elif inst.mnemonic == "PUSH_SEQ_EXT":
            count = inst.raw[1]
            if count == 0:
                raise SystemExit(f"zero extended-repeat count at ${inst.addr:04X}")
            repeat_stack.append([index + 1, count])
        elif inst.mnemonic == "POP_SEQ":
            if not repeat_stack:
                raise SystemExit(f"unmatched POP_SEQ at ${inst.addr:04X}")
            repeat_stack[-1][1] -= 1
            if repeat_stack[-1][1]:
                repeated_body_executions += 1
                index = repeat_stack[-1][0]
                continue
            repeat_stack.pop()
        elif inst.mnemonic == "COND_JUMP_REG_Z":
            table_count = (len(inst.raw) - 1) // 2
            if inst.addr not in branch_decisions and table_count != 1:
                raise SystemExit(f"missing computed-target decision at ${inst.addr:04X}")
            branch_count += 1
            decision = branch_decisions.get(inst.addr, 0)
            # Preserve the old boolean API while making its meaning explicit:
            # True selects zero, False selects the first nonzero entry.
            value = (0 if decision is True else
                     1 if decision is False else int(decision))
            if not 0 <= value < table_count:
                raise SystemExit(
                    f"computed-target value {value} outside 0..{table_count - 1} "
                    f"at ${inst.addr:04X}")
            pair = 1 + 2 * value
            target = inst.raw[pair] | (inst.raw[pair + 1] << 8)
            target_index = next(
                (i for i, candidate in enumerate(instructions)
                 if candidate.addr == target), None)
            if target_index is None:
                instructions = instructions[:index + 1] + [
                    i for i in gd.disassemble_sequence(rom, target)
                    if not i.is_marker]
                index += 1
            else:
                index = target_index
            continue
        elif inst.mnemonic == "SET_SEQ_PTR":
            if max_loop_jumps is None:
                raise SystemExit(f"unbounded SET_SEQ_PTR at ${inst.addr:04X}")
            loop_boundaries.append(update)
            if loop_jumps >= max_loop_jumps:
                end_kind = "LOOP_BOUND"
                break
            loop_jumps += 1
            target = inst.raw[-2] | (inst.raw[-1] << 8)
            target_index = next(
                (i for i, candidate in enumerate(instructions)
                 if candidate.addr == target), None)
            if target_index is None:
                raise SystemExit(f"loop target ${target:04X} absent from trace")
            index = target_index
            continue
        elif inst.mnemonic in ("SWITCH_POKEY", "FORCE_POKEY"):
            # $54CC: AND #$FC clears status bits 0 and 1 and zeroes $0813,
            # which is what the branch at $4844 tests.  $54E5 (FORCE_POKEY)
            # sets $0813 to 1 instead, keeping the duration-table arm.
            pokey_duration_rule = inst.mnemonic == "SWITCH_POKEY"
        elif inst.mnemonic == "SWITCH_YM2151":
            # $54B8: AND #$FC / ORA #$02 -- bit 1 set selects the table arm.
            pokey_duration_rule = False
        elif inst.mnemonic in ("NOTE", "REST"):
            control = inst.raw[1]
            if pokey_duration_rule:
                # $48F9-$4903: AND #$7F then three LSR A / ROR $11 pairs, which
                # forms the 16-bit value (control & $7F) * 32.  No table, no
                # dotted bit, no division field.
                duration = (control & 0x7F) * 32
            else:
                duration = rom.read_word(0x5C5F + 2 * (control & 0x0F))
                if control & 0x40:
                    duration += duration // 2
            timer += duration
            waiting = True
            if first_event_update is None:
                first_event_update = update
            if inst.mnemonic == "NOTE":
                notes += 1
            else:
                rests += 1
        elif inst.mnemonic in ("CHAIN", "END"):
            end_kind = inst.mnemonic
            break
        elif inst.mnemonic in unsupported:
            raise SystemExit(
                f"unsupported {inst.mnemonic} in selected trace at ${inst.addr:04X}")
        index += 1
    if not end_kind:
        raise SystemExit(f"selected duration trace at ${start:04X} is not finite")
    if first_event_update is None:
        first_event_update = 1
    intervals = update - first_event_update
    return {
        "notes": notes, "rests": rests, "first_update": first_event_update,
        "end_update": update, "intervals": intervals,
        "seconds": intervals / service_hz, "residue": timer,
        "final_tempo": tempo, "tempo_changes": tempo_changes,
        "repeat_replays": repeated_body_executions, "branches": branch_count,
        "loop_jumps": loop_jumps, "loop_boundaries": loop_boundaries,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("rom", type=Path)
    p.add_argument("--clock-csv", required=True, type=Path)
    p.add_argument("--cycle-csv", required=True, type=Path)
    p.add_argument("--duration-csv", required=True, type=Path)
    p.add_argument("--loop-csv", required=True, type=Path)
    p.add_argument("--articulation-csv", required=True, type=Path)
    p.add_argument("--tms-ref", required=True, type=Path)
    p.add_argument("--tms-header-ref", required=True, type=Path)
    args = p.parse_args()
    rom = gd.GauntletROM(str(args.rom))
    require_text(args.tms_ref, [
        "if (m_fifo_count < FIFO_SIZE)",
        "if (m_fifo_count <= 8)",
        "if (new_frame_stop_flag())",
        "m_TALK = m_SPEN = false",
    ])
    require_text(args.tms_header_ref, [
        "static constexpr unsigned FIFO_SIZE = 16;",
    ])

    anchors = {
        0x4187: "48 8a 48 d8 8d 30 18",
        0x418E: "a5 02 29 fb 85 02 a5 01",
        0x419D: "ba bd 03 01 29 10 f0 06",
        0x41AD: "e6 00 a5 2a f0 09 c6 2a d0 05 a5 29 8d 20 10",
        0x41BC: "20 c8 41 20 81 83",
        0x41C8: "20 94 58 20 94 58 20 94 58",
        0x41D1: "a5 00 4a 90 08 a2 00 20 0d 50 4c 94 58 a2 01 20 0d 50 4c 94 58",
        0x4532: "a9 07 99 08 04 a9 10 99 ca 05",
        0x4651: "bd e6 07 f0 02 a9 ff 85 17 bd 90 03",
        0x4684: "bd be 02 38 fd ca 05 9d be 02",
        0x4698: "bd fa 02 38 fd ca 05 9d fa 02 b0 1e de 18 03 10 19 a9 7f 9d 18 03 a9 01 8d 2f 08",
        0x4854: "68 85 11 29 0f 0a a8 b9 5f 5c",
        0x488B: "a9 7f 9d 18 03 a5 11 30 31 bd dc 02 9d 18 03 a9 00 85 0f bd ca 05 0a 26 0f",
        0x48A6: "bd be 02 38 e5 0e 9d fa 02 bd 18 03 e5 0f 9d 18 03 a5 11 29 30 c9 10 d0 06 5e 18 03 7e fa 02",
        0x49A5: "ad 13 08 f0 0b bd 82 02 1d a0 02 d0 03 4c 45 4b",
        0x49C5: "bd 62 04 85 06 bd 80 04 85 07 bc 16 05",
        0x49D9: "de 34 05 d0 56 c8 b1 06 9d 34 05 c8 c9 ff d0 26",
        0x4A34: "a9 00 85 12 b1 06 10 02 c6 12 85 11 88 b1 06 0a 26 11 26 12",
        0x4A6F: "7d 82 02 85 11 98 7d a0 02 a8 18 a5 11 7d 7e 06",
        0x4A90: "bd 26 04 85 06 bd 44 04 85 07 bc 9e 04",
        0x4AAA: "c8 b1 06 9d bc 04 c8 c9 ff d0 26",
        0x4AFC: "b1 06 18 7d da 04 50 06 a9 80 b0 02 a9 7f 9d da 04",
        0x4B3F: "1d 42 06 4c 47 4b",
        0x4B47: "ac 13 08 99 17 08 e0 1e b0 0c",
        0x4B5D: "bd e6 07 f0 08 8e 1c 08 aa ca 4c 51 46 60",
        0x4D02: "98 48 c8 a9 00 8d 14 08",
        0x4D87: "ad 11 08 cd 12 08 b0 03 ad 12 08 c5 13 b0 16",
        0x4DAC: "ad 11 08 cd 14 08 90 03 8d 14 08 ad 12 08 cd 14 08 90 15",
        0x4DFC: "a9 00 8d 21 08 a9 ff 8d 25 08",
        0x4E68: "be e6 07 d0 01 60",
        0x4E82: "18 a9 20 6d 3c 08 a8 20 f0 4f",
        0x4EFF: "bd 3d 08 29 07 aa bd a0 57 85 0f",
        0x4F3E: "a4 0c b9 27 08 4a 4a 4a 4a",
        0x4F92: "20 f0 4f 8c 10 18 18 20 f0 4f",
        0x4FBD: "4e 2f 08 90 13 a0 08 20 f0 4f",
        0x4FD6: "a9 07 8d 3c 08 18 bd ae 57 69 07",
        0x4FF0: "24 0d 30 18 48 a9 00 18 2c 11 18 10 0e",
        0x500D: "bd a8 57 85 08 bd aa 57 85 09",
        0x516A: "18 7d ca 05 9d ca 05 38 60",
        0x5173: "4a 4a 9d ca 05 38 60",
        0x5214: "48 20 c6 42 f0 22 48 bd d8 06",
        0x523F: "bd d8 06 f0 14 20 d7 42 de f6 06",
        0x5515: "85 11 20 47 50 9d 64 02 a5 11 9d 46 02 38 60",
        0x5894: "a5 33 f0 13",
        0x58AB: "ad 30 10 29 20 f0 17",
        0x58D5: "a9 ff a4 2f d0 1e",
        0x5926: "8d 20 18 ad 31 10 29 7f 8d 31 10 60",
        0x657B: "02 2c 12 00 02 10 00 12 00 00",
        0x6754: "2a 81 99 54 67",
        0x6732: "b2 05 ab 03 ae 3f 67",
        0x6801: "0d 8a 99 01 68",
        0x6854: "8a a0 00 7d 99 54 68",
        0x6889: "8a a0 00 7d 99 89 68",
        0x69A5: "3d 81 99 a5 69",
        0x6790: "b2 05 ab 0f ae b5 67",
        0x7D22: "b2 05 ab 0f ae 47 7d",
        0x8381: "a9 10 2c 30 10 d0 24",
        0x83AC: "ad 20 10 a2 03 4a 48 b5 3e 29 1f b0 17",
        0x83D0: "c9 1b b0 09 b5 3e 69 20 90 f1 f0 01 18 a9 1f",
        0x83F8: "e6 42 a5 42 4a b0 31",
        0x8430: "a5 36 05 37 8d 35 10 a5 38 05 39 8d 34 10 60",
    }
    for address, expected in anchors.items():
        require_bytes(rom, address, expected)

    pixel_hz = MASTER_HZ / 2.0
    frame_hz = pixel_hz / (HTOTAL * VTOTAL)
    irq_hz = frame_hz * 4.0
    device_hz = irq_hz / 2.0
    speech_attempt_hz = irq_hz * 4.0
    cpu_hz = MASTER_HZ / 8.0
    ym_hz = MASTER_HZ / 4.0
    tms_normal_hz = MASTER_HZ / 2.0 / 11.0
    tms_squeak_hz = MASTER_HZ / 2.0 / 9.0
    watchdog_latencies = []
    for start_phase in range(256):
        target = ((start_phase >> 1) + 0x10 + (start_phase & 1)) & 0x7F
        latency = next(
            delta for delta in range(1, 257)
            if (((start_phase + delta) & 0xFF) >> 1) == target)
        watchdog_latencies.append(latency)
    if set(watchdog_latencies[0::2]) != {32} or set(watchdog_latencies[1::2]) != {33}:
        raise SystemExit("speech watchdog parity latency changed unexpectedly")

    source = ("upstream MAME gauntlet.cpp configuration; ROM scheduler anchors; "
              "independent schematic calculation (user-confirmed 2026-07-12)")
    confidence = "Verified clock tree by independent schematic calculation"
    clock_rows = [
        ["master_xtal", "board", "14318181 Hz", MASTER_HZ, 1.0 / MASTER_HZ, source, confidence],
        ["pixel_clock", "video", "master/2", pixel_hz, 1.0 / pixel_hz, source, confidence],
        ["frame", "video", "pixel/(456*262)", frame_hz, 1.0 / frame_hz, source, confidence],
        ["sound_irq", "$4187", "4/frame: 32V assertions at scanlines 32,96,160,224", irq_hz, 1.0 / irq_hz, source, confidence],
        ["POKEY_full_sweep", "$41D6->$500D X=0", "sound_irq/2; odd $00 parity", device_hz, 1.0 / device_hz, source, "Verified ROM parity; " + confidence],
        ["YM_full_sweep", "$41DE->$500D X=1", "sound_irq/2; even $00 parity", device_hz, 1.0 / device_hz, source, "Verified ROM parity; " + confidence],
        ["speech_service_attempt", "$41C8->$5894", "4/sound_irq", speech_attempt_hz, 1.0 / speech_attempt_hz, source, "Verified ROM call count; READY-limited writes"],
        ["6502_clock", "CPU", "master/8", cpu_hz, 1.0 / cpu_hz, source, confidence],
        ["POKEY_clock", "POKEY", "master/8", cpu_hz, 1.0 / cpu_hz, source, confidence],
        ["YM2151_clock", "YM2151", "master/4", ym_hz, 1.0 / ym_hz, source, confidence],
        ["TMS5220_normal_clock", "TMS5220", "master/2/11", tms_normal_hz, 1.0 / tms_normal_hz, source, confidence],
        ["TMS5220_squeak_clock", "TMS5220", "master/2/9", tms_squeak_hz, 1.0 / tms_squeak_hz, source, confidence],
        ["channel_timer_service", "$4651", "once per matching physical-device sweep", device_hz, 1.0 / device_hz, source, "Verified ROM scheduling and clock source"],
        ["speech_watchdog_even_phase", "$58AB-$58C8", "32 sound-IRQ intervals from first sustained not-ready sample when $00 is even", irq_hz / 32.0, 32.0 / irq_hz, "ROM watchdog arithmetic; MAME active-low READY mapping", "Verified ROM intervals and clock-to-seconds conversion"],
        ["speech_watchdog_odd_phase", "$58AB-$58C8", "33 sound-IRQ intervals from first sustained not-ready sample when $00 is odd", irq_hz / 33.0, 33.0 / irq_hz, "ROM watchdog arithmetic; MAME active-low READY mapping", "Verified ROM intervals and clock-to-seconds conversion"],
    ]
    write_csv(
        args.clock_csv,
        ["event", "consumer_or_device", "derivation", "frequency_hz", "period_seconds", "evidence", "confidence"],
        clock_rows,
        lineterminator="\n")

    # Counts include the listed instructions only. Caller-only rows intentionally
    # exclude all instructions (including RTS) executed inside called routines.
    ym_wait_ready = 29
    ym_wait_one_busy = ym_wait_ready + 13
    ym_wait_254_busy = ym_wait_ready + 13 * 254
    ym_wait_timeout = 3347
    # $4E82-$4FD5: three base-register groups, optional key-off, pitch/KC gate,
    # operator setup, one shared transform, four operator bodies, optional key-on.
    ym_active_ready = (3 * (10 + 47) + 57 + (9 + 8 + 6 + 10 + 57 + 10)
                       + 38 + 33 + (3 * 221 + 219) + 70)
    ym_active_first_timeout = ym_active_ready + (ym_wait_timeout - ym_wait_ready) + 13 * (12 - ym_wait_ready)
    ym_active_last_timeout = ym_active_ready + (ym_wait_timeout - ym_wait_ready)
    ym_active_254_each = ym_active_ready + 14 * (ym_wait_254_busy - ym_wait_ready)
    if (ym_wait_one_busy, ym_wait_254_busy, ym_active_first_timeout,
            ym_active_last_timeout, ym_active_254_each) != (42, 3331, 4448, 4669, 47579):
        raise SystemExit("YM cycle derivation changed unexpectedly")

    speech_idle_cpu = speech_service(rom.data, True, 0)
    speech_kickoff_cpu = speech_service(rom.data, True, 0x80)
    speech_stream_cpu = speech_service(rom.data, True, 0xFF)
    speech_drain_cpu = speech_service(rom.data, True, 0x11)
    speech_watchdog_arm_even = speech_service(rom.data, False, phase=0, watchdog=0xFF)
    speech_watchdog_arm_odd = speech_service(rom.data, False, phase=1, watchdog=0xFF)
    speech_watchdog_wait = speech_service(rom.data, False, phase=2, watchdog=0x20)
    speech_watchdog_expiry = speech_service(
        rom.data, False, phase=64, watchdog=0x20, stop_rts=0x5873)
    speech_ready_idle = speech_idle_cpu.cycles
    speech_ready_kickoff = speech_kickoff_cpu.cycles
    speech_ready_stream = speech_stream_cpu.cycles
    speech_ready_drain = speech_drain_cpu.cycles
    if (speech_ready_idle, speech_ready_kickoff, speech_ready_stream,
            speech_ready_drain, speech_watchdog_arm_even.cycles,
            speech_watchdog_arm_odd.cycles, speech_watchdog_wait.cycles,
            speech_watchdog_expiry.cycles,
            speech_watchdog_arm_even.mem[0x30],
            speech_watchdog_arm_odd.mem[0x30],
            speech_watchdog_expiry.mem[0x30]) != \
            (76, 78, 83, 76, 43, 43, 38, 127, 0x10, 0x11, 0xFF):
        raise SystemExit("instruction-executed speech-service trace changed unexpectedly")

    # Steady configured POKEY command $44 can occupy the first pair member in
    # logical slot X=29. Both timers remain nonnegative, both envelopes are
    # inactive, the second pair member and other pair are empty, and the active
    # priority meets $13. The X=29 counts include page crossings at $07E6,X
    # (entry and exit) and $02FA,X.
    pokey_channel_common = 291
    pokey_channel_rotate = pokey_channel_common + 19
    pokey_empty_pair = 154
    pokey_active_pair_common = pokey_channel_common + 275
    pokey_active_pair_rotate = pokey_channel_rotate + 275
    pokey_one_active_common = 24 + 185 + pokey_active_pair_common + pokey_empty_pair
    pokey_one_active_rotate = 24 + 185 + pokey_active_pair_rotate + pokey_empty_pair
    # Normal cabinet path: self-test input inactive/high, four inactive coin
    # bits, saturated $1F filters, incremented $42 odd, and no pending counters.
    board_quiescent_odd = 201
    irq_one_active_common = 89 + 36 + 4 * speech_ready_idle + pokey_one_active_common + board_quiescent_odd
    irq_one_active_rotate = 89 + 36 + 4 * speech_ready_idle + pokey_one_active_rotate + board_quiescent_odd
    if (pokey_channel_common, pokey_channel_rotate, pokey_active_pair_common,
            pokey_active_pair_rotate, pokey_one_active_common,
            pokey_one_active_rotate, board_quiescent_odd,
            irq_one_active_common, irq_one_active_rotate) != \
            (291, 310, 566, 585, 929, 948, 201, 1559, 1578):
        raise SystemExit("active POKEY/IRQ cycle derivation changed unexpectedly")
    # Execute the actual first three command-$44 services from the type-7
    # allocation seed.  This catches interactions omitted by isolated envelope
    # counts, notably the first REST's secondary-timer expiry on service two.
    initial_cpu, pokey_initial_common, initial_common_instructions = \
        command44_channel_service(rom.data, 0, 3)
    _, pokey_initial_rotate, initial_rotate_instructions = \
        command44_channel_service(rom.data, 0, 0)
    countdown_cpu, pokey_envelopes_common, countdown_common_instructions = \
        command44_channel_service(rom.data, 1, 3)
    _, pokey_envelopes_rotate, countdown_rotate_instructions = \
        command44_channel_service(rom.data, 1, 0)
    boundary_cpu, pokey_boundary_common, boundary_common_instructions = \
        command44_channel_service(rom.data, 2, 3)
    _, pokey_boundary_rotate, boundary_rotate_instructions = \
        command44_channel_service(rom.data, 2, 0)
    if (pokey_initial_common, pokey_initial_rotate,
            initial_common_instructions, initial_rotate_instructions,
            pokey_envelopes_common, pokey_envelopes_rotate,
            countdown_common_instructions, countdown_rotate_instructions,
            pokey_boundary_common, pokey_boundary_rotate,
            boundary_common_instructions, boundary_rotate_instructions) != \
            (1637, 1656, 474, 478, 510, 529, 148, 152,
             557, 576, 163, 167):
        raise SystemExit("instruction-executed command $44 trace changed unexpectedly")
    x = 29
    if (initial_cpu.mem[0x0246 + x], initial_cpu.mem[0x0264 + x],
            initial_cpu.mem[0x0462 + x], initial_cpu.mem[0x0480 + x],
            initial_cpu.mem[0x0516 + x], initial_cpu.mem[0x0534 + x],
            initial_cpu.mem[0x049E + x], initial_cpu.mem[0x04BC + x]) != \
            (0x95, 0x65, 0x7F, 0x65, 2, 2, 1, 2):
        raise SystemExit("command $44 initial decode post-state changed unexpectedly")
    if (countdown_cpu.mem[0x0534 + x], countdown_cpu.mem[0x04BC + x]) != (1, 1):
        raise SystemExit("command $44 countdown post-state changed unexpectedly")
    # The next frequency record at $6582 is count $12 plus zero delta.  The ROM
    # retains A=$12 while ORing the delta bytes, so this is a continuing record,
    # not the zero-record termination path.  Volume likewise continues.
    if (boundary_cpu.mem[0x0516 + x], boundary_cpu.mem[0x0534 + x],
            boundary_cpu.mem[0x049E + x], boundary_cpu.mem[0x04BC + x]) != \
            (5, 0x12, 3, 0x12):
        raise SystemExit("command $44 record reload post-state changed unexpectedly")

    pokey_initial_pair_common = pokey_initial_common + 275
    pokey_initial_pair_rotate = pokey_initial_rotate + 275
    pokey_initial_full_common = 24 + 185 + pokey_initial_pair_common + pokey_empty_pair
    pokey_initial_full_rotate = 24 + 185 + pokey_initial_pair_rotate + pokey_empty_pair
    irq_initial_common = 89 + 36 + 4 * speech_ready_idle + pokey_initial_full_common + board_quiescent_odd
    irq_initial_rotate = 89 + 36 + 4 * speech_ready_idle + pokey_initial_full_rotate + board_quiescent_odd
    pokey_envelope_pair_common = pokey_envelopes_common + 275
    pokey_envelope_pair_rotate = pokey_envelopes_rotate + 275
    pokey_envelope_full_common = 24 + 185 + pokey_envelope_pair_common + pokey_empty_pair
    pokey_envelope_full_rotate = 24 + 185 + pokey_envelope_pair_rotate + pokey_empty_pair
    irq_envelope_common = 89 + 36 + 4 * speech_ready_idle + pokey_envelope_full_common + board_quiescent_odd
    irq_envelope_rotate = 89 + 36 + 4 * speech_ready_idle + pokey_envelope_full_rotate + board_quiescent_odd
    if (pokey_envelopes_common, pokey_envelopes_rotate,
            pokey_envelope_pair_common, pokey_envelope_pair_rotate,
            pokey_envelope_full_common, pokey_envelope_full_rotate,
            irq_envelope_common, irq_envelope_rotate) != \
            (510, 529, 785, 804, 1148, 1167, 1778, 1797):
        raise SystemExit("active-envelope cycle derivation changed unexpectedly")
    pokey_boundary_pair_common = pokey_boundary_common + 275
    pokey_boundary_pair_rotate = pokey_boundary_rotate + 275
    pokey_boundary_full_common = 24 + 185 + pokey_boundary_pair_common + pokey_empty_pair
    pokey_boundary_full_rotate = 24 + 185 + pokey_boundary_pair_rotate + pokey_empty_pair
    irq_boundary_common = 89 + 36 + 4 * speech_ready_idle + pokey_boundary_full_common + board_quiescent_odd
    irq_boundary_rotate = 89 + 36 + 4 * speech_ready_idle + pokey_boundary_full_rotate + board_quiescent_odd
    if (pokey_boundary_common, pokey_boundary_rotate,
            pokey_boundary_pair_common, pokey_boundary_pair_rotate,
            pokey_boundary_full_common, pokey_boundary_full_rotate,
            irq_boundary_common, irq_boundary_rotate) != \
            (557, 576, 832, 851, 1195, 1214, 1825, 1844):
        raise SystemExit("envelope-boundary cycle derivation changed unexpectedly")
    if (pokey_initial_pair_common, pokey_initial_pair_rotate,
            pokey_initial_full_common, pokey_initial_full_rotate,
            irq_initial_common, irq_initial_rotate) != \
            (1912, 1931, 2275, 2294, 2905, 2924):
        raise SystemExit("initial-decode cycle composition changed unexpectedly")

    ff_cpu, pokey_ff_loop_common, ff_common_instructions = \
        command05_ff_loop_service(rom.data, 3)
    _, pokey_ff_loop_rotate, ff_rotate_instructions = \
        command05_ff_loop_service(rom.data, 1)
    x = 28
    if (pokey_ff_loop_common, pokey_ff_loop_rotate,
            ff_common_instructions, ff_rotate_instructions,
            ff_cpu.mem[0x0462 + x], ff_cpu.mem[0x0480 + x],
            ff_cpu.mem[0x0516 + x], ff_cpu.mem[0x0534 + x],
            ff_cpu.mem[0x05AC + x]) != \
            (505, 524, 145, 149, 0xED, 0x68, 11, 0xFC, 0xFF):
        raise SystemExit("command $05 $FF loop-control trace changed unexpectedly")

    command05_common_cpu = command05_full_consumer(rom.data)
    command05_initial_common, command05_initial_common_instructions = \
        command05_full_service(command05_common_cpu, 3)
    command05_rotate_cpu = command05_full_consumer(rom.data)
    command05_initial_rotate, command05_initial_rotate_instructions = \
        command05_full_service(command05_rotate_cpu, 1)
    if (command05_initial_common, command05_initial_rotate,
            command05_initial_common_instructions,
            command05_initial_rotate_instructions) != (6874, 6950, 1978, 1994):
        raise SystemExit("command $05 initial full-consumer trace changed unexpectedly")
    expected_sequence_posts = (0x6846, 0x687B, 0x68B0, 0x68D0)
    expected_frequency_bases = (0x6832, 0x6867, 0x689C, 0x68BC)
    for record in range(4):
        x = 29 - record
        sequence_post = (command05_common_cpu.mem[0x0246 + x] |
                         (command05_common_cpu.mem[0x0264 + x] << 8))
        frequency_base = (command05_common_cpu.mem[0x0462 + x] |
                          (command05_common_cpu.mem[0x0480 + x] << 8))
        if (sequence_post, frequency_base,
                command05_common_cpu.mem[0x0516 + x],
                command05_common_cpu.mem[0x0534 + x]) != \
                (expected_sequence_posts[record], expected_frequency_bases[record], 2, 2):
            raise SystemExit(f"command $05 channel {record + 1} post-state changed")

    irq_fixed_ready_quiescent = 89 + 36 + 4 * speech_ready_idle + board_quiescent_odd
    irq_command05_initial_common = irq_fixed_ready_quiescent + command05_initial_common
    irq_command05_initial_rotate = irq_fixed_ready_quiescent + command05_initial_rotate
    if (irq_command05_initial_common, irq_command05_initial_rotate) != (7504, 7580):
        raise SystemExit("command $05 initial IRQ composition changed unexpectedly")

    # Bound four possible POKEY phase alignments for the first 1,000 services.
    # Only the first all-channel decode exceeds the nominal interval; the
    # largest later service occurs at update 193 when the first two channels
    # remain active.
    command05_prefix_results = []
    odd_phases = (1, 3, 5, 7)
    for start_index in range(4):
        cpu = command05_full_consumer(rom.data)
        phases = odd_phases[start_index:] + odd_phases[:start_index]
        services = []
        for update in range(1, 1001):
            device_cycles, _ = command05_full_service(cpu, phases[(update - 1) % 4])
            services.append((device_cycles, update, phases[(update - 1) % 4]))
        later_max = max(services[1:])
        overruns = sum(
            irq_fixed_ready_quiescent + device + 7 > 7467
            for device, _, _ in services)
        command05_prefix_results.append((services[0], later_max, overruns))
    expected_prefix_results = [
        ((6950, 1, 1), (4201, 193, 1), 1),
        ((6874, 1, 3), (4163, 193, 3), 1),
        ((6874, 1, 5), (4163, 193, 5), 1),
        ((6874, 1, 7), (4163, 193, 7), 1),
    ]
    if command05_prefix_results != expected_prefix_results:
        raise SystemExit("command $05 1,000-service prefix trace changed unexpectedly")
    command05_later_max = 4201
    irq_command05_later_max = irq_fixed_ready_quiescent + command05_later_max

    cycle_rows = [
        ["IRQ_normal_mixer_idle", "$4187-$41C7", "normal path; $2A=0", 89, 96, "", "caller instructions only; includes JSR opcodes, excludes $41C8/$8381 callees", "Verified"],
        ["IRQ_normal_mixer_countdown", "$4187-$41C7", "normal path; $2A>1", 96, 103, "", "caller instructions only; includes JSR opcodes, excludes callees", "Verified"],
        ["IRQ_normal_mixer_expiry", "$4187-$41C7", "normal path; $2A=1 and mixer write", 102, 109, "", "caller instructions only; includes JSR opcodes, excludes callees", "Verified"],
        ["audio_dispatch_POKEY", "$41C8-$41DD", "odd $00 parity", 36, "", "", "three speech JSRs plus parity/device dispatch and tail JMP; callee instructions excluded", "Verified"],
        ["audio_dispatch_YM", "$41C8-$41E5", "even $00 parity", 37, "", "", "three speech JSRs plus parity/device dispatch and tail JMP; callee instructions excluded", "Verified"],
        ["POKEY_empty_full_consumer", "$500D->$4DFC->$4D02", "all four physical list heads zero; global threshold $13=0", 518, "", "", "includes $500D dispatch, two empty pair consumers, all AUDF/AUDC/AUDCTL writes, and final RTS", "Verified representative lower-bound path"],
        ["YM_empty_full_consumer", "$500D->$4FD6->$4E68", "all eight physical list heads zero", 373, "", "", "includes $500D dispatch, eight empty channel probes, and final RTS; no YM register busy waits occur", "Verified representative lower-bound path"],
        ["POKEY_output_wrapper_carry_clear", "$4DFC-$4E67", "both pair consumers return carry clear", 184, "", "", "includes two JSR opcodes but excludes all $4D02 instructions; includes nine hardware writes", "Verified active-output suffix"],
        ["POKEY_output_wrapper_carry_set", "$4DFC-$4E67", "both pair consumers return carry set", 186, "", "", "includes two JSR opcodes and both ORA adjustments but excludes all $4D02 instructions", "Verified active-output suffix"],
        ["POKEY_arbitration_active_tie_join", "$4D87-$4DD3", "$0811=$0812=$0814 and >= $13; second member wins tie", 73, "", "", "post-$4651 arbitration suffix; returns carry set and selects caller's joined-mode mask", "Verified"],
        ["POKEY_arbitration_active_first_wins", "$4D87-$4DFB", "$0811>=$0812 and >=$13; updated first maximum > $0812", 100, "", "", "post-$4651 arbitration suffix; returns carry clear and copies first-member output", "Verified"],
        ["POKEY_arbitration_suppressed_tie_join", "$4D87-$4DD3", "same tie but maximum < global threshold $13", 100, "", "", "clears AUDC/control candidates before joined-mode return", "Verified"],
        ["POKEY_arbitration_suppressed_first_wins", "$4D87-$4DFB", "same first-member win but maximum < global threshold $13", 127, "", "", "clears AUDC/control candidates before carry-clear return", "Verified"],
        ["POKEY_channel_steady_common", "$4651-$4B6A", "configured command $44; X=29; no linked next; both timers nonnegative; inactive envelopes; base frequency nonzero; $00&6!=0", pokey_channel_common, "", "", "includes indexed page crossings and RTS; no bytecode decode or envelope record advance", "Verified representative active path"],
        ["POKEY_channel_steady_rotate", "$4651-$4B6A", "same state; $00&6=0 executes signed-delta rotate at $49BB-$49C2", pokey_channel_rotate, "", "", "one-in-four POKEY frame phase; zero deltas still execute both ROR instructions", "Verified representative active path"],
        ["POKEY_pair_one_active_common", "$4D02-$4DFB", "first pair member uses steady common path; second member empty; priority >=$13; first wins", pokey_active_pair_common, "", "", "includes one $4651 call, pair setup/copy, arbitration, and RTS", "Verified representative pair path"],
        ["POKEY_pair_one_active_rotate", "$4D02-$4DFB", "same pair on $00&6=0 delta-rotation phase", pokey_active_pair_rotate, "", "", "includes one $4651 call and complete pair consumer", "Verified representative pair path"],
        ["POKEY_one_active_full_consumer_common", "$500D->$4DFC->$4D02", "configured command $44 is sole active channel; other three heads empty; common frame phase", pokey_one_active_common, "", "", "dispatch + mixed-carry wrapper + one-active pair + empty pair", "Verified representative full-device path"],
        ["POKEY_one_active_full_consumer_rotate", "$500D->$4DFC->$4D02", "same state on $00&6=0 delta-rotation phase", pokey_one_active_rotate, "", "", "largest of the four steady phases for this state", "Verified representative full-device path"],
        ["board_normal_quiescent_odd_phase", "$8381-$843E", "$1030.4=1 inactive; $1020 low bits=1; filters low5=$1F; incremented $42 odd; counters zero", board_quiescent_odd, "", "", "normal filtered path, four loop iterations, direct output writes, RTS", "Verified representative board path"],
        ["IRQ_POKEY_one_active_common", "$4187->$41C8->$500D/$5894->$8381", "$2A=0; command $44 sole active; four READY-idle speech calls; quiescent board; common frame phase", irq_one_active_common, irq_one_active_common + 7, "", "complete software path; 20.972% of 7,467-cycle IRQ interval including entry", "Verified representative complete IRQ"],
        ["IRQ_POKEY_one_active_rotate", "$4187->$41C8->$500D/$5894->$8381", "same state on $00&6=0 delta-rotation phase", irq_one_active_rotate, irq_one_active_rotate + 7, "", "complete software path; 21.227% of 7,467-cycle IRQ interval including entry", "Verified representative complete IRQ"],
        ["POKEY_channel_initial_decode_common", "$4651-$4B6A", "fresh command $44 allocation; common $00&6!=0 phase; decode six setup opcodes and REST $00,$0A", pokey_initial_common, "", "", "474 instructions executed from ROM; post-state and page penalties asserted", "Verified instruction-executed path"],
        ["POKEY_channel_initial_decode_rotate", "$4651-$4B6A", "same fresh allocation on $00&6=0 delta-rotation phase", pokey_initial_rotate, "", "", "478 instructions executed from ROM", "Verified instruction-executed path"],
        ["POKEY_pair_initial_decode_common", "$4D02-$4DFB", "initial command $44 decode in first member; second empty; first wins", pokey_initial_pair_common, "", "", "complete pair composed from instruction-executed channel and verified fixed suffix", "Verified representative pair path"],
        ["POKEY_pair_initial_decode_rotate", "$4D02-$4DFB", "same initial decode on delta-rotation phase", pokey_initial_pair_rotate, "", "", "complete pair consumer", "Verified representative pair path"],
        ["POKEY_initial_decode_full_common", "$500D->$4DFC->$4D02", "command $44 initial decode; other heads empty", pokey_initial_full_common, "", "", "dispatch + wrapper + initial-decode pair + empty pair", "Verified representative full-device path"],
        ["POKEY_initial_decode_full_rotate", "$500D->$4DFC->$4D02", "same initial decode on delta-rotation phase", pokey_initial_full_rotate, "", "", "selected initial-decode full-device path", "Verified representative full-device path"],
        ["IRQ_POKEY_initial_decode_common", "$4187->$41C8->$500D/$5894->$8381", "$2A=0; command $44 initial decode; four READY-idle speech calls; quiescent board", irq_initial_common, irq_initial_common + 7, "", "complete path; 38.998% of IRQ interval including entry", "Verified representative complete IRQ"],
        ["IRQ_POKEY_initial_decode_rotate", "$4187->$41C8->$500D/$5894->$8381", "same initial decode on delta-rotation phase", irq_initial_rotate, irq_initial_rotate + 7, "", "complete path; 39.253% of IRQ interval including entry", "Verified representative complete IRQ"],
        ["POKEY_channel_both_envelopes_common", "$4651-$4B6A", "command $44 second service; frequency/volume countdowns 2->1; REST secondary timer also expires; $00&6!=0", pokey_envelopes_common, "", "", "148 instructions executed from the initial-decode post-state", "Verified instruction-executed trajectory"],
        ["POKEY_channel_both_envelopes_rotate", "$4651-$4B6A", "same second service on $00&6=0 delta-rotation phase", pokey_envelopes_rotate, "", "", "152 instructions; both envelopes advance without record reload", "Verified instruction-executed trajectory"],
        ["POKEY_pair_both_envelopes_common", "$4D02-$4DFB", "second command $44 service in first member; second empty; first wins", pokey_envelope_pair_common, "", "", "complete pair including instruction-executed $4651 call", "Verified representative pair path"],
        ["POKEY_pair_both_envelopes_rotate", "$4D02-$4DFB", "same pair on delta-rotation phase", pokey_envelope_pair_rotate, "", "", "complete pair consumer", "Verified representative pair path"],
        ["POKEY_both_envelopes_full_common", "$500D->$4DFC->$4D02", "command $44 second service; other heads empty", pokey_envelope_full_common, "", "", "dispatch + mixed-carry wrapper + envelope/secondary-expiry pair + empty pair", "Verified representative full-device path"],
        ["POKEY_both_envelopes_full_rotate", "$500D->$4DFC->$4D02", "same second service on delta-rotation phase", pokey_envelope_full_rotate, "", "", "selected full-device trajectory", "Verified representative full-device path"],
        ["IRQ_POKEY_both_envelopes_common", "$4187->$41C8->$500D/$5894->$8381", "$2A=0; command $44 second service; four READY-idle speech calls; quiescent board", irq_envelope_common, irq_envelope_common + 7, "", "complete path; 23.905% of IRQ interval including entry", "Verified representative complete IRQ"],
        ["IRQ_POKEY_both_envelopes_rotate", "$4187->$41C8->$500D/$5894->$8381", "same second service on delta-rotation phase", irq_envelope_rotate, irq_envelope_rotate + 7, "", "complete path; 24.160% of IRQ interval including entry", "Verified representative complete IRQ"],
        ["POKEY_channel_envelope_boundary_common", "$4651-$4B6A", "command $44 third service; frequency and volume load continuing count-$12 records; unclamped; $00&6!=0", pokey_boundary_common, "", "", "163 instructions; frequency zero delta does not terminate because A retains count $12", "Verified instruction-executed trajectory"],
        ["POKEY_channel_envelope_boundary_rotate", "$4651-$4B6A", "same third service on $00&6=0 delta-rotation phase", pokey_boundary_rotate, "", "", "167 instructions; both records continue", "Verified instruction-executed trajectory"],
        ["POKEY_pair_envelope_boundary_common", "$4D02-$4DFB", "third command $44 service in first member; second empty; first wins", pokey_boundary_pair_common, "", "", "complete pair including record-reload $4651 call", "Verified representative pair path"],
        ["POKEY_pair_envelope_boundary_rotate", "$4D02-$4DFB", "same pair on delta-rotation phase", pokey_boundary_pair_rotate, "", "", "complete pair consumer", "Verified representative pair path"],
        ["POKEY_envelope_boundary_full_common", "$500D->$4DFC->$4D02", "command $44 selected record boundary; other heads empty", pokey_boundary_full_common, "", "", "dispatch + wrapper + boundary pair + empty pair", "Verified representative full-device path"],
        ["POKEY_envelope_boundary_full_rotate", "$500D->$4DFC->$4D02", "same state on delta-rotation phase", pokey_boundary_full_rotate, "", "", "selected boundary full-device path", "Verified representative full-device path"],
        ["IRQ_POKEY_envelope_boundary_common", "$4187->$41C8->$500D/$5894->$8381", "$2A=0; command $44 third service; four READY-idle speech calls; quiescent board", irq_boundary_common, irq_boundary_common + 7, "", "complete path; 24.535% of IRQ interval including entry", "Verified representative complete IRQ"],
        ["IRQ_POKEY_envelope_boundary_rotate", "$4187->$41C8->$500D/$5894->$8381", "same third service on delta-rotation phase", irq_boundary_rotate, irq_boundary_rotate + 7, "", "complete path; 24.789% of IRQ interval including entry", "Verified representative complete IRQ"],
        ["POKEY_channel_frequency_FF_loop_common", "$4651-$4B6A", "command $05 channel 2; $68F3 frequency offset 5/countdown 1; fresh loop count; prepared nonzero pitch; timers nonnegative; $00&6!=0", pokey_ff_loop_common, "", "", "145 instructions; `$FF FF 06` rewinds base $68F3->$68ED, loads repeat $FF, and reloads count $FC", "Verified instruction-executed loop-control path"],
        ["POKEY_channel_frequency_FF_loop_rotate", "$4651-$4B6A", "same configured loop boundary on $00&6=0 delta-rotation phase", pokey_ff_loop_rotate, "", "", "149 instructions; full pair/device IRQ composition depends on the other three command-$05 channels", "Verified instruction-executed loop-control path"],
        ["POKEY_command05_initial_full_common", "$500D->$4DFC->$4D02->$4651", "fresh four-record allocation in slots 29..26 and heads $1E..$21; all four initial setup/REST decodes; $00=3/5/7", command05_initial_common, "", "", "1,978 instructions including both active pairs, arbitration, and all POKEY writes", "Verified instruction-executed full-device path"],
        ["POKEY_command05_initial_full_rotate", "$500D->$4DFC->$4D02->$4651", "same fresh allocation; $00=1 executes all four delta-rotation blocks", command05_initial_rotate, "", "", "1,994 instructions; complete four-channel device service", "Verified instruction-executed full-device path"],
        ["IRQ_POKEY_command05_initial_common", "$4187->$41C8->$500D/$5894->$8381", "$2A=0; four READY-idle speech calls; quiescent board; command $05 initial service; $00=3/5/7", irq_command05_initial_common, irq_command05_initial_common + 7, "", "7,511 cycles including entry, 44 above the 7,467-cycle nominal interval", "Verified composition; level-IRQ consequence from MAME source"],
        ["IRQ_POKEY_command05_initial_rotate", "$4187->$41C8->$500D/$5894->$8381", "same initial command $05 service at $00=1", irq_command05_initial_rotate, irq_command05_initial_rotate + 7, "", "7,587 cycles including entry, 120 above nominal interval", "Verified composition; level-IRQ consequence from MAME source"],
        ["POKEY_command05_1000_service_later_max", "$500D->$4DFC->$4D02->$4651", "maximum after initial service across four phase alignments and 1,000 POKEY services each; update 193 at $00=1; two channels active", command05_later_max, "", "", "bounded trajectory result; not a proof beyond 1,000 services", "Verified bounded instruction-executed trace"],
        ["IRQ_POKEY_command05_1000_service_later_max", "$4187->$41C8->$500D/$5894->$8381", "compose bounded later maximum with idle mixer, READY-idle speech, and quiescent board", irq_command05_later_max, irq_command05_later_max + 7, "", "4,838 cycles including entry; each alignment has exactly one overrun, at initial decode", "Verified bounded composition"],
        ["YM_busy_sticky_return", "$4FF0-$500C", "$0D bit 7 already set", 12, "", "", "BIT/BMI/RTS; no hardware-status read", "Verified"],
        ["YM_busy_ready_immediate", "$4FF0-$500C", "$0D clear; first $1811 status read ready", ym_wait_ready, "", "", "includes RTS; A preserved", "Verified"],
        ["YM_busy_one_poll_then_ready", "$4FF0-$500C", "$0D clear; one busy status read, then ready", ym_wait_one_busy, "", "", "29 + 13*n cycles for n=1 busy polls", "Verified representative path"],
        ["YM_busy_254_polls_then_ready", "$4FF0-$500C", "$0D clear; 254 busy reads, then ready", ym_wait_254_busy, "", "", "largest non-timeout path; 29 + 13*n cycles", "Verified boundary path"],
        ["YM_busy_timeout", "$4FF0-$500C", "$0D clear; 255 consecutive busy reads", ym_wait_timeout, "", "", "sets sticky $0D negative and error flag $02 bit 1", "Verified boundary path"],
        ["YM_active_prepared_ready", "$4E82-$4FD5", "all write/pitch/key gates enabled; four operators selected; unclamped arithmetic; indexed lookups do not page-cross; all 14 busy checks ready immediately", ym_active_ready, "", "", "starts after $4651 prepared state; includes 14 JSR/RTS busy checks and all YM writes", "Verified representative active-output path"],
        ["YM_active_prepared_first_timeout", "$4E82-$4FD5", "same active path; first busy check times out; 13 later checks take sticky return", ym_active_first_timeout, "", "", "timeout adds 3318 cycles; each later sticky return saves 17", "Verified representative timeout path"],
        ["YM_active_prepared_last_timeout", "$4E82-$4FD5", "same active path; first 13 checks ready; final check times out", ym_active_last_timeout, "", "", "largest single-timeout placement on this path", "Verified boundary path"],
        ["YM_active_prepared_254_each", "$4E82-$4FD5", "same active path; every one of 14 checks sees 254 busy polls then ready", ym_active_254_each, "", "", "non-timeout stress bound; not asserted to be hardware-realistic", "Verified arithmetic bound"],
        ["speech_ready_idle_empty_queue", "$5894-$5931", "$33=0; READY; $2F=0; read=write", speech_ready_idle, "", "", "24 instructions including page-crossing BEQ $58E7->$5926, RTS, and zero data/strobe write", "Verified instruction-executed path"],
        ["speech_ready_speak_external", "$5894-$5931", "$33=0; READY; $2F=$80", speech_ready_kickoff, "", "", "26 instructions; writes $60 and strobes", "Verified instruction-executed path"],
        ["speech_ready_stream_byte", "$5894-$5931", "$33=0; READY; $2F=$FF; pointer does not wrap; low length remains nonzero", speech_ready_stream, "", "", "25 instructions; writes one payload byte and strobes", "Verified instruction-executed path"],
        ["speech_ready_drain_zero", "$5894-$5931", "$33=0; READY; $2F=$11..$01", speech_ready_drain, "", "", "24 instructions; decrements drain state and writes/strobes zero", "Verified instruction-executed path"],
        ["speech_not_ready_watchdog_arm", "$5894-$5931", "$33=0; not READY; $30=$FF; either $00 parity", speech_watchdog_arm_even.cycles, "", "", "sets $30=ceil($00/2)+$10; even/odd targets differ by one", "Verified instruction-executed path"],
        ["speech_not_ready_watchdog_wait", "$5894-$5931", "$33=0; not READY; nonnegative $30 does not equal $00>>1", speech_watchdog_wait.cycles, "", "", "returns without write or watchdog reset", "Verified instruction-executed path"],
        ["speech_not_ready_watchdog_expiry", "$5894->$5833-$5873", "$33=0; sustained not READY; $30 equals $00>>1", speech_watchdog_expiry.cycles, "", "", "tail-resets speech state and hardware control; occurs after 32/33 IRQ intervals", "Verified instruction-executed path"],
    ]
    for row in cycle_rows:
        row[5] = row[3] / cpu_hz * 1_000_000.0
    write_csv(
        args.cycle_csv,
        ["path", "range", "branch_assumptions", "software_cycles", "cycles_including_irq_entry", "microseconds_at_1_789772625_MHz", "scope", "confidence"],
        cycle_rows,
        lineterminator="\n")

    duration_rows = []
    chip_test_starts = [0x690C, 0x691F, 0x692E, 0x693F, 0x6952, 0x6961, 0x6972]
    for channel, start in enumerate(chip_test_starts, 1):
        trace = trace_duration(rom, start, device_hz)
        expected = channel * 120
        if trace["intervals"] != expected or trace["residue"] != -16:
            raise SystemExit(
                f"chip-test duration mismatch channel {channel}: {trace}")
        duration_rows.append([
            "0x04", channel, "default", f"0x{start:04X}", trace["notes"], trace["rests"],
            16, trace["final_tempo"], trace["tempo_changes"], trace["repeat_replays"],
            trace["first_update"], trace["end_update"], trace["intervals"],
            trace["seconds"], trace["residue"],
            "finite linear stream; default tempo $10; primary durations only",
            "Verified timer arithmetic and clock-to-seconds conversion"])

    selected = [
        ("0x09", 1, 0x7D87, 104, -16, "SET_TEMPO $F0 -> $3C; finite linear stream"),
        ("0x09", 2, 0x7D94, 104, -16, "SET_TEMPO $F0 -> $3C; finite linear stream"),
        ("0x09", 3, 0x7DA1, 104, -16, "SET_TEMPO $F0 -> $3C; finite linear stream"),
        ("0x2A", 1, 0x66E4, 68, -4, "SET_TEMPO plus eleven modulo ADD_TEMPO decrements"),
        ("0x1C", 1, 0x80E3, 274, -4, "$8E count 2 repeats the eight-event body"),
        ("0x20", 1, 0x8283, 6399, -4, "$8E count 10 repeats one sustained whole note"),
    ]
    for command, channel, start, expected_intervals, expected_residue, scope in selected:
        trace = trace_duration(rom, start, device_hz)
        if expected_intervals is not None and (trace["intervals"] != expected_intervals
                                                or trace["residue"] != expected_residue):
            raise SystemExit(f"selected duration mismatch at ${start:04X}: {trace}")
        duration_rows.append([
            command, channel, "default", f"0x{start:04X}", trace["notes"], trace["rests"],
            16, trace["final_tempo"], trace["tempo_changes"], trace["repeat_replays"],
            trace["first_update"], trace["end_update"], trace["intervals"],
            trace["seconds"], trace["residue"], scope,
            "Verified timer/control arithmetic and clock-to-seconds conversion"])

    rng_branches = [
        ("0x2B", 0x672F, 0x6736, 4, (1, 60)),
        ("0x2C", 0x6789, 0x6794, 16, (1, 12)),
        ("0x3A", 0x7D1F, 0x7D26, 16, (1, 120)),
    ]
    for command, start, branch_address, target_count, expected in rng_branches:
        for value in range(target_count):
            trace = trace_duration(
                rom, start, device_hz, branch_decisions={branch_address: value})
            if ((trace["notes"], trace["intervals"]) != expected
                    or trace["residue"] != -16):
                raise SystemExit(
                    f"RNG duration mismatch at ${branch_address:04X}: {trace}")
            duration_rows.append([
                command, 1, f"rng_value_{value:02X}",
                f"0x{start:04X}", trace["notes"], trace["rests"], 16,
                trace["final_tempo"], trace["tempo_changes"], trace["repeat_replays"],
                trace["first_update"], trace["end_update"], trace["intervals"],
                trace["seconds"], trace["residue"],
                f"Verified-feasible POKEY RNG computed target {value} at ${branch_address:04X}",
                "Verified branch/timer arithmetic and clock-to-seconds conversion"])
    write_csv(
        args.duration_csv,
        ["command", "chain_channel", "variant", "sequence_start", "notes", "rests",
         "initial_tempo", "final_tempo", "tempo_changes", "repeat_replays",
         "first_event_update", "end_update", "elapsed_intervals",
         "elapsed_seconds", "final_signed_residue", "scope", "confidence"],
        duration_rows)

    loop_rows = []
    loop_specs = [
        ("0x2E", 1, 0x674F, 0x6756, 0x6754, 480, 480, "YM sustained F2"),
        ("0x37", 1, 0x67FC, 0x6803, 0x6801, 15, 15, "YM sustained C0"),
        # POKEY-mode rests use (control & $7F) * 32, not the duration table:
        # REST $60 = 96*32 = 3072 units = 192 sweeps at tempo 16, and
        # REST $7D = 125*32 = 4000 units = 250 sweeps.  The prefix reaches the
        # backward jump after 192 + 250 + 250 = 692 sweeps; the loop target
        # itself is first reached at 442.
        ("0x05", 1, 0x6838, 0x6858, 0x6854, 692, 250, "POKEY chip-test channel 1"),
        ("0x05", 2, 0x686D, 0x688D, 0x6889, 692, 250, "POKEY chip-test channel 2"),
        ("0x04", 8, 0x6985, 0x69A7, 0x69A5, 1500, 480, "YM chip-test sustained C5"),
    ]
    for command, channel, start, site, target, expected_prefix, expected_period, scope in loop_specs:
        trace = trace_duration(rom, start, device_hz, max_loop_jumps=3)
        boundaries = trace["loop_boundaries"]
        if len(boundaries) != 4 or trace["loop_jumps"] != 3:
            raise SystemExit(f"loop-bound mismatch at ${site:04X}: {trace}")
        periods = [b - a for a, b in zip(boundaries, boundaries[1:])]
        if (boundaries[0] - trace["first_update"] != expected_prefix
                or periods != [expected_period] * 3 or trace["residue"] != -16):
            raise SystemExit(f"loop timing mismatch at ${site:04X}: {trace}")
        loop_rows.append([
            command, channel, f"0x{start:04X}", f"0x{site:04X}",
            f"0x{target:04X}", trace["loop_jumps"], trace["notes"], trace["rests"],
            trace["first_update"], boundaries[0], boundaries[0] - trace["first_update"],
            ";".join(str(p) for p in periods), boundaries[-1] - trace["first_update"],
            (boundaries[-1] - trace["first_update"]) / device_hz,
            trace["residue"], scope,
            "Verified bounded loop/timer arithmetic and clock-to-seconds conversion"])
    write_csv(
        args.loop_csv,
        ["command", "chain_channel", "sequence_start", "loop_site", "loop_target",
         "executed_back_edges", "notes", "rests", "first_event_update",
         "first_loop_boundary_update", "prefix_intervals", "period_intervals",
         "bounded_elapsed_intervals", "bounded_elapsed_seconds",
         "final_signed_residue", "scope", "confidence"],
        loop_rows)

    # Secondary-timer articulation begins on the sweep after note decode.
    # $04 ch1: allocation subtraction leaves -16, duration[4]=960.
    normal_primary = -16 + rom.read_word(0x5C5F + 2 * 4)
    normal_secondary = normal_primary - 2 * 16
    normal_off = normal_secondary // 16 + 1
    normal_next = normal_primary // 16 + 1
    # $40 ch1 common body: SET_TEMPO $68 -> 26; preceding duration[9] rest
    # advances 18 sweeps and leaves primary residue -4 before duration[10].
    divided_residue = (-16 + rom.read_word(0x5C5F + 2 * 9)) - 18 * 26
    divided_primary = divided_residue + rom.read_word(0x5C5F + 2 * 10)
    divided_pre_shift = divided_primary - 2 * 26
    divided_secondary = divided_pre_shift >> 1
    divided_off = divided_secondary // 26 + 1
    divided_next = divided_primary // 26 + 1
    if ((normal_primary, normal_secondary, normal_off, normal_next),
            (divided_residue, divided_primary, divided_pre_shift,
             divided_secondary, divided_off, divided_next)) != \
            ((944, 912, 58, 60), (-4, 236, 184, 92, 4, 10)):
        raise SystemExit("secondary articulation derivation changed unexpectedly")
    articulation_rows = [
        ["0x04", 1, "0x6917", "normal", 16, 1, normal_primary,
         normal_secondary, normal_off, normal_off / device_hz, normal_next,
         normal_next - normal_off,
         "non-sustain control $04; secondary=primary-2*tempo",
         "Verified timer arithmetic and clock-to-seconds conversion"],
        ["0x40", 1, "0x743E", "divided", 26, 19, divided_primary,
         divided_secondary, divided_off, divided_off / device_hz, divided_next,
         divided_next - divided_off,
         "control $1A; secondary=(primary-2*tempo)/2 after preceding rest residue -4",
         "Verified timer arithmetic and clock-to-seconds conversion"],
        ["0x04", 8, "0x69A5", "sustain_rearm", 16, 1501, "", "high=$7F",
         "", "", 480, "no expiry before rearm",
         "control $81 keeps secondary high at $7F; loop replays every 480 sweeps",
         "Verified branch/rearm relation and clock-to-seconds conversion"],
    ]
    write_csv(
        args.articulation_csv,
        ["command", "channel", "note_address", "case", "tempo",
         "onset_update", "primary_after_duration", "secondary_initial",
         "off_intervals", "audible_seconds", "next_or_rearm_intervals",
         "silent_gap_intervals", "derivation", "confidence"],
        articulation_rows)

    # Validate representative dormant POKEY dividers against the MAME clock.
    cents = []
    for note in range(1, 98):
        divider = rom.read_word(0x5A35 + 2 * note)
        target = 440.0 * 2.0 ** (((note + 11) - 69) / 12.0)
        actual = cpu_hz / (2.0 * (divider + 7.0))
        cents.append(1200.0 * math.log2(actual / target))
    if min(cents) < -3.88 or max(cents) > 2.23:
        raise SystemExit("unexpected POKEY divider error range")

    print(
        f"timing: {len(clock_rows)} clock rows, {len(cycle_rows)} cycle paths, "
        f"{len(duration_rows)} duration traces, {len(loop_rows)} loop traces, "
        f"{len(articulation_rows)} articulation traces, "
        f"IRQ {irq_hz:.9f} Hz, device {device_hz:.9f} Hz, "
        f"POKEY prefix error {min(cents):.3f}..{max(cents):.3f} cents")


if __name__ == "__main__":
    main()
