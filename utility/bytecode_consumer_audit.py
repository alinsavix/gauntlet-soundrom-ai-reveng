#!/usr/bin/env python3
"""Generate consumer-led opcode and support-format catalogs."""

import argparse
import csv
from pathlib import Path

import gauntlet_disasm as gd

ROM_BASE = 0x4000


def hx(v, width=4):
    return f"0x{v:0{width}X}"


ANCHORS = {
    0x5029: bytes.fromhex("c9 bb 90 07 a9 ff 9d 28 02 18 60"),
    0x5039: bytes.fromhex("bd 7c 50 48 bd 7b 50 48"),
    0x5047: bytes.fromhex("bd 46 02 18 69 01"),
    0x5154: bytes.fromhex("9d 26 04 20 47 50 9d 44 04 38 60"),
    0x515F: bytes.fromhex("9d 62 04 20 47 50 9d 80 04 38 60"),
    0x5320: bytes.fromhex("85 11 bd aa 07 d0 05"),
    0x5444: bytes.fromhex("84 11 c9 16 b0 61 c9 06"),
    0x5535: bytes.fromhex("85 11 bd 28 02 c9 fe d0 08"),
    0x558F: bytes.fromhex("a4 17 f0 01 60 ac 1d 08"),
    0x55A3: bytes.fromhex("18 69 1c 9d cc 03 bd f8 04 85 0f 69 00 9d ea 03"),
    0x5613: bytes.fromhex("18 69 24 85 0e 08 20 47 50"),
    0x5655: bytes.fromhex("18 69 29 85 0e 08 20 47 50"),
    0x5676: bytes.fromhex("a5 17 d0 0f 20 f0 4f"),
    0x5715: bytes.fromhex("ac 1d 08 c0 02 f0 01 60"),
    0x5755: bytes.fromhex("bc 28 02 c0 fe d0 02 18 60"),
    0x578A: bytes.fromhex("b9 90 57 4c 15 57"),
    0x4C58: bytes.fromhex("a0 08 bd 9e 04 99 26 08 88 b1 0e 99 26 08 88 d0 f8"),
    0x4F0E: bytes.fromhex("ad 2f 08 4a 4a aa bd 5b 5c 8d 13 08"),
    0x4F3E: bytes.fromhex("a4 0c b9 27 08 4a 4a 4a 4a 8d 13 08"),
}


SPECIAL = {
    0x86: ("both", "replace frequency-envelope pointer with 16-bit operand"),
    0x87: ("both", "replace volume-envelope pointer with 16-bit operand"),
    0x8D: ("both", "push return record and enter 16-bit subsequence"),
    0x99: ("both", "replace sequence pointer with 16-bit operand"),
    0x9D: ("YM2151", "load 28-byte YM register image plus live TL-transform fields"),
    0x9E: ("YM2151", "read five-byte auxiliary block at operand base+$24"),
    0x9F: ("YM2151", "read one-byte auxiliary value at operand base+$29"),
    0xA1: ("YM2151", "negate signed operand and apply it to algorithm-selected carrier total levels"),
    0xB2: ("both", "classify variable into general register"),
}


FORMATS = [
    (0x507B, 0x50F0, 2, 59, "opcode target-minus-one table", "$5029", "opcode $80-$BA", "Verified"),
    (0x5790, 0x579F, 1, 16, "signed YM carrier-TL attenuation table", "$578A", "low nibble of SET_VOLUME reload argument", "Verified"),
    (None, None, 42, None, "YM instrument record at opcode-$9D operand base", "$5535;$558F;$4C16;$4EFF;$5613;$5655", "147 exhaustive bytecode references; 39 distinct bases on the 55-record grid", "Verified structure; offset $1C purpose Unknown"),
    (None, None, 5, None, "YM auxiliary block at operand base+$24", "$5613", "14 exhaustive references; 9 distinct bases", "Verified"),
    (None, None, 1, None, "YM register byte at operand base+$29", "$5655", "2 exhaustive references", "Verified"),
    (None, None, 2, None, "volume-envelope records", "$4954-$4B44", "13 distinct bytecode pointers", "Verified grammar; bounds vary"),
    (None, None, 3, None, "frequency-envelope records", "$46CC-$4A8F", "13 distinct bytecode pointers", "Verified grammar; bounds vary"),
]


