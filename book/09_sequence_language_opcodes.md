# Chapter 9 — The Sequence Language, Part 2: The Opcodes

*Before this chapter: [Chapters 1](01_two_computers.md) to
[8](08_sequence_language_time.md).*

Fire a shot in Gauntlet II and listen to it ricochet. Fire again. The sound is
not quite the same, and it will not be the same the third time either.
There are sixteen versions of it in the ROM, and the sequence picks one by
reading a hardware random number generator and jumping into a table of addresses.
A note list cannot do that. This chapter is about the other half of the sequence
language, the half that makes it a programming language.

## How an instruction is decoded

The engine reads a byte between `$80` and `$BA`, which gives 59 possible
instructions. Each one takes zero to three operand bytes. Somewhere there has to
be a table of 59 addresses and a way to jump to the right one.

The 6502 has no instruction for that. It can jump to a fixed address, and it can
jump through a pointer held at one fixed location in memory, but it cannot jump
to the address held in the *n*th entry of a table. The usual workarounds are to
copy the entry into a scratch pointer first, or to build a chain of comparisons.

The ROM does something better, and this is one of the few places in this book
where the assembly has to be shown, because the trick is the point.

```asm
$5029:  cmp #$bb        ; A holds the opcode byte. Is it an end marker?
$502B:  bcc $5034       ; below $BB, so it is a real instruction: carry on
$502D:  lda #$ff        ; $BB or above: mark this logical channel
$502F:  sta $0228,x     ;   as inactive
$5032:  clc             ; carry clear tells the caller to stop interpreting
$5033:  rts

$5034:  iny             ; step past the opcode byte to its first operand
$5035:  stx $11         ; save the logical channel number
$5037:  asl a           ; double the opcode: $80..$BA becomes $00..$74
$5038:  tax             ;   and use that as a table index
$5039:  lda $507c,x     ; high byte of (handler address - 1)
$503C:  pha             ;   push it
$503D:  lda $507b,x     ; low byte of (handler address - 1)
$5040:  pha             ;   push it
$5041:  ldx $11         ; restore the logical channel number
$5043:  lda ($06),y     ; fetch the instruction's first operand into A
$5045:  sec             ; carry set tells the caller to keep going
$5046:  rts             ; "return" into the handler
```

Two things are happening here.

The doubling on line `$5037` is free arithmetic. Opcodes run from `$80` to
`$BA`, and doubling `$80` gives `$100`, which does not fit in eight bits, so what
lands in the register is `$00`. Doubling `$BA` gives `$74`. The overflow performs
the subtraction of `$80` at no cost, and the result is exactly the index into a
59-entry table of two-byte addresses.

The `rts` on the last line is the trick. A 6502 subroutine return pulls two bytes
off the stack, adds one to them, and jumps there. The ROM pushes an address that
is deliberately one *less* than the handler it wants, so the return lands
precisely on the handler's first instruction. Twelve bytes of code, no scratch
pointer, no self-modification, and every one of the 59 handlers is reached in the
same number of cycles.

The three lines before the `rts` set up the handler's world. X holds the logical
channel number so the handler can index the thirty parallel arrays. A holds the
instruction's first operand, already fetched, because almost every handler wants
it. The carry flag is set, and that is the return contract: a handler that leaves
carry set means "I am finished, fetch the next instruction", and a handler that
clears it means "stop interpreting this channel for now". End markers clear it.
So does any volume instruction that arrives at a channel which is already fading.

The same trick appears in the command dispatcher from
[Chapter 6](06_taking_orders.md), with a fifteen-entry table instead of a
fifty-nine-entry one. Whoever wrote this ROM wrote it once and used it twice.

## Setting the channel's state

Most of the 59 instructions do something unglamorous: they write one number into
one of the thirty parallel arrays. They are best read as groups.

| Group | What the group controls |
|---|---|
| Tempo | How fast this channel's timer counts down |
| Volume | The channel's base loudness |
| Transpose and offset | Constants added to every note's pitch |
| Envelopes | Which stored curve shapes volume and pitch |
| Timbre | Distortion shape and the chip control bits |
| Mode | Whether this channel behaves as POKEY or YM2151 |
| Instrument | Which of the 55 YM2151 voice definitions is loaded |
| Working storage | The channel's register, the shared workspace, ramps |

Most of them come in "set" and "add" pairs, and the add variants are what make
gradual change possible without an envelope.

Tempo shows this at its best. The set instruction shifts its operand right twice
before storing it, so a byte operand becomes a tempo from 0 to 63. The add
instruction performs a plain eight-bit addition with no shift and no range check,
which means an operand of `$FF` subtracts one and `$FA` subtracts six.

"Treasure Chest Opens" is nothing but that idea. It plays the same note twelve
times, and between each pair it adds `$FF`, then `$FF`, then `$FE`, working down
through `$FA`. The tempo starts at 44 and finishes at 6, so the note repeats
faster and faster and then slows to a stop as the chest creaks open. Twelve
notes, one pitch, and a decelerating tempo do all the work.

The complete list of 59 instructions with their operand counts is
[Appendix C](C_opcode_reference.md).

