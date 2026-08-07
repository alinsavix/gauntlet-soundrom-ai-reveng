# Gauntlet II Sound ROM — Memory Map

This is a compact map of the verified image. It intentionally defers detailed
field grammars and instruction semantics to `docs/`, which is the maintained
source of truth. The previous version of this file mixed early hypotheses with
later results—for example, it called speech data “music,” split the LPC corpus at
`$AD00`, treated `$6000-$6023` as unused, and described POKEY status lanes as
physical-channel priorities. Those interpretations are superseded.

## Image mapping and vectors

`soundrom.bin` is a raw 49,152-byte image. File offset 0 maps to CPU `$4000`, so
CPU address A maps to file offset `A-$4000`.

| Vector | Location | Target |
|---|---:|---:|
| NMI | `$FFFA-$FFFB` | `$57B0` |
| RESET | `$FFFC-$FFFD` | `$5A25` |
| IRQ/BRK | `$FFFE-$FFFF` | `$4187` |

## CPU address-space overview

| Range | Use |
|---|---|
| `$0000-$00FF` | Zero-page state and pointers |
| `$0100-$01FF` | 6502 stack |
| `$0200-$0FFF` | Queues, channel arrays, operator state, and work RAM |
| `$1000-$1FFF` | Sparse board and sound-device I/O |
| `$2000-$3FFF` | Unmapped by known program paths |
| `$4000-$FFFF` | 48 KiB ROM |

The detailed RAM reference audit is in
[`docs/02_memory_map.md`](docs/02_memory_map.md) and the generated
`ram_state_*` catalogs.

## Important zero-page state

| Address | Meaning |
|---:|---|
| `$00` | Boot-NMI exit latch during diagnostic startup; later IRQ frame counter |
| `$01` | Initialization/early-IRQ selector |
| `$02` | Heartbeat and RAM/ROM/YM error flags |
| `$04-$05` | Pointer used by the conditional diagnostic NMI indirect-write path |
| `$08-$09` | Indirect POKEY/YM2151 hardware base pointer |
| `$13` | Global sound/speech filter threshold |
| `$18-$27` | Sequence-variable workspace |
| `$28-$2A` | Mixer fields and update countdown |
| `$2B-$2C` | Current TMS5220 LPC stream pointer |
| `$2D-$2E` | LPC bytes remaining |
| `$2F` | Speech state: idle, kickoff, streaming, or post-length drain |
| `$30-$35` | Speech READY watchdog, scratch/deadline, clock flag, and priority |
| `$36-$44` | Four counter-pulse states, four input filters, phase, and cached event fields |

`$36-$39` and `$3E-$41` drive the coin-mechanism/counter logic, not LEDs.
`$3A-$3D` and `$43` have no aligned current-ROM consumer apart from blanket RAM
clearing and the externally driven diagnostic write window.

## Queues and larger RAM objects

| Range | Meaning |
|---|---|
| `$0200-$020F` | Incoming command ring: 16 physical slots, 15 usable entries |
| `$0210/$0211` | Incoming ring read/write positions |
| `$0212/$0213` | Diagnostic indirect-write index/mode; normal mode is `$0213=$FF` |
| `$0214-$0223` | Outgoing reply staging buffer |
| `$0224-$0226` | Outgoing-buffer positions and overflow state |
| `$0228-$0803` | Thirty logical channels stored as parallel arrays |
| `$0804-$080F` | Twelve physical-list heads: four POKEY, eight YM2151 |
| `$0811-$0825` | Physical-output status lanes, candidate values, masks, and arbitration scratch |
| `$0826-$082E` | YM operator total-level transform chain and live volume |
| `$082F` | YM event-control shift register |
| `$0832/$0833` | Speech ring read/write positions |
| `$0834-$083B` | Eight physical speech slots; empty/full encoding limits capacity to seven |
| `$083C-$089F` | YM2151 operator/output workspace |
| `$093D-$0C54` | Four-byte sequence-context records |

The context-pool initializer intends to link 198 records, but an epilogue
off-by-one-path bug places the sentinel at record 134. Current allocatable
capacity is therefore 133 records. See `docs/02_memory_map.md` for the proof.

### Selected logical-channel arrays

All bases below are indexed by logical channel X, `0..29`.

