# Appendix F — Where to Look Next

This book is the readable account. Underneath it sits a technical reference in
[`docs/`](../docs/README.md) that argues every claim, labels how confident it is,
and stores the row-level data in generated CSV files. If a sentence in a chapter
made you want proof, this appendix says exactly where the case is made.

## How the reference is organized

| Directory | What it holds |
|---|---|
| [`docs/`](../docs/README.md) | Ten numbered chapters. The canonical account of the hardware, the memory map, the ROM structure, each subsystem, the data tables, the sequence engine, the function index, the commands, the analysis method, and the open questions |
| [`docs/generated/`](../docs/generated/README.md) | Fifty-odd CSV files produced by scripts in `utility/`. One row per command, per record, per instruction, per envelope, per table entry. These are the evidence, not a summary of it |
| [`hw_docs/`](../hw_docs/) | Chip and board documentation from datasheets and schematics, plus the surviving sound command list |
| [`mame_refs/`](../mame_refs/) and [`ymfm/`](../ymfm/) | Independent implementations of the three chips, used throughout as oracles |

Every claim in [`docs/`](../docs/README.md) carries one of five labels: Verified,
Strong inference, Hypothesis, Unknown, or Contradicted.
[Chapter 16](16_how_this_was_figured_out.md) explains what each means and how
strictly they are applied. Chapters 1 through 15 of this book were filtered to the
top two labels, which is what licenses their flat tone.

## Chapter by chapter

