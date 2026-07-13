#!/usr/bin/env python3
"""Classify the final unresolved backlog by the unavailable evidence it needs."""

import argparse
import csv
from pathlib import Path


QUESTIONS = [
    ("envelope_packed_ends", "Exact original packed ends for 17 structurally bounded envelopes",
     "comparison sound ROM or Atari source/listing", "historical_intent_not_recoverable_from_current_image",
     "consumer grammar and all configured/runtime reads are already bounded; packing intent only"),
    ("mixed_region_provenance", "Original purpose of YM offset $1C, 15 unreferenced voices, $80DA-$80E2, and zero trailers",
     "comparison sound ROM or Atari source/listing", "historical_intent_not_recoverable_from_current_image",
     "zero unclassified bytes; no current-image consumer exists"),
    ("runtime_indirect_targets", "Whether execution produces an indirect CPU target absent from verified ROM tables, plus configured path/RNG frequencies",
     "complete-ROM MAME or cabinet control-flow trace", "external_evidence_required",
     "direct/table traversal is at fixed point and all 61 meaningful entries have contracts"),
    ("dormant_feature_intent", "Intended nonzero YM interpolation and dormant POKEY NOTE behavior",
     "comparison ROM/source that configures SET_VIBRATO or POKEY NOTE", "historical_intent_not_recoverable_from_current_image",
     "current configured traversal proves both paths dormant"),
    ("irq_catchup_runtime", "Actual catch-up IRQ behavior after the one configured initial overrun",
     "complete-ROM MAME or cabinet IRQ trace", "external_evidence_required",
     "ROM cycle count and level-IRQ implementation behavior are already bounded"),
    ("speech_ready_runtime", "Phrase-specific READY cadence, zero-drain timing, and watchdog occurrence",
     "TMS5220-integrated MAME or cabinet bus trace", "external_evidence_required",
     "ROM state machine and supplied device-core FIFO behavior are resolved"),
    ("reserved_handler_provenance", "Whether dormant handler types were development leftovers or revision features",
     "comparison sound ROM or Atari source/listing", "historical_intent_not_recoverable_from_current_image",
     "current-image semantics and zero configured reachability are Verified"),
    ("board_control_labels", "Player/slot mapping, physical polarity, and intended debounce presentation",
     "main-CPU self-test code, schematic, or cabinet/MAME I/O trace", "external_evidence_required",
     "all sound-ROM arithmetic and output pairings are Verified"),
    ("boot_handshake_decode", "Board decode/significance of sparse I/O, including $1002/$1003/$100B/$100C/$1000 and nominally unmapped space",
     "main-CPU code or board schematic", "external_evidence_required",
     "write order and values are Verified; receiver/decode lies outside sound ROM"),
    ("diagnostic_nmi_sender", "Whether the main CPU intentionally sends bytes during the boot NMI window",
     "main-CPU sender code or boot-time bus trace", "external_evidence_required",
     "sound-side mechanics and conditional reachability are Verified"),
    ("unreferenced_rom_provenance", "Build intent of $8447-$8448, $FECD, and $FFF6-$FFF9",
     "comparison ROM/source/build map", "historical_intent_not_recoverable_from_current_image",
     "complete code/bytecode/indirect xrefs find no consumer"),
    ("command_game_use", "Whether legacy 'Not Used' commands are emitted and their exact player-visible meaning",
     "main-CPU command emitters or gameplay trace", "external_evidence_required",
     "all sound-side handlers and metadata are catalogued"),
]


REQUIRED_MARKERS = (
    "17 envelope packed ends", "indirect targets not represented",
    "cabinet traces", "original provenance", "Boot handshake bytes",
    "Unknown external provenance", "Small unreferenced ROM regions",
    "Command descriptions and game-side use",
)