| Base | Meaning |
|---:|---|
| `$0228` | Active command (`$FF` inactive, `$FE` fade/special) |
| `$0246/$0264` | Sequence pointer |
| `$0282/$02A0` | Base frequency |
| `$02BE/$02DC` | Primary timer |
| `$02FA/$0318` | Secondary timer |
| `$0336` | Current note/rest value |
| `$0390` | Status: priority encoded as `4p+1`, plus low mode/lane bits |
| `$03AE` | POKEY volume-shape index |
| `$03CC/$03EA` | Control AND/OR masks |
| `$0408` | Mode-dependent base volume/pitch field |
| `$0426/$0444` | Volume-envelope pointer |
| `$0462/$0480` | Frequency-envelope pointer |
| `$049E-$05AC` | Volume/frequency envelope state |
| `$05CA` | Tempo/speed |
| `$05E8` | Transpose |
| `$0606/$0624` | Repeat state and counter |
| `$0642` | POKEY distortion mask |
| `$0660` | Vibrato depth |
| `$067E/$069C` | Portamento/interpolation delta |
| `$06BA/$06D8/$06F6` | Push/repeat context linkage |
| `$0714-$078C` | Envelope counters, rates, and fraction |
| `$07AA/$07C8` | General-purpose register and shadow |
| `$07E6` | Linked-next array; entries 30..41 are the physical heads above |

### POKEY status lanes

`$0811` and `$0812` are two candidate **status lanes** selected by status bit 0;
they are not the priorities of physical channels 1 and 2. `$0813` is the current
lane/mode selector. The pair consumer can choose independent or joined operation
for each physical POKEY pair, then emits four AUDF/AUDC writes plus AUDCTL. Exact
scratch roles are in `docs/04_subsystems.md` and
`docs/generated/physical_output_catalog.csv`.

## Hardware I/O

| Address/range | Direction | Meaning |
|---:|:---:|---|
| `$1000-$100F` | W | One sound→main reply latch; low four address bits are not decoded |
| `$1010` | R | Main→sound command latch; the write on the main side triggers NMI |
| `$1020` | R | Four active-low coin-mechanism inputs |
| `$1020` | W | Analog mixer control: speech/effects/music fields |
| `$1030` | R | Self-test, TMS5220 READY, and inter-CPU latch-full status |
| `$1030` | W | YM2151 reset control |
| `$1031` | R/W | TMS5220 write strobe |
| `$1032` | W | TMS5220 reset strobe |
| `$1033` | W | TMS5220 clock selection |
| `$1034/$1035` | W | Right/left mechanical coin-counter outputs |
| `$1800-$180F` | R/W | POKEY |
| `$1810/$1811` | W | YM2151 address/data |
| `$1811` | R | YM2151 busy status |
| `$1820` | W | TMS5220 data |
| `$1830` | W | IRQ acknowledge |

The startup writes `$FF,$33,$00,$22,$0F` to five addresses in `$1000-$100F`.
On Gauntlet II all five hit the same reply latch. They are vestigial Atari
System 1 6522 speech-VIA initialization, not five Gauntlet board registers; see
Chapter 17 and `docs/10_known_issues.md`.

## Verified ROM regions

Broad code/data borders are intentionally described as regions rather than a
claim that every byte in a mixed range has the same type.

| Range | Content |
|---|---|
| `$4000-$5C5E` | Boot, interrupts, handlers, channel/bytecode engine, helpers, and embedded tables |
| `$5C5F-$5C7E` | Sixteen little-endian duration values |
| `$5C7F-$5C8E` | Sixteen fade/ramp shift/control selectors |
| `$5C8F-$5D0E` | Eight 16-byte signed POKEY volume-shape trajectories |
| `$5D0F-$5DE9` | 219-byte NMI command-validation table |
| `$5DEA-$5EC4` | 219-byte command→handler-type table |
| `$5EC5-$5F9F` | 219-byte command→parameter table |
| `$5FA0-$5FA7` | Type-3 target view, overlapping the NMI target table at `$5FA2` |
| `$5FA8-$5FE5` | Type-7 parameter→starting-record table, 62 bytes |
| `$5FE6-$6023` | Type-7 command flags, 62 bytes |
| `$6024-$60D9` | Type-7 record priorities, 182 bytes; values `0..$3F` are meaningful |
| `$60DA-$618F` | Type-7 physical-channel map, 182 bytes |
| `$6190-$62FB` | Type-7 sequence pointers, 182 little-endian words |
| `$62FC-$63B1` | Type-7 next-record links, 182 bytes |
| `$63B2-$643E` | Speech parameter→LPC index, 141 bytes |
| `$643F-$64CB` | Speech clock flags, 141 bytes |
| `$64CC-$6558` | Speech priority/filter values, 141 bytes |
| `$6559-$655E` | Two three-byte reserved-handler support records |
| `$655F-$8380` | Interleaved type-7 sequences, envelopes, YM voices, and support data |
| `$8381-$843E` | Board/coin-control routine |
| `$843F-$8446` | Direct NMI-dispatch handlers |
| `$8447-$8448` | Two unreferenced bytes, `$94,$FF` |
| `$8449-$85C2` | 189 LPC stream pointers |
| `$85C3-$873C` | 189 LPC byte lengths |
| `$873D-$FECC` | Contiguous TMS5220 LPC corpus, 30,608 bytes |
| `$FECD` | Unindexed trailing `$FF` guard/unused byte |
| `$FECE-$FFF5` | 296 zero padding bytes |
| `$FFF6-$FFF9` | Four unreferenced pre-vector bytes |
| `$FFFA-$FFFF` | Interrupt vectors |

