# 08 — Command Reference

## Command space

The main command space is `$00-$DA` (219 values). Commands use parallel type and
parameter tables at `$5DEA` and `$5EC5`. Commands 3, 6, and 7 are intercepted by
NMI as direct queries even though their normal handler type is `$FF`.

The exhaustive generated mapping is [`generated/command_catalog.csv`](generated/command_catalog.csv).

## Handler distribution

| Type | Meaning | Commands |
|---:|---|---|
| 0 | Global silent/noisy filter | `$01,$02` |
| 3 | Special target dispatch | `$00` |
| 5 | Stop named sound | `$21,$2F,$39` |
| 7 | Shared POKEY/YM2151 sequences | 62 commands |
| 8 | Main-CPU output queue | `$DA` |
| 9 | Fade named sound | `$3C` |
| 10 | Fade by status | `$41` |
| 11 | TMS5220 speech | `$08,$4A-$D5` (141 commands) |
| 13 | Mixer/control values | `$D6-$D9` |
| `$FF` | Invalid in normal dispatcher | includes direct NMI queries `$03,$06,$07` |

Types 1, 2, 4, 6, 12, and 14 have code entries but no commands select them.
`generated/reserved_handler_catalog.csv` proves their exact effects and sole
fixed-point source. Type 12 is a live-channel meta-dispatcher restricted to
safe opcode ranges; its all-zero support view fails target validation, so it is
inert even under the zero parameter. Original development provenance remains
unrecoverable without another ROM revision or source listing.

The dispatcher at `$432E` rejects command values `$DB+` and handler types 15+,
doubles the valid type, pushes its target-minus-one word from `$4633-$4650`,
loads the parameter from `$5EC5,Y`, and returns into the handler. The exact
configured distribution is 2/1/3/62/1/1/1/141/4 commands for active types
0/3/5/7/8/9/10/11/13 (**Verified**).

Type-7 allocation scans 30 logical slots. If full, it may reclaim only the
lowest-priority head of the requested physical list when the incoming priority
is at least as high. Physical lists are priority sorted; equal priorities
replace the existing channel and return its two context chains to the pool.
All 182 record insertions use interrupt-masked link transactions.

## System and diagnostic commands

| Command | Meaning | Path |
|---:|---|---|
| `$00` | Clear/reinitialize audio state | Type 3 → `$41E6` |
| `$01` | Silent/global high filter | Type 0, parameter `$3C` |
| `$02` | Noisy/clear global filter | Type 0, parameter 0 |
| `$03` | Return four cached input/event fields in `$44` | Direct NMI query |
| `$04` | Eight-channel YM2151 music-chip test | Type 7, chain offsets 0..7 |
| `$05` | Four-channel POKEY effects-chip test | Type 7 |
| `$06` | Echo `$DB` capability/sentinel | Direct NMI query |
| `$07` | Return errors and arm heartbeats | Direct NMI query |
| `$08` | TMS5220 speech-chip test | Type 11, LPC `$873D` |

**Game-side usage of the reply commands** (from the companion 68010 game-ROM
disassembly; see [book Appendix B](../book/B_command_list.md#how-the-game-rom-uses-them)):
in normal play the game sends only `$03` (every frame; the reply's packed
coin-mech counters become credits) and `$07` (when idle or by the watchdog; a
nonzero low-3-bit error field reboots the board). `$FF`, written directly to
`$1000` at boot, is the acknowledgement the game waits for after a reboot. `$06`
is sent only by the operator self-test as a liveness ping — it checks that a byte
answered before a timeout, never that it was `$DB`. `$DA` (→ `$55`) is sent by
neither the game nor its OS. The `$04`/`$05`/`$08` chip tests are also
self-test-only.

## Type-7 commands

Type 7 covers both effects and music. All 62 rows and expanded chains are in
[`generated/type7_chain_catalog.csv`](generated/type7_chain_catalog.csv).

- POKEY-only: `$05,$43-$49`.
- YM2151-only: the other 54 type-7 commands.
- No type-7 command mixes chips.
- Music examples: `$3B` theme, `$3D-$40` treasure-room variants, `$42` level
  opening music.
- Stop/fade commands do not themselves use type 7; they resolve the target
  sound through command metadata.

## Type-11 speech commands

Type 11 includes `$08` plus `$4A-$D5`. Every command has one parameter, one
speech index, and one LPC pointer/length pair. See
[`generated/type11_speech_catalog.csv`](generated/type11_speech_catalog.csv).

Priority groups:

- normal priority 0: 134 commands;
- priority 4: `$BC`;
- high priority `$40`: `$A1-$A6`.

Clock/pitch flag `$80` is set for `$76-$80`, `$89-$8A`, `$A9-$B5`, and `$BC`.

## Control commands

| Command | Handler | Parameter | Current description |
|---:|---:|---:|---|
| `$D6` | 13 | `$E7` | Mixer/control preset; game use unclear |
| `$D7` | 13 | `$EF` | Mixer/control preset |
| `$D8` | 13 | `$F7` | Mixer/control preset |
| `$D9` | 13 | `$FF` | Mixer/control preset |
| `$DA` | 8 | `$55` | Queue `$55` response for main CPU |

The older CSV labels several of these “Not Used.” That is a game-side usage
claim, not a ROM reachability fact; the sound ROM contains valid dispatch rows.

## Command names

Human descriptions come from `docs/soundcmds.csv` and game knowledge. They are
annotations, not evidence for handler mechanics. Spelling and quotation errors
in the legacy CSV should eventually be normalized without changing numeric IDs.
