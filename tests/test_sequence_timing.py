import math
import os
import struct
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO

import gauntlet_disasm as gd


class SoundNameCsvTests(unittest.TestCase):
    def test_default_csv_is_resolved_beside_script(self):
        with tempfile.TemporaryDirectory() as directory:
            script_path = os.path.join(directory, "gauntlet_disasm.py")
            csv_path = os.path.join(directory, "soundcmds.csv")
            with open(csv_path, "w", encoding="utf-8") as csv_file:
                csv_file.write("cmd,subsystem,description\n")

            self.assertEqual(
                gd.resolve_sound_names_csv(script_path=script_path), csv_path)

    def test_missing_default_csv_emits_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            stderr = StringIO()
            with redirect_stderr(stderr):
                result = gd.resolve_sound_names_csv(
                    script_path=os.path.join(directory, "gauntlet_disasm.py"))

            self.assertIsNone(result)
            self.assertIn("Warning: default sound command CSV not found",
                          stderr.getvalue())

    def test_explicit_csv_overrides_default(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = os.path.join(directory, "custom.csv")
            with open(csv_path, "w", encoding="utf-8") as csv_file:
                csv_file.write("cmd,subsystem,description\n")

            self.assertEqual(gd.resolve_sound_names_csv(csv_path), csv_path)


class RomPathTests(unittest.TestCase):
    def test_default_rom_is_resolved_beside_script(self):
        script_path = os.path.join("somewhere", "gauntlet_disasm.py")
        expected = os.path.abspath(os.path.join("somewhere", "soundrom.bin"))
        self.assertEqual(
            gd.resolve_rom_path(script_path=script_path), expected)

    def test_explicit_rom_overrides_default(self):
        self.assertEqual(
            gd.resolve_rom_path("custom.bin"), os.path.abspath("custom.bin"))


class FakeROM:
    """Minimal CPU-addressed ROM used by sequence timing tests."""

    def __init__(self):
        self.data = bytearray(gd.ROM_SIZE)

    def set_bytes(self, addr, values):
        offset = addr - gd.ROM_BASE
        self.data[offset:offset + len(values)] = bytes(values)

    def set_word(self, addr, value):
        self.set_bytes(addr, (value & 0xFF, value >> 8))

    def read_byte(self, addr):
        return self.data[addr - gd.ROM_BASE]

    def read_word(self, addr):
        offset = addr - gd.ROM_BASE
        return self.data[offset] | (self.data[offset + 1] << 8)


class SequenceTimingTests(unittest.TestCase):
    def setUp(self):
        self.rom = FakeROM()
        # Duration-table index 3 ("quarter") = 1,600 timer units.  At the
        # allocation tempo of 16 this is exactly 100 sequence sweeps.
        self.rom.set_word(gd.DURATION_TABLE_ADDR + 3 * 2, 1600)

    def test_disassembly_switches_between_pokey_and_table_rules(self):
        self.rom.set_bytes(0x4000, (
            0x90, 0x00,       # SWITCH_POKEY
            0x00, 0x05,       # 5*32 = 160 units = 10 sweeps
            0x00, 0x87,       # bit 7 masked; 7*32 = 224 = 14 sweeps
            0x91, 0x00,       # SWITCH_YM2151
            0x31, 0x03,       # duration-table index 3 = 100 sweeps
            0x00, 0x00,
        ))

        instructions = gd.disassemble_sequence(self.rom, 0x4000)
        by_addr = {inst.addr: inst for inst in instructions
                   if not inst.is_marker}

        self.assertIn("POKEY 5*32", by_addr[0x4002].operands)
        self.assertIn("160 timer units", by_addr[0x4002].comment)
        self.assertIn("POKEY 7*32", by_addr[0x4004].operands)
        self.assertIn("bit 7 masked", by_addr[0x4004].comment)
        self.assertNotIn("sustain", by_addr[0x4004].comment)
        self.assertIn("quarter", by_addr[0x4008].operands)

        notes, seconds = gd.compute_channel_stats(self.rom, instructions)
        self.assertEqual(notes, 1)
        self.assertTrue(math.isclose(
            seconds, 124 / gd.SEQUENCE_SERVICE_HZ, rel_tol=1e-12))

        timeline = gd.build_channel_timeline(self.rom, instructions)
        self.assertEqual([event.dur_abbrev for event in timeline],
                         ["PK5", "PK7", "Q"])
        self.assertTrue(math.isclose(
            timeline[2].time, 24 / gd.SEQUENCE_SERVICE_HZ,
            rel_tol=1e-12))

    def test_duration_rule_is_replayed_inside_counted_repeats(self):
        self.rom.set_bytes(0x4000, (
            0x8E, 0x02,       # repeat body twice
            0x90, 0x00,
            0x00, 0x05,       # POKEY: 10 sweeps
            0x91, 0x00,
            0x31, 0x03,       # table: 100 sweeps
            0x8F, 0x00,
            0x00, 0x00,
        ))

        instructions = gd.disassemble_sequence(self.rom, 0x4000)
        notes, seconds = gd.compute_channel_stats(self.rom, instructions)
        timeline = gd.build_channel_timeline(self.rom, instructions)

        self.assertEqual(notes, 2)
        self.assertTrue(math.isclose(
            seconds, 220 / gd.SEQUENCE_SERVICE_HZ, rel_tol=1e-12))
        self.assertEqual([event.dur_abbrev for event in timeline],
                         ["PK5", "Q", "PK5", "Q"])

    def test_midi_uses_mode_aware_timeline_start_times(self):
        self.rom.set_bytes(0x4000, (
            0x90, 0x00,
            0x00, 0x05,       # 10 POKEY sweeps
            0x00, 0x87,       # 14 POKEY sweeps
            0x91, 0x00,
            0x31, 0x03,       # first MIDI note begins after 24 sweeps
            0x00, 0x00,
        ))
        instructions = gd.disassemble_sequence(self.rom, 0x4000)
        timeline = gd.build_channel_timeline(self.rom, instructions)

        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "timing.mid")
            gd.write_midi([timeline], path)
            with open(path, "rb") as midi_file:
                midi = midi_file.read()

        # Skip MThd and the tempo MTrk, then decode the first delta-time in
        # the channel track.  It belongs to the first (and only) Note On.
        track0_length = struct.unpack(">I", midi[18:22])[0]
        track1 = 22 + track0_length
        self.assertEqual(midi[track1:track1 + 4], b"MTrk")
        pos = track1 + 8
        delta = 0
        while True:
            byte = midi[pos]
            pos += 1
            delta = (delta << 7) | (byte & 0x7F)
            if not byte & 0x80:
                break

        expected_tick = int((24 / gd.SEQUENCE_SERVICE_HZ) * 960)
        self.assertEqual(delta, expected_tick)
        self.assertEqual(midi[pos] & 0xF0, 0x90)

    def test_duration_rule_persists_through_call_return_and_jump(self):
        self.rom.set_bytes(0x4000, (
            0x90, 0x00,             # POKEY rule
            0x8D, 0x10, 0x40,       # call $4010
            0x00, 0x05,             # still POKEY after return
            0x99, 0x20, 0x40,       # jump $4020
        ))
        self.rom.set_bytes(0x4010, (
            0x00, 0x87,             # POKEY in called segment
            0x00, 0x00,             # return
        ))
        self.rom.set_bytes(0x4020, (
            0x91, 0x00,             # table rule
            0x31, 0x03,
            0x00, 0x00,
        ))

        instructions = gd.disassemble_sequence(self.rom, 0x4000)
        timeline = gd.build_channel_timeline(self.rom, instructions)

        self.assertEqual([event.dur_abbrev for event in timeline],
                         ["PK7", "PK5", "Q"])
        notes, seconds = gd.compute_channel_stats(self.rom, instructions)
        self.assertEqual(notes, 1)
        self.assertTrue(math.isclose(
            seconds, 124 / gd.SEQUENCE_SERVICE_HZ, rel_tol=1e-12))

    def test_force_pokey_uses_duration_table_arm(self):
        self.rom.set_bytes(0x4000, (
            0x90, 0x00,
            0x9C, 0x00,       # historical FORCE_POKEY name; status bit 1 set
            0x00, 0x03,
            0x00, 0x00,
        ))

        instructions = gd.disassemble_sequence(self.rom, 0x4000)
        event = next(inst for inst in instructions
                     if inst.mnemonic == "REST")
        self.assertIn("quarter", event.operands)

        _, seconds = gd.compute_channel_stats(self.rom, instructions)
        self.assertTrue(math.isclose(
            seconds, 100 / gd.SEQUENCE_SERVICE_HZ, rel_tol=1e-12))

    def test_raw_midstream_decode_accepts_an_initial_pokey_rule(self):
        self.rom.set_bytes(0x4000, (
            0x00, 0x05,
            0x00, 0x00,
        ))

        instructions = gd.disassemble_sequence(
            self.rom, 0x4000,
            initial_duration_rule=gd.DURATION_RULE_POKEY)
        event = next(inst for inst in instructions
                     if inst.mnemonic == "REST")
        self.assertIn("POKEY 5*32", event.operands)

        _, seconds = gd.compute_channel_stats(
            self.rom, instructions,
            initial_duration_rule=gd.DURATION_RULE_POKEY)
        self.assertTrue(math.isclose(
            seconds, 10 / gd.SEQUENCE_SERVICE_HZ, rel_tol=1e-12))

    def test_audio_interpreter_uses_pokey_counter_durations(self):
        self.rom.set_bytes(0x4000, (
            0x90, 0x00,
            0x00, 0x05,
            0x00, 0x87,
            0x91, 0x00,
            0x00, 0x03,
            0x00, 0x00,
        ))

        interpreter = gd.SequenceInterpreter(self.rom)
        events = interpreter._interpret_sequence(
            0x4000, channel_id=0, hw_mode="POKEY", max_seconds=10.0)
        end_event = next(event for event in events if event[1] == "end")

        # The practical renderer uses a 120 Hz display/rendering clock.
        self.assertTrue(math.isclose(end_event[0], 124 / 120.0,
                                     rel_tol=1e-12))


if __name__ == "__main__":
    unittest.main()
