# Chapter 17 — What We Still Don't Know

*Before this chapter: [Chapters 1](01_two_computers.md) to
[16](16_how_this_was_figured_out.md).*

There is a nine-byte sequence at `$80DA`. It chooses an instrument, sets a tempo,
rests for a whole note, and ends, and it decodes cleanly as a valid program in the
language of [Chapter 8](08_sequence_language_time.md). No command selects it. No
record points at it. No jump, no call, and no computed branch in the entire ROM
can reach it. Somebody wrote it and it never runs.

That is the flavour of what is left. The mechanics of this board are settled, and
the previous sixteen chapters describe them without hedging because they earned
the right to. What remains is a short list of things the ROM does without saying
why, and things it contains without using. Each one is small. Several of them are
interesting.

## The boot handshake

Before the sound subsystem does anything else useful, it writes five fixed values,
in a fixed order, every time it powers up.

| Order | Value | Address |
|---:|---:|---|
| 1 | `$FF` | `$1003` |
| 2 | `$33` | `$1002` |
| 3 | `$00` | `$100B` |
| 4 | `$22` | `$100C` |
| 5 | `$0F` | `$1000` |

For a long time these looked like five separate board registers being
configured. They are not. On this board the address decoder ignores the low four
bits of `$1000`–`$100F`, so all five addresses are **the same location** — the
reply latch of [Chapter 6](06_taking_orders.md) that hands the main CPU a byte
and interrupts it. The board schematic shows this decode directly, and MAME
confirms it: its sound map routes the whole block to one write handler,
`map(0x1000, 0x100f).mirror(0x27c0).w(m_mainlatch, ...)`. So the handshake is not
configuration at all. It is five bytes written to the one mailbox, back to back —
`$FF`, `$33`, `$00`, `$22`, `$0F` — each landing on top of the last about three
microseconds later, and then, a few instructions into the rest of boot, the `$FF`
acknowledgement of [Chapter 5](05_waking_up.md) lands on top of all of them.

