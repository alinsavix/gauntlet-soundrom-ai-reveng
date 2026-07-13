# 05 — Data Reference

This chapter is the canonical human-readable table catalog. Generated row-level
catalogs live under [`generated/`](generated/README.md).

## Command dispatch tables

| Name | Range | Count/format | Indexed by | Consumer |
|---|---|---|---|---|
| NMI validation | `$5D0F-$5DE9` | 219 bytes | command `$00-$DA` | NMI `$57B0` |
| Handler type | `$5DEA-$5EC4` | 219 bytes | command | dispatcher `$432E` |
| Handler parameter | `$5EC5-$5F9F` | 219 bytes | command | selected handler |
| Type-3 targets | `$5FA0-$5FA7` | 4 target-minus-one words | parameter | handler `$4369` |
| Handler addresses | `$4633-$4650` | 15 target-minus-one words | handler type | dispatcher |

The type-3 target table is deliberately overlapped: entries 1..3 at `$5FA2`
are also the NMI direct-dispatch table. Only type-3 parameter 0 is selected by
the command table.

## Type-7 sequence tables

| Name | Range | Format | Meaning |
|---|---|---|---|
| Start offset | `$5FA8-$5FE5` | 62 bytes | Parameter → first record 0..181 |
| Command flags | `$5FE6-$6023` | 62 bytes | All `$FF` in this ROM |
| Priority | `$6024-$60D9` | 182 bytes | Record → playback/preemption priority |
| Hardware channel | `$60DA-$618F` | 182 bytes | 0..3 POKEY, 4..11 YM2151 |
| Sequence pointer | `$6190-$62FB` | 182 LE words | Record → bytecode entry |
| Next offset | `$62FC-$63B1` | 182 bytes | Record → next record; zero terminates after current record |

Every record offset 0..181 is reachable from exactly one of the 62 parameter
starts. Some sequence pointers are shared by multiple physical-channel records:
182 records reduce to 153 distinct entries.

Zero has context-sensitive meaning: it is valid as the initial offset selected
by parameter 0, but terminates when read as a next link.

## Speech metadata and corpus

| Name | Range | Format | Observed values/use |
|---|---|---|---|
| Speech index | `$63B2-$643E` | 141 bytes | Parameter 0..140 → index 0..188 |
| Speech clock flags | `$643F-$64CB` | 141 bytes | 114 × `$00`, 27 × `$80` |
| Speech priority | `$64CC-$6558` | 141 bytes | 134 × 0, 1 × 4, 6 × 64 |
| LPC pointers | `$8449-$85C2` | 189 LE words | Gapless stream starts |
| LPC lengths | `$85C3-$873C` | 189 LE words | Byte lengths |
| LPC payload | `$873D-$FECC` | 30,608 bytes | 189 variable-length streams |

All 141 type-11 parameters are used exactly once. They select 141 real speech
streams. The remaining 48 indices each select a one-byte immediate-stop stream.

Clock flag `$80` is set for commands `$76-$80`, `$89-$8A`, `$A9-$B5`, and
`$BC`. Priority `$40` is used by urgent time-pressure phrases `$A1-$A6`;
priority 4 is used only by `$BC`.

## Sequence-engine tables

| Name | Range | Format | Status |
|---|---|---|---|
| Opcode jump table | `$507B-$50F0` | 59 target-minus-one LE words for `$80-$BA` | Verified |
| YM carrier attenuation | `$5790-$579F` | 16 signed bytes selected by SET_VOLUME low nibble | Verified |
| YM algorithm carrier masks | `$57A0-$57A7` | 8 one-byte operator masks | Verified |
| Duration table | `$5C5F-$5C7E` | 16 LE words | Verified |
| Fade/ramp rate control | `$5C7F-$5C8E` | 16 shift/control bytes | Verified |
| POKEY volume shapes | `$5C8F-$5D0E` | 8 rows × 16 signed bytes | Verified; rows 0,1,4,5,7 configured |
| POKEY note lookup view | `$5A35-$5B34` | 128 LE words | Consumer extent verified; entries 1..97 are chromatic divider prefix |
| YM key-code view | `$5AF9-$5B78` | 128 bytes | Note → KC; tail overlaps total-level scale table |

`generated/channel_engine_catalog.csv` records the bounded consumers: duration
lookup at `$485B`, frequency-envelope initialization/stepping at `$4954/$49C5`,
and volume-envelope initialization/stepping at `$4981/$4A90`. `$4B0D` indexes
`$5C8F,Y`; `$03AE=(event_control&$38)<<1` selects one of eight rows and the
low-nibble phase saturates at 15. POKEY-configured instruction states reach rows
0,1,4,5,7; rows 2,3,6 remain dormant.

Mode-aware traversal finds all 13 configured SET_FREQ_ENV `$86` operations in
POKEY mode and none in YM mode. It finds no configured SET_VIBRATO `$8C` at
all. Thus the frequency-envelope objects below do not supply a live YM glide
path in this ROM.