# Instruction-aligned semantic ownership for the dispatcher and every handler
# implementation not already owned by the channel-engine catalog.  Entry lists
# name opcode entries; ranges also include their shared internal tails/helpers.
RANGES = [
    (0x5029, 0x5046, "opcode/end dispatch", "$5029", "classify note/opcode/end byte; synthesize target-minus-one return", "Verified"),
    (0x5047, 0x5058, "sequence advance/read helper", "$5047", "advance 16-bit stream pointer and fetch next operand", "Verified"),
    (0x5059, 0x506E, "active-command chain search", "$5059", "interrupt-atomic physical-list search and type dispatch", "Verified"),
    (0x506F, 0x507A, "command-type dispatcher", "$506F", "synthesize handler-table return using shared parameter", "Verified"),
    (0x50F1, 0x514A, "timer/repeat reset and stream rewind", "$50F1", "clear timers; arbitrate repeat identity; rewind sequence pointer by two", "Verified"),
    (0x514B, 0x5153, "repeat-counter setter", "$514B", "store repeat value and clear active repeat state", "Verified"),
    (0x5154, 0x5169, "envelope-pointer setters", "$5154;$515F", "load volume/frequency 16-bit pointers through $5047", "Verified"),
    (0x516A, 0x51B2, "tempo/volume/transpose handlers", "$516A;$5173;$517A;$5192;$51AA;$51AE", "set/add scalar state with POKEY/YM and fade-state gates", "Verified"),
    (0x51B3, 0x51E5, "distortion/control/vibrato handlers", "$51B3;$51B7;$51CB;$51E2", "chip-dependent control-bit transforms and vibrato-depth store", "Verified"),
    (0x51E6, 0x5270, "sequence context push/pop", "$51E6;$5214;$523F", "allocate/free context records; save/restore pointers and repeat state", "Verified"),
    (0x5271, 0x529D, "variable/ramp loader", "$5271", "load signed ramp, integer/fraction accumulator, and rate state", "Verified"),
    (0x529E, 0x531F, "general-register ALU and shifts", "$529E;$52AA;$52B4;$52BA;$52C0;$52C6;$52F3", "mutate $07AA and publish shadow $07C8", "Verified"),
    (0x5320, 0x5374, "computed conditional target-table handlers", "$5320;$5347", "index inline little-endian target table; optional register increment", "Verified"),
    (0x5375, 0x53FA, "workspace store and YM application", "$5375;$53C2", "store register to indexed workspace or route it to chip state", "Verified"),
    (0x53FB, 0x5443, "classifier-backed compare/branch handlers", "$53FB;$5401;$5404;$5410;$5417;$541E;$5425", "classify state; update shadow or consume/take 16-bit branch", "Verified"),
    (0x5444, 0x54B0, "variable classifier", "$5444", "map index to chip/channel/global/workspace/random state while preserving Y", "Verified"),
    (0x54B1, 0x5514, "chip-mode/output/fade handlers", "$54B1;$54CC;$54E5;$54F4;$54F9", "switch POKEY/YM state, queue output, or initialize fadeout", "Verified"),
    (0x5515, 0x5523, "sequence-pointer replacement", "$5515", "load absolute 16-bit stream target", "Verified"),
    (0x5524, 0x5534, "speech-command bridge", "$5524", "priority-check type-11 metadata and invoke speech loader", "Verified"),
    (0x5535, 0x558E, "YM voice state preload", "$5535", "load record pointer, channel fields, and four base operator TL bytes", "Verified"),
    (0x558F, 0x5612, "YM voice register-image loader", "$558F", "winner-only 28-byte voice image write and live shadow update", "Verified"),
    (0x5613, 0x5675, "YM auxiliary loaders", "$5613;$5655", "load record offsets $24-$29 into YM registers/shadow", "Verified"),
    (0x5676, 0x5689, "indirect YM register writer", "$5676", "winner-gated ready/write/shadow primitive", "Verified"),
    (0x568A, 0x5714, "YM/frequency modifier handlers", "$568A;$56AF;$56CB;$56DC;$5703;$5711", "saturating volume/frequency transforms and loop control", "Verified"),
    (0x5715, 0x5754, "YM carrier-TL delta application", "$5715", "negate signed input and saturating-add it to algorithm-selected carrier TL bases", "Verified"),
    (0x5755, 0x578F, "YM volume-base reload", "$5755", "reload four operator TL bases and tail-apply signed carrier attenuation", "Verified"),
]


