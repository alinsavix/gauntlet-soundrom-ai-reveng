# Chapter 8 — The Sequence Language, Part 1: Notes, Rests, and Time

*Before this chapter: [Chapters 1](01_two_computers.md) to
[7](07_command_to_channel.md).*

Every level of Gauntlet II opens with the same short fanfare: five voices, a
rising figure over a held chord, about four and a half seconds long. Somewhere in
the 48 KB of ROM there has to be a description of that fanfare. What is actually
there is a program, written in a language that exists nowhere else, executed by a
routine that runs inside the interrupt.

## Atari wrote a language instead of writing sounds

The sequence pointer that [Chapter 7](07_command_to_channel.md) left in each
logical channel points at a stream of bytes in ROM. When a channel's timer
expires, the engine reads the byte at that pointer, does what it says, and moves
the pointer along. That is the entire model: a program counter, an instruction
stream, and a small machine that executes it.

The first byte of an instruction decides everything, by range:

| First byte | Means |
|---|---|
| `$00`–`$7F` | A note or a rest, followed by one more byte |
| `$80`–`$BA` | An instruction, followed by zero to three operand bytes |
| `$BB`–`$FF` | Stop this channel |

Notes and rests account for 1,124 of the ROM's 2,166 decoded sequence
instructions, and this chapter is about them.
[Chapter 9](09_sequence_language_opcodes.md) covers the middle row.

## A note is two bytes

The first byte is the pitch. Zero means a rest, and any other value is a
semitone number.

The second byte is where the design gets interesting. It packs four separate
fields into eight bits, only one of which is the length. That is how a channel
attached to the YM2151 reads it, which covers 171 of the ROM's 182 records. The
eleven POKEY records read the same byte by a simpler rule, and this chapter comes
back to them.

| Bit | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
|---|---|---|---|---|---|---|---|---|
| Field | sustain | dotted | division | division | duration | duration | duration | duration |

Reading a real one, from the theme song's bass line:

```
20 83     NOTE G2, quarter, sustained
```

The pitch byte is `$20`. The control byte `$83` breaks down as duration index 3,
division field 0, dotted bit clear, sustain bit set. So: a quarter note, held
rather than released.

And one from the food blip, on the first of its two voices:

```
13 49     NOTE F#1, dotted sixteenth
```

Control byte `$49` is duration index 9, division field 0, dotted bit set, sustain
clear.

Musical notation is sitting right there in the byte. Somebody wrote a music
editor for this, or wrote the data by hand while thinking in bars and beats, and
either way the format was designed by someone who expected to write tunes with
it.

## The duration table

The low four bits index a table of sixteen 16-bit values in ROM. Here it is in
full, with the length each entry works out to at the tempo a channel starts with:

| Index | Value | Sweeps at default tempo | What it is | Times used |
|---:|---:|---:|---|---:|
| 0 | 0 | 0 | Adds no time at all | 0 |
| 1 | 7,680 | 480 | Whole note | 33 |
| 2 | 3,840 | 240 | Half | 73 |
| 3 | 1,920 | 120 | Quarter | 186 |
| 4 | 960 | 60 | Eighth | 121 |
| 5 | 2,560 | 160 | Half-note triplet | 0 |
| 6 | 1,280 | 80 | Quarter-note triplet | 0 |
| 7 | 640 | 40 | Eighth-note triplet | 1 |
| 8 | 1,536 | 96 | Quarter-note quintuplet | 0 |
| 9 | 480 | 30 | Sixteenth | 265 |
| 10 | 240 | 15 | Thirty-second | 375 |
| 11 | 120 | 7.5 | Sixty-fourth | 34 |
| 12 | 60 | 3.75 | Hundred-twenty-eighth | 17 |
| 13 | 320 | 20 | Sixteenth-note triplet | 1 |
| 14 | 160 | 10 | Thirty-second triplet | 0 |
| 15 | 768 | 48 | Eighth-note quintuplet | 0 |

Read the values as a ruler. A whole note is 7,680 units and everything else is a
clean fraction of it: halves and quarters down the left, thirds for the triplets,
fifths for the quintuplets. Three half-note triplets add up to 7,680 exactly.
Five quarter-note quintuplets do too. This is a music theorist's table, not a
programmer's.

The last column counts how often each row is chosen by a note on a YM2151
channel. The plain halves and quarters and the two shortest notes carry almost
everything, because the short effects that make up most of the ROM are built out
of rapid runs rather than tunes. Six rows are never used at all, and the triplets
are used twice between them, which makes the table's careful thirds and fifths
look like a facility built for music that was never written.

(The disassembler prints shorthand names for a few of these rows that do not
match the arithmetic. The values above come straight from the ROM.)

