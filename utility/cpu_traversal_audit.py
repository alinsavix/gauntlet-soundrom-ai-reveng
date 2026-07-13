#!/usr/bin/env python3
"""Validate the bounded CPU traversal and derive its classified entry catalog."""

import argparse
import csv
import re


HEX_ADDRESS = re.compile(r"0x[0-9A-Fa-f]{4}")


def read_rows(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batches", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    batches = read_rows(args.batches)
    states = read_rows(args.state)
    if any(not 0 < int(row["instructions_reachable"]) <= 64 for row in batches):
        raise SystemExit("invalid batch size")
    if any(row["state"] == "queued" for row in states):
        raise SystemExit("traversal queue is not empty")

    entries = {}
    for row in states:
        address = int(row["address"], 16)
        if address in entries:
            raise SystemExit(f"duplicate state address: {row['address']}")
        entries[address] = {
            "address": f"0x{address:04X}",
            "entry_kind": row["entry_kind"],
            "source": row["source"],
            "classification_basis": "traversal_state",
            "confidence": "Verified",
        }

    incoming = {}
    for row in batches:
        for target in row["new_targets"].split(";"):
            if not HEX_ADDRESS.fullmatch(target):
                continue
            address = int(target, 16)
            incoming.setdefault(address, set()).add(row["root"])
    for address, sources in incoming.items():
        if address in entries:
            continue
        entries[address] = {
            "address": f"0x{address:04X}",
            "entry_kind": "internal_basic_block",
            "source": ";".join(sorted(sources)),
            "classification_basis": "direct_branch_or_fallthrough_target",
            "confidence": "Verified",
        }

    rows = [entries[address] for address in sorted(entries)]
    with open(args.output, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"batches={len(batches)}")
    print(f"state_entries={len(states)}")
    print(f"internal_labels={sum(r['entry_kind'] == 'internal_basic_block' for r in rows)}")
    print(f"classified_entries={len(rows)}")
    print(f"output={args.output}")


if __name__ == "__main__":
    main()
