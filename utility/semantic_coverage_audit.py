#!/usr/bin/env python3
"""Join semantic range catalogs against all known sound-ROM code islands."""

import argparse
import csv
from collections import defaultdict
from pathlib import Path


CODE_DOMAINS = ((0x4002, 0x5A30), (0x8381, 0x8446))
DATA_EXCLUSIONS = {
    (0x4633, 0x4650): "command_handler_target_table",
    (0x507B, 0x50F0): "bytecode_opcode_target_table",
    (0x5790, 0x57AF): "ym_tl_and_hardware_configuration_tables",
    (0x5874, 0x5893): "dummy_speech_payload",
    (0x83A4, 0x83AB): "board_input_field_masks",
}


def hx(value):
    return f"0x{value:04X}"


def read_ranges(path, label):
    with path.open(newline="") as f:
        for item in csv.DictReader(f):
            yield int(item["start"], 16), int(item["end_inclusive"], 16), label


def intervals(classes):
    addresses = sorted(classes)
    start = previous = addresses[0]
    value = classes[start]
    for address in addresses[1:]:
        if address != previous + 1 or classes[address] != value:
            yield start, previous, value
            start = address
            value = classes[address]
        previous = address
    yield start, previous, value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--initialization", required=True, type=Path)
    parser.add_argument("--control-plane", required=True, type=Path)
    parser.add_argument("--channel-engine", required=True, type=Path)
    parser.add_argument("--support-staging", required=True, type=Path)
    parser.add_argument("--bytecode-engine", required=True, type=Path)
    parser.add_argument("--physical-output", required=True, type=Path)
    parser.add_argument("--nmi-protocol", required=True, type=Path)
    parser.add_argument("--speech-lifecycle", required=True, type=Path)
    parser.add_argument("--board-control", required=True, type=Path)
    parser.add_argument("--csv", required=True, type=Path)
    args = parser.parse_args()

    sources = [
        (args.initialization, "initialization_main"),
        (args.control_plane, "control_plane"),
        (args.channel_engine, "channel_engine"),
        (args.support_staging, "support_staging"),
        (args.bytecode_engine, "bytecode_engine"),
        (args.physical_output, "physical_output"),
        (args.nmi_protocol, "nmi_protocol"),
        (args.speech_lifecycle, "speech_lifecycle"),
        (args.board_control, "board_control"),
    ]
    owners = defaultdict(set)
    for path, label in sources:
        for start, end, owner in read_ranges(path, label):
            for address in range(start, end + 1):
                owners[address].add(owner)

    classes = {}
    for domain_start, domain_end in CODE_DOMAINS:
        for address in range(domain_start, domain_end + 1):
            exclusion = next((name for (start, end), name in DATA_EXCLUSIONS.items()
                              if start <= address <= end), None)
            if exclusion:
                classes[address] = ("known_data_exclusion", exclusion)
            elif owners[address]:
                classes[address] = ("semantic_owned", ";".join(sorted(owners[address])))
            else:
                classes[address] = ("unowned_executable", "")

    output = []
    for start, end, (classification, owner) in intervals(classes):
        output.append({
            "start": hx(start), "end_inclusive": hx(end), "size": end - start + 1,
            "classification": classification, "owners_or_data": owner,
            "next_action": ("none" if classification != "unowned_executable" else
                            "add bounded semantic range catalog"),
        })
    gaps = [(int(row["start"], 16), int(row["end_inclusive"], 16))
            for row in output if row["classification"] == "unowned_executable"]
    expected_gaps = []
    if gaps != expected_gaps:
        raise SystemExit(f"semantic gap set changed: {[(hx(a), hx(b)) for a, b in gaps]}")
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)
    gap_bytes = sum(end - start + 1 for start, end in gaps)
    owned_bytes = sum(row["size"] for row in output
                      if row["classification"] == "semantic_owned")
    print(f"semantic coverage: owned={owned_bytes} bytes, gaps={gap_bytes} bytes/"
          f"{len(gaps)} ranges, data exclusions={len(DATA_EXCLUSIONS)}")


if __name__ == "__main__":
    main()