Two modifiers adjust the result. The dotted bit adds half the value again, which
is exactly what a dot means on a page of music: a dotted quarter is 1,920 plus
960. It appears on 107 of the ROM's YM notes and rests.

The division field is a two-bit number that does two different jobs, and the
second job belongs to [Chapter 12](12_driving_the_ym2151.md). Its first job is
described below, under articulation.

## POKEY notes count differently

**[needs verification]** The POKEY-only duration rule in this section conflicts
with `docs/generated/timing_loop_trace_catalog.csv`: direct ROM execution gives
the effects chip test a 250-sweep period, while duration-table interpretation
gives 30 sweeps. Resolve that disagreement before treating the examples below as
settled timing.

A channel attached to one of the POKEY's four voices never touches the duration
table. It masks off the top bit of the control byte and multiplies what is left
by 32.

```
duration = (control byte AND $7F) * 32
```

No table, no dotted bit, no division field. The sword's two events read `00 05`
and `00 87`, giving 5 times 32 and 7 times 32, so at the default tempo of 16 the
sword is ten sweeps of one thing and fourteen of another: about a fifth of a
second in total, which is what it sounds like.

The rule makes sense for what the POKEY is used for here. All eleven POKEY
records are short effects whose shape comes from the envelopes in
[Chapter 10](10_shaping_the_sound.md) rather than from anything resembling
notation, and none of them plays a pitch at all. Every POKEY event in the ROM is
a rest, with the actual sound produced entirely by envelopes running underneath.

## How duration becomes time

Each logical channel has a **tempo**, a number from 0 to 63. Every sweep, the
engine subtracts the tempo from the channel's timer. When the timer goes
negative, the next event is due.

So a duration of 1,920 at a tempo of 44 lasts 1,920 divided by 44, which is 43.6
sweeps, which is 0.364 seconds. Larger tempo values make the music faster. A
channel starts at tempo 16, which makes a whole note 480 sweeps, or almost
exactly four seconds.

Now the part that makes it exact.

When an event comes due, the engine does not reload the timer with the new
duration. It **adds** the new duration to whatever is currently in the timer,
which is a small negative number, because the timer just went past zero.

Work the example through. Timer starts at 1,920 and tempo is 44:

```
timer = 1920            44 sweeps later it holds -16
timer = -16 + 1920      44 sweeps later it holds -32
timer = -32 + 1920      43 sweeps later it holds -4
timer = -4 + 1920       and so on
```

Each note is scheduled from where the previous one actually ended, so the
leftover is never thrown away. Two of those notes took 44 sweeps and the third
took 43, and the average stays at 43.6 forever. A hundred bars later the music is
still in time with itself.

The technique is called a **phase accumulator**, and it is the same trick a
software clock uses when its tick rate does not divide evenly into a second. The
consequence for anyone reading the ROM is that there is no formula for how long a
given note lasts. Rounding each note up individually gives an answer that is
close and wrong, and it drifts further out with every note. The only exact method
is to run the arithmetic note by note, which is why the MIDI files this
repository's tool exports have approximate timing, and why the chapter on case
studies says so out loud.

Every one of the seven finite channels in the music chip test finishes with the
timer holding exactly the same residue it started with, which is the neatest
possible demonstration that the arithmetic closes.

## Two timers, and why notes sound detached

A channel has a second timer running alongside the first. The primary timer
schedules the *next event*. The secondary timer schedules **key-off**, the moment
the current note stops sounding. This is a YM2151 idea: that chip has a key that
gets struck and released, and a POKEY channel has only a volume, so the POKEY
path skips the whole arrangement and lets its envelope decide when the sound
stops.

The secondary timer is derived from the primary one at the moment the note
starts:

```
secondary = primary - 2 * tempo
if the division field is exactly 1:
    secondary = secondary / 2
```

Subtracting twice the tempo takes two sweeps off the end. That is the default
behaviour, and it is what gives the music its articulation: the first note of the
music chip test is an eighth, so its primary timer is 960 and its secondary is
928 at tempo 16, and it sounds for 58 sweeps and then leaves a two-sweep gap
before the next note begins. Sixteen milliseconds of silence is not something you
consciously hear, but without it every note in a run would join onto the next one
and the line would sound like a single sliding tone.

Setting the division field to 1 halves the sounding time and turns that small gap
into a real one. The level-opening fanfare uses it on every quarter note: at
tempo 44 the primary timer is 1,916 and the secondary is 914, so the note sounds
for 21 sweeps and the voice is then silent for 23 before the next attack. The
result is the crisp, detached delivery that makes the fanfare sound like a
fanfare. Two hundred and forty events in the ROM are marked this way, and all of
them are on YM2151 channels.

