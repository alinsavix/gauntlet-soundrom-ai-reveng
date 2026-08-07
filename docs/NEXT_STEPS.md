# Consumer-Led Analysis Handoff

This file defines the current analysis priorities for a new context. It is an
operational handoff, while `10_known_issues.md` remains the authoritative list
of unresolved technical questions.

## Current direction

Prioritize code, functions, consumers, and precise data formats. The final
mixed-region structural audit is complete; do not reopen it without a new
consumer or comparison ROM.

Candidate table bounds may remain **Strong inference** when the consumer and
record grammar are understood, referenced instances fit that grammar, packing
is structurally reasonable, and proving the exact final byte would not improve
functional understanding.

## Completed target: channel engine `$4651-$4B6A`

The completed pass decomposed this range into callable entries, meaningful
internal state-machine blocks, shared suffixes, and tail-call destinations.

It recorded, as evidence permits:

- incoming control-flow sources and entry assumptions;
- return, non-returning, and tail-call exits;
- A/X/Y and processor-flag clobbers;
- zero-page and RAM reads/writes;
- interrupt safety, atomic sections, and shared-state hazards;
- ROM tables and data formats consumed;
- configured reachability, confidence, and an explicit next test.

The canonical analysis now explains:

- sequence timing and note processing;
- opcode-dispatch interaction;
- frequency- and volume-envelope initialization and stepping;
- sequence termination, chaining, stopping, and fades;
- logical-channel state and physical-channel list traversal;
- state prepared for POKEY and YM output code.

The first consumer-led pass is recorded in
`generated/channel_engine_catalog.csv`: 14 blocks, 15 validated instruction
anchors, three direct callers, and a Verified shared tail-loop/RTS suffix.
The later 61-entry contract join closes transitive callable effects. Runtime
path frequencies and hardware-timed traces remain external follow-up tests.

## Completed target: physical output `$4D02-$500C`

The pass records 10 generated blocks, seven consumer-derived table rows, and 26
validated instruction anchors in `physical_output_catalog.csv` and
`physical_output_table_catalog.csv`. POKEY pair arbitration, all four POKEY
channel writes, eight-channel YM iteration, register busy waits, timeout state,
lookup-table dataflow, and POKEY AUDCTL mask/carry meanings are Verified. Stable
YM conversion is resolved; corrected `$AE` traversal contradicts the former
command-`$3A` high-note claim. No configured `$8C`
exists, so nonzero YM convergence is dormant. Common countdown, initial decode,
and configured `$FF` record-boundary paths are timed; observed path frequencies
remain an external trace question.

## Completed target: bytecode consumers `$5029-$578F`

The generated pass resolves all 59 opcode rows, the synthesized dispatch/carry
contract, variable-classifier domains, envelope pointer loaders, the 42-byte YM
instrument-record view, and five-byte/one-byte auxiliary views. Nineteen instruction anchors
back the catalogs. Twenty-six instruction-aligned semantic ranges now own every
executable byte in `$5029-$578F` outside the target table. Bounded evidence extends the former `$5774` endpoint through
`$578F`; the 16-byte table at `$5790-$579F` is consumed immediately afterward.
Offset `$1C` original intent and chip-specific dormant runtime paths remain
follow-up tests; configured field semantics are otherwise resolved.

## Completed target: speech lifecycle `$5894-$5A0A`

The nine-block generated pass resolves ready/watchdog state, queue dequeue and
priority rules, scheduled reset transitions, Speak External kickoff, one-byte
ready service, length exhaustion, drain writes, metadata/mixer loading, atomic
sections, and exits. Sixteen instruction anchors back
`speech_lifecycle_catalog.csv`. Hardware-level drain rationale and exact timing
remain explicit follow-up tests.

## Completed target: board/coin control `$8381-$8446`

The generated pass decomposes self-test-active direct input caching,
normal/inactive filtering, event generation, alternate-IRQ pulse stretching,
and physical counter writes; the adjacent NMI query-3 entry returns cached
`$44` through the main-CPU latch. Five blocks and eight transition rules are
backed by 15 instruction anchors. The
arithmetic and output pairing are Verified; debounce/pulse-width roles remain
Strong inference pending a cabinet or MAME trace.

## Completed target: ROM-side pitch conversion

