# 10 — Known Issues and Research Backlog

This is the reference list of unresolved work, and the place to add an item when
one is found. Items are ordered roughly by impact.

"Reference" is not the same as complete. A later consistency audit of `book/`
turned up errors that were not on this list and could not have been, because
each individual claim looked sound and only the *combination* was wrong — two
generated catalogs whose scripts modelled the ROM incorrectly, and a ROM bug
that two different plausible record counts had been covering up. Both are
written up where they belong (`06_sequence_engine.md`, `04_subsystems.md`,
`02_memory_map.md`). Treat an empty backlog as "nothing currently known",
never as "nothing left".

Current execution order and new-context instructions are maintained in
[`NEXT_STEPS.md`](NEXT_STEPS.md). That handoff prioritizes consumer-led code and
function analysis; exhaustive byte-level cleanup is deferred.

**Completion classification (2026-07-12):** all current-image static tests in
this backlog are exhausted. `external_question_catalog.csv` classifies the 12
remaining questions: five are historical-intent questions not recoverable from
this image and seven require missing runtime/hardware/main-CPU/comparison-ROM
evidence. `external_evidence_inventory.csv` verifies that none of the required
artifact classes is present in this workspace.

The generated question catalog names the canonical section, exact missing
evidence, completed static result, and confidence for each item. These are
evidence-bound residual questions, not undiscovered sound-ROM code semantics.

## P0 — Exact type-7 segment map

**Known:** 182 reachable records, 153 distinct entry pointers, pointer span
`$6569-$8378`, and chip/channel assignments are catalogued. The corrected
bounded traversal records 2,166 instructions, 4,670 consumed bytes, 72 explicit
control-flow edges, and 189 support-data references. It has zero decode errors.

**Known:** `$AE/$AF` do not have a conventional target/fallthrough form.
`$5320/$5347` index an inline little-endian target table by the masked register
value and always replace the sequence pointer. Thirty-one `$AB 00` sites select
their sole entry. The three POKEY-RANDOM sites use one four-entry and two
sixteen-entry tables; supplied 9- and 17-bit polynomial domains reach every
index. The old nonzero-fallthrough decode and its timing results are
**Contradicted**.

**Known:** the final mixed-region audit leaves zero bytes labeled
`unclassified_no_type7_reference`. `$69D6-$72DB` is a Verified 55-by-42-byte YM
instrument-record grid: 39 records are `$9D`-selected, one additional record is
`$9E`-only, and 15 are structurally valid but have no configured reference.
The audit also classifies 56 zero bytes after unconditional sequence-pointer
replacement as Verified unreachable trailers and `$80DA-$80E2` as a valid but
unreferenced nine-byte sequence candidate.

**Known:** direct CPU xrefs, all five constructed mixed-region pointer classes,
and runtime-crossed frequency-envelope reads are exhaustively represented in
generated catalogs. `$68D6` reads through `$69FF` and stops after 12,583
updates; `$68F3` reads through `$69AF` and stops after 71,171. These overlapping
runtime views do not redefine packed object boundaries.

**Unknown:** 17 envelope packed ends remain **Strong inference**; offset `$1C`
of each YM record is skipped by all configured consumers; the 15 unreferenced
instrument records, the nine-byte sequence candidate, and the unreachable zero
trailers have unknown original provenance/use. Zero mechanically unclassified
bytes therefore does not mean zero historical-intent unknowns.

**Next test:** no further static mixed-region consumer is currently indicated.
Compare other Atari sound-ROM revisions/source listings for the unreferenced
records, offset `$1C`, and `$80DA-$80E2`; otherwise preserve their explicit
Unknown provenance rather than guessing names.

## P0 — Complete 6502 entry-point and control-flow inventory

**Known:** the bounded direct/table-target traversal reached fixed point after
70 successful batches. All 59 opcode entries and 54 unique bytecode-handler
starts were visited; `cpu_entry_catalog.csv` classifies 458 entries, including
307 internal basic-block labels.

