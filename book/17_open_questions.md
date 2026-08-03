# Chapter 17 — What We Still Don't Know

*Before this chapter: [Chapters 1](01_two_computers.md) to
[16](16_how_this_was_figured_out.md).*

There is a nine-byte sequence at `$80DA`. It chooses an instrument, sets a tempo,
rests for a whole note, and ends, and it decodes cleanly as a valid program in the
language of [Chapter 8](08_sequence_language_time.md). No command selects it. No
record points at it. No jump, no call, and no computed branch in the entire ROM
can reach it. Somebody wrote it and it never runs.

That is the flavour of what is left. The mechanics of this board are settled, and
the previous fifteen chapters describe them without hedging because they earned
the right to. What remains is a short list of things the ROM does without saying
why, and things it contains without using. Each one is small. Several of them are
interesting.

## The boot handshake

Before the sound board does anything else useful, it writes five fixed values to
five board addresses, in a fixed order, every time it powers up.

| Order | Value | Address |
|---:|---:|---|
| 1 | `$FF` | `$1003` |
| 2 | `$33` | `$1002` |
| 3 | `$00` | `$100B` |
| 4 | `$22` | `$100C` |
| 5 | `$0F` | `$1000` |

The last row is understood. `$1000` is the reply latch from
[Chapter 6](06_taking_orders.md), so that write hands the main CPU the byte `$0F`
and interrupts it. The board's first act after initializing itself is to say
something to the game.

The other four are a blank. `$1002`, `$1003`, `$100B` and `$100C` appear nowhere
else in the sound program: nothing reads them, nothing writes them again, and no
code path branches on anything derived from them. They are outputs into board
logic that this ROM has no visibility into.

The answer is on the other side of the connector. Either the main CPU's program
reads these latches and acts on them, or the board's decode logic turns them into
configuration signals for something. Both possibilities are outside a sound ROM's
reach, and no amount of further work on this file will settle it. What would
settle it is the 68010's disassembly or a look at the schematic sheet covering
that address decoder.

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
load a voice, so it can change tempo, volume, transpose, or control bits on a
running sound from outside. A game could duck the music under a spoken line with
it. The support table it reads is six bytes at `$6559`, all of them zero, so type
12 fails its own validation before doing anything.

Two explanations fit. These may be leftovers from development, written and then
routed around when the game's sound design turned out simpler than expected. Or
this sound board and this program may have been intended to serve more than one
game, with another title's command table selecting the features Gauntlet II does
not use. Distinguishing between those requires a second ROM. One image cannot tell
you what a different image would have done with the same code.

## The command that gets written into RAM

There is a narrow window during a self-test boot when a command from the main CPU
does something unrecognizable.

Initialization enables interrupts and waits for the first IRQ, so it can enter the
main loop at a known point in the tick cycle. During that wait the incoming
command path has not yet been switched into its normal mode. If an NMI arrives
first, the handler takes a different branch: instead of queueing the byte, it
writes it into RAM through a pointer, then advances the pointer and its index.
Whatever the main CPU sends during that window gets deposited into memory at a
place the main CPU is effectively choosing.

Every step of that is traced. The branch, the pointer, the index arithmetic, and
the exit condition are all understood, and so is the fact that the window closes
the moment the mode byte is set. What is missing is any reason for it to exist. A
main CPU that never speaks during those few milliseconds would never trigger it,
and this ROM contains nothing that hints at what the intended payload was.

A boot-time capture of the bus between the two processors would answer it in one
recording. So would the main CPU's initialization code.

## Small unexplained things

**One byte in every instrument.** Offset `$1C` of the 42-byte voice record from
[Chapter 12](12_driving_the_ym2151.md) is skipped. The register-image copy stops
one byte short of it, the level-transform reader starts one byte past it, and no
other code in the ROM indexes it. Across the 55 records it takes exactly two
values, `$00` and `$80`, which is the shape of a flag that meant something to
whoever built the voice data.

**Fifteen instruments with no name.** Of the 55 records, 39 are loaded by
sequences and one more is reached only through the auxiliary-block instruction.
The remaining fifteen are structurally valid, sit on the same grid, and are never
selected. They may be voices for sounds that were cut, or alternates kept for
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
[Chapter 11](11_driving_the_pokey.md). A 128-entry chromatic divider table sits in
ROM, correct and complete, and no POKEY sequence in the game plays a note.

**[needs verification]** Only entries 1–97 are established as a chromatic
divider prefix. The remaining entries overlap the YM key-code/level-table region,
so “128-entry chromatic” and “complete” overstate what is known.

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