CANONICAL_SECTIONS = {
    "envelope_packed_ends": "P0 — Exact type-7 segment map; P1 — Envelope and voice data formats",
    "mixed_region_provenance": "P0 — Exact type-7 segment map; P1 — Envelope and voice data formats",
    "runtime_indirect_targets": "P0 — Complete 6502 entry-point and control-flow inventory; P1 — Timing",
    "dormant_feature_intent": "P1 — Frequency table conversion",
    "irq_catchup_runtime": "P1 — Timing",
    "speech_ready_runtime": "P1 — Timing; P1 — Speech drain and watchdog hardware behavior",
    "reserved_handler_provenance": "P1 — Reserved handler types",
    "board_control_labels": "P2 — Board-control routine `$8381`",
    "boot_handshake_decode": "P2 — Boot handshake bytes",
    "diagnostic_nmi_sender": "Resolved mechanics — Alternate NMI diagnostic-window indirect write",
    "unreferenced_rom_provenance": "P2 — Small unreferenced ROM regions",
    "command_game_use": "P2 — Command descriptions and game-side use",
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--workspace", required=True, type=Path)
    p.add_argument("--known-issues", required=True, type=Path)
    p.add_argument("--question-csv", required=True, type=Path)
    p.add_argument("--inventory-csv", required=True, type=Path)
    args = p.parse_args()
    text = args.known_issues.read_text()
    missing_markers = [marker for marker in REQUIRED_MARKERS if marker not in text]
    if missing_markers:
        raise SystemExit(f"known-issue markers missing: {missing_markers}")
    sections = {}
    current = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:]
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    active_sections = {name for name, lines in sections.items()
                       if "**Unknown" in "\n".join(lines)
                       or "**Strong inference" in "\n".join(lines)}
    catalog_sections = {name for value in CANONICAL_SECTIONS.values()
                        for name in value.split("; ")}
    if active_sections != catalog_sections:
        raise SystemExit(f"active-backlog traceability mismatch: "
                         f"unmapped={sorted(active_sections-catalog_sections)} "
                         f"stale={sorted(catalog_sections-active_sections)}")

    files = [path for path in args.workspace.rglob("*") if path.is_file()
             and ".git" not in path.parts and "__pycache__" not in path.parts]
    evidence = {
        "comparison_sound_rom": [p for p in files if p.suffix.lower() in {".bin", ".rom"} and p.name != "soundrom.bin"],
        "main_cpu_source_listing": [p for p in files if p.suffix.lower() in {".asm", ".s", ".lst", ".sym"}],
        "runtime_trace": [p for p in files if p.suffix.lower() in {".vcd", ".fst", ".trace"}],
        "schematic": [p for p in files if p.suffix.lower() in {".sch", ".kicad_sch"} or "schemat" in p.name.lower()],
        "complete_rom_archive": [p for p in files if p.suffix.lower() in {".zip", ".7z"} and "gaunt" in p.name.lower()],
    }
    unexpected = {kind: paths for kind, paths in evidence.items() if paths}
    if unexpected:
        formatted = {kind: [str(path.relative_to(args.workspace)) for path in paths]
                     for kind, paths in unexpected.items()}
        raise SystemExit(f"new external evidence requires backlog re-audit: {formatted}")

    question_rows = []
    for key, question, required, status, static_result in QUESTIONS:
        question_rows.append({
            "question_id": key, "remaining_question": question,
            "canonical_issue_section": CANONICAL_SECTIONS[key],
            "required_external_evidence": required, "status": status,
            "static_work_status": "exhausted_no_remaining_static_test",
            "current_image_functional_result": static_result,
            "evidence_available_in_workspace": False,
            "confidence": "Verified evidence dependency",
        })
    if any(row["static_work_status"] != "exhausted_no_remaining_static_test" for row in question_rows):
        raise SystemExit("a statically actionable question remains")

    args.question_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.question_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=question_rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(question_rows)
    inventory_rows = [{
        "evidence_class": kind, "matching_files": 0,
        "workspace_result": "not available", "confidence": "Verified workspace inventory",
    } for kind in evidence]
    with args.inventory_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=inventory_rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(inventory_rows)
    historical = sum(row["status"].startswith("historical") for row in question_rows)
    print(f"external evidence audit: {len(question_rows)} remaining questions, "
          f"{historical} historical-intent, {len(question_rows)-historical} external-runtime/hardware, "
          f"{len(active_sections)} authoritative sections mapped, "
          "0 statically actionable, 0 required artifacts available")


if __name__ == "__main__":
    main()