Mode-aware traversal proves all configured NOTE instructions are YM and resolves
the direct `$5AF9-$5B78` KC view plus the KF preparation path. It also corrects
`$72DC/$5B5B` from pitch to operator total-level processing. The dormant POKEY
lookup has a 97-entry chromatic prefix matching nominal 1.790 MHz joined-divider
targets exactly; the tuning-model interpretation remains Strong inference. Eight catalog
rows capture the overlapping views and corrections.

The selected YM KC/KF checkpoint is also complete. The supplied YMFM register
composition, OPM phase-step table, prescale, and sample-rate formula validate
command `$04`'s zero-KF notes as C4 through C5. All stable chromatic notes
13..97 are within -1.528 to +0.189 cents under the implementation clock, and
the corrected sequence convention is `MIDI=note+11`.

The former command `$3A` raw-note values above 97 are **Contradicted**: they
were inline target-table words decoded as notes. The 16 real targets use
ordinary values `$31-$3F,$44`; configured YM notes span 13..95.

## Active target: timing and clock validation

The clock/cadence checkpoint is complete at Verified hardware-evidence strength.
The upstream MAME 14.318181 MHz clock tree, independently confirmed by a
user-reported schematic calculation on 2026-07-12, and raw video timing derive
239.6909904 IRQ/s, 119.8454952 sweeps/s for each alternating device, and at most
958.7639614 speech service attempts/s. Bounded ROM evidence verifies odd parity
selects POKEY, even parity selects YM, and speech is called four times per IRQ.
The older ~245 Hz estimate is Contradicted.

The cycle checkpoint covers the IRQ shell, both parity dispatches, complete
empty-list consumers, the POKEY write wrapper, three READY speech paths, the YM
busy/timeout helper, and a fully enabled prepared YM output path. The busy wait
is exactly `29 + 13n` cycles before timeout; the 255-poll timeout is 3,347
cycles and later sticky returns are 12 cycles. A configured steady command
`$44` steady comparison path composes `$4651` (291/310 cycles), its pair (566/585), the full
POKEY consumer (929/948), and a quiescent normal complete IRQ
(1,566/1,585 cycles including entry, 20.972%/21.227% utilization).

The immediate consumer-led target is complete: an instruction-level executor
now follows command `$44` from allocation through its first three services.
Initial setup/REST decode costs 1,637/1,656 cycles at `$4651` and a composed
2,912/2,931-cycle IRQ including entry. The next services cost 510/529 and
557/576 at `$4651`; the latter reloads continuing count-`$12` records. This
also corrects the prior false frequency-termination claim.

The first stateful duration checkpoint is complete for command `$04` channels
1..7. Starting from Verified tempo `$10` and a zero timer, they end after 120
through 840 service intervals in exact 120-interval steps; every trace retains
the expected -16 residue. The disassembler's former default-tempo-zero and
exact-120-Hz statistics are corrected.

Tempo and counted-repeat coverage is also complete for selected paths. Command
`$09` validates SET_TEMPO, command `$2A` validates modulo ADD_TEMPO decrements,
and `$8E/$8F` repeats are expanded for commands `$1C/$20`. Command `$20` lasts
6,399 service intervals (53.393747 s), not the former single-body 5.3-second
estimate.

All values of all three Verified-feasible RNG computed jumps are complete.
Commands `$2B/$2C/$3A` have 4/16/16 targets, each taking 60/12/120 intervals
respectively.

Bounded tracing of all five `$99` back edges is complete. Prefix/period pairs
are 480/480 (`$2E`), 15/15 (`$37`), 60/30 (both `$05` channels), and 1,500/480
(`$04` channel 8) service intervals. They are explicitly loop measurements,
not finite durations.

The secondary-timer checkpoint is complete for normal, divided, and sustained
controls. Command `$04` keys off after 58 of 60 sweeps, command `$40`'s `$1A`
control keys off after 4 of 10 sweeps, and the sustained `$69A5` loop re-arms
its `$7Fxx` secondary timer before expiry.

The proposed configured-glide trace is closed as infeasible: no reachable `$8C`
writes vibrato depth, allocation zeros it, and every configured `$86` frequency
envelope is POKEY-mode. The initial multi-opcode/REST path and one configured
`$FF` loop-control path are now bounded. Command `$05` channel 2's `$68F3`
boundary costs 505/524 cycles and rewinds to `$68ED` with repeat `$FF`.

