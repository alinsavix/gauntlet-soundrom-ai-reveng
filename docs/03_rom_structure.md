# 03 — ROM Structure

## Image mapping and vectors

`soundrom.bin` is 49,152 bytes with no container format. File offset 0 maps to
CPU `$4000`; CPU address A maps to file offset `A-$4000`.

| Vector | Location | Target |
|---|---:|---:|
| NMI | `$FFFA-$FFFB` | `$57B0` |
| RESET | `$FFFC-$FFFD` | `$5A25` |
| IRQ/BRK | `$FFFE-$FFFF` | `$4187` |

RESET begins with the verified hardware-ready loop:

```asm
lda $1030
and #$c0
cmp #$80
bne $5a2c
jmp $4002
```

## Verified major regions

This is a region-oriented map, not an assertion that every byte inside a broad
range has been classified.

The generated semantic-coverage join now classifies every executable byte in
`$4002-$5A30` and `$8381-$8446`: 6,681 bytes are owned by a semantic range
catalog, five embedded data regions are explicit exclusions, and no executable
byte is unowned (**Verified**).

| Range | Content | Confidence |
|---|---|---|
| `$4000-$5C5E` | Boot, interrupts, handlers, channel engine, helpers | Partly verified; exact function boundaries incomplete |
| `$5790-$579F` | 16 signed YM carrier-TL attenuation values | Verified |
| `$57A0-$57A7` | Eight YM algorithm carrier/operator masks | Verified |
| `$57A8-$57AF` | Hardware pointers/types/list-head configuration views | Verified overlapping consumers |
| `$5A35-$5B34` | 128-word POKEY note-lookup consumer view; only entries 1..97 form a chromatic divider prefix | Verified consumer extent; configured POKEY NOTE path absent |
| `$5AF9-$5B78` | 128-byte YM note → KC view, overlapping the POKEY view and `$5B5B` table | Verified |
| `$5C5F-$5C7E` | 16 little-endian duration values | Verified |
| `$5C7F-$5C8E` | 16 fade/ramp shift and control selectors | Verified |
| `$5C8F-$5D0E` | Eight 16-byte signed POKEY volume-shape trajectories | Verified |
| `$5D0F-$5DE9` | NMI command validation table, 219 bytes | Verified |
| `$5DEA-$5EC4` | Command → handler type, 219 bytes | Verified |
| `$5EC5-$5F9F` | Command → parameter, 219 bytes | Verified |
| `$5FA0-$5FA7` | Type-3 target table; `$5FA2+` overlaps NMI dispatch table | Verified |
| `$5FA8-$5FE5` | Type-7 parameter → starting record, 62 bytes | Verified |
| `$5FE6-$6023` | Type-7 command flags, 62 bytes, all `$FF` | Verified |
| `$6024-$60D9` | Type-7 record priority, 182 bytes | Verified |
| `$60DA-$618F` | Type-7 physical channel, 182 bytes | Verified |
| `$6190-$62FB` | Type-7 sequence pointers, 182 little-endian words | Verified |
| `$62FC-$63B1` | Type-7 next-record links, 182 bytes | Verified |
| `$63B2-$643E` | Speech parameter → LPC index, 141 bytes | Verified |
| `$643F-$64CB` | Speech clock flags, 141 bytes | Verified |
| `$64CC-$6558` | Speech priority/filter, 141 bytes | Verified |
| `$6559-$655E` | Two three-byte handler-match records | Verified by width and exclusive bound at first envelope pointer `$655F` |
| `$655F-$8380` | Interleaved type-7 sequence and support data | Byte-level catalog generated; envelope extents are strong inference |
| `$8381-$843E` | Board/coin control routine | Strongly supported |
| `$843F-$8446` | NMI direct-dispatch handlers | Verified |
| `$8447-$8448` | Bytes `$94,$FF`; no known reference | Strong inference: unused |
| `$8449-$85C2` | 189 LPC stream pointers | Verified |
| `$85C3-$873C` | 189 LPC byte lengths | Verified |
| `$873D-$FECC` | Complete contiguous TMS5220 LPC corpus, 30,608 bytes | Verified |
| `$FECD` | Unindexed trailing `$FF` after the final LPC range | Strong inference: unused/guard byte |
| `$FECE-$FFF5` | 296 zero bytes | Strong inference: unused padding |
| `$FFF6-$FFF9` | `$8C,$FF,$00,$00`; no known reference | Strong inference: unused/build metadata |
| `$FFFA-$FFFF` | Interrupt vectors | Verified |

## Type-7 corpus

All 62 type-7 parameters expand through `$62FC` links to all 182 records. Those
records contain 153 distinct sequence entry pointers ranging from `$6569` to
`$8378`. A client-managed static traversal now catalogs 2,166 bytecode
instructions consuming 4,670 distinct bytes and 72 explicit control-flow
edges. It also identifies 189 support-data references. See the generated
`type7_sequence_catalog.csv`, `type7_control_flow_catalog.csv`,
`type7_data_reference_catalog.csv`, `type7_envelope_catalog.csv`, and
`type7_region_catalog.csv`.

Fresh bounded disassembly verified that code begins at `$8381`; bytes
`$837F-$8380` are the complete `00 00` chain/end pair reached from the
sequence entry at `$8378`. The earlier `$837F` boundary and incomplete-decode
claim are **Contradicted**.