The speech corpus begins at `$873D`; there is no YM “music sequence” region
from `$873D-$ACFF`. Type-11 commands select LPC streams directly and do not run
through the type-7 bytecode engine.

## Key code entries

| Address | Role |
|---:|---|
| `$4002` | Initialization and diagnostic entry |
| `$40C8` | Main command/output service loop |
| `$4187` | IRQ/BRK handler |
| `$41E6` | Atomic audio-state reinitialization |
| `$432E` | Normal command dispatcher |
| `$44DE` | Type-7 shared POKEY/YM sequence allocation |
| `$4651` | Logical-channel engine |
| `$4D02` | POKEY pair/status-lane consumer |
| `$4DFC` | POKEY device pass |
| `$4E68` | YM2151 physical-channel consumer |
| `$4FD6` | Eight-channel YM2151 pass |
| `$5029` | Type-7 bytecode dispatcher |
| `$57B0` | NMI vector entry |
| `$5894` | TMS5220 service state machine |
| `$59E2` | Priority-aware speech-ring enqueue |
| `$5A25` | RESET-vector hardware-ready gate |
| `$8381` | Coin input/filter/counter routine |

## Command dispatch

The accepted command space is `$00-$DA` (219 values). Commands `$03,$06,$07`
are intercepted by NMI. The normal dispatcher uses these configured handlers:

| Type | Meaning | Commands/count |
|---:|---|---:|
| 0 | Global filter | `$01,$02` |
| 3 | Special dispatch/reset | `$00` |
| 5 | Stop named sound | `$21,$2F,$39` |
| 7 | Shared POKEY/YM2151 sequences | 62 |
| 8 | Queue reply to main CPU | `$DA` |
| 9 | Fade named sound | `$3C` |
| 10 | Fade by status | `$41` |
| 11 | TMS5220 speech | 141 |
| 13 | Mixer presets | `$D6-$D9` |

Types 1, 2, 4, 6, 12, and 14 have code but no command selects them. Type 7 is
not “the POKEY handler”: eight configured type-7 commands use POKEY and 54 use
YM2151. Type 11 is speech, not YM music. The game emits `$D7` during the
level-start screen; the sound-side entries for all five `$D6-$DA` controls are
valid regardless of current game use.

## Type-7 stream format and timing

Only type-7 POKEY/YM logical channels use the shared stream language:

- `$00-$7F`: note/rest followed by a duration/control byte;
- `$80-$BA`: one of 59 opcodes;
- `$BB-$FF`: end marker;
- a note/rest followed by `$00`: chain/return marker.

Duration bits select the `$5C5F` table, division/control, dotted duration, and
sustain behavior. Timing is a carried phase-accumulator process; a simple
`duration/tempo/120` expression is not generally exact. With the MAME-derived
clock, each device is swept at 119.8454952 Hz. See
`docs/06_sequence_engine.md` and the generated timing catalogs.

ROM-to-pitch mapping for the verified chromatic data is `MIDI = ROM note + 11`,
not minus one. The POKEY divider view and YM2151 key-code view overlap in ROM;
see `docs/10_known_issues.md` and the pitch catalogs before treating either as
one monolithic 256-byte table.

Envelope formats are consumer-defined and not one uniform pair of two-/three-
byte records. Nine of 26 candidate packed envelopes have consumer-proven
terminators; 17 packed ends remain Strong inference. Runtime reads and channel
lifetime bounds are cataloged in `docs/generated/type7_envelope_catalog.csv`.

## Unreferenced ROM

The defensible likely-unused total is 303 bytes:

| Range | Bytes |
|---|---:|
| `$8447-$8448` | 2 |
| `$FECD` | 1 |
| `$FECE-$FFF5` | 296 |
| `$FFF6-$FFF9` | 4 |

`$6000-$6023` is part of the type-7 flag table and `$5874-$5893` is a referenced
dummy speech stream; neither is unused. “Unused” remains a Strong inference
about original intent even though exhaustive current-image consumers find no
reference.

## Maintained references

- [`docs/02_memory_map.md`](docs/02_memory_map.md) — RAM and I/O details
- [`docs/03_rom_structure.md`](docs/03_rom_structure.md) — verified region map
- [`docs/04_subsystems.md`](docs/04_subsystems.md) — device pipelines
- [`docs/06_sequence_engine.md`](docs/06_sequence_engine.md) — type-7 language
- [`docs/08_command_reference.md`](docs/08_command_reference.md) — all command classes
- [`docs/10_known_issues.md`](docs/10_known_issues.md) — confidence boundaries
- [`docs/generated/README.md`](docs/generated/README.md) — exhaustive catalogs
