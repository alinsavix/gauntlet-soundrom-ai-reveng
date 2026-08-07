#!/usr/bin/env python3
"""Verify the operator sound test's selectable command domain.

This joins the main-CPU OS selector at $229C-$27AA to the sound ROM's
command-$06 direct reply.  The test uses that reply as an exclusive selector
limit and writes the selected command directly to the sound latch at $2786.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path


OS_SHA1 = "6e0d2026317e4a050fd79aac24ee0a644bf5a836"
SOUND_SHA1 = "a9795393899fd20ce23ef98811195b9406485ed0"
SOUND_BASE = 0x4000
VALIDATION_TABLE = 0x5D0F
HANDLER_TYPE_TABLE = 0x5DEA
PARAMETER_TABLE = 0x5EC5
DIRECT_QUERY_TABLE = 0x5FA2
TARGET_COMMANDS = (0xD6, 0xD8, 0xD9, 0xDA)


OS_ANCHORS = {
    # Send direct query $06 and preserve its reply as the selector's exclusive
    # upper bound at $904012.
    0x242C: bytes.fromhex(
        "48 78 00 06 4e b9 00 00 27 ac 33 c0 00 90 40 12"
    ),
    # The selector starts at command $04.
    0x25B2: bytes.fromhex("7a 0f 76 04"),
    # Increment/decrement rules: skip $03/$06/$07 and wrap at the bound.
    0x25FC: bytes.fromhex(
        "52 43 70 03 b0 43 66 04 76 04 60 40 "
        "70 06 b0 43 66 04 76 08 60 36 "
        "b6 79 00 90 40 12 6d 2e 76 01 60 2a "
        "08 04 00 06 67 24 53 43 70 01 b0 43 6f 0a "
        "36 39 00 90 40 12 53 43 60 12 "
        "70 03 b0 43 66 04 76 02 60 08 "
        "70 07 b0 43 66 02 76 05"
    ),
    # Test-input bit 1 emits the selected word in D3 to the sound latch.
    0x2780: bytes.fromhex("08 04 00 01 67 06 33 c3 00 80 31 70"),
}


def sound_offset(address: int) -> int:
    return address - SOUND_BASE


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def next_command(command: int, limit: int) -> int:
    command += 1
    if command == 3:
        command = 4
    if command == 6:
        command = 8
    if command >= limit:
        command = 1
    return command


def previous_command(command: int, limit: int) -> int:
    command -= 1
    if command < 1:
        command = limit - 1
    if command == 3:
        command = 2
    if command == 7:
        command = 5
    return command


def cycle(start: int, step, limit: int) -> list[int]:
    values = [start]
    command = step(start, limit)
    while command != start:
        if command in values:
            raise SystemExit("operator selector entered a secondary cycle")
        values.append(command)
        command = step(command, limit)
    return values


def verify_sound_limit(sound_rom: bytes) -> int:
    validation = sound_rom[sound_offset(VALIDATION_TABLE) + 6]
    if validation != 1:
        raise SystemExit(f"command $06 validation code is {validation:#x}, expected 1")

    pointer_offset = sound_offset(DIRECT_QUERY_TABLE) + validation * 2
    target_minus_one = int.from_bytes(sound_rom[pointer_offset:pointer_offset + 2], "little")
    handler = target_minus_one + 1
    if handler != 0x44B8:
        raise SystemExit(f"command $06 direct handler is ${handler:04X}, expected $44B8")

    handler_bytes = sound_rom[sound_offset(handler):sound_offset(handler) + 5]
    if handler_bytes[:2] != bytes.fromhex("a9 db") or handler_bytes[2:] != bytes.fromhex("20 c8 44"):
        raise SystemExit("command $06 handler no longer loads $DB and calls $44C8")
    return handler_bytes[1]


def rows(sound_rom: bytes, limit: int, reachable: set[int]) -> list[dict[str, str]]:
    effects = {
        0xD6: "set mixer effects level 0 (off)",
        0xD8: "set mixer effects level 2 (medium)",
        0xD9: "set mixer effects level 3 (full)",
        0xDA: "queue $55 reply byte",
    }
    result = []
    for command in TARGET_COMMANDS:
        result.append({
            "command": f"0x{command:02X}",
            "handler_type": str(sound_rom[sound_offset(HANDLER_TYPE_TABLE) + command]),
            "parameter": f"0x{sound_rom[sound_offset(PARAMETER_TABLE) + command]:02X}",
            "effect": effects[command],
            "selector_limit": f"0x{limit:02X} (exclusive)",
            "selector_reachable": str(command in reachable),
            "emitter": "main-CPU OS run_sound_test",
            "emit_site": "0x2786",
            "emit_condition": "operator presses test-input bit 1 while command is selected",
            "usage_scope": "operator self-test; does not by itself establish normal gameplay use",
            "confidence": "Verified",
        })
    return result


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--os-rom", type=Path, default=root / "row9.bin")
    parser.add_argument("--sound-rom", type=Path, default=root / "soundrom.bin")
    parser.add_argument(
        "--csv",
        type=Path,
        default=root / "docs/generated/operator_sound_test_command_catalog.csv",
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    os_rom = args.os_rom.read_bytes()
    sound_rom = args.sound_rom.read_bytes()
    if len(os_rom) != 0x10000 or sha1(os_rom) != OS_SHA1:
        raise SystemExit("row9.bin is not the documented 64 KiB OS ROM")
    if len(sound_rom) != 0xC000 or sha1(sound_rom) != SOUND_SHA1:
        raise SystemExit("soundrom.bin is not the documented 48 KiB sound ROM")
    for address, expected in OS_ANCHORS.items():
        actual = os_rom[address:address + len(expected)]
        if actual != expected:
            raise SystemExit(f"OS selector anchor mismatch at 0x{address:04X}")

    limit = verify_sound_limit(sound_rom)
    forward = cycle(4, next_command, limit)
    reverse = cycle(4, previous_command, limit)
    expected = {1, 2, 4, 5, *range(8, 0xDB)}
    if set(forward) != expected or set(reverse) != expected:
        raise SystemExit("operator selector domain does not match $01,$02,$04,$05,$08-$DA")
    if len(forward) != 215 or len(reverse) != 215:
        raise SystemExit("operator selector should expose exactly 215 commands")

    output_rows = rows(sound_rom, limit, set(forward))
    if not all(row["selector_reachable"] == "True" for row in output_rows):
        raise SystemExit("one or more target control commands is not selector-reachable")

    if args.check:
        with args.csv.open(newline="") as stream:
            existing = list(csv.DictReader(stream))
        if existing != output_rows:
            raise SystemExit(f"{args.csv.name} is stale; regenerate it")
        action = "verified"
    else:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(output_rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(output_rows)
        action = "wrote"

    commands = ",".join(row["command"] for row in output_rows)
    print(
        f"operator sound test: {action} {len(output_rows)} target rows; "
        f"$06 reply=${limit:02X}; selector domain=215 commands; "
        f"targets reachable={commands}; emit site=0x2786"
    )


if __name__ == "__main__":
    main()