CALLABLE_CONTRACTS = [
    (0x5029, "callable_indirect_dispatcher", "opcode/end dispatcher",
     "A=current stream byte; X=logical channel; Y=current stream offset; ($06) is stream base",
     "end >=$BB: mark $0228,X=$FF and CLC/RTS; opcode: increment Y, push target-minus-one, load first operand, SEC/RTS into handler",
     "A,Y,P;$11;X restored before synthetic dispatch", "($06),Y;$507B-$50F0", "$0228,X;$11;stack",
     "IRQ channel-service context; CPU I flag already set", "all configured type-7 streams", "Verified"),
    (0x5047, "callable_subroutine", "advance/read sequence helper",
     "X=logical channel; Y=operand cursor; ($06) is current stream base",
     "RTS with A=next byte; Y incremented; C reports low-pointer wrap",
     "A,Y,P", "$0246-$0264,X;($06),Y", "$0246-$0264,X",
     "caller-governed; used from IRQ bytecode service", "configured opcode operand loaders", "Verified"),
    (0x5059, "tail_jump_entry", "active-command chain search and safe opcode apply",
     "X=index of physical-list head; $0830=target command; Y=opcode-table byte offset; $0831=operand",
     "RTS after no match or after every matching handler returns",
     "A,X,Y plus selected handler; caller P restored", "$07E6;$0228;$0830-$0831;$507B-$50F0", "selected handler effects;stack",
     "PHP/SEI protects full traversal and handler application; PLP restores caller P", "only dormant handler type 12 reaches this entry", "Verified"),
    (0x506F, "callable_indirect_dispatcher", "safe bytecode handler dispatcher",
     "X=matching logical channel; Y=even target-table byte offset; $0831=operand",
     "push target-minus-one and synthesize return into selected handler; selected handler returns to caller",
     "A,P plus selected handler;X/Y caller-dependent", "$507B-$50F0;$0831", "stack plus selected handler effects",
     "called inside $5059 interrupt-masked critical section", "only dormant handler type 12 reaches this entry", "Verified"),
    (0x5181, "callable_with_tail_exit", "apply signed channel-volume delta",
     "A=signed delta; X=logical channel",
     "POKEY: add to $0408,X and SEC/RTS; YM: tail $5715 carrier-TL application",
     "A,Y,P;$0E-$0F;$11;X preserved on YM tail", "$081D;$0408,X plus $5715 inputs", "$0408,X or algorithm-selected YM TL bases",
     "IRQ channel-service context; CPU I flag already set", "active fade/ramp path; also ADD_VOLUME shared suffix", "Verified"),
    (0x5444, "callable_subroutine", "variable classifier",
     "A=classifier index; X=logical channel; Y=caller value to preserve",
     "RTS with classified byte in A and original Y restored; YM index 0 deliberately preserves incoming A",
     "A,P;$11;X/Y preserved", "$081D;$0408;$049E;$05CA;$05E8;$18-$27;$180A;$07C8", "$11 scratch",
     "IRQ bytecode-service context; CPU I flag already set", "all configured compare/classify opcodes", "Verified"),
    (0x558F, "callable_subroutine", "YM voice register-image loader",
     "X=logical channel with voice pointer in $04DA/$04F8; $17=0 only for physical-list winner",
     "nonwinner/non-YM RTS unchanged; winner writes 28-byte image, restores X, SEC/RTS",
     "A,Y,P;$0C-$0F;$11;X preserved", "$17;$081D;$04DA-$04F8;28 bytes through ($0E);$083C", "$03CC/$03EA;YM $20/$40-$E0 banks;$083D shadows;$02 on timeout",
     "IRQ channel-service context; CPU I flag already set", "configured SET_VOICE operations; hardware writes only for YM winners", "Verified"),
    (0x5676, "callable_subroutine", "winner-gated indirect YM register writer",
     "X=YM register selector; ($0E),Y=next value; $17=0 only for winner",
     "suppressed RTS without consuming Y; winner waits, writes/shadows byte, increments Y, RTS",
     "A,Y,P;X preserved", "$17;($0E),Y;$1811", "$1810-$1811;$083D,X;$02 on timeout",
     "IRQ bytecode-service context; CPU I flag already set", "configured $9E/$9F YM auxiliary loaders", "Verified"),
    (0x5715, "tail_jump_entry", "YM carrier total-level delta application",
     "A=signed operand to negate; X=logical YM channel",
     "non-YM RTS; YM saturating-adds negated delta to carrier TL bases selected by algorithm and SEC/RTS",
     "A,Y,P;$0E-$0F;$11;X preserved", "$081D;$04BC,X;$57A0-$57A7;$0426/$0444/$0462/$0480", "$0426/$0444/$0462/$0480 carrier-selected entries",
     "IRQ bytecode-service context; CPU I flag already set", "31 configured opcode $A1 operations plus ADD_VOLUME/SET_VOLUME/fade tails", "Verified"),
    (0x5755, "tail_jump_entry", "YM operator-TL base reload",
     "A=SET_VOLUME low-nibble selector; X=logical channel with voice pointer",
     "fade status $FE: CLC/RTS; otherwise reload four base TLs and tail $5715 with signed attenuation table value",
     "A,Y,P;$0C;$0E-$0F;X preserved;stack balanced", "$0228;$04DA-$04F8;voice offsets 5/11/17/23;$5790-$579F", "$0426/$0444/$0462/$0480 plus $5715 effects",
     "IRQ bytecode-service context; CPU I flag already set", "YM SET_VOLUME and shared reload suffix", "Verified"),
]


