# Gauntlet II Sound CPU ROM — Canonical Documentation

This directory is the canonical technical reference for the 48 KiB Gauntlet II
arcade sound-CPU ROM (`soundrom.bin`). It replaces the old practice of layering
corrections into `REPORT.md` and `REPORT_SUMMARY.md`.

## When two sources disagree

"Canonical" means these documents are the place a claim is argued in full. It
does **not** mean they win an argument by rank. Everything here is a derived view
of a binary: so are the CSVs under `generated/`, so is the book under `book/`,
and so is any script in `utility/`. When two of them disagree, do not pick the
more authoritative-looking one — **work out which is wrong and correct it.**

The ROM decides. Find the code that produces or consumes the value and read it;
`09_analysis_method.md` describes the discipline. Two worked examples are on
record. In both, a generated catalog disagreed with a direct execution of the
ROM, and in both the catalog's script had a state assumption wrong: the POKEY
duration rule (`06_sequence_engine.md`, "Two duration rules") and the
volume-shape row selector (`04_subsystems.md`). Each was fixed in the generator
and the catalog regenerated. A "Verified" confidence column certifies the
evidence a script was shown, not the script's model of the ROM.

Where a disagreement genuinely cannot be settled from the ROM, label it and say
so where it appears rather than choosing a side. Corrected claims keep a
**Contradicted** note instead of being deleted, so the same wrong reading is not
rediscovered later.

## Document map

1. [Hardware](01_hardware.md)
2. [CPU memory map](02_memory_map.md)
3. [ROM structure](03_rom_structure.md)
4. [Subsystems and control flow](04_subsystems.md)
5. [Data reference](05_data_reference.md)
6. [Sequence engine](06_sequence_engine.md)
7. [Function index](07_function_index.md)
8. [Command reference](08_command_reference.md)
9. [Analysis and reproduction method](09_analysis_method.md)
10. [Known issues and research backlog](10_known_issues.md)

The current operational priority and new-context handoff are maintained in
[Consumer-led analysis handoff](NEXT_STEPS.md).

Machine-readable catalogs are under [`generated/`](generated/README.md).

## Diagram guide

The behavioral diagrams are embedded beside the prose they summarize:

- [System, boot/NMI, Type-7, chip-output, speech, and board-control
  flows](04_subsystems.md)
- [Sequence interpreter cycle and bytecode control flow](06_sequence_engine.md)
- [IRQ device-service cadence](01_hardware.md#clock-tree-and-service-cadence)

## Evidence vocabulary

- **Verified** — established directly from ROM bytes, bounded 6502
  disassembly, table consumers, and/or supplied hardware documentation.
- **Strong inference** — multiple independent observations agree, but a final
  hardware trace or complete control-flow proof is absent.
- **Hypothesis** — plausible interpretation that still needs decisive evidence.
- **Unknown** — not determined.
- **Contradicted** — an older claim disproved by current evidence.

Addresses are 6502 CPU addresses unless explicitly described as file offsets.
Ranges are inclusive in prose and tables unless an end is labeled “exclusive.”

## Source hierarchy

For current conclusions, use this directory first. Other files have narrower
roles:

- `REPORT.md` is the historical phase-by-phase work log and contains
  superseded conclusions.
- `REPORT_SUMMARY.md` is an obsolete attempted summary with internal
  contradictions.
- `AUDIT.md` explains defects found in those reports.
- `AUDIT_R2_CHECKPOINT.md` records the stopped r2 session.
- `CONTINUED_ANALYSIS.md` contains the transitional analysis from which these
  chapters were backfilled.
- `gauntlet_disasm.py` and `rom_table_audit.py` are practical tools, not
  independent authorities.

## Current high-level result

The ROM coordinates a POKEY, YM2151, and TMS5220 using two distinct command
data paths:

- **Type 7** drives a shared bytecode sequence engine. Commands select linked
  records assigned either to POKEY channels 0..3 or YM2151 channels 4..11.
  Music and most effects use this path.
- **Type 11** is exclusively TMS5220 speech. Commands select a pointer and byte
  length for a variable-length LPC stream, which IRQ-time code feeds to the
  speech chip.

The documentation is intentionally not marked complete. The prioritized
remaining work is tracked in [Known issues](10_known_issues.md).