**Resolved static contract inventory:** all 61 vector, callable, tail-jump,
table-dispatch, list-follow, and synthesized-dispatch entries now have explicit
entry, exit, clobber, RAM/I/O effect, interrupt-context, configured-reachability,
and confidence fields in `cpu_entry_contract_catalog.csv`. Grouped internal
basic-block labels remain owned by semantic ranges rather than being promoted
to false standalone functions. No known direct/table target lacks a contract.

**Unknown external reachability:** indirect targets not represented by the
verified ROM tables and exact path frequencies require a runtime trace. No
static evidence indicates an additional target class.

**Next test:** compare a complete-ROM MAME/cabinet control-flow trace against
the fixed-point catalog; treat any new indirect target as a new finding.

**Current semantic-coverage progress (2026-07-12):** the generated range join
owns all 6,681 executable bytes in `$4002-$5A30` and `$8381-$8446`, with zero
unowned bytes and five explicit embedded-data exclusions. This is complete
location/range coverage, not a claim that every internal label has a standalone
contract. The subsequent 61-entry contract audit reports zero missing entries.

**Current initialization/main-loop progress (2026-07-12):** initialization and
RESET code is decomposed into 14 generated blocks backed by 16 anchors. Normal boot skips
diagnostics after clearing zero page; active self-test performs destructive RAM
tests over `$0000-$0FFF`, verifies three 16-KiB modulo checksums equal `$FF`,
and synchronizes on the first early IRQ. Fatal and recoverable error classes,
common device initialization, one-byte-per-iteration output/input queue service,
the `$415F/$4183` helper contracts, fixed `$5A0B` board-handshake writes, and
the `$5A25` RESET-vector status gate are Verified.

**Current control-plane progress (2026-07-12):** `$4187-$4650` is decomposed
into 32 generated blocks backed by 27 anchors. IRQ/BRK recovery, atomic global
reset, both chip-reset paths, the 198-record context pool and its misplaced
sentinel, all 15
handler targets, every active handler, and complete type-7 admission/state/list
insertion are Verified. New-slot publication, head reclamation, and equal-
priority replacement prove IRQ-safe list mutation; the former partial-list
visibility concern is **Contradicted**.

**Current support-staging progress (2026-07-12):** `$4B6B-$4D01` is decomposed
into six contiguous blocks backed by 12 anchors. Signed fade/ramp scaling,
fraction accumulation, mode-overloaded POKEY-pointer/YM-TL arrays, winner-only
TL/live-field staging, dormant vibrato convergence, and KC/KF splitting are
Verified. `$5C7F-$5C8E` is a 16-byte fade shift/control table and
`$5C8F-$5D0E` is exactly 8×16 signed POKEY volume shapes. The old four-byte
YM-detune role is **Contradicted**, while the corrected shift trace reaffirms
its exact `$5C5B-$5C5E` extent as a four-entry TL event/control-bias table. No
functional Unknown remains in this gap.

**Current consumer-led progress (2026-07-12):** `$4651-$4B6A` is decomposed
into 14 generated rows backed by 15 validated instruction-byte anchors. Direct
callers `$4D36/$4D84/$4E7A`, the X/list-head entry contract, the `$4B5D`
tail-loop, and the sole RTS at `$4B6A` are Verified. Allocation-side interrupt
safety, transitive callable contracts, and representative exact timing are now
resolved elsewhere; only configured runtime path frequencies require tracing.

**Current physical-output progress (2026-07-12):** `$4D02-$500C` is decomposed
into 10 generated blocks and seven consumer table rows backed by 26 validated
instruction anchors. POKEY pair arbitration and all four AUDF/AUDC writes,
eight-channel YM iteration, busy-wait timeout behavior, and the two 256-byte YM
conversion lookups are Verified. Stable zero-KF KC conversion is now validated
against YMFM; the proposed configured YM portamento path is absent. One
configured `$FF` envelope-loop channel and the fresh whole-command `$05`
composition are now closed. Representative
steady `$4651`, POKEY pair/device, board, and complete IRQ paths are now
composed. POKEY AUDCTL carry/mask semantics are Verified against the supplied
MAME implementation. Subsequent bytecode-consumer work is recorded below.

