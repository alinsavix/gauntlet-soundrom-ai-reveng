# Chapter 16 — How This Was Figured Out

*Before this chapter: [Chapters 1](01_two_computers.md) to
[15](15_case_studies.md).*

Everything in the last fifteen chapters was recovered from one file. There was no
source code, no symbol table, no comments, no listing, and nobody left at Atari to
ask. This chapter is about where the confidence in the previous fifteen came
from, and where it ran out.

## The starting point

Two EPROMs, dumped and concatenated into 49,152 bytes. A schematic. A set of
datasheets for a 6502, a POKEY, a YM2151, and a TMS5220. That is the entire
evidence base.

A ROM image is harder to read than people expect, and the reason is worth
stating plainly for anyone who has never tried. **Nothing in the file says which
bytes are instructions.** There is no header, no section table, no alignment
convention that separates code from data. The byte `$A9` is the instruction "load
the accumulator with a constant" if the processor arrives at that address while
executing, and it is the number 169 if some other code reads it as data. Both
readings are available for every byte in the file, and the file contains 49,152
of them.

Worse, both readings can be correct at once. This ROM has bytes that are read as
sequence bytecode by one routine and as envelope records by another, and the two
readings overlap. [Chapter 14](14_chip_tests.md)'s effects chip test runs a
frequency envelope that eventually walks off the end of its own object and starts
consuming bytes that are also somebody's sequence. Any tool that assumes each
byte has one meaning will get that wrong.

What a disassembler gives you, then, is not a program. It is a hypothesis about a
program, seeded by whatever addresses you were confident enough to start from. In
this ROM there were exactly three such addresses: the reset, NMI, and IRQ vectors
in the last six bytes of the file. Everything else had to be reached from those.

## The method that worked: follow the consumer

The technique that produced most of this book can be stated in one sentence. Do
not ask what a block of data means. Ask what code reads it, and what that code
does with the value.

That inversion matters because data has no self-description and code does.
Finding a 256-byte table of smoothly increasing numbers tells you nothing: it
could be pitches, volumes, gamma correction, or a sine table. Finding the single
instruction that indexes it, and following the result to the register it is
eventually written to, tells you everything.

The clearest example in this project is a 256-byte table near `$72DC`. It was
labelled a frequency table for a long time, and the label was plausible. The
values had the right shape. Frequency tables are common. Sound ROMs have them.

Then somebody followed the consumer. One instruction reads that table. The value
it produces is combined with a per-operator descriptor from the instrument
record, passed through a second table, and written to YM2151 registers `$60`
through `$7F`. Those registers are total level. They are attenuation. The chip's
pitch registers are `$28` and `$30` and this code never touches them.

The table is an operator level transform, and the frequency label was simply
wrong. No amount of staring at the numbers would have settled it. One trace of
where the result went settled it in a paragraph.

The same move corrected several other things. A routine at `$5715` had been
labelled a detune helper; following its writes showed it modifying carrier levels
selected by an algorithm mask, which made it the volume machinery of
[Chapter 12](12_driving_the_ym2151.md). Four per-channel arrays had been read as
envelope pointers; following the two different consumers showed they mean
envelope pointers in POKEY mode and operator levels in YM mode, which is the
memory overloading in [Chapter 9](09_sequence_language_opcodes.md). A run of
bytes in one sound had been read as an implausible run of very high notes;
following the instruction above them showed they were the inline jump-target
table of a computed branch.

Every one of those was a case of a pattern that looked right being beaten by a
consumer that could be traced.

## Cross-checking against independent implementations

The second technique was to use somebody else's chip as an oracle.

MAME contains careful implementations of the POKEY and the TMS5220. The YMFM
library contains one of the YM2151. None of them knows anything about Gauntlet.
They are independent descriptions of what these chips do when you write a
particular byte to a particular register.

That makes them checkable against the ROM in both directions. When the ROM writes
`$28` to AUDCTL, the POKEY implementation says what that means, and the meaning
has to be consistent with what the code around the write was trying to do. When
the ROM computes a key code of `$3E` and a key fraction of zero, the YM2151
implementation says the resulting frequency is 261.58 Hz, and that has to be
close to a C. It is, within a third of a cent. Eight such notes all landing within
half a cent of equal temperament is not something a wrong reading produces by
accident.

The TMS5220 implementation supplied the answer to the seventeen zero bytes in
[Chapter 13](13_speaking.md). The ROM writes them; the ROM does not say why. The
chip model has a sixteen-byte input buffer and aborts an utterance if that buffer
empties before the encoded stop frame arrives. Sixteen to fill, one to spare. The
ROM's behaviour and the chip's behaviour explain each other, and neither
explains itself.

## Executing the ROM to check the reading

The strongest validation available for a reverse-engineered ROM is to run it.

`gauntlet_disasm.py` contains a 6502 interpreter. When it renders a sound to WAV
it does not simulate what the analysis thinks the ROM does. It executes the
ROM's own reset routine, its own command dispatcher, its own allocator, and then
calls its own interrupt service routine at the measured interrupt rate,
repeatedly, capturing every byte the code writes to a chip address. The register
writes that come out are the ROM's, produced by the ROM's arithmetic. Feeding
them to an independent chip model produces audio.

If the theme song comes out recognizable, the reading is right. There is very
little room for a subtle misunderstanding to survive that test, because a
misunderstanding anywhere in the scheduler, the interpreter, the timers, the
envelopes, or the arbitration comes out as noise.

