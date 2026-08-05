# Chapter 10 — Shaping the Sound: Envelopes, Ramps, and Distortion

*Before this chapter: [Chapters 1](01_two_computers.md) to
[9](09_sequence_language_opcodes.md).*

The fireball is a swoop. It starts somewhere near the top of hearing, dives, and
comes back up, swelling and then fading as it goes. Its sequence is eight
instructions long and contains no notes at all, only a rest. Everything you hear
happens on the sweeps in between, while the interpreter is doing nothing, and
this chapter is about that machinery.

## The problem an envelope solves

A note that switches on at full volume and off again sounds like a beep. Real
instruments swell and decay, and interesting noises change while they last.

The engine is already in a good position to do something about that. It visits
every channel 120 times a second whether or not anything has changed, so
adjusting a volume or a pitch by a small amount on each visit costs a handful of
instructions and no extra scheduling. An **envelope** is a list of those small
adjustments, stored in ROM, walked one step per sweep.

Gauntlet II's ROM contains 13 volume envelopes and 13 frequency envelopes.

## Volume envelopes

A volume envelope is a list of two-byte records:

| Byte | Meaning |
|---|---|
| 0 | How many sweeps to apply this record |
| 1 | A signed amount to add on each of those sweeps |

The sword is the clearest example in the ROM. Its volume envelope is six
records:

| Record | Sweeps | Change each sweep | Running total |
|---:|---:|---:|---:|
| 1 | 14 | +8 | 8 up to 112 |
| 2 | 2 | −56 | 56, then 0 |
| 3 | 2 | +8 | 8, then 16 |
| 4 | 2 | 0 | held at 16 |
| 5 | 2 | −8 | 8, then 0 |
| 6 | 2 | 0 | held at 0 |

Twelve bytes, and out of them comes a rising swipe, a sharp cut, and a short
second tap. The whole thing is over in twenty-four sweeps, which is a fifth of a
second.

The running total goes through three more steps before anything is audible. The
engine keeps it in an internal accumulator, divides it by eight, adds the
channel's base volume, and clamps the result to the POKEY's range of 0 to 15. So
the envelope works in units
eight times finer than the four bits it is ultimately steering, which is what
lets a fade cross one audible step over several sweeps rather than jumping.

The sword's fourteen `+8` steps therefore produce exactly fourteen audible
volume levels, one per sweep, 8.3 ms apart. That is what the exercise at the end
of this chapter measures.

Two other numbers join the volume at the last moment. A signed value from the
shape table described below is added to the accumulator before the division, and
the channel's distortion setting is OR'd into the top three bits after it. One
byte reaches the chip, and it carries loudness in its bottom half and timbre
above that.

## Ending an envelope, and looping one

A record whose count and amount are both zero ends the envelope. The channel
falls back to its plain base volume and stops stepping.

A count of `$FF` means something else entirely: this is a **loop control**
record, and it has a third byte.

| Byte | Meaning |
|---|---|
| 0 | `$FF`, marking this as a control record |
| 1 | How many times to take the loop |
| 2 | How many bytes to rewind |

The engine keeps a separate loop counter per channel. On first arrival it loads
the counter from byte 1; on later arrivals it decrements the counter, and when
the counter runs out it steps past the control record and carries on. While the
loop is live, byte 2 is subtracted from the envelope's base pointer, so the
records just played are played again.

Both kinds of envelope use the same control record. The effects chip test has one
in the frequency envelope of its second channel: the three bytes `FF FF 06`
rewind six bytes and take the loop 255 times, so two records are replayed until
something stops the sound. A repeating tremolo, or in this case a repeating
churn, costs three bytes.

## Envelopes restart with every note

A channel's envelope pointers are set once, by an instruction, and then stay put
for as long as the sound lasts. The *cursors* into them do not.

Every time a channel begins a new note, the engine zeroes the accumulator, the
loop counter, and the position within each envelope, and reads the first record
of each one fresh. So a sequence sets up a shape once and gets it applied to
every note that follows, which is exactly how an instrument behaves: strike it
again and it swells and decays again.

That also explains why the envelope pointer itself is what a loop control record
rewinds. The cursor is a position; the pointer is the base the position is
measured from; and moving the base backwards is cheaper than storing a second
address.

## Frequency envelopes

A frequency envelope has the same shape with a wider amount:

| Byte | Meaning |
|---|---|
| 0 | How many sweeps to apply this record |
| 1–2 | A signed 16-bit amount to add on each of those sweeps |

Sixteen bits are needed because this envelope steers a divider rather than a
volume, and dividers need range. As with volume, the accumulated value is finer
than the register it feeds, so a slow sweep can crawl.

All 13 frequency envelopes in the ROM belong to POKEY channels, and here is why
that matters more than it sounds. [Chapter 8](08_sequence_language_time.md)
established that every POKEY event in Gauntlet II is a rest with the pitch byte
left at zero. The POKEY sequences do not play notes. Their entire melodic
content, every swoop and dive and chirp, comes out of these envelopes.