## Hardware dispatch tables

The tables around `$57A8` intentionally overlap because consumers index
different bases:

| Base | Bytes/meaning |
|---:|---|
| `$57A8` | Hardware-pointer low bytes |
| `$57AA` | Hardware-pointer high bytes |
| `$57AC` | Type values `00 02 1E 22` |
| `$57AE-$57AF` | Physical-list-head bases: POKEY `$1E`, YM `$22` |

Type 0 is POKEY and type 2 is YM2151. Values `$1E/$22` address RAM workspace
contexts rather than normal physical-device updates. The configured domain is
exactly X=0/1, and `$57B0` is the independently reached NMI entry, proving the
two-byte extent. Dormant type 6 can calculate broader indices, but has no
configured command/input domain.

The physical-output consumers add the following bounded tables:

| Range | Consumer-derived role | Status |
|---|---|---|
| `$57A0-$57A7` | Eight YM algorithm/operator scaling masks | Verified |
| `$57AE-$57AF` | POKEY/YM physical-list-head bases `$1E/$22` | Verified exact extent |
| `$5B5B-$5C5A` | 256-byte YM operator total-level scaling transform | Verified |
| `$5C5B-$5C5E` | Four-byte YM TL event/control-bias table; original `$082F` bits 5..4 select indices 0..3 | Verified exact extent |
| `$72DC-$73DB` | 256-byte YM operator total-level nonlinear transform | Verified |

Row-level consumers and index domains are in
`generated/physical_output_table_catalog.csv`. `$4EEC` reads `$5AF9,X` for KC;
mode-aware traversal proves configured YM note indices 13..95. The 128-byte
consumer view still extends through `$5B78`, where indices 98..127 structurally
alias `$5B5B-$5B78`, but no configured sequence reaches that tail. The former
command `$3A` high-index claim was an inline `$AE` pointer table misdecoded as
notes and is **Contradicted**.

## Handler-match records

The six zero bytes `$6559-$655E` precede the first explicit type-7 support
pointer at `$655F`. They are not a single universal three-byte format. Dormant
types 1/2 use sliding selector/value pairs at `$6559+A/$655A+A`; dormant type
12 uses a sliding four-field view at `$655B+X..$655E+X` for safe opcode,
argument, target command, and physical offset. With all bytes zero, type 12
fails its required target-type-7 validation. No configured command selects any
of these consumers.

## Generated type-7 byte and support catalogs

The exact traversal output is stored row-wise rather than duplicated here:

- `type7_sequence_catalog.csv`: 2,166 decoded instructions and every consumed
  byte, including all 153 table seeds;
- `type7_control_flow_catalog.csv`: 72 explicit control-flow edges, including
  every indexed `$AE` table target;
- `type7_data_reference_catalog.csv`: 189 opcode references, including 13
  frequency envelopes, 13 volume envelopes, 147 voice loads selecting 39
  distinct instrument bases, 14 YM envelope-block loads selecting 9 distinct
  blocks, and 2 YM register-block loads;
- `type7_region_catalog.csv`: coalesced byte classifications for
  `$6559-$8380`;
- `type7_envelope_catalog.csv`: one row per distinct frequency/volume-envelope
  pointer, including consumer record width, loop-marker count, terminator
  presence, and confidence of the bounded end;
- `ym_voice_field_catalog.csv`: all offsets `$00-$29` in the 42-byte instrument
  record, with register mapping, distinct values, and the live TL chain;
- `ym_voice_record_catalog.csv`: all 55 records on the `$69D6-$72DB` grid;
- `type7_residual_catalog.csv`: unreachable zero trailers and the sole valid
  unreferenced sequence candidate.

Fresh bounded consumer disassembly verifies two-byte volume-envelope records
and three-byte frequency-envelope records. A zero-filled record terminates;
an `$FF` count introduces a three-byte loop-control record. Some referenced
envelopes do not contain a terminator before the next independently reached
object, so their packed ends remain **Strong inference**, not Verified.
Nine of the 26 distinct envelopes have consumer-proven terminators; the other
17 retain **Strong inference** ends.

`type7_envelope_catalog.csv` now records the finite sequence-event count,
whether the owning sequence is runtime-unbounded, and the last byte that is
Verified read. The region catalog labels inferred packing with
`*_candidate_extent` and overlays `*_verified_read` for proven accesses. The
envelope union contains 339 Verified-consumed bytes and 210 candidate-only
bytes.

For the two sequence-unbounded frequency envelopes used by POKEY chip-test
command `$05`, the catalog records command `$00` as a Verified external stop.
Bounded listings establish that `$41E6` clears `$0390,X` for all 30 logical
channels and `$07E6,X` for all 42 channel/list entries, then reinitializes the
sound devices. The type-5 handler at `$438D` instead resolves its parameter
through the command tables and only stops matching active type-7 parameters;
its three selected rows name commands `$20`, `$2E`, and `$37`, not `$05`.
Thus no named stop command terminates the chip test.