It is worth recording the moment this failed, because it is the most instructive
event in the project's history.

An early version of the tooling exported the theme song as MIDI. The result was
about three seconds long and contained a handful of notes. To a program that had
never heard Gauntlet II, that was a plausible output. To the repository's author,
who had, it was obviously wrong: the theme is half a minute long and there is a
lot of it.

The correction needed was two words: *that's too short*. What came back was a
re-examination of the type-7 record tables, and what it found was that the record
chaining had been misread. The analysis had believed music used two channels. It
uses eight. The "next" column had been under-followed, so six of the theme's
eight voices were never reached, and the piece was being reconstructed from a
quarter of its data.

Everything in [Chapter 7](07_command_to_channel.md) about chains, and everything
in [Chapter 15](15_case_studies.md) about the arrangement, is downstream of that
one correction. A human who knew what the song sounded like was the only
available source of that evidence.

## The evidence discipline

The reference documents in [`docs/`](../docs/README.md) label every claim with one
of five words:

| Label | Means |
|---|---|
| Verified | Established from ROM bytes, bounded disassembly, a table's actual consumer, or supplied hardware documentation |
| Strong inference | Several independent observations agree, but a decisive trace is missing |
| Hypothesis | Plausible, and still needs evidence |
| Unknown | Not determined |
| Contradicted | An earlier claim that current evidence disproves |

The rules behind those labels are strict in a specific way. A table's extent is
verified only when its indexing consumer and the largest index that consumer can
reach both establish the bound. A function's entry point is verified only when
something is known to jump to it. A data interval's end is verified only when a
record length, a control-flow edge, or an exclusive boundary establishes it.
Guessing where a table stops, however obvious the guess, produces strong
inference rather than verification.

Chapters 1 through 15 of this book were filtered to the top two rows of that
table and nothing else. That is what licenses their flat, unhedged tone. Where
this book says a thing happens, `docs/` says it is verified or strongly
supported, and the "Going deeper" list at the end of each chapter points at the
place where the case is argued.

Two places in those chapters still carry an unresolved disagreement between the
generated catalogs and a direct execution of the ROM, and both are marked in the
source of the book rather than smoothed over. The rest is settled.

Nine of the ROM's 26 envelopes have a terminator that a consumer has been proven
to read. The other seventeen are bounded by the next object that something else
independently reaches, which is a good argument and not a proof. That distinction
is the sort of thing the labels exist to preserve.

## That it was mostly done by an AI

This project is an experiment as well as a reverse-engineering effort, and the
result is only honest with that stated.

The repository's author had been working on Gauntlet II's ROMs for years and had
made real progress on the game side. The sound ROM had resisted, for the reason
this chapter opened with: it is abstract, it is table-driven, and there is
nothing obvious to grab. So the sound ROM, a written description of what the
author already knew about the board, and a disassembler were handed to Claude
Code, and it was set to work.

The bulk of what this book describes came out of that. The cost, in API usage,
was about fifty dollars. The number of human corrections needed was small enough
to list:

- **The theme song was too short.** The record chaining was misread, two channels
  instead of eight. Described above, and by a distance the most important
  correction of the project.
- **A false disassembly start.** The analysis had been finding new code by
  searching for the byte pattern "jump-to-subroutine followed by a plausible
  address". One such match was a coincidence inside a data table, so a stretch of
  ROM was being disassembled one byte out of alignment, which produced a handful
  of nonsensical calls into hardware addresses. Spotting those calls was enough
  to unwind it.
- **How the interrupt is generated.** Settled by reading the schematic, which is
  outside anything derivable from the ROM.
- **A memory location was a coin counter.** Board knowledge, not ROM knowledge.

Three of those four are the same kind of thing: evidence that does not exist
inside the file. A ROM cannot tell you what its outputs are wired to, and it
cannot tell you what its music is supposed to sound like. Everything that *is*
inside the file was recoverable from the file, and it was recovered.

The honest summary is that the analysis was very good at the mechanical part and
had no access at all to the parts that require having been in the room. That
division is worth remembering the next time somebody claims either that this kind
of work is now solved or that it cannot be automated.

## What you now know

- A ROM image carries no marker separating code from data, and the same bytes can
  legitimately be both.
- The technique that resolves ambiguity is to find the code that reads a piece of
  data and follow where the result is written.
- Independent chip implementations can be used as oracles, both to interpret
  register writes and to explain behaviour the ROM performs without justifying.
- Executing the ROM and listening to the output is the strongest available test,
  because a misunderstanding anywhere in the pipeline is audible.
- The one thing that test cannot supply is knowing what the result is supposed to
  sound like, which is how the project's biggest error was caught.
- A five-level evidence vocabulary sits behind this book, and chapters 1 through
  15 use only its top two levels.

## Where this leads

[Chapter 17](17_open_questions.md) is the other side of the ledger: the things
that are still unknown, why they are unknown, and what evidence would close each
one.

## Going deeper

- [`docs/09_analysis_method.md`](../docs/09_analysis_method.md) — the allowed
  evidence, the disassembly protocol, and the commands that regenerate every
  catalog.
- [`docs/README.md`](../docs/README.md) — the evidence vocabulary and the source
  hierarchy.
- [`README.md`](../README.md) — the project's own account of the experiment,
  including the ROM part numbers and checksums.
- [`prompting/PROMPT.md`](../prompting/PROMPT.md) and
  [`prompting/PLAN.md`](../prompting/PLAN.md) — the original brief and the plan
  it produced.