**Current progress (2026-07-11):** a fresh session opened `soundrom.bin` first,
applied the raw map, and verified the map, vectors, RESET prefix, envelope
consumers, and `$8378-$8381` transition. Seventy successful traversal batches
are persisted in the generated batch/state catalogs. Verified entry-kind
corrections include RESET tail-jump `$4002`, main-loop tail-jump `$40C8`,
callable-with-tail-exits `$41C8`, NMI table entries `$44A8/$44B8`, callable
helper `$44C8`, and handler-table entry `$44DE`. The queue is now empty and the
fixed-point derived catalog is complete for known direct/table targets. The pass has additionally
verified JSR entries `$4B6B/$4C16/$5029/$558F` and demoted `$4719/$4809/`
`$49A5/$4B45/$4B5D` to internal basic-block labels. `$4D02` has verified JSR
callers at `$4E0F/$4E36`, and `$4E68` is called at `$4FE4`. `$4DFC/$4FD6` are
now Verified tail-jump targets of `$500D`; `$5029/$506F` are callable indirect
dispatchers. The NMI vector path and its `$582D` synthesized table dispatch
are now traversed, `$5755` is a Verified tail-jump entry, and `$5894` is
Verified as both callable and a tail-jump destination.

The original vector/call/table-derived queue is drained. The final pass has
seeded all 59 bytecode opcode-table entries: 54 unique targets, with two already
visited and 52 initially queued as bytecode handlers. All 52 have now been
visited and the external queue is empty. The derived catalog contains 458
classified entries, including 307 internal basic-block labels. A
mid-instruction continuation at `$527F`
was detected from the structured listing and corrected to `$5280`; the bogus
single decode was excluded from the saved batch.

## P1 — Frequency table conversion

**Known:** the older single-table interpretation is **Contradicted**. The code
has overlapping views: `$5A35-$5B34` is a 128-word possible POKEY lookup, but
only entries 1..97 are a chromatic divider prefix; `$5AF9-$5B78` is the full
128-byte YM note-to-KC view. Its indices 98..127 alias the first 30 bytes of
the total-level table at `$5B5B`. Mode-aware traversal of all 2,166 sequence
instructions finds 64 distinct NOTE values, all in YM mode (13..95), and no
configured POKEY NOTE instruction.

**Known:** the POKEY prefix exactly matches rounded joined-divider targets for
a nominal 1.790 MHz clock, equal temperament, MIDI=note+11, and the hardware
`combined_AUDF+7` rule. This is a **Strong inference** about table generation,
not proof of the board oscillator. YM KC is read directly at `$4EEC`; KF is
prepared by `$4C16` and written earlier to `$30+channel`.

**Known:** applying the upstream MAME master/8 POKEY clock (1,789,772.625 Hz)
to the ROM's dormant chromatic prefix yields errors from -3.876 to +2.227 cents
over notes 1..97, with a -0.232-cent mean. This corroborates the prior nominal
1.790 MHz generation model.

**Known:** the supplied YMFM source composes OPM pitch from KC register `$28`
bits 6..0 and KF register `$30` bits 7..2. Its prescale/operator constants and
phase-step equation produce a 55,930.39453125 Hz sample rate and
`frequency = phase_step * sample_rate / 2^20` under the implementation clock.
The command `$04` voice has base KF zero; its eight notes validate as C4 through
C5 within -0.500 to +0.189 cents. All stable chromatic ROM notes 13..97 fall
within -1.528 to +0.189 cents, establishing `MIDI=note+11`. Exact rows are in
`generated/ym_pitch_validation_catalog.csv`.

