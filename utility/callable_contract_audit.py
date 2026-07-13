#!/usr/bin/env python3
"""Join every externally meaningful CPU entry to an explicit semantic contract."""

import argparse
import csv
from collections import Counter
from pathlib import Path


SELECTED_KINDS = {
    "tail_jump_entry", "callable_subroutine", "vector_entry",
    "table_dispatch_entry", "list_follow_entry", "callable_with_tail_exits",
    "callable_with_tail_exit", "callable_and_tail_jump_entry",
    "callable_indirect_dispatcher", "nmi_indirect_dispatcher",
}


def read_csv(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def entry_text(row):
    direct = row.get("entry_contract", "")
    if direct:
        return direct
    incoming = row.get("incoming", "")
    assumptions = row.get("entry_assumptions", "")
    return "; ".join(part for part in (incoming, assumptions) if part)


def interrupt_context(label, address):
    if label == "initialization_main":
        return "RESET/diagnostic/main context; interrupt state is part of the entry contract"
    if label == "control_plane":
        if 0x4187 <= address <= 0x41E5:
            return "IRQ context; CPU I flag set; architectural registers restored by IRQ shell"
        if 0x44A8 <= address <= 0x44DD:
            return "NMI direct-query context; selected path restores interrupted state before RTI"
        if address < 0x432E:
            return "caller-governed reset/IRQ helper; shared mutations are serialized by enclosing caller"
        return "main-loop command context; IRQ may preempt except during explicit PHP/SEI critical sections"
    if label in {"channel_engine", "support_staging", "physical_output"}:
        return "IRQ audio-service context; CPU I flag set"
    if label == "speech_lifecycle":
        return "IRQ service or main-command context; queue mutations use explicit PHP/SEI serialization"
    if label == "board_control":
        return ("NMI direct-query context; interrupted state restored by common NMI tail" if address >= 0x843F
                else "IRQ board-service context; CPU I flag set")
    if label == "reserved_handler":
        return "configured dormant; hypothetical main-loop handler context; routine-local atomicity is catalogued"
    return "caller-governed; see explicit supplemental contract"


def rich_contract(row, label, source):
    return {
        "contract_catalog": label,
        "contract_entry": row["start"],
        "role": row.get("role", row.get("phase", "")),
        "entry_contract": entry_text(row),
        "exits": row.get("exits", row.get("exit", "")),
        "clobbers": row.get("clobbers", ""),
        "reads": row.get("reads", ""),
        "writes": row.get("writes", ""),
        "interrupt_safety": row.get("interrupt_safety", "") or interrupt_context(label, int(row["start"], 16)),
        "configured_reachability": row.get("configured_reachability", "") or f"verified CPU entry source: {source}",
        "contract_confidence": row.get("confidence", ""),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cpu-entry", required=True, type=Path)
    p.add_argument("--semantic-coverage", required=True, type=Path)
    p.add_argument("--initialization", required=True, type=Path)
    p.add_argument("--control-plane", required=True, type=Path)
    p.add_argument("--channel-engine", required=True, type=Path)
    p.add_argument("--support-staging", required=True, type=Path)
    p.add_argument("--physical-output", required=True, type=Path)
    p.add_argument("--speech-lifecycle", required=True, type=Path)
    p.add_argument("--board-control", required=True, type=Path)
    p.add_argument("--reserved-handler", required=True, type=Path)
    p.add_argument("--bytecode-callable", required=True, type=Path)
    p.add_argument("--nmi-entry", required=True, type=Path)
    p.add_argument("--csv", required=True, type=Path)
    args = p.parse_args()

    cpu_rows = [row for row in read_csv(args.cpu_entry) if row["entry_kind"] in SELECTED_KINDS]
    if len(cpu_rows) != 61:
        raise SystemExit(f"expected 61 contract-requiring CPU entries, got {len(cpu_rows)}")

    coverage = read_csv(args.semantic_coverage)
    contracts = {}
    rich_sources = [
        (args.initialization, "initialization_main"),
        (args.control_plane, "control_plane"),
        (args.channel_engine, "channel_engine"),
        (args.support_staging, "support_staging"),
        (args.physical_output, "physical_output"),
        (args.speech_lifecycle, "speech_lifecycle"),
        (args.board_control, "board_control"),
    ]
    sources_by_address = {int(row["address"], 16): row["source"] for row in cpu_rows}
    for path, label in rich_sources:
        for row in read_csv(path):
            address = int(row["start"], 16)
            contracts[address] = rich_contract(row, label, sources_by_address.get(address, "catalog range"))

    # Reserved rows are more precise than combined control-plane ranges.
    for row in read_csv(args.reserved_handler):
        address = int(row["entry"], 16)
        contracts[address] = {
            "contract_catalog": "reserved_handler", "contract_entry": row["entry"],
            "role": row["semantic_role"], "entry_contract": row["input_contract"],
            "exits": row["exit"], "clobbers": "A,X,Y,P as implied by exact semantic row",
            "reads": row["reads"], "writes": row["writes_or_effect"],
            "interrupt_safety": interrupt_context("reserved_handler", address),
            "configured_reachability": row["configured_status"],
            "contract_confidence": row["confidence"],
        }

    # Standalone contracts close entries nested inside coarse bytecode/NMI ranges.
    for path, label in ((args.bytecode_callable, "bytecode_callable"),
                        (args.nmi_entry, "nmi_entry")):
        for row in read_csv(path):
            address = int(row["address"], 16)
            contracts[address] = {
                "contract_catalog": label, "contract_entry": row["address"],
                "role": row["role"], "entry_contract": row["entry_contract"],
                "exits": row["exits"], "clobbers": row["clobbers"],
                "reads": row["reads"], "writes": row["writes"],
                "interrupt_safety": row["interrupt_safety"],
                "configured_reachability": row["configured_reachability"],
                "contract_confidence": row["confidence"],
            }
            cpu = next((item for item in cpu_rows if int(item["address"], 16) == address), None)
            if cpu is None or cpu["entry_kind"] != row["entry_kind"]:
                raise SystemExit(f"supplemental entry-kind mismatch at {row['address']}")

    output = []
    missing = []
    for cpu in cpu_rows:
        address = int(cpu["address"], 16)
        owner = next((row["owners_or_data"] for row in coverage
                      if int(row["start"], 16) <= address <= int(row["end_inclusive"], 16)
                      and row["classification"] == "semantic_owned"), "")
        contract = contracts.get(address)
        if not contract:
            missing.append(cpu["address"])
            continue
        required = ("role", "entry_contract", "exits", "clobbers", "reads", "writes",
                    "interrupt_safety", "configured_reachability", "contract_confidence")
        empty = [field for field in required if not contract[field]]
        if empty:
            raise SystemExit(f"empty contract fields at {cpu['address']}: {empty}")
        if not owner:
            raise SystemExit(f"no semantic owner for {cpu['address']}")
        output.append({
            "address": cpu["address"], "entry_kind": cpu["entry_kind"],
            "entry_source": cpu["source"], "semantic_owner": owner,
            **contract, "status": "complete",
        })
    if missing:
        raise SystemExit(f"entries without explicit contracts: {','.join(missing)}")

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)
    counts = Counter(row["entry_kind"] for row in output)
    print(f"callable contracts: {len(output)} complete entries, 0 missing; "
          f"{len(counts)} entry kinds, {len(set(row['contract_catalog'] for row in output))} contract catalogs")


if __name__ == "__main__":
    main()
