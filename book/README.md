# How Gauntlet II Makes Noise

Eat a plate of food in Gauntlet II and the game writes one byte into a
pigeonhole. Everything else is done by a second computer, on its own board, with
its own processor, its own memory, and three sound chips that work in three
completely different ways.

This book is about that second computer. It explains the hardware, the program
that runs on it, the small custom language every sound in the game is written in,
and what happens between the byte arriving and the noise coming out of the
speaker.

## Who this is for

A programmer who has never seen 6502 assembly and has never taken an arcade board
apart. You are assumed to know what a variable, a loop, an array, a lookup table,
and a hexadecimal number are. Everything else gets introduced at the point it is
first needed: interrupts, memory-mapped I/O, ring buffers, free lists, fixed-point
arithmetic, FM synthesis, and speech coding.

There is very little assembly in here. Three or four moments in the whole book
show real 6502 instructions, and they are the moments where the trick being
described cannot be explained without them. Everything else is plain English,
tables, and short pseudocode.

## How to read it

Straight through. Each chapter assumes the ones before it and nothing from the
ones after.

The book is in four movements.

**The machine.** Chapters 1 to 4. What the sound CPU can see and touch, what the
three chips do, and the interrupt that drives everything. Chapter 4 defines the
unit of time the rest of the book counts in, so it is the one to read slowly.

**Waking up and taking orders.** Chapters 5 and 6. Power-on, self-test, and the
pipeline that turns an arriving byte into a decision about what to play.

**Making a sound.** Chapters 7 to 13. The heart of it. How a command becomes a set
of voices, the language that describes every sound in the game, the curves that
shape it, and the last few inches into each of the three chips.

**Watching it happen.** Chapters 14 and 15. Complete walkthroughs: first the three
self-test sounds, which were written to be obvious, then three real game sounds
traced from one byte to air.

Two closing chapters step outside the machine, and six appendices are reference
you can dip into at any point.

## Contents

### The machine

| | |
|---|---|
| **[1. Two Computers in One Cabinet](01_two_computers.md)** | Why the sound needs its own processor, the one-byte conversation between the two, and how to get set up to follow along |
| **[2. A Tour of the Sound Board](02_tour_of_the_board.md)** | 65,536 numbered boxes, some of which are chips rather than memory |
| **[3. Meet the Three Sound Chips](03_three_sound_chips.md)** | POKEY, YM2151, and TMS5220, and the surprising way the work is divided between them |
| **[4. The Heartbeat](04_heartbeat.md)** | The interrupt borrowed from the video circuitry, and where the 8.3-millisecond tick comes from |

### Waking up and taking orders

| | |
|---|---|
| **[5. Waking Up](05_waking_up.md)** | Reset, the walking-bit RAM test, three ROM checksums, and a watchdog built out of one byte |
| **[6. Taking Orders](06_taking_orders.md)** | One byte, two table lookups, and fifteen kinds of job |

### Making a sound

| | |
|---|---|
| **[7. From Command to Channel](07_command_to_channel.md)** | Thirty sounds in progress, twelve chip voices, and what happens when they collide |
| **[8. Notes, Rests, and Time](08_sequence_language_time.md)** | The sequence language, first half: a note is two bytes, and time never drifts |
| **[9. The Opcodes](09_sequence_language_opcodes.md)** | The sequence language, second half: 59 instructions, control flow, and a hardware random number generator |
| **[10. Shaping the Sound](10_shaping_the_sound.md)** | Envelopes, loop records, fades, and what happens on the ticks between notes |
| **[11. Driving the POKEY](11_driving_the_pokey.md)** | Four channels, a priority contest, a pair trick, and nine register writes |
| **[12. Driving the YM2151](12_driving_the_ym2151.md)** | A 42-byte instrument, a chip that has to be asked before every write, and a volume control that is not a volume control |
| **[13. Speaking](13_speaking.md)** | Two thirds of the ROM, a queue, a byte pump, and seventeen zeroes at the end of every phrase |