The companion game-ROM disassembly shows the 68010 reads none of the intermediate
values. Its only interest in this latch is that final `$FF`, the byte its watchdog
waits for; nothing on the main side ever compares against `$33`, `$22`, `$00` or
`$0F`. The burst is overwritten before it can mean anything, and
[Appendix B](B_command_list.md#the-handshake-burst) follows the bytes through to
the game side.

What is left is not a hardware question but a historical one, and it has an
answer. The code writes to five *distinct* addresses with five fixed values, as
hardcoded load-and-store pairs — exactly what a programmer writes to initialize
five separate registers, not to poke one latch five times. Those registers did
exist, on the board this firmware grew up on: **Atari System 1**, the
swappable-cartridge platform whose best-known title is Marble Madness. On a
System 1 board with speech, `$1000`–`$100F` is a **MOS 6522 VIA**, and MAME maps
it there directly — `map(0x1000, 0x100f).mirror(0x27f0).m(m_via, ...)`, the same
sixteen-byte block, the same mirror.

The 6522 is not the inter-CPU mailbox there; System 1 keeps that in a separate
latch at `$1810`. It is the **TMS5220 speech interface**. Port A carries the
speech data and status; Port B carries the control lines — a write strobe and a
read strobe, a clock/frequency select on bit 4, and an LED on bit 5. Read the
five boot writes against a 6522's register map and each one is a line of
speech-port setup:

| Write | VIA register | Effect on the speech interface |
|---|---|---|
| `$1003` ← `$FF` | DDRA | Speech data bus: all eight pins **outputs** |
| `$1002` ← `$33` | DDRB | Outputs on bits 0, 1, 4, 5; inputs on 2, 3, 6, 7 — drive the two strobes, the bit-4 clock select and the bit-5 LED, and read the chip's status lines |
| `$100B` ← `$00` | ACR | Plain parallel I/O; timers and shift register off |
| `$100C` ← `$22` | PCR | CA2/CB2 as independent negative-edge interrupt inputs — the TMS5220's `/READY` and `/INT` handshake |
| `$1000` ← `$0F` | ORB | Initial Port B: both strobes idle-high (they are active-low), clock select 0 (normal, not "squeak"), LED off |

The `$33` in the direction register is the tell. It makes outputs of exactly the
four Port B lines that drive the chip — the two strobes, the clock select, the
LED — and inputs of the four that read its status. That is not a value that lands
on a latch by accident; it is a hand-written 6522 initialization for a speech
chip.

Gauntlet's board threw the VIA out and reused its address window. Where System 1
put a 6522 at `$1000`–`$100F` and its mailbox at `$1810`, Gauntlet II puts the
mailbox at `$1000`–`$100F` and re-implements the speech interface with plain
decode: `$1820` for the data byte, and the control latch at `$1030`–`$1037` for
the strobes and the clock. Those Gauntlet controls are the VIA's Port B pulled
apart into separate addresses — `$1033`, "select the speech clock," is the old
bit-4 frequency select; `$1031`, the speech write strobe, is one of the old Port
B strobes. The speech chip survived the move; only its wiring changed. The
initialization routine survived too, unedited, and now fires its five 6522
register writes into the mailbox that sits where the VIA used to be, where they
are read by nobody.

One step would nail it down completely: a byte-level match against a System 1
sound ROM. The speech path is the System 1 titles that *have* a TMS5220 — Indiana
Jones and the Temple of Doom, Peter Pack Rat, Road Runner, rather than the
speechless Marble Madness — so one of their sound ROMs should carry this same
sequence written against a live VIA. Short of that, the register-by-register fit
is already as much as inference can carry.

## Six handler types nobody calls

[Chapter 6](06_taking_orders.md) counted fifteen slots in the handler jump table
and nine that commands point at. The other six hold finished, working routines.

| Type | What it would do |
|---:|---|
| 1 | Write a value into one of the sixteen shared workspace bytes, choosing both the slot and the value from a small support table |
| 2 | Add to one of those workspace bytes instead of replacing it |
| 4 | Silence every logical channel whose status field matches a supplied class |
| 6 | Silence every logical channel currently linked to one selected physical voice |
| 12 | Apply one sequence-language instruction to every live channel playing a named sound |
| 14 | Nothing at all: a return instruction and no body |

Type 12 is the ambitious one. It reads four fields from a support table, checks
that the named target is a type-7 sound, walks the physical list, and executes a
chosen bytecode instruction against every channel it finds. It restricts itself to
a safe range of opcodes, excluding the ones that would move a sequence pointer or
load an instrument, so it can change tempo, volume, transpose, or control bits on a
running sound from outside. A game could duck the music under a spoken line with
it. The support table it reads is six bytes at `$6559`, all of them zero, so type
12 fails its own validation before doing anything.

Two explanations fit. These may be leftovers from development, written and then
routed around when the game's sound design turned out simpler than expected. Or
this sound subsystem and this program may have been intended to serve more than one
game, with another title's command table selecting the features Gauntlet II does
not use. Distinguishing between those requires a second ROM. One image cannot tell
you what a different image would have done with the same code.

## The reset-time command that may get written into RAM

There is a narrow window during a self-test boot when a pending command from the
main CPU may do something unrecognizable.

Initialization enables interrupts and waits for the first IRQ, so it can enter the
main loop at a known point in the tick cycle. During that wait the incoming
command path has not yet been switched into its normal mode. If an NMI arrives
first, the handler takes a different branch: instead of queueing the byte, it
writes it into RAM through a pointer, then advances the pointer and its index.
The companion game/OS disassembly settles what the main CPU supplies. Its sound
reset routine asserts reset, writes a startup command into the command latch, and
then releases reset. Gauntlet II always passes `$00`; the operator-test reset path
also clears the latch. The sender, byte, and ordering are therefore known.

What is not known is how the reset and latch logic deliver that write. The sound
CPU's reset gate waits for the input-full signal but never reads the byte. If the
write made while reset is asserted remains pending and produces an NMI after
release, then a diagnostic boot can reach the alternate branch after `CLI`. At
that point the RAM test has cleared the pointer, index, and mode, so the known
`$00` is written through a zero pointer to `$0000`, after which the pointer/index
state advances. If the reset-time NMI edge is discarded, the branch never runs.
The ROMs establish both sides of that boundary; they cannot establish the board's
edge-delivery behavior.

A reset-time bus capture or cycle-accurate board trace would answer it in one
recording.

## Small unexplained things

**One byte in every instrument.** Offset `$1C` of the 42-byte instrument record from
[Chapter 12](12_driving_the_ym2151.md) is skipped. The register-image copy stops
one byte short of it, the level-transform reader starts one byte past it, and no
other code in the ROM indexes it. Across the 55 records it takes exactly two
values, `$00` and `$80`, which is the shape of a flag that meant something to
whoever built the instrument data.

**Fifteen instruments with no name.** Of the 55 records, 39 are loaded by
sequences and one more is reached only through the auxiliary-block instruction.
The remaining fifteen are structurally valid, sit on the same grid, and are never
selected. They may be instruments for sounds that were cut, or alternates kept for
comparison, or a library the tooling emitted whether or not the game wanted them.

**The sequence at `$80DA`.** Nine bytes, four instructions, unreachable. It reads
as a fragment of something under construction more than as a deleted sound, since
it plays one rest and stops.

**Fifty-six zero bytes in the middle of the music.** After certain unconditional
jumps and computed branches, the ROM contains a `00 00` pair that execution can
never arrive at. Twenty-eight such pairs are scattered through the sequence data.
The most likely reading is a tool emitting an end marker after every stream
whether the stream needed one or not, but that is a guess about a build process
nobody has a record of.

**About 300 bytes of unused ROM.** Four regions have no consumer anywhere: two
bytes at `$8447` reading `$94 $FF`, a single `$FF` at `$FECD` just past the end of
the speech corpus, 296 zero bytes filling the gap before the interrupt vectors,
and four bytes at `$FFF6` reading `$8C $FF $00 $00`. The zero padding is obviously
padding. The other three look more like build metadata, with a version stamp or a
checksum adjustment as the usual candidates.

**Seventeen envelope endings.** [Chapter 10](10_shaping_the_sound.md) described
envelopes as ending on an all-zero record. Nine of the ROM's 26 envelopes have
that terminator, proven by following the code that reads them. The other
seventeen are bounded by the fact that another object, independently reachable,
starts immediately after. That is a strong argument and it is not the same as a
proof, and the distinction matters for anyone trying to reconstruct the original
data files rather than just play the sounds.

## Features that are complete and dormant

Three capabilities in this ROM are finished code with no live path to them, and
they are worth separating from the merely unused because in each case something
would have had to change elsewhere to bring them to life.

The vibrato instruction sets a per-channel depth value. Allocation clears that
value to zero and no sequence ever sets it, so the YM2151 pitch-interpolation
block that consumes a nonzero depth never runs. What it would sound like at a
nonzero depth has not been determined, because determining it means guessing at
inputs that nothing supplies.

The POKEY note path is the same story from
[Chapter 11](11_driving_the_pokey.md). A chromatic divider table covering
ninety-seven notes sits in ROM, correct and complete over that range, and no
POKEY sequence in the game plays a note. Its consumer can index further, but
entry 97 is the last one that belongs to the table; past `$5AF8` it is reading
the YM2151 key-code table and the total-level scaling table beyond it. What those
entries would mean is not a question worth asking, because nothing reaches them.

The frequency-envelope machinery has a YM2151 branch as well as a POKEY one. All
thirteen frequency envelopes in the ROM are attached to POKEY channels, so the YM
branch never executes.

## Things only a real machine can answer

Everything above is a question about intent. The following are questions about
behaviour, and they are unanswerable from a ROM image by construction, because a
ROM image does not include the hardware it ran on.

**How long the YM2151 actually makes you wait.** [Chapter 12](12_driving_the_ym2151.md)
gave the cost of a register write assuming the chip answers immediately, and the
cost of the 255-poll timeout. Real waits fall somewhere between, and where they
fall depends on the chip's internal timing at that instant. The arithmetic bounds
are known exactly. The distribution is not.

**What the mixer does.** Writing to `$1020` sets three levels feeding an analog
mixer, and the three sources are then summed and amplified by circuitry this
project has no measurements of. Every WAV file the tooling in this repository
produces is one chip rendered on its own and normalized. What a cabinet sounds
like, with all three sources at their real relative levels through the real
filters, is a recording nobody has made for this purpose.

**What the coin pulse looks like on a cabinet.** The player mapping is now
settled: `$1020` bits 3..0 become the four `$44` fields and then player/color
indexes 0..3—red, blue, yellow, green, matching coin slots 1..4. What remains is
whether the inferred debounce and pulse-stretch descriptions match the physical
switches and solenoids, including polarity and pulse duration.

**Whether the one overrun matters.** The first tick of the four-channel POKEY chip
test slightly exceeds the interrupt interval. The interrupt is asserted as a level
rather than a pulse, so a late handler leaves the next interrupt pending and it
gets serviced immediately after the return. That is what the implementation says
should happen, and it has not been watched happening on a board.

**How often speech stalls.** The watchdog that resets the speech chip fires after
a seventh of a second of a stuck ready line. Nothing establishes whether it ever
fires during normal play, or what the accepted-write cadence looks like for a real
phrase against a real chip.

**What the random branches actually pick.** The three sounds that read the POKEY's
polynomial counter each select one of four or sixteen endings, and every one of
those endings has been traced and is finite. Which one you hear depends on where
the free-running counter happens to be, which depends on how long the board has
been powered up.

## Two places this book used to disagree with itself

An earlier draft carried two unresolved disagreements, where a static reading of
the generated catalogs and a direct execution of the ROM gave different answers.
Both are now settled, and both turned out the same way: the static reading had a
state assumption wrong.

The first was the effects chip test's loop period. The catalogs read its rest
durations through the duration table of
[Chapter 8](08_sequence_language_time.md) and got 30 sweeps; execution gave 250.
The decisive evidence is the branch at `$4844`, which tests two bits of the
channel's status byte and only then decides which rule applies. The catalog
generator was applying the table unconditionally. It has been corrected.

The second was the volume-shape table. A static enumeration of note control
bytes said five of the eight rows were reachable on POKEY channels; execution
showed the index being zeroed on every POKEY event. Both readings were describing
real code — the row derivation exists, on the arm of that same branch that POKEY
channels never take — and the index is only ever read on the POKEY side. The
generator has been corrected, and
[`docs/generated/volume_shape_catalog.csv`](../docs/generated/volume_shape_catalog.csv)
now carries the discarded derivation in a column of its own, because a rule that
runs and is thrown away is worth recording.

Neither correction changes anything a listener would hear: row 0 is sixteen
zeroes, and the chip test loops either way. What they changed is the confidence
this book can claim, which is why they are written up here rather than quietly
fixed.

## How you could help

Three kinds of new external evidence would close most of this list. All static
questions that can be answered from the ROMs currently in hand are closed.

A **logic-analyzer capture from a running board** would settle the busy-wait
distribution, the catch-up interrupt, the speech cadence, and the physical
coin-counter pulses, all at once. A capture of the first few milliseconds after
power-on would additionally resolve the boot NMI window.

The **main CPU's disassembly**, now consulted, named the boot handshake bytes,
proved that reset writes startup command `$00` before releasing the sound CPU,
and closed the reply protocol: `$03` is the every-frame coin poll, `$07` the
health probe, and `$FF` the reboot acknowledgement. User-provided runtime
evidence establishes use of `$04,$05,$08-$D5`, while direct inspection finds
`$D7` at the level-start screen even though the legacy list calls it unused.
The final four commands are exposed by the OS operator sound test: its `$06`
query returns the exclusive bound `$DB`, its selector covers
`$01,$02,$04,$05,$08-$DA`, and OS `$2786` emits the selected value
([Appendix B](B_command_list.md#replies-to-the-main-cpu)). The boot's
five-register init is now understood as leftover Atari System 1 speech-VIA setup
(see above).

**Another revision of this sound ROM**, or the equivalent ROM from another Atari
title on related hardware, would distinguish development leftovers from features
intended for a different configuration. If a second image selects the vibrato
instruction, or points a command at handler type 12, the question answers itself.
A speech-equipped **Atari System 1** sound ROM (Indiana Jones, Peter Pack Rat,
Road Runner) would separately confirm the boot handshake as 6522 speech-VIA
initialization, by carrying the same sequence written against a live VIA.

**Original Atari source or a build listing** would close every remaining item in
one document, including the ones about intent that no amount of ROM analysis can
reach.

Absent those external sources, the right thing to do with the historical and
hardware items is leave them where they are. A plausible name attached to an
unexplained byte is worse than no name, because the next person to read it will
not know it was a guess.

## What you now know

- Five bytes go out at every boot to five addresses the board decodes as one
  latch — the sound→main mailbox. The game ROM reads none of them, the `$FF`
  alive-byte overwrites the whole burst, and the five-register init is leftover
  Atari System 1 code that once set up a 6522 VIA driving the speech chip.
- Six handler types are finished routines with no command pointing at them,
  including a live-channel meta-dispatcher that could have modified running sounds.
- Reset always places `$00` in the command latch; whether the board delivers it
  as a post-release NMI into the diagnostic RAM-write window needs a bus trace.
- One byte of every instrument record, fifteen whole instruments, one complete
  sequence, and about 300 bytes of ROM have no consumer anywhere.
- Vibrato, POKEY notes, and the YM2151 frequency-envelope branch are complete
  machinery that this ROM's sounds never activate.
- Questions about real chip timing, the analog mixer, and physical coin-counter
  pulses cannot be answered from a ROM image at all.
- A board capture, a second ROM revision, or original source would each close a
  specific part of this list; the available main-CPU code has closed the static
  emitter questions.

## Where this leads

The chapters are finished. What follows is reference: a glossary, the complete
command and opcode lists, the tables worth having open while reading, a guide to
the tool, and a map from each chapter to the documents that argue its case in
full.

## Going deeper

- [`docs/10_known_issues.md`](../docs/10_known_issues.md) — the full research
  backlog, with the exact evidence each item still needs.
- [`docs/generated/external_question_catalog.csv`](../docs/generated/external_question_catalog.csv)
  — the ten remaining questions, each classified by the artifact or analysis
  that would close it.
- [`docs/generated/operator_sound_test_command_catalog.csv`](../docs/generated/operator_sound_test_command_catalog.csv)
  — the closed selector/emitter audit for the final four control commands.
- [`docs/generated/reserved_handler_catalog.csv`](../docs/generated/reserved_handler_catalog.csv)
  — the six dormant handler types with their exact effects.
- [`docs/generated/type7_residual_catalog.csv`](../docs/generated/type7_residual_catalog.csv)
  — the unreachable trailers and the unreferenced sequence.
- [`docs/03_rom_structure.md`](../docs/03_rom_structure.md) — the unused regions
  and why "unused" is a careful word here.