## Control flow

Four instructions change the sequence pointer, and between them they turn a
stream of bytes into a program.

**Counted repeat.** The pair `$8E n` and `$8F` bracket a block. The opening
instruction takes a four-byte record from the free list of
[Chapter 7](07_command_to_channel.md), writes the current sequence pointer and
the previous repeat count into it, and sets the channel's repeat count to *n*.
The closing instruction decrements the count; if the result is not zero it
restores the saved pointer and the block runs again, and when it reaches zero it
returns the record to the pool and execution continues past it. Because the
record holds the outer count, blocks nest.

"Message Appears on Screen" uses it to halve its size. Its first channel plays a
four-note arpeggio, then opens a repeat block, plays the same four notes again,
and closes it with a count of two, so the phrase is heard three times in total
from two copies of the notes.

"Death Touches Player" uses a repeat count of ten around a single sustained whole
note, which is how one instruction produces fifty-three seconds of sound.

**Unconditional jump.** One instruction replaces the sequence pointer with a
16-bit address. There are five of them in the whole ROM, and every one of them
jumps backwards to form a loop:

| Sound | Reaches the loop after | Repeats every |
|---|---:|---:|
| Player Touches Force Field | 480 sweeps | 480 sweeps |
| Slow Motion | 15 sweeps | 15 sweeps |
| Effects chip test, channel 1 | 442 sweeps | 250 sweeps |
| Effects chip test, channel 2 | 442 sweeps | 250 sweeps |
| Music chip test, channel 8 | 1,500 sweeps | 480 sweeps |

Five back edges are the complete set of looping sound in Gauntlet II. Three of
them are the two chip tests, which loop so a technician can leave them running.
The other two are the force field and slow motion, and those are exactly two of
the three sounds that [Chapter 6](06_taking_orders.md) gave a stop command to.

**Subroutine call.** The language has one. It pushes a return record and enters a
16-bit target, and the `xx 00` marker from
[Chapter 8](08_sequence_language_time.md) returns from it. No sequence in this
ROM calls it. The mechanism is complete, the return path in the interpreter is
live code, and nothing uses it.

**Indexed jump.** This one is the reason the chapter opened with a ricochet, and
it gets its own section.

## Variables, arithmetic, and decisions

Each logical channel has a general-purpose register of its own, plus a shadow
copy that the comparison instructions use. All thirty channels also share
sixteen bytes of workspace in the zero page, so one channel can leave a value
where another can find it.

The arithmetic instructions add, subtract, AND, OR, and exclusive-OR an
immediate operand into the register, and two more shift it left or right.

The interesting one is the classifier. It takes a small index and loads a
*named* piece of state into the register:

| Index | Loads |
|---:|---|
| 0 | This channel's base volume, on a POKEY channel |
| 1 | This channel's tempo |
| 2 | This channel's transpose |
| 3 or 4 | Volume state, with the exact meaning depending on the chip |
| 5 | The POKEY's hardware random number |
| 6 to 21 | One of the sixteen shared workspace bytes |
| 22 and up | The register's own shadow |

Four more instructions compare the register against a classified value and jump
to a 16-bit address if the result is zero, non-zero, positive, or negative. Put
those together with the arithmetic and the classifier, and a sequence can read
its own tempo, do a calculation on it, and change what it plays as a result. A
piece of music in this ROM is able to make decisions about itself while it runs.

None of the four comparison instructions is used by any sound in this ROM. Of
the arithmetic, only AND is used, and only in the pattern the next section
describes.

## Randomness, and the jump table trick

The indexed jump instruction reads the channel's register, uses it as an index
into a table of 16-bit addresses stored inline in the sequence itself, and jumps
to the entry it finds. There is a variant that increments the register
afterwards, so successive visits walk down the table.

Combined with classifier index 5, which reads the POKEY's free-running
polynomial counter as a random byte, it gives a sound a menu of endings:

```
B2 05                  load the POKEY's random number
AB 0F                  keep the low four bits
AE <sixteen addresses> jump to the one that number selects
```

That is the whole of "Shots Reflecting", right after it chooses an instrument and
a tempo. Sixteen targets, each a single note, chosen fresh every time the sound
plays. "Cyclical Walls" does the same with a mask of `$03` and four targets, and
"Player Shoots Dragon" uses sixteen again.

The ROM contains 34 indexed jumps, and 31 of them are preceded by an AND with
zero, which forces the index to zero and leaves a table with exactly one entry.
Those 31 are ordinary jumps written in an unusual way. Only three are actually
random, and they are the three sounds just named.

## The same language, two different chips

One sequence engine drives both chips, and some instructions mean different
things depending on which one the channel is attached to.

The volume instruction is the clearest case. On a POKEY channel it stores a base
volume. On a YM2151 channel it reloads the four operator levels of the current
instrument and applies an attenuation from a sixteen-step curve, because
[Chapter 3](03_three_sound_chips.md) established that making an FM voice quieter
is not a matter of turning a knob. The control-bits instruction accumulates an OR
mask for the POKEY's mode register on one chip and does something quite different
on the other.