**Known:** the earlier command `$3A` high-note evidence is **Contradicted**.
`$7D27-$7D46` is `$AE`'s 16-entry target table, and its targets use ordinary
notes `$31-$3F,$44`. No configured note reaches alias indices 98..127.

**Known:** no configured nonzero-vibrato/glide path exists. Mode-aware traversal
finds no SET_VIBRATO `$8C`; `$51E2` is the sole opcode write to `$0660`, and
allocation zeros it. The zero-depth path at `$48CA-$48D5` clears
`$067E/$069C`. All 13 configured SET_FREQ_ENV `$86` operations are POKEY-mode,
so they cannot activate YM `$4C69-$4CBD`. That block remains real code but is
**Verified dormant under configured sequences**.

**Verified external clock evidence:** an independent calculation from the board
schematic confirms the 14.318181 MHz master and derived clocks (user-provided
confirmation, 2026-07-12). The schematic artifact is not present in this
workspace. The intended dormant YM interpolation semantics and whether dormant
POKEY NOTE handling was intended for another configuration remain **Unknown**.

**Next test:** defer dormant interpolation semantics unless another ROM revision
selects `$8C`.

**Corrected consumer evidence:** `$4EEC` writes KC, but `$4EFF-$4FB1` writes
operator total-level registers `$60-$7F`. Therefore `$72DC-$73DB` and
`$5B5B-$5C5A` are nonlinear/scaling volume transforms, not pitch transforms.
The older frequency labels are **Contradicted**.

## P1 — Envelope and voice data formats

**Known:** bytecode opcodes point to frequency envelopes, volume envelopes, and
YM2151 voice/register blocks. Some interpreter behavior exists in the tool.

**Unknown:** exact packed bounds for the 17 envelopes that remain Strong
inference, original intent of instrument offset `$1C`, and whether every
human-facing field name captures original author intent. Consumer grammar and
all other configured field behavior are resolved.

**Next test:** leave candidate envelope ends at Strong inference unless a new
consumer resolves them; compare another ROM/source for offset `$1C` intent.

**Current consumer result (2026-07-12):** all 59 opcode-table rows are resolved
with an exact dispatch/carry contract. The `$9D` consumer verifies a 28-byte YM
register image; `$9E` verifies five bytes at operand+`$24`; `$9F` verifies one
byte at operand+`$29`. The complete grid has 55 42-byte records and the 39
configured `$9D` bases now have a 42-row field catalog. Offset +`$1C` is
skipped by `$4C16` and has no found configured consumer;
+`$1D/$1F/$21/$23` are per-operator TL transform descriptors, while
+`$1E/$20/$22` chain correction/index state between M1, M2, C1, and C2. The
former +`$1D-$23` grammar Unknown is resolved. The
`$5755` consumer extends through `$578F` and proves a 16-byte carrier-TL
attenuation table at `$5790-$579F`. `$5715` changes algorithm-selected operator
TL bases, not KC/KF or YM detune; the former detune label is **Contradicted**.

## P1 — Timing

**Known:** the upstream MAME configuration uses a 14.318181 MHz master, raw
456x262 video timing at master/2, 6502 and POKEY at master/8, YM2151 at master/4,
and TMS5220 at master/2/11 or master/2/9. Its 32V schedule gives exactly four
sound IRQ assertions per frame: 239.6909904 IRQ/s. The older ~245 Hz estimate
is **Contradicted**.

**Known:** ROM instructions independently verify odd `$00` parity selects the
POKEY pass, even parity selects the YM pass, and `$5894` is invoked four times
per IRQ. Thus each device sweep is 119.8454952 Hz (8.344077 ms) and speech has
at most 958.7639614 service attempts/s under that clock configuration.