def validate(rom):
    if len(rom) != 0xC000:
        raise SystemExit(f"expected 0xC000-byte ROM, got {len(rom):#x}")
    for addr, expected in ANCHORS.items():
        off = addr - ROM_BASE
        if rom[off:off + len(expected)] != expected:
            raise SystemExit(f"anchor mismatch at {hx(addr)}")
    for opcode in range(0x80, 0xBB):
        off = 0x507B - ROM_BASE + 2 * (opcode - 0x80)
        target = int.from_bytes(rom[off:off + 2], "little") + 1
        if not 0x4651 <= target <= 0x5774:
            raise SystemExit(f"invalid opcode target {hx(target)} for {hx(opcode, 2)}")
    code_addresses = set(range(0x5029, 0x507B)) | set(range(0x50F1, 0x5790))
    owned = set()
    for start, end, *_ in RANGES:
        current = set(range(start, end + 1))
        if owned & current:
            raise SystemExit(f"overlapping bytecode semantic range at {hx(start)}")
        owned |= current
    if owned != code_addresses:
        missing = sorted(code_addresses - owned)
        extra = sorted(owned - code_addresses)
        raise SystemExit(f"bytecode semantic coverage mismatch: missing={missing[:4]} extra={extra[:4]}")


def opcode_rows(rom):
    for opcode in range(0x80, 0xBB):
        off = 0x507B - ROM_BASE + 2 * (opcode - 0x80)
        target = int.from_bytes(rom[off:off + 2], "little") + 1
        name, args, _, _ = gd.OPCODES[opcode]
        chip, effect = SPECIAL.get(opcode, ("chip-dependent", "see canonical opcode semantics"))
        argument_bytes = "variable" if opcode in (0xAE, 0xAF) else args
        yield [hx(opcode, 2), hx(target), name, argument_bytes, chip, effect, "synthetic return from target-minus-one table; carry reports continuation", "Verified"]


OPERATOR_PARAMETERS = ("DT1/MUL", "TL", "KS/AR", "AMSEN/D1R", "DT2/D2R", "D1L/RR")
OPERATOR_LAYOUT = (("M1", 0x00), ("M2", 0x08), ("C1", 0x10), ("C2", 0x18))


def voice_bases(sequence_csv):
    references = []
    with sequence_csv.open(newline="") as f:
        for row in csv.DictReader(f):
            if row["mnemonic"] == "SET_VOICE":
                raw = bytes.fromhex(row["raw_hex"])
                references.append(raw[1] | (raw[2] << 8))
    bases = sorted(set(references))
    if len(references) != 147 or len(bases) != 39:
        raise SystemExit(
            f"expected 147 SET_VOICE references/39 bases, got {len(references)}/{len(bases)}")
    return bases