The map is not an exact proof of original author intent. Nine envelopes
have consumer-proven terminators; 17 are bounded by the next independently
reached sequence start (**Strong inference**). Before runtime-envelope tracing,
1,389 bytes were labeled `unclassified_no_type7_reference`; the final
consumer/grid audit has eliminated that mechanical class without claiming
that structurally unreferenced records are used.

Sequence-lifetime correlation further separates actual reads from candidate
packing. Across the 26 distinct envelopes, 339 unique bytes are **Verified**
consumed; another 210 bytes belong only to candidate extents. All 15 finite or
pointer-replaced unterminated cases end before the consumer advances beyond
their first record. Two unterminated frequency envelopes used by the looping
POKEY chip test are sequence-unbounded and retain **Strong inference** ends.
Command `$00` is a Verified external stop because `$41E6` clears every logical
channel status and physical-list link before device reinitialization. None of
the three named type-5 stop commands targets chip-test command `$05`; this
external stop does not prove how far either envelope advances before `$00`.
Direct modeling of the Verified `$4954/$49C5` consumer shows that `$68D6`
first reads beyond its candidate end after 2,458 envelope-update calls and
`$68F3` after 65,440 calls. Thus neither candidate end is a runtime bound.
Reissuing equal-priority command `$05` replaces and restarts the old channels;
the other POKEY type-7 priorities coexist in the physical lists rather than
terminating them.

Continuing the Verified consumer state through zero terminators shows that
`$68D6` reads every byte through `$69FF` and stops after 12,583 updates;
`$68F3` reads through `$69AF` and stops after 71,171. These are overlapping
runtime interpretations of bytes also used as sequence/voice data, not new
packed envelope extents.

Fresh CPU-reference auditing identifies `$72DC-$73DB` as a 256-byte lookup
table (**Verified**): `$4F51` reads `$72DC,Y`, the producer forms an eight-bit
index, and the next independently reached object is the sequence entry at
`$73DC`. Consumer-led output analysis now shows that this is an operator
total-level nonlinear lookup, not a frequency table; the older frequency label
is **Contradicted**.

A complete absolute/indexed CPU-operand candidate scan over `$4000-$5C5E`
found 37 raw byte matches into `$6559-$8380`. Bounded listings validate nine
aligned instructions: eight reserved-handler reads of `$6559-$655E` and the
`$4F51` frequency-table read. The other 28 are mid-instruction or data-table
byte coincidences. No additional Unknown mixed-region byte is directly
referenced by an aligned absolute/indexed CPU instruction.

The constructed-indirect audit finds five mixed-region pointer classes:
sequence bytecode, frequency envelopes, volume envelopes, YM voices, and YM
auxiliary blocks. Every pointer source is already exhaustive in the chain or
bytecode data-reference catalogs. Overlaying the two runtime-crossed frequency
traces promotes 58 formerly Unknown bytes to Verified reads. The direct and
constructed-indirect audits initially left 1,331 bytes unclassified.

Conditional feasibility is now complete for all 34 `$AE` sites. `$5320` does
not have a target/fallthrough pair: it indexes an inline little-endian target
table by the masked register value and always replaces the sequence pointer.
Thirty-one `$AB 00` sites select their sole entry. The three POKEY-RANDOM sites
use masks `$03/$0F`; both supplied polynomial domains reach every table index.
The corrected traversal includes all alternatives and has no sequential
fallthrough.

The final structural pass identifies `$69D6-$72DB` as 55 contiguous 42-byte YM
instrument records. Thirty-nine are selected by `$9D`, one additional record
is selected only through `$9E`, and 15 have no configured reference. It also
classifies 56 zero bytes after unconditional pointer replacements as Verified
unreachable trailers (original purpose Unknown), plus the valid but
unreferenced nine-byte sequence at `$80DA-$80E2`. Consequently the region has
zero bytes left under `unclassified_no_type7_reference`; the 15 unreferenced
records and nine-byte sequence remain explicit provenance/use Unknowns.

## Speech corpus

The 189 pointer/length records form a gapless, non-overlapping partition of
`$873D-$FECD` (exclusive end). Of these:

- 141 are selected by type-11 commands and occupy 30,560 bytes;
- 48 are one-byte immediate-stop streams and occupy 48 bytes;
- every entry parses as a complete variable-length TMS5220 bitstream with a
  stop frame and no truncated final frame.

The region is speech from its first byte, not “music until `$AD00`.”

## Confirmed and disputed unused space

Likely unused ROM totals approximately 303 bytes:

| Range | Bytes | Note |
|---|---:|---|
| `$6000-$6023` | 36 | This older claimed gap is **not** actually a gap: it is the tail of the verified 62-byte flags table `$5FE6-$6023`; do not count it unused |
| `$8447-$8448` | 2 | Unreferenced bytes `$94,$FF` |
| `$FECD` | 1 | Unindexed `$FF` after final pointer/length range |
| `$FECE-$FFF5` | 296 | Zero padding |
| `$FFF6-$FFF9` | 4 | Unreferenced pre-vector bytes |

After correcting the flags-table extent, the defensible current unused total
is **303 bytes**, not 334 or 366. Complete code, bytecode, constructed-pointer,
and semantic-coverage audits find no consumer. “Unused” remains Strong
inference only because original build/alignment intent requires comparison
source or another ROM image.

`$5874-$5893` is not unused: it is a referenced 32-byte `$FF` dummy stream used
to prime/reset speech state.