**Known:** branch-qualified counts cover three IRQ-shell paths, both parity
dispatch paths, complete empty-list device consumers, and three READY speech
paths. Empty POKEY takes 518 cycles with `$13=0`, including hardware writes;
empty YM takes 373 cycles with no writes. Speech takes 76 cycles for idle/empty
queue, 78 for Speak External, 83 for a normal non-wrapping payload write, and
76 for a drain-zero write.
The primary sequence timer is a carried phase accumulator, so per-note
`ceil(duration/tempo)` is not a generally exact conversion.

**Known:** a stateful trace of command `$04` channels 1..7 starts from the
Verified allocation state (tempo `$10`, timer zero) and ends after exactly 120
through 840 service intervals in 120-interval steps. At the implementation
clock this is 1.001289 through 7.009024 seconds. Every stream finishes with
signed residue -16. The disassembler's former tempo-zero/120-Hz statistics are
**Contradicted** and corrected for default tempo and service rate.

**Known:** selected tempo/control traces are now stateful. Command `$09` uses
SET_TEMPO `$F0 -> $3C` and ends after 104 intervals. Command `$2A` verifies raw
modulo ADD_TEMPO decrements and ends after 68 intervals at tempo 6. Extended
repeat `$8E/$8F` executes command `$1C`'s body twice (274 intervals) and command
`$20`'s sustained note ten times (6,399 intervals, 53.393747 s). The former
single-body command-`$20` estimate is **Contradicted**.

**Known:** all 36 values across the three Verified-feasible POKEY-RNG computed
jumps are traced. Commands `$2B`, `$2C`, and `$3A` select 4/16/16 one-note
targets; every target lasts 60/12/120 service intervals respectively and ends
with residue -16. Target feasibility and finite duration are Verified, while
value probabilities remain runtime-dependent.

**Known:** every `$99` edge is a tight self-loop with a stable carried-residue
period. Prefix/period pairs for `$2E`, `$37`, `$05` channels 1/2, and `$04`
channel 8 are 480/480, 15/15, 60/30, 60/30, and 1,500/480 intervals. These are
bounded prefix/period facts, not finite command durations. The disassembler now
labels them as decoded loop prefixes instead of estimated play times.

**Known:** the POKEY register-write wrapper is 184..186 cycles excluding its
two pair consumers. The YM busy helper is 29 cycles when immediately ready,
`29 + 13n` after `n` busy polls, 3,347 cycles on the 255-poll timeout, and 12
cycles after the sticky timeout flag. A prepared fully enabled active YM output
path with 14 immediately-ready checks is 1,351 cycles; first- and last-check
timeout placements are 4,448 and 4,669 cycles respectively. Fourteen separate
254-poll-then-ready checks form a 47,579-cycle arithmetic stress bound, not an
expected hardware path.

**Known:** supplied POKEY definitions resolve the control masks. Configured
POKEY `$8B` operations only OR CH3_HICLK `$20`; no `$9B` clear is reachable.
Second-member wins or ties return carry set and force `$28` (CH3_HICLK plus
CH34_JOINED) or `$50` (CH1_HICLK plus CH12_JOINED). Active tie/first-win
arbitration suffixes take 73/100 cycles; threshold-suppressed variants take
100/127 cycles. These suffix counts exclude `$4651`.

**Known:** secondary-timer articulation is validated for normal, divided, and
sustained controls. Command `$04` channel 1 keys off after 58 of 60 sweeps;
command `$40` at `$743E` uses control `$1A` to halve the secondary timer and
keys off after 4 of 10 sweeps; command `$04`'s sustained `$69A5` loop re-arms
secondary high byte `$7F` every 480 sweeps before expiry. Exact state rows are
in `generated/timing_articulation_trace_catalog.csv`.

**Known:** configured command `$44` provides a one-active-channel steady POKEY
case. `$4651` costs 291 cycles normally and 310 on the `$00&6=0` rotate phase;
the one-active pair costs 566/585, and the complete POKEY consumer costs
929/948. With four READY-idle speech calls and a 201-cycle quiescent normal
board path, the complete idle-mixer IRQ costs 1,566/1,585 cycles including
interrupt entry, 20.972%/21.227% of the 7,467-cycle interval. These are
representative configured paths, not worst-case bounds.