### Watching it happen

| | |
|---|---|
| **[14. The Chip Tests](14_chip_tests.md)** | Commands `$04`, `$05`, and `$08` traced end to end: one clean example of each pipeline |
| **[15. Case Studies](15_case_studies.md)** | "Food Eaten", "Needs food, badly.", and the Gauntlet II theme, from one byte to air |

### About the work

| | |
|---|---|
| **[16. How This Was Figured Out](16_how_this_was_figured_out.md)** | Reverse engineering a ROM with no symbols, no labels, and nobody left to ask |
| **[17. What We Still Don't Know](17_open_questions.md)** | The honest ledger, and what evidence would close each item |

### Reference

| | |
|---|---|
| **[A. Glossary](A_glossary.md)** | Every term the book defines, with the chapter that introduces it |
| **[B. The Complete Command List](B_command_list.md)** | All 219 commands, what each one plays or says, and which chip does it |
| **[C. The Bytecode Opcode Reference](C_opcode_reference.md)** | All 59 sequence instructions, with operand counts and how often each is used |
| **[D. Reference Tables](D_reference_tables.md)** | Memory map, clock tree, durations, envelope shapes, pitch tables, and the instrument record layout |
| **[E. Using `gauntlet_disasm.py`](E_using_the_tool.md)** | Building the ROM image, every flag with real output, and regenerating the catalogs |
| **[F. Where to Look Next](F_where_to_look_next.md)** | Chapter by chapter, where the rigorous version of each claim lives |

The seventeen chapters and six appendices above are the whole book. One other
file sits in this directory: [`OUTLINE.md`](OUTLINE.md) is the working outline
and author's brief the book was written from. It is a specification rather than
prose, it is kept for the record, and it is not part of the book.

## Before the first exercise

Most chapters end with a **Try it yourself** box, and every one of those boxes
needs a copy of the sound ROM. (Chapters 16 and 17 are the exceptions; they are
about how the work was done and what is still unknown, and there is nothing to
run.) **The ROM is not in this repository**, because the code is still Atari's.
You supply it by concatenating two EPROM images; the part numbers, the expected
SHA-1, and the one command that checks it are in
[Chapter 1](01_two_computers.md) and again in
[Appendix E](E_using_the_tool.md).

Once `soundrom.bin` is in the repository root, the tool needs nothing installed:

```bash
uv run gauntlet_disasm.py soundrom.bin --list --csv hw_docs/soundcmds.csv
```

That form works on Windows, macOS, and Linux, and every box in the book is
written to be pasted verbatim. One exception: rendering YM2151 audio compiles a
bundled chip model, so those specific commands need a C++ compiler.
[Chapter 12](12_driving_the_ym2151.md) says so where it first matters.

## How confident this book is

Chapters 1 through 15 state things plainly, with no hedging anywhere. That flat
tone is not confidence for its own sake. Underneath the book sits a technical
reference in [`docs/`](../docs/README.md) that labels every claim with how well it
is established, and these chapters were filtered to admit only the two strongest
levels. Anything weaker was left out or handed to
[Chapter 17](17_open_questions.md), where the uncertainty is the subject.

<!-- TODO: Qualify this confidence statement. Two disagreements between the
     generated catalogs and direct ROM execution are still open, and are marked
     [needs verification] where they appear:
       - the POKEY duration rule: chapters 8, 9, 14 and appendix D.7
       - the volume-shape selector: chapter 10 and appendices C and D.8
     Chapter 17 states both. Either resolve them or say here that the
     verified/strong-inference filter has two documented exceptions. -->

So if a sentence here makes you suspicious, there is somewhere specific to go.
The **Going deeper** list at the end of each chapter names the `docs/` chapter and
the generated data files covering the same ground rigorously, and
[Appendix F](F_where_to_look_next.md) collects all of those in one table.

[Chapter 16](16_how_this_was_figured_out.md) explains where the confidence came
from, including the part where most of the analysis was done by an AI, what that
cost, and the four corrections a human had to make.