The four-channel composition is now complete: initial `$500D` costs
6,874/6,950 cycles and the composed IRQ costs 7,511/7,587 including entry,
exceeding the nominal interval by 44/120 cycles. Across four phase-aligned
1,000-service traces, only the initial decode overruns. MAME's level assertion
and `$1830` clear imply a pending catch-up IRQ, but a runtime trace still needs
a complete ROM set or cabinet access.

The TMS core also resolves the 17-write zero drain as a full-FIFO-plus-one
padding window and bounds sustained not-ready reset at 32/33 IRQs.

YM voice fields +`$1D-$29` are now resolved. `$1C` is skipped by all found
configured consumers; odd offsets `$1D/$1F/$21/$23` are M1/M2/C1/C2 TL transform
descriptors, and even `$1E/$20/$22` chain correction/index state between
operators. `$9E/$9F` consume `$24-$28/$29`. The 42-row generated catalog
validates all 39 configured `$9D` bases.
Reserved handlers are now closed for current-image semantics and reachability.
Types 1/2/4/6/12/14 have zero configured commands and only handler-table
fixed-point sources; the generated catalog records their exact effects. Their
original development provenance requires another ROM/source and is not
recoverable here. The `$57AE-$57AF` configuration object is also closed: its
only live indices are 0/1 (`$1E/$22`), and `$57B0` proves the exact end.
The final mixed-region classification audit is complete. `$69D6-$72DB` is a
55-by-42-byte instrument grid; 39 records are `$9D`-selected, one is `$9E`-only,
and 15 are unreferenced. Correct `$AE` target-table traversal incorporates all
alternate RNG sequences. Zero mechanically unclassified bytes remain, while
unreferenced records, offset `$1C`, zero trailers, and `$80DA-$80E2` retain
explicit Unknown provenance.

POKEY AUDCTL semantics are no longer part of that open work. The supplied MAME
implementation maps the ROM's configured `$20`, forced `$28`, and forced `$50`
to CH3 high clock, joined 3/4, and joined 1/2 behavior; a tie between the two
internal status lanes selects the joined lane. This is independent of
equal-priority replacement within each physical list. Generated mode traversal
finds no configured POKEY `$9B` clear.

## Subsequent consumer-led targets

The alternate NMI path is now closed for current-ROM mechanics and conditional
reachability. On the `$1030` bit-4-clear full-test branch, `$01=$FF` makes the
first IRQ increment `$00` and release the `$40B2` wait. An earlier NMI can use
the `$0213=0` indirect-write path; external intent is Unknown. `$40D2` later
installs normal `$FF` mode. The bit-4-set fast branch skips the window. Only
`$40D2/$44C3` directly write `$0213`, both with `$FF`. Sender intent remains
external.

The initialization pass is complete: 14 generated blocks cover normal
and self-test boot, RAM/ROM failures, first-IRQ synchronization, common device
initialization, both main-loop queue phases, callable helpers, the `$5A0B`
fixed board-handshake writes, and the `$5A25` RESET-vector status gate.

The `$4187-$4650` control-plane pass is also complete: 32 generated blocks cover
IRQ/BRK handling, global reset, both chip resets, the context pool, all active
handlers, and type-7 allocation. Atomic publication/reclamation/replacement
resolves the prior IRQ-visible partial-list concern.

The `$4B6B-$4D01` support/KF-staging gap is complete: six generated blocks
resolve signed fade/ramp scaling, mode-overloaded state arrays, winner-only YM
TL/live-field staging, dormant vibrato convergence, and KC/KF splitting. The
adjacent `$5C7F-$5D0E` tables are now completely formatted. The stale detune
role at `$5C5B` is contradicted; its exact four-byte extent is reaffirmed as a
TL event/control-bias table after accounting for all four `$082F` shifts.

The completion-oriented code-coverage audit is complete. Generated semantic
catalogs own all 6,681 executable bytes in `$4002-$5A30` and `$8381-$8446`;
five embedded data regions are explicitly excluded and zero executable bytes
are unowned. The audit corrected three initialization instruction boundaries
and separated the `$83A4-$83AB` mask table from code.