**Known:** command `$44` has an instruction-executed three-service trajectory.
Its initial six-opcode/REST decode costs 1,637/1,656 cycles at `$4651` and a
composed 2,912/2,931-cycle IRQ including entry (38.998%/39.253%). Service two
costs 510/529 at `$4651` because its two envelopes decrement and the secondary
timer expires; service three costs 557/576 while both envelopes reload
count-`$12` records. The former claim that frequency `12 00 00` terminates was
wrong: `A=$12` keeps the ROM's OR test nonzero.

**Known:** command `$05` channel 2's configured `$68F3` `$FF FF 06` boundary
costs 505/524 cycles at `$4651` (145/149 instructions). It rewinds the base to
`$68ED`, loads repeat `$FF`, and reloads count `$FC`.

**Known:** the complete fresh command `$05` POKEY consumer is 6,874/6,950
cycles. The representative complete IRQ is 7,511/7,587 cycles including entry,
44/120 cycles longer than the nominal interval. Four 1,000-service traces, one
per phase alignment, each overrun exactly once at this initial decode; the
largest later complete IRQ is 4,838 cycles. MAME asserts the timed IRQ as a
level and `$1830` clears it, so a next assertion during the long handler stays
pending for catch-up after RTI (**Strong inference** without a runtime trace).

**Known:** the TMS5220 core has a 16-byte FIFO, starts external TALK after nine
bytes, and aborts on premature FIFO-empty. The ROM's `$11` drain state performs
17 accepted zero writes, providing a full-FIFO-plus-one padding window after
the stop-coded payload. The not-ready watchdog resets after exactly 32 or 33
IRQ intervals (133.505/137.677 ms under the implementation clock).

**Verified external clock evidence:** the implementation clocks agree with an
independent calculation from the board schematic (user-provided confirmation,
2026-07-12). Phrase-specific successful TMS5220 FIFO write timing and an actual
MAME or cabinet trace confirming the inferred catch-up IRQ and zero-drain
behavior remain **Unknown**.

**Next test:** capture selected MAME/cabinet traces when a complete Gauntlet ROM
set and trace-capable runtime are available. The supplied local refs contain
device cores only.

**New speech-timing evidence (2026-07-12):** `$5894` is called four times per
IRQ. Each ready service performs at most one TMS5220 data/command write. `$33`
schedules a reset pulse at frame-counter deltas 8 and 0, and `$30` implements a
phase watchdog for sustained not-ready status. Under the implementation clock
this is 958.7639614 service attempts/s, but successful writes and watchdog
latency remain path- and READY-dependent.

## P1 — Speech drain and watchdog hardware behavior

**Known:** `$2F=$80` writes Speak External `$60`, `$FF` streams payload, and
length exhaustion enters `$11..0`. During that drain, each ready service writes
zero and pulses the strobe. The active-low-ready watchdog can tail-reset all
speech state through `$5833`.

**Known:** the supplied TMS5220 core establishes a 16-byte FIFO, TALK startup
after the ninth byte, FIFO-empty abort behavior, and stop-frame shutdown. The
ROM's 17 accepted zero writes therefore provide a full-FIFO-plus-one padding
window so the stop frame can be parsed without a premature empty abort. The
watchdog expires after exactly 32/33 IRQ intervals, 133.505/137.677 ms under
the implementation clock.

**Unknown:** whether cabinet traces ever reach the reset path during normal
phrases and phrase-specific successful-write cadence under READY stalls.

**Next test:** compare `$1820/$1031/$1032` traces against a TMS5220 device trace
for normal completion, delayed-ready, and forced-not-ready cases.

## P1 — Reserved handler types