The sustain bit at the top of the control byte skips the whole calculation. The
secondary timer is loaded with a value so large it will not expire during the
note, so the sound is left running until something else stops it. The theme's
held bass notes work this way, and so does the final note of the music chip test,
which sustains and loops forever.

## Ending, and returning

A note byte followed by a duration byte of exactly zero is the end marker, and it
is the most common instruction in the ROM after notes and rests: 152 of them, one
at the end of nearly every sequence.

What it does depends on context. If this stream was entered as a subroutine, the
marker returns to whoever called it. Otherwise it stops the channel, and stopping
is thorough: the status, volume, current note, and fade state are all cleared, a
key-off is requested so the chip actually goes quiet, both context chains go back
to the free list from [Chapter 7](07_command_to_channel.md), and the channel
unlinks itself from its physical voice's list. The slot is immediately available
for the next sound that needs it.

A first byte of `$BB` or higher stops the channel too, without the second byte
and without the return check. No sequence in this ROM uses it.

## Pitch

Note values are semitone numbers on an ordinary chromatic scale, so adding one
goes up a semitone and adding twelve goes up an octave. The numbering is offset
from MIDI's by eleven: ROM note 49 is MIDI note 60, which is middle C. The 691
notes in this ROM use 64 distinct values running from 13 to 95, a range of just
under seven octaves.

Turning that number into something a chip can use is the last step, and the two
chips want completely different things. The YM2151 wants an octave-and-semitone
code plus a fine-tuning fraction. The POKEY wants a countdown value, where a
bigger number means a lower pitch. [Chapter 11](11_driving_the_pokey.md) and
[Chapter 12](12_driving_the_ym2151.md) do the conversions.

Every one of those 691 notes plays on the YM2151. The POKEY's eleven records
leave the pitch byte at zero and steer their frequency entirely with the
envelopes of [Chapter 10](10_shaping_the_sound.md), which is the next chapter's
first surprise.

> **Try it yourself**
>
> ```bash
> uv run gauntlet_disasm.py soundrom.bin --cmd 0x42 --csv hw_docs/soundcmds.csv
> uv run gauntlet_disasm.py soundrom.bin --score 0x42 --csv hw_docs/soundcmds.csv
> ```
>
> The first command prints the level-opening fanfare as five streams of
> instructions. Channel 1 begins `9D A4 6B` to choose an instrument, `82 0A` to
> set a volume, `80 B0` to set the tempo, and then a quarter rest before its first
> note. Look for the notes written `48 13` and `41 13`: control byte `$13` is
> duration index 3 with the division field set to 1, so those are the crisply
> detached quarter notes described above. The second command lays the same five
> streams out in time. The rows land at 0.36-second intervals, which is 1,920
> duration units divided by a tempo of 44, converted to seconds at 120 sweeps
> per second. Every number in this chapter is visible in those two outputs.

## What you now know

- A sequence is a byte stream: notes and rests below `$80`, instructions from
  `$80` to `$BA`, and a stop marker above that.
- A note is a pitch byte plus a control byte; on a YM2151 channel that control
  byte carries a duration index, a division field, a dotted bit, and a sustain
  bit.
- Sixteen 16-bit durations in ROM cover whole notes down to hundred-twenty-eighths,
  plus triplets and quintuplets, all exact fractions of 7,680 units.
- A POKEY channel ignores that table and takes the low seven bits of the control
  byte times 32.
- Time passes by subtracting the channel's tempo from a timer on every sweep, and
  the next duration is added to the leftover rather than replacing it, so nothing
  drifts.
- A second timer releases YM notes early, by two sweeps normally and by half the
  note when the division field says so; the sustain bit disables it entirely.
- A duration byte of zero returns from a subroutine if there is one, and
  otherwise shuts the channel down and frees everything it held.
- Note numbers are chromatic semitones, eleven below the MIDI numbering.

## Where this leads

[Chapter 9](09_sequence_language_opcodes.md) takes the other half of the
language: the 59 instructions that make a sequence a program rather than a list,
including one piece of 6502 assembly that cannot be explained without showing
it.

## Going deeper

- [`docs/06_sequence_engine.md`](../docs/06_sequence_engine.md) — the stream
  format, the timer arithmetic, and traced note-by-note timings.
- [`docs/05_data_reference.md`](../docs/05_data_reference.md) — the duration
  table and every other sequence-engine table.
- [`docs/04_subsystems.md`](../docs/04_subsystems.md) — the articulation traces
  quoted in this chapter.
- [`docs/generated/timing_duration_trace_catalog.csv`](../docs/generated/timing_duration_trace_catalog.csv)
  — exact timer states through real sequences.
- [`docs/generated/type7_sequence_catalog.csv`](../docs/generated/type7_sequence_catalog.csv)
  — all 2,166 decoded instructions.