The P0 callable-contract completeness audit is complete. All 61 vector,
callable, tail-jump, table-dispatch, list-follow, and synthesized-dispatch
entries have explicit entry/exit, clobber, RAM/I/O, interrupt-context,
configured-reachability, and confidence fields. Ten bytecode helpers and two
NMI entries gained standalone contracts; the combined NMI control-plane row was
split into exact query, restore, and output-latch blocks. This pass also
Contradicted the stale `$5715` detune label: it applies signed carrier-TL deltas.

The completion classification audit records eleven remaining questions: five
concern historical author/build intent that is not recoverable from this image,
five require a comparison ROM, runtime trace, original source/listing, or
cabinet measurement, and one is an available cross-image static follow-up. The
companion main-game/OS analysis, hardware write-up, and MAME device sources are
incorporated; they resolved the boot-handshake decode and startup-command
sender. They also revealed that game-side command use still needs a
dataflow-complete emitter catalog: `$D7` is used at game `$44F68`, while the
present companion summary omits table-fed `$22-$25`.
The one remaining startup question is whether `$00`, written while sound reset
is asserted, is delivered as a post-release NMI. The audit reports zero remaining
sound-ROM-only static tests; the companion emitter catalog is the one remaining
actionable static analysis. Preserve the other confidence boundaries until one
of their evidence classes becomes available.

The practical type-7 WAV renderer is also complete at ROM/chip-implementation
strength. It executes the real 6502 reset, command allocation, and IRQ audio
service paths to obtain shared POKEY and YM2151 register writes. POKEY rendering
uses one four-channel device at the Verified clock; YM rendering compiles and
uses the supplied YMFM core. The former POKEY tempo-2 override, independent-chip
mixing, and hand-written YM approximation are bypassed. Remaining audio-output
uncertainty is limited to cabinet analog mixing/filtering and runtime RNG phase.

## Current checkpoints

Do not restart completed traversals unnecessarily.

- CPU fixed point: 70 batches, empty queue, 458 classified entries, 307
  internal labels, all 59 opcode entries and 54 unique handler starts visited.
- Conservative type-7 map: 2,166 instructions, 4,670 bytes, 72 explicit
  edges, zero decode errors.
- Feasibility-pruned type-7 map: identical 2,166 instructions and 4,670 bytes.
- Conditional sites: 31 Verified single-index tables and three Verified with
  every POKEY-RNG target-table index feasible; none unresolved.
- Mixed-region direct CPU audit: 37 candidates, nine aligned references, 28
  rejected byte coincidences.
- All five known constructed mixed-region pointer classes are catalogued.
- Runtime envelope traces:
  - `$68D6-$69FF`, zero termination after 12,583 envelope updates;
  - `$68F3-$69AF`, zero termination after 71,171 envelope updates.
- Current mixed-region mechanically unclassified total: zero bytes. Fifteen
  unreferenced YM records, offset `$1C`, 56 unreachable zero trailer bytes,
  and one nine-byte sequence candidate retain explicit provenance/use Unknowns.
- Semantic executable coverage: 6,681 owned bytes, zero unowned bytes, and five
  explicit embedded-data exclusions across both code islands.
- Entry-contract coverage: 61 externally meaningful CPU entries complete,
  zero missing, across ten entry kinds.

## Evidence and tooling constraints

Follow `09_analysis_method.md` exactly. In particular:

- use the documented raw 6502 mapping and verify vectors/RESET first;
- do not run broad automatic analysis;
- keep r2mcp batches at or below 64 instructions;
- maintain traversal state outside r2mcp;
- stop all r2mcp calls immediately after an error or rejection;
- treat automatic functions, pseudocode, and `gauntlet_disasm.py` behavior as
  hypotheses until checked against instructions and consumers;
- preserve existing workspace changes and avoid unrelated files.

Use the canonical confidence labels: **Verified**, **Strong inference**,
**Hypothesis**, **Unknown**, and **Contradicted**.

## Required completion behavior

Update canonical chapters and generated catalogs as evidence changes. Revise
`10_known_issues.md` when priorities or next tests change. Run every
regeneration and regression command in `09_analysis_method.md` before handing
off.

Report concrete function findings, consumer-derived data formats, files and
catalogs changed, validation performed, remaining uncertainty, and the next
consumer-led test.