**Known:** types 1, 2, 4, 6, 12, and 14 have code targets but zero configured
commands. Fixed-point sources contain only their handler-table entries. Types
1/2 set/add workspace bytes from sliding `$6559/$655A` pairs; type 4 soft-kills
logical channels by encoded status class; type 6 soft-kills a selected physical
list; type 12 validates a target type-7 command then applies only safe opcode
ranges to matching active channels through `$5059/$506F`; type 14 is a null
RTS. The six support bytes `$6559-$655E` are zero, making the type-12 zero view
fail target validation. Exact rows are generated.

**Unknown:** original provenance—development leftovers versus features for
another ROM revision. This cannot be distinguished from the current ROM,
which has no configured or direct runtime source for them.

**Next test:** compare with related Atari sound ROM revisions or source listings
if supplied; no further current-image consumer work remains for these entries.

## Resolved — `$57AE-$57AF` hardware configuration view

**Known:** three parallel two-byte views at `$57A8/$57AA/$57AC` produce
hardware bases `$1800/$1810` and types 0/2. The separate exact two-byte table
at `$57AE-$57AF` contains physical-list-head bases `$1E/$22`.

**Known:** `$4DFC` reads index 0 (`$1E`) for the two POKEY pairs; `$4FD6` reads
index 1 (`$22`) then iterates eight YM heads `$29..$22`. Dispatcher X is
Verified 0/1. `$57B0` is the independently reached NMI entry, proving the table
ends at `$57AF`. Dormant type 6 is the only broader indexer, but has no
configured command or input domain.

No current-image unknown remains for this object.

## Resolved — `$082F` event control and unused zero-page bytes

**Known:** a linear decode of every semantic-owned code interval covers 3,199
aligned instructions and finds exactly 11 direct `$082F` references. Producers
clear it, set key-off bit 0, set new-note/key-on bit 2, and stage bits 5..4 plus
mandatory refresh bit 1. `$4EBB/$4ED5` destructively consume bits 0/1;
`$4FBD` consumes original bit 2; `$4F0E/$4F14` reduce original bits 5..4 to
indices 0..3 of `$5C5B-$5C5E`. Bits 7..6/3 have no producer or live consumer.

**Known:** `$3A-$3D/$43` have no aligned direct/pointer reference. All nine
nearby indexed candidates are `$36,X` or `$3E,X` in the board routine, whose
Verified X=3..0 domain ends at `$39/$41`. They are unused storage in this ROM,
apart from blanket RAM clearing and the externally driven boot indirect-write
window. Generated reference and semantic rows preserve both proofs.

No current-image semantic unknown remains for these RAM bytes.

## P2 — Board-control routine `$8381`

**Known:** the complete bounded transition map is generated. Active-low
self-test mode maps four active-low inputs directly to four two-bit `$44`
fields. Normal inactive/high operation uses four saturating `$21`-step filters
at `$3E-$41`; threshold crossings update `$44` and increment `$36-$39`. Every
other IRQ, nonzero `$36-$39` states form
the exact sequence `$F0,$E0,...,$10,0`. `$36|$37` drives physical left counter
`$1035`, and `$38|$39` drives physical right counter `$1034`.

**Strong inference:** `$3E-$41` implement debounce/integration and `$36-$39`
stretch counter pulses. This matches the state arithmetic and mechanical output
identity, but intended self-test presentation and cabinet behavior still need
external runtime evidence. Earlier normal/self-test path labels were
**Contradicted** by the active-low hardware definition plus the `$8386` branch.

**Next test:** compare input, `$44`, and `$1034/$1035` traces with main-CPU
self-test behavior or a cabinet/MAME execution trace; map the four inputs to
named player/slot positions.

## Resolved mechanics — Boot handshake bytes

**Known:** `$FF,$33,$00,$22,$0F` are written once to
`$1003,$1002,$100B,$100C,$1000`. These are **not** five separate registers. The
board does not decode the low four bits of `$1000`–`$100F`, so all five addresses
are the one sound→main latch — confirmed by the schematic and by MAME
(`map(0x1000,0x100f).mirror(0x27c0).w(m_mainlatch)`). The handshake is therefore
five overwriting writes to the mailbox, followed a few instructions later by the
`$FF` boot acknowledgement (`$40E9`). The companion game-ROM (68010) disassembly
reads none of the intermediate bytes; the only value the game acts on is that
final `$FF` (game routines `sound_response` / `sound_system_reset`).