The economy goes further than the instruction set. Four of the thirty
per-channel arrays are used as two 16-bit envelope pointers when the channel is
in POKEY mode, and as the four operator base levels when it is in YM2151 mode.
The same 120 bytes of RAM, two entirely different meanings, decided by one status
bit. RAM was the scarcest thing on this board.

Eight instructions are YM2151-only, and they are the ones
[Chapter 12](12_driving_the_ym2151.md) needs: load an instrument, load a block of
registers, adjust the carrier levels, offset the pitch. The most used of all 59
instructions is the instrument load, which appears 147 times and selects one of
39 distinct voice definitions.

One instruction crosses subsystems entirely. It triggers a speech command from
inside a sequence, so a piece of music could speak. Nothing in this ROM uses it.

## What is actually used

The language has 59 instructions. The 62 sounds in this ROM use 26 of them.

| Used | Count | Used | Count |
|---|---:|---|---:|
| Load instrument | 147 | Distortion shape | 18 |
| Set volume | 109 | Load YM envelope block | 14 |
| Set tempo | 106 | Set volume envelope | 13 |
| YM pitch offset | 88 | Set frequency envelope | 13 |
| Add tempo | 50 | Switch to POKEY mode | 13 |
| Set transpose | 46 | Classify into register | 10 |
| Start a volume ramp | 44 | Store register to workspace | 9 |
| AND the register | 43 | Set control bits | 7 |
| Indexed jump | 34 | Unconditional jump | 5 |
| YM carrier level delta | 31 | Fade this channel out | 5 |
| Open repeat block | 23 | Shift YM level left | 4 |
| Close repeat block | 23 | Load one YM register | 2 |
| Add to frequency | 19 | Subtract from YM volume | 14 |

The other 33 are dead in this ROM: the subroutine call, the vibrato instruction,
all four comparison-and-branch instructions, every arithmetic instruction except
AND, the speech trigger, the instruction that queues a reply to the main CPU,
and six that do nothing at all except consume their operand.

The honest reading of that list is that Atari built a general-purpose sound
language and then wrote a fairly conservative set of sounds with it. The parts
that go unused are not stubs; they are finished, working code with no callers.
[Chapter 17](17_open_questions.md) returns to the question of what they were for.

> **Try it yourself**
>
> ```bash
> uv run gauntlet_disasm.py soundrom.bin --cmd 0x1C --csv hw_docs/soundcmds.csv
> uv run gauntlet_disasm.py soundrom.bin --cmd 0x2C --csv hw_docs/soundcmds.csv
> uv run gauntlet_disasm.py soundrom.bin --cmd 0x2E --csv hw_docs/soundcmds.csv
> ```
>
> Three sounds, three kinds of control flow. `$1C` shows `PUSH_SEQ_EXT $02` at
> `$80FB` and `POP_SEQ` at `$810D` with eight events between them, the counted
> repeat block. `$2C` is only four instructions long before it reaches
> `COND_JUMP_REG_Z` with sixteen targets printed out, and the tool labels it
> `computed table, mask $0F`: the random branch. `$2E` sets a voice, a volume, and
> a sustained whole note, then jumps back onto that note forever, and the tool
> prints `LOOP -> $6754` and stops. Notice that the disassembler reports `$2E` as
> a "decoded loop prefix" of 4.0 seconds rather than a play time, because the
> sound has no end.

## What you now know

- The interpreter reaches all 59 instruction handlers by doubling the opcode,
  pushing a target-minus-one address, and executing a return.
- The carry flag is the contract between a handler and the interpreter: set to
  continue, clear to stop.
- Most instructions write one number into one per-channel array, and most come in
  set-and-add pairs; adding a negative tempo is how sounds slow down.
- Counted repeat blocks borrow a four-byte record so they can nest, and five
  backward jumps account for every looping sound in the game.
- A channel has a register, a shadow, and sixteen shared workspace bytes, plus
  arithmetic and comparison instructions to work on them.
- Reading the POKEY's random number into that register and using it to index an
  inline table of addresses is how three sounds vary each time they play.
- Twenty-six of the 59 instructions are used by this ROM's sounds.

## Where this leads

[Chapter 10](10_shaping_the_sound.md) covers what happens on the sweeps between
instructions, when no note is starting and no instruction is being decoded, and
the engine is quietly nudging volume and pitch a step at a time.

## Going deeper

- [`docs/06_sequence_engine.md`](../docs/06_sequence_engine.md) — the full opcode
  table, the dispatch mechanism, and the control-flow model.
- [`docs/05_data_reference.md`](../docs/05_data_reference.md) — the opcode jump
  table and the classifier's index map.
- [`docs/generated/bytecode_handler_catalog.csv`](../docs/generated/bytecode_handler_catalog.csv)
  — all 59 handlers with operand counts and chip scope.
- [`docs/generated/type7_control_flow_catalog.csv`](../docs/generated/type7_control_flow_catalog.csv)
  — every jump, repeat, and indexed target in the ROM.
- [`docs/generated/type7_sequence_catalog.csv`](../docs/generated/type7_sequence_catalog.csv)
  — every decoded instruction, with the bytes it consumed.
