# 09 — Analysis and Reproduction Method

## Allowed evidence

Current analysis uses:

- `soundrom.bin`;
- bounded radare2/r2mcp disassembly when stable;
- ROM table extraction through `rom_table_audit.py`;
- practical decoding/rendering through `gauntlet_disasm.py`;
- ROM-driven YM2151 rendering through `ymfm_renderer.cpp` and supplied YMFM;
- supplied board notes under `docs/`;
- supplied MAME device references under `refs/`.

The upstream MAME Gauntlet driver may be used as corroborating implementation
evidence for clock configuration and scheduling. It does not by itself promote
a hardware fact to Verified. The clock tree is now separately Verified by a
user-reported independent calculation from the board schematic (2026-07-12),
although the schematic artifact is not present in this workspace.

Automatically discovered functions, pseudocode, and tool-generated names are
hypotheses until validated against 6502 instructions and data consumers.

## Raw ROM setup

The image must be mapped as raw 6502 code:

```text
e asm.arch=6502
e anal.arch=6502
e asm.bits=8
om-1
om 3 0x4000 0xc000 0 r-x soundrom
```

Before any analysis, verify map `$4000-$FFFF`, vectors `$57B0/$5A25/$4187`,
and the RESET prefix printed in [ROM structure](03_rom_structure.md).

## r2 stability protocol

- Do not run broad automatic analysis first.
- Seed RESET, NMI, and IRQ.
- Maintain breadth-first queues and visited sets outside r2mcp.
- Query at most 64 addresses/instructions per batch.
- Prefer structured disassembly calls.
- Do not perform recursive traversal in `run_javascript` or repeatedly issue
  `aoj` from one qjs invocation.
- Save progress after every successful batch.
- If any r2mcp call fails, stop issuing r2mcp calls, save the last successful
  address/batch, and do not replace it with handwritten 6502 disassembly.

The previous stopped state is recorded in `AUDIT_R2_CHECKPOINT.md`. A new
session should start a fresh r2 instance rather than reuse that damaged state.
The current fresh traversal persists its batch log and external queue/visited
state in `generated/cpu_control_flow_batches.csv` and
`generated/cpu_traversal_state.csv`.

Derive and validate the classified entry catalog with:

```sh
python3 cpu_traversal_audit.py \
  --batches newdoc/generated/cpu_control_flow_batches.csv \
  --state newdoc/generated/cpu_traversal_state.csv \
  --output newdoc/generated/cpu_entry_catalog.csv

```

Validate and regenerate the consumer-led channel-engine catalog with:

```sh
python3 channel_engine_audit.py soundrom.bin \
  --csv newdoc/generated/channel_engine_catalog.csv

python3 physical_output_audit.py soundrom.bin \
  --csv newdoc/generated/physical_output_catalog.csv \
  --table-csv newdoc/generated/physical_output_table_catalog.csv \
  --pokey-control-csv newdoc/generated/pokey_control_catalog.csv \
  --pokey-ref refs/pokey.cpp

python3 bytecode_consumer_audit.py soundrom.bin \
  --opcode-csv newdoc/generated/bytecode_handler_catalog.csv \
  --format-csv newdoc/generated/bytecode_support_format_catalog.csv \
  --sequence-csv newdoc/generated/type7_sequence_catalog.csv \
  --ym-voice-field-csv newdoc/generated/ym_voice_field_catalog.csv \
  --range-csv newdoc/generated/bytecode_engine_catalog.csv \
  --callable-csv newdoc/generated/bytecode_callable_contract_catalog.csv

python3 speech_lifecycle_audit.py soundrom.bin \
  --csv newdoc/generated/speech_lifecycle_catalog.csv

python3 board_control_audit.py soundrom.bin \
  --csv newdoc/generated/board_control_catalog.csv \
  --transition-csv newdoc/generated/board_control_transition_catalog.csv

python3 nmi_protocol_audit.py soundrom.bin \
  --csv newdoc/generated/nmi_protocol_catalog.csv \
  --contract-csv newdoc/generated/nmi_entry_contract_catalog.csv

python3 initialization_main_audit.py soundrom.bin \
  --csv newdoc/generated/initialization_main_catalog.csv

python3 control_plane_audit.py soundrom.bin \
  --csv newdoc/generated/control_plane_catalog.csv

python3 support_staging_audit.py soundrom.bin \
  --code-csv newdoc/generated/support_staging_catalog.csv \
  --fade-rate-csv newdoc/generated/fade_rate_catalog.csv \
  --volume-shape-csv newdoc/generated/volume_shape_catalog.csv \
  --ym-tl-bias-csv newdoc/generated/ym_tl_bias_catalog.csv

python3 pitch_conversion_audit.py soundrom.bin \
  --csv newdoc/generated/pitch_conversion_catalog.csv \
  --consumer-validation-csv newdoc/generated/type7_consumer_validation.csv \
  --ym-pitch-csv newdoc/generated/ym_pitch_validation_catalog.csv \
  --ymfm-ref refs/ymfm/src/ymfm_fm.ipp \
  --ymfm-opm-ref refs/ymfm/src/ymfm_opm.h \
  --ymfm-engine-ref refs/ymfm/src/ymfm_fm.h

python3 timing_clock_audit.py soundrom.bin \
  --clock-csv newdoc/generated/timing_clock_catalog.csv \
  --cycle-csv newdoc/generated/timing_cycle_catalog.csv \
  --duration-csv newdoc/generated/timing_duration_trace_catalog.csv \
  --loop-csv newdoc/generated/timing_loop_trace_catalog.csv \
  --articulation-csv newdoc/generated/timing_articulation_trace_catalog.csv \
  --tms-ref refs/tms5220.cpp \
  --tms-header-ref refs/tms5220.h
```