**Remaining (historical, not hardware):** the code targets four distinct
addresses with four distinct values as hardcoded load/store pairs — a
five-register init. On this board those registers do not exist, so the writes are
vestigial, most likely inherited from a sibling board/game. Which hardware, and
what the registers drove, would need a sibling ROM or that board's schematic; it
is not answerable from either Gauntlet II ROM and does not affect this board's
behavior.

## Resolved mechanics — Alternate NMI diagnostic-window indirect write

**Known:** when `$1030` bit 4 is clear, the full RAM test's final pass zeros all `$0000-$0FFF`, including
`$04/$05`, `$0212/$0213`, and `$00`. Initialization sets `$01=$FF` and executes
CLI at `$40B2`; the early IRQ path increments `$00`, normally releasing this
first-IRQ synchronization wait. An NMI arriving first while `$0213=0` takes
`$57BD-$57DC`, which writes each `$1010` byte
through `($04),Y` and advances/transforms its index/pointer state. `$40D2` then
sets `$0213=$FF` before normal operation. An exhaustive direct-write scan finds
only `$40D2` and `$44C3`, both selecting `$FF`; the bit-4-set fast branch skips
the window and goes directly to `$40C8`. `$01-$FE` are drop/ack modes
with no direct current-ROM selector. Generated rows and anchors preserve the
proof.

**Unknown external provenance:** whether the main CPU intentionally sends any
byte during this short diagnostic window and, if so, the intended sequence.
The mechanics and conditional current-ROM reachability are resolved; naming requires the
main-CPU sender or source listing.

## P2 — Small unreferenced ROM regions

**Known:** `$FECE-$FFF5` is zero padding. `$8447-$8448`, the unindexed `$FF` at
`$FECD`, and `$FFF6-$FFF9` have no currently known references. `$6000-$6023` is **not** unused; it belongs
to the type-7 flag table. `$5874-$5893` is referenced dummy speech data.

**Unknown:** whether `$8447-$8448` and `$FFF6-$FFF9` are build metadata,
alignment residue, or obscure data references.

**Next test:** code and bytecode xrefs plus semantic executable coverage are
complete and find no consumers. The likely-unused total remains 303 bytes;
compare another ROM/source image if original build intent matters.

## P2 — Command descriptions and game-side use

**Known:** handler mechanics and ROM metadata are catalogued. Human descriptions
come from a legacy CSV and game knowledge.

**Unknown:** whether commands labeled “Not Used” are truly never emitted by the
main game CPU; exact user-visible meaning of some diagnostic/control commands.

**Next test:** inspect main-CPU command emitters or capture gameplay traces.

## Tooling issues

- **Current r2mcp state (2026-07-12):** the latest raw-mapped session completed
  the consumer checks used for scheduler, YM-field, reserved-handler, and
  `$57AE` conclusions and was closed cleanly. The persisted fixed-point CPU
  traversal remains batch 70 because these bounded checks did not add new
  callable-entry seeds.

- The previous r2 session stopped after structured RESET function disassembly
  returned “Linear size differs too much from the bbsum.” Follow the fresh-
  session and stop-on-failure rules in `09_analysis_method.md`.
- `gauntlet_disasm.py` score/MIDI summaries remain executable hypotheses where
  they use mean timing. Type-7 WAV control and register generation now execute
  the actual ROM reset, dispatch, scheduler, sequence engine, and output paths;
  YM synthesis uses supplied YMFM and POKEY uses one shared four-channel model.
  Cabinet analog mixing, exact board filtering, and runtime RNG phase still
  require external validation.
- Historical reports contain contradictions. Do not copy claims from them into
  this directory without revalidation.