**Which coin switch is which.** The board-control routine filters four inputs and
drives two counter solenoids, and the arithmetic tying inputs to outputs is fully
traced. Which physical slot or player position each of the four inputs corresponds
to is a cabinet wiring question.

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

## Two places this book disagrees with itself

Honesty about the ledger includes the ledger's own inconsistencies.

**[needs verification]** The two disagreements below propagate into Chapters 8,
9, 10, 11, and 14 and Appendices C and D. Do not treat either interpretation as
settled until the static catalogs and direct execution agree.

The generated catalogs give the effects chip test a thirty-sweep loop period,
computed by reading its rest durations through the duration table of
[Chapter 8](08_sequence_language_time.md). Executing the ROM's own interrupt
service gives 250 sweeps, which is what the POKEY rule of "control byte times 32"
produces. [Chapter 9](09_sequence_language_opcodes.md)'s loop table prints the
executed figures. The two readings have not been reconciled, and one of them is
wrong.

The second is the shape table. A static enumeration of note control bytes says
five of the eight rows are reachable on POKEY channels. Executing the ROM shows
the POKEY note path storing zero into the shape index every time, which would make
row 0 the only row anything ever selects. [Chapter 10](10_shaping_the_sound.md)
reports the executed result.

Both are cases of a static reading and a dynamic reading of the same code
producing different answers, which usually means one of them has a state
assumption wrong. Neither changes anything a listener would hear.

<!-- TODO: Revisit the final sentence after resolving shape-row reachability;
     non-neutral configured shape rows could affect audible POKEY output. -->

## How you could help

Four artifacts would close most of this list, and none of them requires access to
anything that has not survived.

A **logic-analyzer capture from a running board** would settle the busy-wait
distribution, the catch-up interrupt, the speech cadence, and the coin wiring, all
at once. A capture of the first few milliseconds after power-on would additionally
resolve the boot NMI window.

The **main CPU's disassembly** would name the boot handshake bytes, confirm which
commands the game actually emits, and explain the `$0F` reply. Gauntlet II's game
ROMs are as available as its sound ROM.

**Another revision of this sound ROM**, or the equivalent ROM from another Atari
title on related hardware, would distinguish development leftovers from features
intended for a different configuration. If a second image selects the vibrato
instruction, or points a command at handler type 12, the question answers itself.

**Original Atari source or a build listing** would close every remaining item in
one document, including the ones about intent that no amount of ROM analysis can
reach.

Failing all four, the right thing to do with these items is leave them where they
are. A plausible name attached to an unexplained byte is worse than no name,
because the next person to read it will not know it was a guess.

## What you now know

- Five bytes go out to board latches at every boot and only the last one has a
  known meaning.
- Six handler types are finished routines with no command pointing at them,
  including a live-channel meta-dispatcher that could have modified running sounds.
- A boot-time window lets the main CPU write a byte straight into the sound
  board's RAM, and nothing explains why.
- One byte of every instrument record, fifteen whole instruments, one complete
  sequence, and about 300 bytes of ROM have no consumer anywhere.
- Vibrato, POKEY notes, and the YM2151 frequency-envelope branch are complete
  machinery that this ROM's sounds never activate.
- Questions about real chip timing, the analog mixer, and cabinet wiring cannot be
  answered from a ROM image at all.
- A board capture, the main CPU's code, a second ROM revision, or original source
  would each close a specific part of this list.

## Where this leads

The chapters are finished. What follows is reference: a glossary, the complete
command and opcode lists, the tables worth having open while reading, a guide to
the tool, and a map from each chapter to the documents that argue its case in
full.

## Going deeper

- [`docs/10_known_issues.md`](../docs/10_known_issues.md) — the full research
  backlog, with the exact evidence each item still needs.
- [`docs/generated/external_question_catalog.csv`](../docs/generated/external_question_catalog.csv)
  — the twelve remaining questions, each classified by the artifact that would
  close it.
- [`docs/generated/reserved_handler_catalog.csv`](../docs/generated/reserved_handler_catalog.csv)
  — the six dormant handler types with their exact effects.
- [`docs/generated/type7_residual_catalog.csv`](../docs/generated/type7_residual_catalog.csv)
  — the unreachable trailers and the unreferenced sequence.
- [`docs/03_rom_structure.md`](../docs/03_rom_structure.md) — the unused regions
  and why "unused" is a careful word here.