## Rebuilding generated catalogs

Using the bundled workspace Python (or another environment with NumPy). The
interactive disassembler can instead provision its own NumPy dependency from
PEP 723 inline metadata, for example
`uv run gauntlet_disasm.py soundrom.bin --list`:

```sh
python3 rom_table_audit.py soundrom.bin \
  --csv newdoc/generated/type11_speech_catalog.csv \
  --index-csv newdoc/generated/speech_index_catalog.csv \
  --type7-csv newdoc/generated/type7_chain_catalog.csv \
  --command-csv newdoc/generated/command_catalog.csv \
  --type7-sequence-csv newdoc/generated/type7_sequence_catalog.csv \
  --type7-edge-csv newdoc/generated/type7_control_flow_catalog.csv \
  --type7-data-ref-csv newdoc/generated/type7_data_reference_catalog.csv \
  --type7-region-csv newdoc/generated/type7_region_catalog.csv \
  --type7-envelope-csv newdoc/generated/type7_envelope_catalog.csv \
  --type7-cpu-support-csv newdoc/generated/type7_cpu_support_catalog.csv \
  --type7-cpu-xref-audit-csv newdoc/generated/type7_cpu_xref_audit.csv \
  --type7-indirect-xref-audit-csv newdoc/generated/type7_indirect_xref_audit.csv \
  --type7-conditional-feasibility-csv newdoc/generated/type7_conditional_feasibility.csv \
  --type7-feasible-sequence-csv newdoc/generated/type7_feasible_sequence_catalog.csv \
  --ym-voice-record-csv newdoc/generated/ym_voice_record_catalog.csv \
  --type7-residual-csv newdoc/generated/type7_residual_catalog.csv \
  --region-summary-csv newdoc/generated/rom_regions.csv

python3 reserved_handler_audit.py soundrom.bin \
  --command-csv newdoc/generated/command_catalog.csv \
  --cpu-entry-csv newdoc/generated/cpu_entry_catalog.csv \
  --csv newdoc/generated/reserved_handler_catalog.csv

python3 semantic_coverage_audit.py \
  --initialization newdoc/generated/initialization_main_catalog.csv \
  --control-plane newdoc/generated/control_plane_catalog.csv \
  --channel-engine newdoc/generated/channel_engine_catalog.csv \
  --support-staging newdoc/generated/support_staging_catalog.csv \
  --bytecode-engine newdoc/generated/bytecode_engine_catalog.csv \
  --physical-output newdoc/generated/physical_output_catalog.csv \
  --nmi-protocol newdoc/generated/nmi_protocol_catalog.csv \
  --speech-lifecycle newdoc/generated/speech_lifecycle_catalog.csv \
  --board-control newdoc/generated/board_control_catalog.csv \
  --csv newdoc/generated/semantic_code_coverage_catalog.csv

python3 callable_contract_audit.py \
  --cpu-entry newdoc/generated/cpu_entry_catalog.csv \
  --semantic-coverage newdoc/generated/semantic_code_coverage_catalog.csv \
  --initialization newdoc/generated/initialization_main_catalog.csv \
  --control-plane newdoc/generated/control_plane_catalog.csv \
  --channel-engine newdoc/generated/channel_engine_catalog.csv \
  --support-staging newdoc/generated/support_staging_catalog.csv \
  --physical-output newdoc/generated/physical_output_catalog.csv \
  --speech-lifecycle newdoc/generated/speech_lifecycle_catalog.csv \
  --board-control newdoc/generated/board_control_catalog.csv \
  --reserved-handler newdoc/generated/reserved_handler_catalog.csv \
  --bytecode-callable newdoc/generated/bytecode_callable_contract_catalog.csv \
  --nmi-entry newdoc/generated/nmi_entry_contract_catalog.csv \
  --csv newdoc/generated/cpu_entry_contract_catalog.csv

python3 ram_state_reference_audit.py soundrom.bin \
  --semantic-coverage newdoc/generated/semantic_code_coverage_catalog.csv \
  --csv newdoc/generated/ram_state_reference_catalog.csv \
  --summary-csv newdoc/generated/ram_state_semantics_catalog.csv

python3 external_evidence_audit.py \
  --workspace . \
  --companion-docs ../gauntlet-gamerom-ai-reveng/doc \
  --known-issues newdoc/10_known_issues.md \
  --question-csv newdoc/generated/external_question_catalog.csv \
  --inventory-csv newdoc/generated/external_evidence_inventory.csv
```