| Chapter | Canonical reference | Row-level data |
|---|---|---|
| [1. Two Computers](01_two_computers.md) | [`01_hardware.md`](../docs/01_hardware.md), [`08_command_reference.md`](../docs/08_command_reference.md), [`hw_docs/operation.txt`](../hw_docs/operation.txt), repo [`README.md`](../README.md) | [`command_catalog.csv`](../docs/generated/command_catalog.csv) |
| [2. Tour of the Board](02_tour_of_the_board.md) | [`02_memory_map.md`](../docs/02_memory_map.md), [`01_hardware.md`](../docs/01_hardware.md), [`03_rom_structure.md`](../docs/03_rom_structure.md) | [`ram_state_semantics_catalog.csv`](../docs/generated/ram_state_semantics_catalog.csv), [`ram_state_reference_catalog.csv`](../docs/generated/ram_state_reference_catalog.csv) |
| [3. Three Sound Chips](03_three_sound_chips.md) | [`hw_docs/POKEY.md`](../hw_docs/POKEY.md), [`hw_docs/YM2151.md`](../hw_docs/YM2151.md), [`mame_refs/tms5220.txt`](../mame_refs/tms5220.txt), [`01_hardware.md`](../docs/01_hardware.md), [`04_subsystems.md`](../docs/04_subsystems.md) | [`type7_chain_catalog.csv`](../docs/generated/type7_chain_catalog.csv) |
| [4. The Heartbeat](04_heartbeat.md) | [`01_hardware.md`](../docs/01_hardware.md) clock tree, [`04_subsystems.md`](../docs/04_subsystems.md) IRQ service, [`06_sequence_engine.md`](../docs/06_sequence_engine.md) timing | [`timing_clock_catalog.csv`](../docs/generated/timing_clock_catalog.csv), [`timing_cycle_catalog.csv`](../docs/generated/timing_cycle_catalog.csv) |
| [5. Waking Up](05_waking_up.md) | [`04_subsystems.md`](../docs/04_subsystems.md) boot, [`02_memory_map.md`](../docs/02_memory_map.md) error flags, [`07_function_index.md`](../docs/07_function_index.md) | [`initialization_main_catalog.csv`](../docs/generated/initialization_main_catalog.csv), [`control_plane_catalog.csv`](../docs/generated/control_plane_catalog.csv) |
| [6. Taking Orders](06_taking_orders.md) | [`08_command_reference.md`](../docs/08_command_reference.md), [`04_subsystems.md`](../docs/04_subsystems.md) main loop and NMI, [`05_data_reference.md`](../docs/05_data_reference.md) dispatch tables | [`command_catalog.csv`](../docs/generated/command_catalog.csv), [`nmi_protocol_catalog.csv`](../docs/generated/nmi_protocol_catalog.csv), [`control_plane_catalog.csv`](../docs/generated/control_plane_catalog.csv) |
| [7. Command to Channel](07_command_to_channel.md) | [`04_subsystems.md`](../docs/04_subsystems.md) type-7 subsystem, [`05_data_reference.md`](../docs/05_data_reference.md) type-7 tables, [`02_memory_map.md`](../docs/02_memory_map.md) channel arrays | [`type7_chain_catalog.csv`](../docs/generated/type7_chain_catalog.csv), [`control_plane_catalog.csv`](../docs/generated/control_plane_catalog.csv) |
| [8. Notes, Rests, and Time](08_sequence_language_time.md) | [`06_sequence_engine.md`](../docs/06_sequence_engine.md) stream format and timing, [`05_data_reference.md`](../docs/05_data_reference.md) duration table | [`timing_duration_trace_catalog.csv`](../docs/generated/timing_duration_trace_catalog.csv), [`timing_articulation_trace_catalog.csv`](../docs/generated/timing_articulation_trace_catalog.csv), [`type7_sequence_catalog.csv`](../docs/generated/type7_sequence_catalog.csv) |
| [9. The Opcodes](09_sequence_language_opcodes.md) | [`06_sequence_engine.md`](../docs/06_sequence_engine.md) opcode reference and control-flow model | [`bytecode_handler_catalog.csv`](../docs/generated/bytecode_handler_catalog.csv), [`type7_control_flow_catalog.csv`](../docs/generated/type7_control_flow_catalog.csv), [`type7_sequence_catalog.csv`](../docs/generated/type7_sequence_catalog.csv), [`timing_loop_trace_catalog.csv`](../docs/generated/timing_loop_trace_catalog.csv) |
| [10. Shaping the Sound](10_shaping_the_sound.md) | [`06_sequence_engine.md`](../docs/06_sequence_engine.md) envelope formats, [`04_subsystems.md`](../docs/04_subsystems.md) fade and ramp staging | [`type7_envelope_catalog.csv`](../docs/generated/type7_envelope_catalog.csv), [`volume_shape_catalog.csv`](../docs/generated/volume_shape_catalog.csv), [`fade_rate_catalog.csv`](../docs/generated/fade_rate_catalog.csv) |
| [11. Driving the POKEY](11_driving_the_pokey.md) | [`04_subsystems.md`](../docs/04_subsystems.md) POKEY pipeline, [`hw_docs/POKEY.md`](../hw_docs/POKEY.md) | [`pokey_control_catalog.csv`](../docs/generated/pokey_control_catalog.csv), [`pitch_conversion_catalog.csv`](../docs/generated/pitch_conversion_catalog.csv), [`physical_output_catalog.csv`](../docs/generated/physical_output_catalog.csv) |
| [12. Driving the YM2151](12_driving_the_ym2151.md) | [`04_subsystems.md`](../docs/04_subsystems.md) YM pipeline, [`05_data_reference.md`](../docs/05_data_reference.md) YM tables, [`hw_docs/YM2151.md`](../hw_docs/YM2151.md) | [`ym_voice_field_catalog.csv`](../docs/generated/ym_voice_field_catalog.csv), [`ym_voice_record_catalog.csv`](../docs/generated/ym_voice_record_catalog.csv), [`ym_pitch_validation_catalog.csv`](../docs/generated/ym_pitch_validation_catalog.csv), [`ym_tl_bias_catalog.csv`](../docs/generated/ym_tl_bias_catalog.csv) |
| [13. Speaking](13_speaking.md) | [`04_subsystems.md`](../docs/04_subsystems.md) type-11 subsystem, [`05_data_reference.md`](../docs/05_data_reference.md) speech metadata, [`mame_refs/tms5220.txt`](../mame_refs/tms5220.txt) | [`type11_speech_catalog.csv`](../docs/generated/type11_speech_catalog.csv), [`speech_index_catalog.csv`](../docs/generated/speech_index_catalog.csv), [`speech_lifecycle_catalog.csv`](../docs/generated/speech_lifecycle_catalog.csv) |
| [14. The Chip Tests](14_chip_tests.md) | [`08_command_reference.md`](../docs/08_command_reference.md) diagnostics, [`06_sequence_engine.md`](../docs/06_sequence_engine.md) traced timings, [`03_rom_structure.md`](../docs/03_rom_structure.md) | [`type7_chain_catalog.csv`](../docs/generated/type7_chain_catalog.csv), [`ym_pitch_validation_catalog.csv`](../docs/generated/ym_pitch_validation_catalog.csv), [`timing_duration_trace_catalog.csv`](../docs/generated/timing_duration_trace_catalog.csv) |
| [15. Case Studies](15_case_studies.md) | Everything, especially [`04_subsystems.md`](../docs/04_subsystems.md) and [`06_sequence_engine.md`](../docs/06_sequence_engine.md); [`hw_docs/soundcmds.csv`](../hw_docs/soundcmds.csv) for names | [`type7_chain_catalog.csv`](../docs/generated/type7_chain_catalog.csv), [`type7_sequence_catalog.csv`](../docs/generated/type7_sequence_catalog.csv), [`type11_speech_catalog.csv`](../docs/generated/type11_speech_catalog.csv) |
| [16. How This Was Figured Out](16_how_this_was_figured_out.md) | [`09_analysis_method.md`](../docs/09_analysis_method.md), [`docs/README.md`](../docs/README.md), repo [`README.md`](../README.md), [`prompting/`](../prompting/) | [`cpu_entry_contract_catalog.csv`](../docs/generated/cpu_entry_contract_catalog.csv), [`semantic_code_coverage_catalog.csv`](../docs/generated/semantic_code_coverage_catalog.csv) |
| [17. What We Still Don't Know](17_open_questions.md) | [`10_known_issues.md`](../docs/10_known_issues.md), [`03_rom_structure.md`](../docs/03_rom_structure.md) unused space | [`external_question_catalog.csv`](../docs/generated/external_question_catalog.csv), [`external_evidence_inventory.csv`](../docs/generated/external_evidence_inventory.csv), [`reserved_handler_catalog.csv`](../docs/generated/reserved_handler_catalog.csv), [`type7_residual_catalog.csv`](../docs/generated/type7_residual_catalog.csv) |

## Appendix by appendix

| Appendix | Where its data comes from |
|---|---|
| [A. Glossary](A_glossary.md) | The chapters themselves |
| [B. Command List](B_command_list.md) | [`command_catalog.csv`](../docs/generated/command_catalog.csv), [`type7_chain_catalog.csv`](../docs/generated/type7_chain_catalog.csv), [`type11_speech_catalog.csv`](../docs/generated/type11_speech_catalog.csv), [`hw_docs/soundcmds.csv`](../hw_docs/soundcmds.csv) |
| [C. Opcode Reference](C_opcode_reference.md) | [`bytecode_handler_catalog.csv`](../docs/generated/bytecode_handler_catalog.csv), [`type7_sequence_catalog.csv`](../docs/generated/type7_sequence_catalog.csv), [`06_sequence_engine.md`](../docs/06_sequence_engine.md) |
| [D. Reference Tables](D_reference_tables.md) | [`02_memory_map.md`](../docs/02_memory_map.md), [`03_rom_structure.md`](../docs/03_rom_structure.md), [`05_data_reference.md`](../docs/05_data_reference.md), and the fade, shape, pitch, clock, and YM voice catalogs |
| [E. Using the Tool](E_using_the_tool.md) | [`09_analysis_method.md`](../docs/09_analysis_method.md), [`docs/generated/README.md`](../docs/generated/README.md), `gauntlet_disasm.py` itself |

## If you want one thing per question

| Question | Go straight to |
|---|---|
| What does command `$NN` do? | [`command_catalog.csv`](../docs/generated/command_catalog.csv) |
| What are the records behind a sound? | [`type7_chain_catalog.csv`](../docs/generated/type7_chain_catalog.csv) |
| What does a sequence actually contain? | `uv run gauntlet_disasm.py soundrom.bin --cmd 0xNN` |
| What is at ROM address `$NNNN`? | [`type7_region_catalog.csv`](../docs/generated/type7_region_catalog.csv) for the mixed data region, [`03_rom_structure.md`](../docs/03_rom_structure.md) for everything else |
| What does this RAM address hold? | [`02_memory_map.md`](../docs/02_memory_map.md), then [`ram_state_semantics_catalog.csv`](../docs/generated/ram_state_semantics_catalog.csv) |
| What does this 6502 routine do? | [`07_function_index.md`](../docs/07_function_index.md), then [`cpu_entry_contract_catalog.csv`](../docs/generated/cpu_entry_contract_catalog.csv) |
| How long does this sound really last? | [`timing_duration_trace_catalog.csv`](../docs/generated/timing_duration_trace_catalog.csv) and [`timing_loop_trace_catalog.csv`](../docs/generated/timing_loop_trace_catalog.csv) |
| How confident is a given claim? | The confidence column of the relevant catalog, or the label in the `docs/` chapter |
| What is still unknown? | [`10_known_issues.md`](../docs/10_known_issues.md) and [`external_question_catalog.csv`](../docs/generated/external_question_catalog.csv) |

## Files not to use

Four files in this repository are history rather than reference. They are kept
because they record how the project got where it is, and they contain
conclusions that later work overturned.

| File | Why to avoid it |
|---|---|
| `REPORT.md` | A working log from earlier phases. Contains superseded and internally contradictory conclusions |
| `REPORT_SUMMARY.md` | The same material condensed, with the same problems |
| `REVIEW_FINDINGS.md` | An older review artifact, superseded by `docs/` |
| `MEMMAP.md` | An early memory map, superseded by [`02_memory_map.md`](../docs/02_memory_map.md) |

Several specific claims in those files are labelled Contradicted in the current
reference: a frequency table that turned out to be an operator level transform, a
detune routine that turned out to be the volume machinery, a two-channel reading
of the music that is actually eight, an interrupt rate of about 245 Hz, and a
POKEY note path the sequences never take. Anything copied out of them needs
revalidating against `docs/` before it is trusted.

One more file is a pointer rather than a source.
[`docs/NEXT_STEPS.md`](../docs/NEXT_STEPS.md) is an internal handoff document; use
it to find which `docs/` chapter is authoritative on a topic, not as an authority
itself.

If `docs/` and anything else disagree, `docs/` wins.