The fireball's is a good one to follow. Its first records add 144, then 32, then
0, then 32, and carry on climbing in small steps before turning around and
descending again. A rising divider is a falling pitch, so the register the chip
sees climbs from 0 to 20 over about a third of a second and then falls back to 0.
Underneath it, the volume envelope swells from 1 to 8 and decays to 2. Two
envelopes, one rest, and the result is a fireball.

## The shape table

Between the volume envelope and the division by eight sits one more table: eight
rows of sixteen signed bytes each, stored in ROM as a single 128-byte block.

| Row | The sixteen steps |
|---:|---|
| 0 | 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 |
| 1 | 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 |
| 2 | 0 0 0 0 0 0 −64 −128 −128 −128 −128 −128 −128 −128 −128 −128 |
| 3 | 0 0 0 −64 −128 −128 −128 −128 −128 −128 −128 −128 −128 −128 −128 −128 |
| 4 | 32 32 32 32 32 32 31 29 26 22 18 12 6 3 1 0 |
| 5 | 32 32 32 29 22 12 4 1 0 0 0 0 0 0 0 0 |
| 6 | 64 64 64 64 64 64 63 59 53 45 36 24 12 4 1 0 |
| 7 | 64 64 64 59 45 24 4 0 0 0 0 0 0 0 0 0 |

Read a row left to right. Each sweep, the engine adds the value at the current
position to the volume accumulator and advances the position by one, stopping on
the last entry and staying there. Rows 4 and 6 are a slow decay at two different
strengths, rows 5 and 7 are a fast one, and rows 2 and 3 are a delayed cut that
takes the volume down rather than up.

One byte per channel holds both the row and the position within it: the high
nibble picks the row, the low nibble counts along it and stops at 15.

That byte gets written in two places, and which one runs depends on the same
status bits that chose the duration rule in
[Chapter 8](08_sequence_language_time.md). A channel on the duration-table side
takes the row from bits 3 to 5 of the note's control byte. A channel on the
POKEY side has the byte set to zero, every time it starts a note or a rest.

The consequence is a small joke at the ROM's expense. The row index is only ever
*read* on the POKEY volume path — it is added to the volume accumulator, which
only POKEY channels have. So the write that could select an interesting row
happens on channels that never read it, and the channels that do read it are
guaranteed to find row 0, which is sixteen zeroes. The table changes nothing
about any sound Gauntlet II makes. The mechanism is complete and the curves are
real; the two halves of it never meet.

It is worth saying what does *not* select the row, because the name invites the
guess: the distortion instruction of
[Chapter 9](09_sequence_language_opcodes.md) has nothing to do with it. That
handler is two instructions long and stores one byte, the distortion field that
gets OR'd into the POKEY control byte. It never touches the shape index.

## Fades and ramps

An envelope is a fixed shape. A **fade** is different: it is a request to move
the volume by a certain total amount at a certain rate, arriving whenever it
arrives.

The fade commands from [Chapter 6](06_taking_orders.md) and the ramp
instruction from [Chapter 9](09_sequence_language_opcodes.md) both feed the same
machinery. They hand a channel three things: a signed amount, a duration, and a
rate index.

The awkward part is that a fade usually needs to move the volume by less than one
step per sweep. Rounding down means never moving at all. Rounding up means
arriving far too early.

The engine's answer is **fixed-point arithmetic**. The amount is a 16-bit
number in which the high byte counts whole volume steps and the low byte counts
two-hundred-and-fifty-sixths of one. The rate index selects a byte from a
sixteen-entry table, and that byte says how many times to halve the amount before
using it. Several indices give the same byte, so the sixteen entries cover nine
distinct settings ([Appendix D](D_reference_tables.md) has the table in full):

| Rate byte | Divides the amount by |
|---|---:|
| `$80` | 2 |
| `$40` | 4 |
| `$20` | 8 |
| `$10` | 16 |
| `$08` | 32 |
| `$04` | 64 |
| `$02` | 128 |
| `$00` | 256 |
| `$FF` | Special: count down and stop |

Each sweep, the divided amount is split. The whole-step part is applied
immediately. The fractional part is added to a remainder byte the channel keeps,
and whenever that remainder overflows, one extra whole step goes with it.

The theme song's fade-out is the concrete case. Command `$3C` hands every channel
playing the theme an amount of −48 steps, a countdown, and a rate that divides by
32, which comes to one and a half steps per update. Watch the channel's stored
levels while it runs and they climb 25, 26, 28, 29, 31, 32, 34: one step, then
two, then one, then two, as the accumulated halves tip over. Without the
remainder byte the fade would move one step each time and take half as long
again, or two steps each time and be over too soon.

The same machinery serves the ramp instruction inside a sequence. The theme's
lead part uses one to push its own level up before a phrase, which is a
crescendo written in three bytes.