The audit checks:

- all type-11 commands, metadata, and LPC frame completion;
- all 189 speech pointer/length records;
- contiguity of the LPC corpus;
- expansion of all type-7 linked chains;
- reachability of all 182 type-7 records;
- command handler/parameter mapping.
- bounded static type-7 bytecode traversal from all 153 distinct pointers;
- sequence control-flow edges, consumed-byte rows, support-data references,
  and coalesced mixed-region classifications.
- every raw absolute/indexed CPU data-reference candidate into the mixed
  region, including bounded-listing acceptance or rejection.
- every constructed indirect-pointer class capable of reading the mixed
  region, tied back to its exhaustive target catalog.
- computed-target feasibility, the complete 55-record YM grid, and explicit
  classification of consumer-unreachable/unreferenced residual objects.

## Regression checks

At minimum:

```sh
python3 -m py_compile gauntlet_disasm.py rom_table_audit.py \
  cpu_traversal_audit.py channel_engine_audit.py physical_output_audit.py \
  bytecode_consumer_audit.py speech_lifecycle_audit.py board_control_audit.py \
  nmi_protocol_audit.py initialization_main_audit.py control_plane_audit.py \
  support_staging_audit.py pitch_conversion_audit.py mos6502_cycle.py \
  timing_clock_audit.py \
  reserved_handler_audit.py semantic_coverage_audit.py \
  callable_contract_audit.py ram_state_reference_audit.py \
  external_evidence_audit.py
python3 gauntlet_disasm.py soundrom.bin --list
python3 gauntlet_disasm.py soundrom.bin --cmd 0x04
python3 gauntlet_disasm.py soundrom.bin --speech-wav 0x4A --out /tmp/one.wav
python3 gauntlet_disasm.py soundrom.bin --sfx-wav 0x44 \
  --max-seconds 2 --out /tmp/pokey.wav
python3 gauntlet_disasm.py soundrom.bin --music-wav 0x09 \
  --max-seconds 3 --out /tmp/ym2151.wav
uv run gauntlet_disasm.py soundrom.bin --cmd 0x04
```

Command `$04` must show eight YM2151 records beginning at offset 0. Command
`$4A` must resolve as TMS5220 speech at `$8834`, not music bytecode.
The two type-7 WAV checks must identify their backend as ROM-driven 6502,
terminate within the requested cap, and produce nonempty PCM. The YM check
must compile/use the bundled YMFM renderer rather than the legacy Python FM
approximation.

## Documentation workflow

1. Record new evidence in the appropriate canonical chapter.
2. Add row-level facts to a generated catalog or its generator.
3. Put unresolved questions in `10_known_issues.md` with an explicit next test.
4. Do not duplicate full maps or inventories across chapters; link to their
   canonical location.
5. Preserve old reports as history rather than editing every superseded phase.

## Confidence discipline

A table extent is verified only when its indexing consumer and maximum reachable
index establish the bound. A function entry is verified only when an incoming
control-flow source is known. A data interval is verified only when record
lengths, control flow, or exclusive bounds establish its end.
