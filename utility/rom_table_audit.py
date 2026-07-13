#!/usr/bin/env python3
"""Generate ROM-grounded catalogs for Gauntlet II sound command data.

This tool intentionally analyzes data tables and TMS5220 bitstreams only.  It
does not disassemble 6502 code and therefore remains useful when r2 analysis is
unavailable or paused.
"""

import argparse
import csv
from collections import Counter, defaultdict, deque
from dataclasses import dataclass

import gauntlet_disasm as gd


@dataclass
class LpcStats:
    frames: int = 0
    silent: int = 0
    stop: int = 0
    repeat: int = 0
    unvoiced: int = 0
    voiced: int = 0
    bits: int = 0
    truncated: bool = False


class BitReader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def read(self, count):
        if self.pos + count > len(self.data) * 8:
            raise EOFError
        value = 0
        for _ in range(count):
            byte = self.data[self.pos // 8]
            bit = (byte >> (self.pos % 8)) & 1
            value = (value << 1) | bit
            self.pos += 1
        return value


def parse_lpc(data):
    """Count variable-length TMS5220 frames using the ROM's LSB-first order."""
    br = BitReader(data)
    out = LpcStats()
    try:
        while br.pos + 4 <= len(data) * 8:
            energy = br.read(4)
            out.frames += 1
            if energy == 0:
                out.silent += 1
                continue
            if energy == 15:
                out.stop += 1
                break
            repeat = br.read(1)
            pitch = br.read(6)
            if repeat:
                out.repeat += 1
                continue
            for bits in gd.TMS5220_KBITS[:4]:
                br.read(bits)
            if pitch == 0:
                out.unvoiced += 1
                continue
            for bits in gd.TMS5220_KBITS[4:]:
                br.read(bits)
            out.voiced += 1
    except EOFError:
        out.truncated = True
    out.bits = br.pos
    return out


def type11_commands(rom):
    for cmd in range(gd.MAX_COMMANDS):
        if rom.read_byte(gd.DISPATCH_TYPE_TABLE + cmd) != 11:
            continue
        param = rom.read_byte(gd.DISPATCH_PARAM_TABLE + cmd)
        index = rom.read_byte(gd.SPEECH_INDEX_TABLE + param)
        ptr = rom.read_word(gd.SPEECH_PTR_TABLE + index * 2)
        length = rom.read_word(gd.SPEECH_LEN_TABLE + index * 2)
        flags = rom.read_byte(gd.SPEECH_FLAGS_TABLE + param)
        priority = rom.read_byte(gd.SPEECH_PRIORITY_TABLE + param)
        data = rom.read_bytes(ptr, length)
        stats = parse_lpc(data)
        yield {
            "command": cmd,
            "parameter": param,
            "index": index,
            "pointer": ptr,
            "length": length,
            "end_exclusive": ptr + length,
            "flags": flags,
            "priority": priority,
            "frames": stats.frames,
            "silent_frames": stats.silent,
            "stop_frames": stats.stop,
            "repeat_frames": stats.repeat,
            "unvoiced_frames": stats.unvoiced,
            "voiced_frames": stats.voiced,
            "parsed_bits": stats.bits,
            "truncated_frame": stats.truncated,
        }


def type7_records(rom):
    """Expand every type-7 command's linked record chain."""
    for cmd in range(gd.MAX_COMMANDS):
        if rom.read_byte(gd.DISPATCH_TYPE_TABLE + cmd) != 7:
            continue
        param = rom.read_byte(gd.DISPATCH_PARAM_TABLE + cmd)
        start = rom.read_byte(gd.SFX_OFFSET_TABLE + param)
        flags = rom.read_byte(gd.SFX_FLAGS_TABLE + param)
        current = start
        seen = set()
        position = 0
        while current not in seen and position < 182:
            seen.add(current)
            next_offset = rom.read_byte(gd.SFX_NEXT_TABLE + current)
            channel = rom.read_byte(gd.SFX_CHANNEL_TABLE + current)
            yield {
                "command": cmd,
                "parameter": param,
                "command_flags": flags,
                "chain_position": position,
                "offset": current,
                "priority": rom.read_byte(gd.SFX_PRIORITY_TABLE + current),
                "hardware_channel": channel,
                "chip": "POKEY" if channel <= 3 else "YM2151",
                "sequence_pointer": rom.read_word(gd.SFX_SEQ_PTR_TABLE + current * 2),
                "next_offset": next_offset,
            }
            position += 1
            if next_offset == 0:
                break
            current = next_offset


def command_rows(rom, names):
    """Resolve all command-table rows into a compact machine-readable index."""
    for cmd in range(gd.MAX_COMMANDS):
        info = gd.resolve_command(rom, cmd)
        subsystem, description = names.get(cmd, ("", ""))
        direct_nmi = {3: "input_event_status", 6: "echo_db", 7: "error_heartbeat"}.get(cmd, "")
        chips = ""
        chain_count = 0
        if info.channels:
            chain_count = len(info.channels)
            chip_set = {
                "POKEY" if channel.channel <= 3 else "YM2151"
                for channel in info.channels
            }
            chips = "+".join(sorted(chip_set))
        yield {
            "command_hex": f"0x{cmd:02X}",
            "command": cmd,
            "handler_type": info.handler_type,
            "handler_name": info.type_name,
            "parameter": info.param,
            "direct_nmi_query": direct_nmi,
            "subsystem_annotation": subsystem,
            "description": description,
            "chain_records": chain_count,
            "chips": chips,
            "primary_offset_or_speech_index": info.offset,
            "primary_pointer": info.seq_ptr,
            "speech_length": info.seq_len,
        }


TYPE7_START = 0x6559
TYPE7_END = 0x8380
TYPE7_SEQ_MIN = 0x6569
YM_RECORD_START = 0x69D6
YM_RECORD_WIDTH = 42
YM_RECORD_COUNT = 55
YM_RECORD_END = YM_RECORD_START + YM_RECORD_WIDTH * YM_RECORD_COUNT - 1

ROM_REGION_ROWS = [
    {"start": "0x4000", "end_inclusive": "0x5C5E", "size": 7263, "name": "program_and_embedded_tables", "classification": "mixed", "confidence": "partial"},
    {"start": "0x5C5F", "end_inclusive": "0x5C7E", "size": 32, "name": "duration_table", "classification": "data", "confidence": "verified"},
    {"start": "0x5C7F", "end_inclusive": "0x5C8E", "size": 16, "name": "fade_rate_shift_control_table", "classification": "data", "confidence": "verified"},
    {"start": "0x5C8F", "end_inclusive": "0x5D0E", "size": 128, "name": "pokey_volume_shape_table_8x16", "classification": "data", "confidence": "verified"},
    {"start": "0x5D0F", "end_inclusive": "0x5DE9", "size": 219, "name": "nmi_validation_table", "classification": "data", "confidence": "verified"},
    {"start": "0x5DEA", "end_inclusive": "0x5EC4", "size": 219, "name": "command_handler_type_table", "classification": "data", "confidence": "verified"},
    {"start": "0x5EC5", "end_inclusive": "0x5F9F", "size": 219, "name": "command_parameter_table", "classification": "data", "confidence": "verified"},
    {"start": "0x5FA0", "end_inclusive": "0x5FA7", "size": 8, "name": "type3_and_nmi_target_table", "classification": "data", "confidence": "verified"},
    {"start": "0x5FA8", "end_inclusive": "0x5FE5", "size": 62, "name": "type7_start_offsets", "classification": "data", "confidence": "verified"},
    {"start": "0x5FE6", "end_inclusive": "0x6023", "size": 62, "name": "type7_command_flags", "classification": "data", "confidence": "verified"},
    {"start": "0x6024", "end_inclusive": "0x60D9", "size": 182, "name": "type7_priorities", "classification": "data", "confidence": "verified"},
    {"start": "0x60DA", "end_inclusive": "0x618F", "size": 182, "name": "type7_hardware_channels", "classification": "data", "confidence": "verified"},
    {"start": "0x6190", "end_inclusive": "0x62FB", "size": 364, "name": "type7_sequence_pointers", "classification": "data", "confidence": "verified"},
    {"start": "0x62FC", "end_inclusive": "0x63B1", "size": 182, "name": "type7_next_links", "classification": "data", "confidence": "verified"},
    {"start": "0x63B2", "end_inclusive": "0x643E", "size": 141, "name": "speech_indices", "classification": "data", "confidence": "verified"},
    {"start": "0x643F", "end_inclusive": "0x64CB", "size": 141, "name": "speech_clock_flags", "classification": "data", "confidence": "verified"},
    {"start": "0x64CC", "end_inclusive": "0x6558", "size": 141, "name": "speech_priorities", "classification": "data", "confidence": "verified"},
    {"start": "0x6559", "end_inclusive": "0x8380", "size": 7720, "name": "type7_bytecode_and_support_data", "classification": "mixed", "confidence": "partial"},
    {"start": "0x8381", "end_inclusive": "0x843E", "size": 190, "name": "board_control_code", "classification": "code", "confidence": "verified"},
    {"start": "0x843F", "end_inclusive": "0x8446", "size": 8, "name": "nmi_direct_handlers", "classification": "code", "confidence": "verified"},
    {"start": "0x8447", "end_inclusive": "0x8448", "size": 2, "name": "unreferenced_gap", "classification": "unknown", "confidence": "strong_inference"},
    {"start": "0x8449", "end_inclusive": "0x85C2", "size": 378, "name": "speech_pointer_table", "classification": "data", "confidence": "verified"},
    {"start": "0x85C3", "end_inclusive": "0x873C", "size": 378, "name": "speech_length_table", "classification": "data", "confidence": "verified"},
    {"start": "0x873D", "end_inclusive": "0xFECC", "size": 30608, "name": "tms5220_lpc_corpus", "classification": "data", "confidence": "verified"},
    {"start": "0xFECD", "end_inclusive": "0xFECD", "size": 1, "name": "unindexed_trailing_ff", "classification": "unknown", "confidence": "strong_inference"},
    {"start": "0xFECE", "end_inclusive": "0xFFF5", "size": 296, "name": "zero_padding", "classification": "unused", "confidence": "strong_inference"},
    {"start": "0xFFF6", "end_inclusive": "0xFFF9", "size": 4, "name": "pre_vector_bytes", "classification": "unknown", "confidence": "strong_inference"},
    {"start": "0xFFFA", "end_inclusive": "0xFFFF", "size": 6, "name": "interrupt_vectors", "classification": "data", "confidence": "verified"},
]


def _hex_bytes(values):
    return " ".join(f"{value:02X}" for value in values)


def type7_sequence_map(rom, seeds, forced_taken=None):
    """Statically traverse type-7 bytecode from table and control-flow seeds.

    The work queue and visited set live in this Python client.  Calls expose
    both their target and return continuation.  The $AE/$AF handlers index a
    packed target table by the masked register value, so traversal exposes
    every table target and terminates that basic block.  Fixed conditional
    branches expose target and fallthrough.  This deliberately does not
    emulate variable values.
    """
    forced_taken = set(forced_taken or ())
    queue = deque()
    queued = set()
    seed_sources = defaultdict(set)
    for source, address in seeds:
        if address not in queued:
            queue.append(address)
            queued.add(address)
        seed_sources[address].add(source)

    rows = []
    visited = set()
    byte_owners = defaultdict(set)
    edges = []
    errors = []

    def enqueue(source, target, kind):
        edges.append({"source": source, "target": target, "kind": kind})
        if not TYPE7_START <= target <= TYPE7_END:
            errors.append((source, f"{kind}_target_out_of_region", target))
            return
        if target not in queued:
            queue.append(target)
            queued.add(target)

    while queue:
        block = queue.popleft()
        address = block
        while TYPE7_START <= address <= TYPE7_END:
            if address in visited:
                if address != block:
                    edges.append({"source": block, "target": address,
                                  "kind": "fallthrough_shared"})
                break
            visited.add(address)
            opcode = rom.read_byte(address)
            mnemonic = ""
            target = None
            computed_targets = []
            target_kind = ""
            terminal = False

            if opcode <= 0x7F:
                size = 2
                second = rom.read_byte(address + 1)
                mnemonic = "CHAIN" if second == 0 else ("REST" if opcode == 0 else "NOTE")
                terminal = second == 0
            elif opcode <= 0xBA:
                if opcode not in gd.OPCODES:
                    errors.append((address, "unknown_opcode", opcode))
                    size = 1
                    mnemonic = "UNKNOWN"
                    terminal = True
                else:
                    mnemonic, arg_count, _, _ = gd.OPCODES[opcode]
                    size = 1 + arg_count
                    if opcode in (0xAE, 0xAF):
                        if address < TYPE7_START + 2 or rom.read_byte(address - 2) != 0xAB:
                            errors.append((address, "computed_jump_without_preceding_reg_and", opcode))
                            terminal = True
                        else:
                            mask = rom.read_byte(address - 1)
                            if mask not in (0x00, 0x03, 0x0F):
                                errors.append((address, "unsupported_computed_jump_mask", mask))
                                terminal = True
                            size = 1 + 2 * (mask + 1)
                    args = [rom.read_byte(address + i) for i in range(1, size)]
                    if opcode in (0x8D, 0x99):
                        target = args[0] | (args[1] << 8)
                    elif opcode in (0xAE, 0xAF):
                        computed_targets = [
                            args[2 * i] | (args[2 * i + 1] << 8)
                            for i in range(len(args) // 2)
                        ]
                        target = computed_targets[0]
                    elif opcode in (0xB5, 0xB6, 0xB7, 0xB8):
                        target = args[1] | (args[2] << 8)
                    if opcode == 0x8D:
                        target_kind = "push_seq"
                    elif opcode == 0x99:
                        target_kind = "set_seq_ptr"
                        terminal = True
                    elif opcode in (0xAE, 0xAF):
                        target_kind = "conditional"
                        terminal = True
                    elif opcode in (0xB5, 0xB6, 0xB7, 0xB8):
                        target_kind = "conditional"
                        if address in forced_taken:
                            terminal = True
            else:
                size = 1
                mnemonic = "END"
                terminal = True

            if address + size - 1 > TYPE7_END:
                errors.append((address, "instruction_crosses_region", size))
                break
            raw = [rom.read_byte(address + i) for i in range(size)]
            for byte_address in range(address, address + size):
                byte_owners[byte_address].add(address)
            rows.append({
                "address": address,
                "end_inclusive": address + size - 1,
                "size": size,
                "raw_hex": _hex_bytes(raw),
                "opcode": opcode,
                "mnemonic": mnemonic,
                "target": "" if target is None else target,
                "target_kind": target_kind,
                "is_seed": address in seed_sources,
                "seed_sources": ";".join(sorted(seed_sources.get(address, ()))),
            })
            if computed_targets:
                for value, computed_target in enumerate(computed_targets):
                    enqueue(address, computed_target,
                            "conditional" if value == 0 else f"conditional_value_{value}")
            elif target is not None:
                enqueue(address, target, target_kind)
            if terminal:
                break
            address += size

    rows.sort(key=lambda row: row["address"])
    edges.sort(key=lambda row: (row["source"], row["target"], row["kind"]))
    return rows, edges, byte_owners, errors


def type7_conditional_feasibility(rom, sequence_rows, edge_rows):
    """Classify every reachable conditional edge from its register producer."""
    def pokey_random_values(size):
        mask = (1 << size) - 1
        lfsr = mask
        values = []
        for _ in range(mask):
            if size == 17:
                in8 = ((lfsr >> 8) & 1) ^ ((lfsr >> 13) & 1)
                incoming = lfsr & 1
                lfsr >>= 1
                lfsr = (lfsr & 0xFF7F) | (in8 << 7)
                lfsr = (incoming << 16) | lfsr
                values.append((lfsr >> 8) & 0xFF)
            else:
                incoming = (lfsr & 1) ^ ((lfsr >> 5) & 1)
                lfsr = (lfsr >> 1) | (incoming << 8)
                values.append(lfsr & 0xFF)
        return values

    random_domains = {size: pokey_random_values(size) for size in (9, 17)}
    by_end = {row["end_inclusive"]: row for row in sequence_rows}
    rows = []
    for edge in edge_rows:
        if edge["kind"] != "conditional":
            continue
        source = edge["source"]
        and_row = by_end.get(source - 1)
        if not and_row or and_row["opcode"] != 0xAB:
            raise ValueError(f"conditional ${source:04X} lacks preceding REG_AND")
        mask = bytes.fromhex(and_row["raw_hex"])[1]
        producer = by_end.get(and_row["address"] - 1)
        source_row = next(row for row in sequence_rows if row["address"] == source)
        raw = bytes.fromhex(source_row["raw_hex"])
        alternatives = [raw[i] | (raw[i + 1] << 8)
                        for i in range(3, len(raw), 2)]
        if mask == 0:
            result = "always_taken"
            zero_target_feasible = True
            nonzero_targets_feasible = False
            evidence = ("REG_AND $00 selects computed target-table entry zero "
                        "before COND_JUMP_REG_Z")
        elif (producer and producer["opcode"] == 0xB2 and
              bytes.fromhex(producer["raw_hex"])[1] == 0x05 and
              mask in (0x03, 0x0F)):
            if not all({value & mask for value in domain} == set(range(mask + 1))
                       for domain in random_domains.values()):
                raise ValueError(f"POKEY polynomial mask ${mask:02X} lacks a table index")
            result = "all_indices"
            zero_target_feasible = True
            nonzero_targets_feasible = True
            evidence = ("POKEY RANDOM classifier; supplied 9/17-bit polynomial "
                        f"domains reach every computed target-table index 0..{mask} "
                        f"under mask ${mask:02X}")
        else:
            result = "unresolved"
            zero_target_feasible = True
            nonzero_targets_feasible = True
            evidence = "register producer not statically resolved"
        rows.append({
            "source": source,
            "target": edge["target"],
            "alternative_targets": ";".join(f"0x{target:04X}" for target in alternatives),
            "register_and_address": and_row["address"],
            "mask": f"0x{mask:02X}",
            "result": result,
            "zero_target_feasible": zero_target_feasible,
            "nonzero_targets_feasible": nonzero_targets_feasible,
            "evidence": evidence,
            "confidence": "Verified" if result != "unresolved" else "Unknown",
        })
    return rows


def type7_data_references(rom, sequence_rows):
    """Collect explicit support-data operands without guessing record ends."""
    refs = []
    kinds = {
        0x86: ("frequency_envelope", "pointer", 3),
        0x87: ("volume_envelope", "pointer", 2),
        0x9D: ("ym2151_voice", "pointer", 28),
        # Both opcodes carry the same 16-bit instrument-base form as $9D.
        # Their consumers address base+$24..+$28 and base+$29 respectively.
        0x9E: ("ym2151_envelope_register_block", "base_plus_0x24", 5),
        0x9F: ("ym2151_register_block", "base_plus_0x29", 1),
    }
    for row in sequence_rows:
        opcode = row["opcode"]
        if opcode not in kinds:
            continue
        kind, storage, fixed_size = kinds[opcode]
        raw = bytes.fromhex(row["raw_hex"])
        if storage != "inline":
            base = raw[1] | (raw[2] << 8)
            if storage == "base_plus_0x24":
                target = base + 0x24
            elif storage == "base_plus_0x29":
                target = base + 0x29
            else:
                target = base
            referenced_end = (target + fixed_size - 1
                              if kind.startswith("ym2151_") else "")
            confidence = ("Verified" if kind.startswith("ym2151_")
                          else "Unknown")
        else:
            target = row["address"] + 1
            referenced_end = target + fixed_size - 1
            confidence = "Verified"
        refs.append({
            "instruction_address": row["address"],
            "opcode": opcode,
            "kind": kind,
            "storage": storage,
            "referenced_start": target,
            "referenced_end_inclusive": referenced_end,
            "fixed_size": fixed_size if referenced_end != "" else "",
            "operand_hex": _hex_bytes(raw[1:]),
            "confidence": confidence,
        })
    # Fresh bounded consumer disassembly establishes two-byte volume records,
    # three-byte frequency records, zero-filled terminators, and three-byte FF
    # loop controls.  Support objects may overlap, so only a terminator or the
    # next independently reached sequence instruction bounds an envelope.
    sequence_starts = sorted(row["address"] for row in sequence_rows)
    for ref in refs:
        if ref["kind"] not in ("frequency_envelope", "volume_envelope"):
            continue
        start = ref["referenced_start"]
        end_exclusive = next((address for address in sequence_starts
                              if address > start), TYPE7_END + 1)
        width = 3 if ref["kind"] == "frequency_envelope" else 2
        address = start
        terminated = False
        while address + width <= end_exclusive:
            count = rom.read_byte(address)
            record_width = 3 if count == 0xFF else width
            if address + record_width > end_exclusive:
                break
            values = [rom.read_byte(address + i) for i in range(record_width)]
            address += record_width
            if count != 0xFF and not any(values):
                terminated = True
                break
        end = address if terminated else end_exclusive
        ref["referenced_end_inclusive"] = end - 1
        ref["fixed_size"] = end - start
        ref["confidence"] = "Verified" if terminated else "Strong inference"
    return refs


def ym_voice_record_rows(data_refs):
    """Inventory the complete 55-by-42-byte YM instrument-record grid."""
    voice_refs = Counter()
    ym9e_refs = Counter()
    ym9f_refs = Counter()
    for ref in data_refs:
        if ref["kind"] == "ym2151_voice":
            voice_refs[ref["referenced_start"]] += 1
        elif ref["kind"] == "ym2151_envelope_register_block":
            ym9e_refs[ref["referenced_start"] - 0x24] += 1
        elif ref["kind"] == "ym2151_register_block":
            ym9f_refs[ref["referenced_start"] - 0x29] += 1
    if len(voice_refs) != 39 or sum(voice_refs.values()) != 147:
        raise ValueError(
            f"expected 147 voice refs/39 bases, got {sum(voice_refs.values())}/{len(voice_refs)}")
    all_bases = set(voice_refs) | set(ym9e_refs) | set(ym9f_refs)
    for base in all_bases:
        if not (YM_RECORD_START <= base <= YM_RECORD_END and
                (base - YM_RECORD_START) % YM_RECORD_WIDTH == 0):
            raise ValueError(f"YM base ${base:04X} is off the 42-byte record grid")
    rows = []
    for index in range(YM_RECORD_COUNT):
        start = YM_RECORD_START + index * YM_RECORD_WIDTH
        configured = start in voice_refs
        auxiliary_only = not configured and (start in ym9e_refs or start in ym9f_refs)
        rows.append({
            "index": index,
            "start": start,
            "end_inclusive": start + YM_RECORD_WIDTH - 1,
            "width": YM_RECORD_WIDTH,
            "voice_reference_count": voice_refs[start],
            "ym9e_reference_count": ym9e_refs[start],
            "ym9f_reference_count": ym9f_refs[start],
            "configured_voice": configured,
            "referenced_record": configured or auxiliary_only,
            "verified_live_tl_start": start + 29 if configured else "",
            "verified_live_tl_end_inclusive": start + 35 if configured else "",
            "classification": ("configured_instrument_record" if configured else
                               "auxiliary_only_instrument_record" if auxiliary_only else
                               "unreferenced_instrument_record"),
            "confidence": ("Verified record grid and configured consumers"
                           if configured or auxiliary_only else
                           "Verified grid; original provenance Unknown"),
        })
    return rows


def type7_residual_rows(rom, sequence_rows):
    """Classify bytes that are structurally present but never consumer-read."""
    rows = []
    owned = {address for row in sequence_rows
             for address in range(row["address"], row["end_inclusive"] + 1)}
    for row in sequence_rows:
        if row["opcode"] not in (0xAE, 0xAF) or row["size"] != 3:
            continue
        start = row["end_inclusive"] + 1
        values = rom.read_bytes(start, 2)
        if values != b"\x00\x00":
            continue
        rows.append({
            "start": start,
            "end_inclusive": start + 1,
            "size": 2,
            "raw_hex": _hex_bytes(values),
            "classification": "computed_jump_unreachable_zero_trailer",
            "consumer_evidence": (f"${row['address']:04X} $AE/$AF handler always replaces "
                                  "the sequence pointer with its sole table entry"),
            "confidence": "Verified unreachable; original purpose Unknown",
        })
    for row in sequence_rows:
        if row["opcode"] != 0x99:
            continue
        start = row["end_inclusive"] + 1
        values = rom.read_bytes(start, 2)
        if values != b"\x00\x00" or start in owned or start + 1 in owned:
            continue
        rows.append({
            "start": start,
            "end_inclusive": start + 1,
            "size": 2,
            "raw_hex": _hex_bytes(values),
            "classification": "set_seq_ptr_unreachable_zero_trailer",
            "consumer_evidence": (f"${row['address']:04X} SET_SEQ_PTR unconditionally "
                                  "replaces the sequence pointer"),
            "confidence": "Verified unreachable; original purpose Unknown",
        })
    standalone_start = 0x80DA
    standalone = rom.read_bytes(standalone_start, 9)
    expected = bytes.fromhex("9D 6A 6F 80 A0 00 01 00 00")
    if standalone != expected:
        raise ValueError("standalone sequence candidate anchor mismatch")
    rows.append({
        "start": standalone_start,
        "end_inclusive": standalone_start + len(standalone) - 1,
        "size": len(standalone),
        "raw_hex": _hex_bytes(standalone),
        "classification": "unreferenced_sequence_candidate",
        "consumer_evidence": ("valid SET_VOICE/SET_TEMPO/REST/CHAIN grammar; no command, "
                              "record, call, jump, or computed-target reference"),
        "confidence": "Strong inference; original provenance Unknown",
    })
    return rows


def type7_envelope_rows(rom, data_refs, sequence_rows):
    """Describe each distinct envelope pointer and its bounded packed extent.

    The consumers establish two-byte volume records and three-byte frequency
    records.  A zero-filled record terminates; FF in the count byte introduces
    a three-byte loop control record.  Some ROM envelopes have no terminator
    before the next independently reached object, so their ends remain a
    strong inference rather than a verified consumer bound.
    """
    sequence_by_address = {row["address"]: row for row in sequence_rows}
    lifetime = defaultdict(lambda: {"events": 0, "unbounded": False})
    for ref in data_refs:
        kind = ref["kind"]
        if kind not in ("frequency_envelope", "volume_envelope"):
            continue
        address = ref["instruction_address"] + 3
        events = 0
        terminal = False
        for _ in range(4096):
            row = sequence_by_address.get(address)
            if row is None:
                break
            opcode = row["opcode"]
            if opcode <= 0x7F:
                if row["mnemonic"] == "CHAIN":
                    terminal = True
                    break
                events += 1
            if ((kind == "frequency_envelope" and opcode == 0x86) or
                    (kind == "volume_envelope" and opcode == 0x87)):
                terminal = True
                break
            if opcode == 0x99:
                lifetime[(kind, ref["referenced_start"])]["unbounded"] = True
                break
            address = row["end_inclusive"] + 1
        state = lifetime[(kind, ref["referenced_start"])]
        state["events"] = max(state["events"], events)

    def runtime_frequency_trace(start, end_inclusive, limit=1_000_000):
        """Trace frequency-envelope reads through a zero terminator.

        This is a direct state model of the frequency-envelope consumer at
        $4954/$49C5.  The initial record count is incremented once; later
        zero counts wrap through 256 decrements.  FF records use a persistent
        repeat counter and rewind the base pointer by their third byte.
        """
        base = start
        y = 2
        loop_count = 0
        initial = [rom.read_byte(start + i) for i in range(3)]
        if not any(initial):
            return {"cross_update": "", "stop_update": 0,
                    "read_end": start + 2}
        read_end = start + 2
        cross_update = ""
        countdown = (initial[0] + 1) & 0xFF
        for update in range(1, limit + 1):
            countdown = (countdown - 1) & 0xFF
            if countdown:
                continue
            while True:
                y = (y + 1) & 0xFF
                count_address = base + y
                countdown = rom.read_byte(count_address)
                y = (y + 1) & 0xFF
                read_addresses = [count_address]
                if countdown == 0xFF:
                    if loop_count:
                        loop_count = (loop_count - 1) & 0xFF
                        if not loop_count:
                            y = (y + 1) & 0xFF
                            read_end = max(read_end, *read_addresses)
                            if not cross_update and read_end > end_inclusive:
                                cross_update = update
                            continue
                    else:
                        loop_count = rom.read_byte(base + y)
                        read_addresses.append(base + y)
                    y = (y + 1) & 0xFF
                    rewind = rom.read_byte(base + y)
                    read_addresses.append(base + y)
                    read_end = max(read_end, *read_addresses)
                    if not cross_update and read_end > end_inclusive:
                        cross_update = update
                    base = (base - rewind) & 0xFFFF
                    continue
                value_addresses = [base + y, base + ((y + 1) & 0xFF)]
                read_addresses.extend(value_addresses)
                read_end = max(read_end, *read_addresses)
                if not cross_update and read_end > end_inclusive:
                    cross_update = update
                values = [rom.read_byte(address) for address in value_addresses]
                if not (countdown or any(values)):
                    return {"cross_update": cross_update,
                            "stop_update": update, "read_end": read_end}
                y = (y + 1) & 0xFF
                if y >= 0xF9:
                    base = (base + y - 1) & 0xFFFF
                    y = 1
                break
        return {"cross_update": cross_update, "stop_update": "",
                "read_end": read_end}

    rows = []
    seen = set()
    for ref in data_refs:
        kind = ref["kind"]
        start = ref["referenced_start"]
        if kind not in ("frequency_envelope", "volume_envelope") or (kind, start) in seen:
            continue
        seen.add((kind, start))
        end_exclusive = ref["referenced_end_inclusive"] + 1
        width = 3 if kind == "frequency_envelope" else 2
        address = start
        records = 0
        loop_records = 0
        terminator = False
        aligned = True
        while address < end_exclusive:
            count = rom.read_byte(address)
            record_width = 3 if count == 0xFF else width
            if address + record_width > end_exclusive:
                aligned = False
                break
            values = [rom.read_byte(address + i) for i in range(record_width)]
            records += 1
            if count == 0xFF:
                loop_records += 1
            elif not any(values):
                terminator = True
                address += record_width
                break
            address += record_width
        exact_end = address - 1 if terminator else end_exclusive - 1
        life = lifetime[(kind, start)]
        verified_read_end = ""
        if life["events"]:
            verified_read_end = start + width - 1
        cross_update = ""
        runtime_stop_update = ""
        runtime_read_end = ""
        if kind == "frequency_envelope" and life["unbounded"] and not terminator:
            trace = runtime_frequency_trace(start, exact_end)
            cross_update = trace["cross_update"]
            runtime_stop_update = trace["stop_update"]
            runtime_read_end = trace["read_end"]
            verified_read_end = runtime_read_end
        rows.append({
            "kind": kind,
            "start": start,
            "end_inclusive": exact_end,
            "size": exact_end - start + 1,
            "record_width": width,
            "records": records,
            "loop_records": loop_records,
            "terminator_found": terminator,
            "aligned_to_next_object": aligned and address == end_exclusive,
            "finite_sequence_events": life["events"],
            "runtime_unbounded": life["unbounded"],
            # Command $00 dispatches to $41E6, whose bounded listing clears
            # all channel-status and channel/list-link entries before device
            # reinitialization.  The three type-5 stop rows do not name $05.
            "verified_external_stop_command": "0x00" if life["unbounded"] else "",
            "named_stop_command": "",
            "equal_priority_replacement_command": "0x05" if life["unbounded"] else "",
            "candidate_end_cross_after_envelope_updates": cross_update,
            "runtime_zero_terminator_after_envelope_updates": runtime_stop_update,
            "runtime_read_end_inclusive": runtime_read_end,
            "verified_read_end_inclusive": verified_read_end,
            "confidence": "Verified" if terminator else "Strong inference",
        })
    rows.sort(key=lambda row: (row["start"], row["kind"]))
    return rows


def intervals_from_byte_classes(classes):
    rows = []
    start = TYPE7_START
    current = classes[start]
    for address in range(TYPE7_START + 1, TYPE7_END + 2):
        value = classes[address] if address <= TYPE7_END else None
        if value != current:
            rows.append({"start": start, "end_inclusive": address - 1,
                         "size": address - start, "classification": current})
            start = address
            current = value
    return rows


# Absolute/absolute-indexed 6502 data-access opcodes used for the mixed-region
# direct-xref candidate scan.  Candidate instruction alignment is validated by
# bounded r2 listings; raw byte matches alone are not evidence.
CPU_ABSOLUTE_DATA_OPS = {
    0x0D: "ORA", 0x1D: "ORA,X", 0x19: "ORA,Y", 0x2C: "BIT",
    0x2D: "AND", 0x3D: "AND,X", 0x39: "AND,Y", 0x4D: "EOR",
    0x5D: "EOR,X", 0x59: "EOR,Y", 0x6D: "ADC", 0x7D: "ADC,X",
    0x79: "ADC,Y", 0x8C: "STY", 0x8D: "STA", 0x8E: "STX",
    0x99: "STA,Y", 0x9D: "STA,X", 0xAC: "LDY", 0xAD: "LDA",
    0xAE: "LDX", 0xB9: "LDA,Y", 0xBC: "LDY,X", 0xBD: "LDA,X",
    0xBE: "LDX,Y", 0xCC: "CPY", 0xCD: "CMP", 0xCE: "DEC",
    0xD9: "CMP,Y", 0xDD: "CMP,X", 0xDE: "DEC,X", 0xEC: "CPX",
    0xED: "SBC", 0xEE: "INC", 0xF9: "SBC,Y", 0xFD: "SBC,X",
    0xFE: "INC,X", 0x0E: "ASL", 0x1E: "ASL,X", 0x2E: "ROL",
    0x3E: "ROL,X", 0x4E: "LSR", 0x5E: "LSR,X", 0x6E: "ROR",
    0x7E: "ROR,X",
}

# Fresh bounded listings verified these nine aligned instructions.  All other
# raw candidates are operand/data coincidences, documented in the audit CSV.
VERIFIED_MIXED_REGION_DIRECT_XREFS = {
    0x434D, 0x4353, 0x435A, 0x4360,
    0x4462, 0x4483, 0x448A, 0x4490,
    0x4F51,
}


def mixed_region_cpu_xref_audit(rom):
    rows = []
    for address in range(0x4000, 0x5C5F - 2):
        opcode = rom.read_byte(address)
        if opcode not in CPU_ABSOLUTE_DATA_OPS:
            continue
        target = rom.read_word(address + 1)
        if not TYPE7_START <= target <= TYPE7_END:
            continue
        verified = address in VERIFIED_MIXED_REGION_DIRECT_XREFS
        rows.append({
            "candidate_address": address,
            "mnemonic": CPU_ABSOLUTE_DATA_OPS[opcode],
            "encoded_target": target,
            "classification": ("verified_aligned_instruction" if verified
                               else "rejected_raw_byte_coincidence"),
            "evidence": ("bounded_r2_listing" if verified
                         else "not_an_instruction_start_in_bounded_listing"),
            "confidence": "Verified",
        })
    return rows


def mixed_region_indirect_xref_audit():
    """Catalog constructed pointer classes capable of reading the mixed region.

    The pointer provenance and consumers were verified in bounded listings;
    their concrete ROM targets are already exhaustively supplied by the type-7
    chain and data-reference catalogs.
    """
    return [
        {
            "kind": "sequence_bytecode",
            "scratch_pointer": "$06-$07",
            "pointer_source": "$0246/$0264 channel pointer loaded from $6190-$62FB",
            "consumer_group": "$4729/$47DA/$4915/$5043/$5056",
            "target_catalog": "type7_sequence_catalog.csv",
            "additional_unknown_bytes_found": 0,
            "confidence": "Verified",
        },
        {
            "kind": "frequency_envelope",
            "scratch_pointer": "$06-$07",
            "pointer_source": "$0462/$0480 loaded by opcode $86",
            "consumer_group": "$496D-$4A41",
            "target_catalog": "type7_data_reference_catalog.csv;type7_envelope_catalog.csv",
            "additional_unknown_bytes_found": 58,
            "confidence": "Verified",
        },
        {
            "kind": "volume_envelope",
            "scratch_pointer": "$06-$07",
            "pointer_source": "$0426/$0444 loaded by opcode $87",
            "consumer_group": "$4AAB-$4AFC",
            "target_catalog": "type7_data_reference_catalog.csv;type7_envelope_catalog.csv",
            "additional_unknown_bytes_found": 0,
            "confidence": "Verified",
        },
        {
            "kind": "ym2151_voice",
            "scratch_pointer": "$0E-$0F",
            "pointer_source": "$04DA/$04F8 loaded by opcode $9D",
            "consumer_group": "$5559-$55FA;$4C16;$4EFF",
            "target_catalog": "type7_data_reference_catalog.csv;ym_voice_record_catalog.csv",
            "additional_unknown_bytes_found": 273,
            "confidence": "Verified",
        },
        {
            "kind": "ym2151_auxiliary_blocks",
            "scratch_pointer": "$0E-$0F",
            "pointer_source": "opcode $9E base+$24 and opcode $9F base+$29",
            "consumer_group": "$5613-$5680",
            "target_catalog": "type7_data_reference_catalog.csv",
            "additional_unknown_bytes_found": 0,
            "confidence": "Verified",
        },
    ]


def write_catalog(path, rows):
    if not path or not rows:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("rom")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--index-csv")
    parser.add_argument("--type7-csv")
    parser.add_argument("--command-csv")
    parser.add_argument("--type7-sequence-csv")
    parser.add_argument("--type7-edge-csv")
    parser.add_argument("--type7-data-ref-csv")
    parser.add_argument("--type7-region-csv")
    parser.add_argument("--type7-envelope-csv")
    parser.add_argument("--type7-cpu-support-csv")
    parser.add_argument("--type7-cpu-xref-audit-csv")
    parser.add_argument("--type7-indirect-xref-audit-csv")
    parser.add_argument("--type7-conditional-feasibility-csv")
    parser.add_argument("--type7-feasible-sequence-csv")
    parser.add_argument("--ym-voice-record-csv")
    parser.add_argument("--type7-residual-csv")
    parser.add_argument("--region-summary-csv")
    parser.add_argument("--names-csv", default="docs/soundcmds.csv")
    args = parser.parse_args()

    rom = gd.GauntletROM(args.rom)
    rows = list(type11_commands(rom))
    with open(args.csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    unique_indices = {r["index"] for r in rows}
    unique_ranges = {(r["pointer"], r["length"]) for r in rows}
    print(f"type11_commands={len(rows)}")
    print(f"parameters={min(r['parameter'] for r in rows)}..{max(r['parameter'] for r in rows)}")
    print(f"unique_indices={len(unique_indices)} of 189")
    print(f"unique_payload_ranges={len(unique_ranges)}")
    print(f"payload_min=${min(r['pointer'] for r in rows):04X}")
    print(f"payload_max_end=${max(r['end_exclusive'] for r in rows):04X}")
    print(f"streams_with_stop={sum(r['stop_frames'] > 0 for r in rows)}")
    print(f"streams_truncated_mid_frame={sum(r['truncated_frame'] for r in rows)}")

    index_rows = []
    for index in range(189):
        ptr = rom.read_word(gd.SPEECH_PTR_TABLE + index * 2)
        length = rom.read_word(gd.SPEECH_LEN_TABLE + index * 2)
        stats = parse_lpc(rom.read_bytes(ptr, length))
        index_rows.append({
            "index": index,
            "pointer": ptr,
            "length": length,
            "end_exclusive": ptr + length,
            "used_by_command": index in unique_indices,
            "frames": stats.frames,
            "stop_frames": stats.stop,
            "truncated_frame": stats.truncated,
        })
    contiguous = all(
        index_rows[i]["end_exclusive"] == index_rows[i + 1]["pointer"]
        for i in range(len(index_rows) - 1)
    )
    print(f"all_index_payload_min=${min(r['pointer'] for r in index_rows):04X}")
    print(f"all_index_payload_max_end=${max(r['end_exclusive'] for r in index_rows):04X}")
    print(f"all_index_ranges_contiguous={contiguous}")
    print(f"unused_indices={sum(not r['used_by_command'] for r in index_rows)}")
    print(f"all_index_streams_with_stop={sum(r['stop_frames'] > 0 for r in index_rows)}")
    print(f"all_index_streams_truncated={sum(r['truncated_frame'] for r in index_rows)}")
    if args.index_csv:
        with open(args.index_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=index_rows[0].keys())
            writer.writeheader()
            writer.writerows(index_rows)
        print(f"index_csv={args.index_csv}")

    type7 = list(type7_records(rom))
    type7_commands = {r["command"] for r in type7}
    type7_params = {r["parameter"] for r in type7}
    type7_offsets = {r["offset"] for r in type7}
    type7_ptrs = {r["sequence_pointer"] for r in type7}
    print(f"type7_commands={len(type7_commands)}")
    print(f"type7_parameters={len(type7_params)}")
    print(f"type7_expanded_records={len(type7)}")
    print(f"type7_reachable_offsets={len(type7_offsets)} of 182")
    print(f"type7_unique_sequence_pointers={len(type7_ptrs)}")
    print(f"type7_pointer_min=${min(type7_ptrs):04X}")
    print(f"type7_pointer_max=${max(type7_ptrs):04X}")
    print(f"type7_pokey_records={sum(r['chip'] == 'POKEY' for r in type7)}")
    print(f"type7_ym2151_records={sum(r['chip'] == 'YM2151' for r in type7)}")
    if args.type7_csv:
        with open(args.type7_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=type7[0].keys())
            writer.writeheader()
            writer.writerows(type7)
        print(f"type7_csv={args.type7_csv}")

    sequence_seeds = [
        (f"record_{row['offset']}", row["sequence_pointer"])
        for row in type7
    ]
    sequence_rows, edge_rows, byte_owners, sequence_errors = type7_sequence_map(
        rom, sequence_seeds)
    conditional_rows = type7_conditional_feasibility(rom, sequence_rows, edge_rows)
    forced_taken = {row["source"] for row in conditional_rows
                    if row["result"] == "always_taken"}
    feasible_sequence_rows, feasible_edge_rows, feasible_byte_owners, feasible_errors = (
        type7_sequence_map(rom, sequence_seeds, forced_taken=forced_taken))
    data_refs = type7_data_references(rom, sequence_rows)
    ym_record_rows = ym_voice_record_rows(data_refs)
    residual_rows = type7_residual_rows(rom, sequence_rows)
    envelope_rows = type7_envelope_rows(rom, data_refs, sequence_rows)
    cpu_support_rows = [
        {
            "start": 0x6559,
            "end_inclusive": 0x655E,
            "size": 6,
            "kind": "handler_match_records",
            "consumer": "0x434D;0x4353;0x435A;0x4360;0x4462;0x4483;0x448A;0x4490",
            "index_domain": "reserved handlers; no selected command rows",
            "confidence": "Verified",
        },
        {
            "start": 0x72DC,
            "end_inclusive": 0x73DB,
            "size": 0x100,
            "kind": "ym_total_level_nonlinear_lookup",
            "consumer": "0x4F51",
            "index_domain": "Y=0x00..0xFF",
            "confidence": "Verified",
        },
    ]
    cpu_xref_rows = mixed_region_cpu_xref_audit(rom)
    indirect_xref_rows = mixed_region_indirect_xref_audit()
    class_sets = {address: {"unclassified_no_type7_reference"}
                  for address in range(TYPE7_START, TYPE7_END + 1)}
    # Two complete three-byte handler-match records precede the first support
    # pointer at $655F.  The explicit envelope reference provides the exclusive
    # bound, avoiding the old assumption that all bytes before $6569 matched.
    for address in range(0x6559, 0x655F):
        class_sets[address] = {"handler_match_records"}
    for support in cpu_support_rows:
        for address in range(support["start"], support["end_inclusive"] + 1):
            class_sets[address] = {support["kind"]}
    for record in ym_record_rows:
        classification = {
            "configured_instrument_record": "ym2151_voice_record_structural",
            "auxiliary_only_instrument_record": "ym2151_voice_record_auxiliary_only",
            "unreferenced_instrument_record": "ym2151_voice_record_unreferenced",
        }[record["classification"]]
        for address in range(record["start"], record["end_inclusive"] + 1):
            class_sets[address] = {classification}
        if record["configured_voice"]:
            for address in range(record["start"] + 29, record["start"] + 36):
                class_sets[address].add("ym2151_live_tl_verified_read")
    for address in byte_owners:
        class_sets[address] = {
            ("sequence_bytecode" if address in feasible_byte_owners
             else "sequence_bytecode_infeasible_fallthrough")
        }
    for residual in residual_rows:
        for address in range(residual["start"], residual["end_inclusive"] + 1):
            if class_sets[address] != {"unclassified_no_type7_reference"}:
                raise ValueError(f"residual overlaps classified byte ${address:04X}")
            class_sets[address] = {residual["classification"]}
    for ref in data_refs:
        if ref["storage"] == "inline" or ref["referenced_end_inclusive"] == "":
            continue
        for address in range(ref["referenced_start"], ref["referenced_end_inclusive"] + 1):
            if TYPE7_START <= address <= TYPE7_END:
                if class_sets[address] == {"unclassified_no_type7_reference"}:
                    class_sets[address].clear()
                classification = ref["kind"]
                if ref["confidence"] == "Strong inference":
                    classification += "_candidate_extent"
                class_sets[address].add(classification)
    for envelope in envelope_rows:
        read_end = envelope["verified_read_end_inclusive"]
        if read_end == "" or envelope["confidence"] == "Verified":
            continue
        for address in range(envelope["start"], read_end + 1):
            if TYPE7_START <= address <= TYPE7_END:
                class_sets[address].discard("unclassified_no_type7_reference")
                class_sets[address].add(envelope["kind"] + "_verified_read")
    classes = {address: "+".join(sorted(values))
               for address, values in class_sets.items()}
    region_rows = intervals_from_byte_classes(classes)
    write_catalog(args.type7_sequence_csv, sequence_rows)
    write_catalog(args.type7_edge_csv, edge_rows)
    write_catalog(args.type7_data_ref_csv, data_refs)
    write_catalog(args.type7_region_csv, region_rows)
    write_catalog(args.type7_envelope_csv, envelope_rows)
    write_catalog(args.type7_cpu_support_csv, cpu_support_rows)
    write_catalog(args.type7_cpu_xref_audit_csv, cpu_xref_rows)
    write_catalog(args.type7_indirect_xref_audit_csv, indirect_xref_rows)
    write_catalog(args.type7_conditional_feasibility_csv, conditional_rows)
    write_catalog(args.type7_feasible_sequence_csv, feasible_sequence_rows)
    write_catalog(args.ym_voice_record_csv, ym_record_rows)
    write_catalog(args.type7_residual_csv, residual_rows)
    write_catalog(args.region_summary_csv, ROM_REGION_ROWS)
    distinct_seeds = {address for _, address in sequence_seeds}
    print(f"type7_sequence_seed_pointers={len(distinct_seeds)}")
    print(f"type7_sequence_instructions={len(sequence_rows)}")
    print(f"type7_sequence_bytes={len(byte_owners)}")
    print(f"type7_sequence_edges={len(edge_rows)}")
    print(f"type7_sequence_errors={len(sequence_errors)}")
    edge_target_counts = Counter(e["target"] for e in edge_rows)
    print(f"type7_shared_edge_targets={sum(count > 1 for count in edge_target_counts.values())}")
    print(f"type7_data_references={len(data_refs)}")
    print(f"type7_distinct_envelopes={len(envelope_rows)}")
    print(f"type7_terminated_envelopes={sum(r['terminator_found'] for r in envelope_rows)}")
    print(f"type7_cpu_support_regions={len(cpu_support_rows)}")
    print(f"type7_cpu_xref_candidates={len(cpu_xref_rows)}")
    print(f"type7_cpu_xref_verified={sum(r['classification'].startswith('verified') for r in cpu_xref_rows)}")
    print(f"type7_indirect_xref_classes={len(indirect_xref_rows)}")
    print(f"type7_conditional_always_taken={sum(r['result'] == 'always_taken' for r in conditional_rows)}")
    print(f"type7_conditional_all_indices={sum(r['result'] == 'all_indices' for r in conditional_rows)}")
    print(f"type7_conditional_unresolved={sum(r['result'] == 'unresolved' for r in conditional_rows)}")
    print(f"type7_feasible_sequence_instructions={len(feasible_sequence_rows)}")
    print(f"type7_feasible_sequence_bytes={len(feasible_byte_owners)}")
    print(f"type7_infeasible_fallthrough_only_bytes={len(set(byte_owners) - set(feasible_byte_owners))}")
    print(f"ym_voice_records={len(ym_record_rows)}")
    print(f"ym_voice_configured_records={sum(r['configured_voice'] for r in ym_record_rows)}")
    print(f"type7_residual_regions={len(residual_rows)}")
    print(f"type7_unclassified_bytes={sum(r['size'] for r in region_rows if r['classification'] == 'unclassified_no_type7_reference')}")
    if feasible_errors:
        for error in feasible_errors[:20]:
            print(f"type7_feasible_sequence_error={error}")
    if sequence_errors:
        for error in sequence_errors[:20]:
            print(f"type7_sequence_error={error}")
    if args.command_csv:
        commands = list(command_rows(rom, gd.load_sound_names(args.names_csv)))
        with open(args.command_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=commands[0].keys())
            writer.writeheader()
            writer.writerows(commands)
        print(f"command_csv={args.command_csv}")
    print(f"csv={args.csv}")


if __name__ == "__main__":
    main()