def voice_field_rows(rom, bases):
    roles = {
        0: ("channel", "FB/CON", "$20+channel; ROM sets RL later with OR $C0"),
        1: ("channel", "KC base", "$28+channel"),
        2: ("channel", "KF base", "$30+channel"),
        3: ("channel", "PMS/AMS", "$38+channel"),
        28: ("record", "skipped byte", "$4C16 stops before +$1C; no configured consumer found"),
        29: ("M1", "TL transform descriptor", "high/low nibble feed $72DC/$5B5B transforms"),
        30: ("M1->M2", "TL chain byte", "M1 correction source and M2 nonlinear-index seed"),
        31: ("M2", "TL transform descriptor", "high/low nibble feed $72DC/$5B5B transforms"),
        32: ("M2->C1", "TL chain byte", "M2 correction source and C1 nonlinear-index seed"),
        33: ("C1", "TL transform descriptor", "high/low nibble feed $72DC/$5B5B transforms"),
        34: ("C1->C2", "TL chain byte", "C1 correction source and C2 nonlinear-index seed"),
        35: ("C2", "TL transform descriptor", "high/low nibble feed $72DC/$5B5B transforms; dynamic volume is C2 correction"),
        36: ("$9E", "auxiliary register $18 value", "$5613 writes YM register $18"),
        37: ("$9E", "auxiliary register $19 value 1", "$5613 writes YM register $19"),
        38: ("$9E", "auxiliary register $19 value 2", "$5613 writes YM register $19"),
        39: ("$9E", "auxiliary register $1B value", "$5613 writes YM register $1B"),
        40: ("$9E", "auxiliary shadow byte", "$5613 stores $083E after writing YM register $01=$00"),
        41: ("$9F", "auxiliary register $0F value", "$5655 writes YM register $0F"),
    }
    for operator_index, (operator, slot) in enumerate(OPERATOR_LAYOUT):
        for parameter_index, parameter in enumerate(OPERATOR_PARAMETERS):
            offset = 4 + operator_index * 6 + parameter_index
            bank = 0x40 + parameter_index * 0x20
            roles[offset] = (
                operator, parameter,
                f"${bank:02X}+channel+${slot:02X}")
    for offset in range(42):
        scope, role, consumer = roles[offset]
        values = sorted({rom[base - ROM_BASE + offset] for base in bases})
        yield [
            f"0x{offset:02X}", scope, role, consumer,
            len(values), " ".join(f"{value:02X}" for value in values),
            len(bases),
            ("Verified" if offset < 28 else
             "Verified skipped; original purpose Unknown" if offset == 28 else
             "Verified $4C16/$4EFF consumer formula" if offset < 36 else
             "Verified $5613/$5655 consumer"),
        ]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("rom", type=Path)
    p.add_argument("--opcode-csv", required=True, type=Path)
    p.add_argument("--format-csv", required=True, type=Path)
    p.add_argument("--sequence-csv", required=True, type=Path)
    p.add_argument("--ym-voice-field-csv", required=True, type=Path)
    p.add_argument("--range-csv", required=True, type=Path)
    p.add_argument("--callable-csv", required=True, type=Path)
    args = p.parse_args()
    rom = args.rom.read_bytes()
    validate(rom)
    args.opcode_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.opcode_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["opcode", "handler", "name", "argument_bytes", "chip_scope", "consumer_effect", "return_contract", "confidence"])
        w.writerows(opcode_rows(rom))
    with args.format_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["start", "end_inclusive", "record_width", "count", "role", "consumers", "index_domain", "confidence"])
        for start, end, *rest in FORMATS:
            w.writerow(["" if start is None else hx(start), "" if end is None else hx(end), *rest])
    bases = voice_bases(args.sequence_csv)
    with args.ym_voice_field_csv.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["offset", "scope", "role", "register_or_formula", "distinct_value_count", "configured_values_hex", "configured_voice_bases", "confidence"])
        w.writerows(voice_field_rows(rom, bases))
    with args.range_csv.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["start", "end_inclusive", "role", "entries", "consumer_effect", "confidence"])
        for start, end, *rest in RANGES:
            w.writerow([hx(start), hx(end), *rest])
    with args.callable_csv.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["address", "entry_kind", "role", "entry_contract", "exits", "clobbers", "reads", "writes", "interrupt_safety", "configured_reachability", "confidence"])
        for address, *rest in CALLABLE_CONTRACTS:
            w.writerow([hx(address), *rest])
    print(f"bytecode consumers: 59 opcodes, {len(FORMATS)} formats, "
          f"42 YM instrument fields, {len(RANGES)} semantic ranges, "
          f"{len(CALLABLE_CONTRACTS)} callable contracts, {len(ANCHORS)} anchors validated")


if __name__ == "__main__":
    main()