There is a third way in, and it is the tidiest thing in this chapter. One
instruction in the sequence language does nothing except write the same five
values the fade command writes: amount zero, remainder zero, ramp −48, a
countdown of two, and the marker that says this channel is fading. A sequence
that executes it fades itself out from that point, using the identical machinery
the game would have used to fade it from outside. The level-opening fanfare uses
it: each of its five parts reaches that instruction two thirds of the way
through, so the last phrase of the fanfare is already dying away while it plays.
All five uses of that instruction in the entire ROM are the five parts of that
one fanfare, two bytes each.

## Where the shaping lands

On a POKEY channel, all of this converges on a single byte. Base volume plus
envelope plus shape, divided by eight, clamped to the range 0 to 15, and OR'd
with the distortion setting. Sixteen levels of loudness and a handful of
timbres is the entire expressive range of the chip, and the engine spends 120
updates a second working inside it.

On a YM2151 channel the same instructions mean something else. Making an FM
voice quieter means increasing the attenuation of its **carrier** operators, and
which of the four operators are carriers depends on which of the eight
algorithms the instrument uses. A fade on a YM channel therefore has to consult
a table of algorithms before it knows which numbers to change, and changing the
wrong ones would alter the timbre rather than the loudness.
[Chapter 12](12_driving_the_ym2151.md) is where that gets sorted out.

> **Try it yourself**
>
> ```bash
> uv run gauntlet_disasm.py soundrom.bin --sfx-wav 0x47 --csv hw_docs/soundcmds.csv
> ```
>
> That writes `sfx_0x47.wav`, 1.204 seconds of audio built from 237 POKEY
> register writes, of which the last second is a tail added so the sound can ring
> out. To see the envelope rather than hear it, measure the loudest sample in each
> 8.3 ms sweep:
>
> ```bash
> python -c "
> import wave, struct
> w = wave.open('sfx_0x47.wav')
> s = struct.unpack('<%dh' % w.getnframes(), w.readframes(w.getnframes()))
> step = int(44100 * 0.008344)
> for i in range(24):
>     peak = max(abs(x) for x in s[i*step:(i+1)*step])
>     print('%2d %5d %s' % (i, peak, '#' * (peak * 40 // 32768)))
> "
> ```
>
> Twenty-four lines come out. The first fourteen climb steadily, from 1,166 to
> 29,490, one step per line: that is the sword's `14 x +8` record, drawn in the
> audio. Then line 15 drops by half and line 16 falls to almost nothing, which is
> the `2 x -56` record cutting the level to 7 and then to 0. The small plateau in
> lines 17 to 20 is the third and fourth records, the short second tap. The whole
> shape from the table earlier in this chapter is visible in the waveform, and
> every step of it is one sweep of the interrupt.

## What you now know

- An envelope is a list of records saying "add this much, this many times", and
  the engine walks it one record step per sweep.
- Volume envelope records are two bytes; frequency envelope records are three,
  because a pitch delta needs sixteen bits.
- Both accumulate in a value finer than the register they feed, so small changes
  are possible.
- A zero record ends an envelope, and a record beginning `$FF` rewinds the
  envelope pointer a given number of bytes a given number of times.
- All 13 frequency envelopes belong to POKEY channels, and since no POKEY event
  in the ROM carries a pitch, those envelopes are the entire melodic content of
  every POKEY sound.
- Every new note restarts both envelopes from their first record.
- A fade moves a level by a fractional amount per update, keeping the fraction in
  a remainder byte so nothing is lost to rounding.
- The fade command, the ramp instruction, and the self-fade instruction all write
  the same five values into the same five per-channel fields.
- On the POKEY everything ends up in one byte; on the YM2151 it ends up in the
  operator levels, which is a longer story.

## Where this leads

[Chapter 11](11_driving_the_pokey.md) takes the last few inches of the POKEY
path: four prepared channels, a priority contest, a pair of channels joined into
one 16-bit counter, and nine register writes.

## Going deeper

- [`docs/06_sequence_engine.md`](../docs/06_sequence_engine.md) — envelope record
  formats, loop controls, and the consumers that read them.
- [`docs/05_data_reference.md`](../docs/05_data_reference.md) — the shape table,
  the fade-rate table, and every envelope object in the ROM.
- [`docs/04_subsystems.md`](../docs/04_subsystems.md) — fade and ramp staging.
- [`docs/generated/type7_envelope_catalog.csv`](../docs/generated/type7_envelope_catalog.csv)
  — every envelope with its records, terminators, and confidence.
- [`docs/generated/volume_shape_catalog.csv`](../docs/generated/volume_shape_catalog.csv)
  — the eight shape rows with their signed values.
- [`docs/generated/fade_rate_catalog.csv`](../docs/generated/fade_rate_catalog.csv)
  — all sixteen rate settings.