The `$4954/$49C5` state model now records when an indefinitely retained
frequency envelope first reads past its Strong inference candidate end. The
`$68D6` object crosses after 2,458 envelope-update calls. The `$68F3` object
crosses after 65,440 calls because its `$FF FF 06` control repeats the prior
record 255 times before falling through. These are exact consumer-call counts,
not seconds: IRQ/device-update timing remains unresolved. Equal-priority list
insertion replaces the old channel, so reissuing command `$05` restarts it;
unequal POKEY priorities do not provide a termination bound.

The same consumer model continues beyond those crossings to Verified zero
terminators. `$68D6` consumes the contiguous interval `$68D6-$69FF` and stops
after 12,583 updates. `$68F3` consumes `$68F3-$69AF` and stops after 71,171.
The region catalog overlays these runtime reads on the pre-existing bytecode
and voice classifications; it does not redefine those intervals as packed
envelope objects. The traces consume 58 bytes that previously had no type-7
reference, reducing the then-unclassified total from 1,389 to 1,331.

`type7_cpu_support_catalog.csv` records CPU-indexed support data not named by
bytecode operands. It contains the six handler-match bytes at `$6559-$655E`
and the 256-byte `ym_total_level_nonlinear_lookup` at `$72DC-$73DB`, consumed by
`LDA $72DC,Y` at `$4F51` with an eight-bit combined index.

`type7_cpu_xref_audit.csv` preserves the complete raw absolute/indexed operand
scan of CPU range `$4000-$5C5E`. Of 37 encoded targets in the mixed region,
nine are Verified aligned instructions in bounded listings. Eight read the
handler-match records at `$6559-$655E`; `$4F51` reads the frequency table. The
remaining 28 rows are retained as Verified rejections because the apparent
opcode occurs inside another instruction or a data table. This audit found no
new direct CPU reference to any byte still classified Unknown.

`type7_indirect_xref_audit.csv` traces all five constructed pointer classes
that can read the mixed region back to exhaustive generated targets: the type-7
sequence pointer table and opcodes `$86`, `$87`, `$9D`, `$9E`, and `$9F`.
Other indirect accesses target RAM, hardware, or speech outside this region;
the alternate NMI `$04-$05` pointer is a write path. The runtime frequency
trace accounts for the 58 newly reached bytes; the other four constructed
pointer classes add none.

`type7_conditional_feasibility.csv` resolves all 34 `$AE` sites. The consumer
indexes an inline target table; it never falls through sequentially. Thirty-one
`$AB 00` sites select a one-entry table, while the three RNG sites reach every
entry in their four- or sixteen-entry tables. The corrected conservative and
feasible traversals are therefore identical: 2,166 instructions and 4,670
bytes.

YM2151 data forms a 55-record grid of 42-byte instrument records from
`$69D6-$72DB`. `$9D` consumes offsets `$00-$1B`; `$4EFF` additionally consumes
the live TL fields `$1D-$23`; `$9E` consumes `$24-$28`; and `$9F` consumes
`$29`. Offset `$1C` is skipped by every configured consumer found. Thirty-nine
records have `$9D` references, one more is `$9E`-only, and 15 have no configured
reference.

Fresh bounded loader listings refine this layout. `$5535/$558F/$4C16` establish
the 28-byte register image. `$4EFF` reads odd offsets `$1D/$1F/$21/$23` as
M1/M2/C1/C2 TL transform descriptors and even offsets `$1E/$20/$22` as chained
correction/index state. Offset `$1C` is not copied to `$0826` and has no found
consumer; its original purpose remains **Unknown**.

Opcode `$9E` adds `$24` to its operand and consumes exactly five bytes; `$9F`
adds `$29` and consumes exactly one byte. These are separate operand-selected
auxiliary views and need not be contiguous with every `$9D` voice base. The
generated support-format catalog records that distinction.

The final region overlay leaves zero bytes labeled
`unclassified_no_type7_reference`. This is a classification result, not a use
claim: 15 full records and the valid `$80DA-$80E2` sequence remain unreferenced,
and 56 zero trailer bytes are consumer-proven unreachable but have Unknown
original purpose.

## Referenced dummy data

`$5874-$5893` contains 32 bytes of `$FF`. It is intentionally addressed as a
dummy speech stream during initialization; it is not unused padding and it is
not a 32-byte zero block.

## Catalog requirements for future additions

Each newly identified table should record:

- inclusive start and end;
- record width and count;
- index domain and maximum reachable index;
- byte order;
- all known consumers;
- whether pointers are direct or target-minus-one;
- overlap/alias behavior;
- reachability and confidence.
