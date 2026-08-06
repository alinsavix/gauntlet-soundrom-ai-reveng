# Chapter 11 — Driving the POKEY

*Before this chapter: [Chapters 1](01_two_computers.md) to
[10](10_shaping_the_sound.md).*

Swing the sword. Fire an arrow. Watch a Lobber's rock arc across the room. Those
three noises, and four more, are the whole of what the POKEY contributes to
Gauntlet II. Seven effects and one diagnostic, out of 219 commands. This chapter
follows the last few inches of the path they take: from four winning candidates,
one per POKEY voice, to nine numbers written into a chip.

## The sweep

[Chapter 4](04_heartbeat.md) established the alternation. On odd ticks the
interrupt services the POKEY, on even ticks the YM2151, so each chip gets a full
refresh about 120 times a second.

A POKEY sweep begins at a small dispatcher that knows two things: which chip
this tick belongs to, and where that chip lives. It builds a pointer to `$1800`
and hands control to the POKEY routine. Everything that follows writes through
that pointer rather than to fixed addresses, which is why the same code could
in principle drive a POKEY anywhere in the address space.

The routine then works through the four physical channels as **two pairs**:
channels 3 and 4 first, then channels 1 and 2. Pairs matter for a hardware
reason that the rest of this chapter builds up to.

A word on numbering, because two schemes meet here. POKEY numbers its own
registers from one, so AUDF1 through AUDF4 and "channel 3" mean the chip's
channels. The allocator of [Chapter 7](07_command_to_channel.md) numbers the
twelve physical voices from zero, so POKEY occupies 0 through 3 there. Chip
channel 1 is physical voice 0, and so on up.

For each channel it takes the head of that channel's priority-sorted list from
[Chapter 7](07_command_to_channel.md) and runs the sequence engine down the
whole list. Every logical channel on it advances: timers counted down, notes
and instructions decoded, envelopes stepped, fades applied. Each one leaves
behind a set of numbers describing what it would like the chip to do.

## What a candidate looks like

The engine's output for one logical channel is small:

| Value | What it is |
|---|---|
| Priority | The number this sound was allocated with |
| Frequency | An 8-bit divider for AUDF |
| Control | Volume in the low nibble, distortion in the top three bits, for AUDC |
| OR mask | Bits this channel wants set in the chip's mode register |
| AND mask | Bits this channel is willing to leave set |

[Chapter 10](10_shaping_the_sound.md) built the middle two. Base volume plus
volume envelope plus shape, divided by eight and clamped to 0 through 15, OR'd
with the distortion setting, gives the control byte. Base frequency plus
frequency envelope gives the divider.

The distortion field is worth a table of its own, because it is the POKEY's
whole palette of timbre and Gauntlet II uses seven of its eight settings. It is
three bits wide, sitting at the top of the control byte, so the values below all
end in five zero bits:

| Value | What the chip does | Used by |
|---|---|---|
| `$00` | 5-bit then 17-bit polynomial | Sword's second phase, Lobber's second phase |
| `$40` | 5-bit then 4-bit polynomial | Unable to Join In, No Potions |
| `$60` | 5-bit polynomial only | Axe |
| `$80` | 17-bit polynomial only | Fireball, Sword, Arrow's second phase |
| `$A0` | No polynomial: a clean square wave | Effects chip test |
| `$C0` | 4-bit polynomial only | Arrow |
| `$E0` | No polynomial: a clean square wave | Lobber Throwing Rock |

[Chapter 3](03_three_sound_chips.md) explained what those polynomial counters
do: the divider's steady flipping is gated by a shift register running through a
long pseudo-random cycle, so a short cycle gives a rough buzz and a long one
gives hiss. Reading down that table is reading the character of each sound. The
axe is a 5-bit rasp. The fireball is broadband noise. The Lobber's rock starts
as a clean tone and turns into noise halfway through, which is why it sounds
like something being thrown and then landing.

## Choosing a winner, and the global filter

Only one of the logical channels on a physical voice can be heard, and it is the
one at the front of the list, which is the highest priority. That much was
settled in Chapter 7.

Two more things happen before the winner reaches the chip.

The first is the global threshold from [Chapter 6](06_taking_orders.md). One
byte of RAM holds a number that commands `$01` and `$02` set. Before a pair's
candidates are accepted, the engine compares the best priority in that pair
against the threshold. A winner that falls short has its control byte replaced
with zero, which is a volume of zero, which is silence. The frequency still goes
out. The sound is still running, still stepping its envelopes, still counting
down its timers. It just contributes nothing.

Command `$01` sets that threshold to 240, and nothing in the ROM has a priority
anywhere near 240, so the whole board goes quiet without a single sound being
stopped. Command `$02` sets it back to zero. Muting the machine costs one byte
and reuses the arbitration that was already there.

The second is the pair rule, and it needs the hardware explained first.

## The pair trick

A POKEY channel counts down from an 8-bit number. At the fast clock the ROM
selects, that gives 256 possible pitches spread over the audible range in a very
uneven way. Down at the bottom the steps between adjacent numbers are tiny; up
at the top a difference of one is a difference of several semitones. Eight bits
is not enough resolution to play a tune.

The chip has an answer built in. Two channels can be **joined** into one 16-bit
counter: the lower-numbered channel's frequency register becomes the low half,
the higher-numbered one becomes the high half, and the pair sounds as a single
voice through the higher channel. Two registers, 65,536 possible dividers, and a
pitch you can actually tune. Channels 1 and 2 can be joined this way, and so can
channels 3 and 4.

That is why the routine processes the four channels as two pairs. Within a pair
it compares the two candidate priorities, and the rule is:

```
if the higher-numbered channel's priority >= the lower-numbered channel's:
    select joined 16-bit mode for this pair
else:
    leave the pair as two independent 8-bit channels
```

Notice the direction of the comparison. A tie selects joined mode. Both channels
of a pair sitting at the same priority is exactly what happens when one sound
allocates both of them, which is exactly the case where it wants the 16-bit
resolution. Defaulting a tie the other way would have meant every sound that
wanted precision had to arrange for a priority difference it did not otherwise
need.

The comparison also decides which channel is heard. When the higher-numbered
channel wins, the engine sets the lower one's volume to zero, which is what
joined mode requires: that channel is now only a counter, and its own output
would be a second unwanted voice.

## Building AUDCTL

Joined mode is selected by bits in the POKEY's mode register, AUDCTL, and so is
the choice of clock, and so are the high-pass filters and the polynomial length.
One byte, eight independent switches, and four voices with opinions about it.

Four, but the opinions come from more than four places. The engine keeps one
pair of accumulators per voice, and every logical channel queued on that voice
contributes to them as the sweep walks the list — not just the winner. So a
sound that loses the arbitration and is never heard still gets a say in the mode
register. Since the channels sharing a voice are usually asking for the same
thing, that rarely matters, and in this ROM it never does.

The engine solves this with **mask accumulation**, a pattern worth learning once
because it turns up wherever independent parties have to agree on a shared set
of flags:

```
or_mask  = 0        # bits somebody wants ON
and_mask = 0xFF     # bits nobody has vetoed

for each logical channel:
    or_mask  |= channel's requested bits
    and_mask &= channel's permitted bits

audctl = or_mask & and_mask
```

Every channel contributes a request and a veto. The requests pile up, the vetoes
narrow the result, and one byte comes out the other end. The sequence language's
control-bits instruction from [Chapter 9](09_sequence_language_opcodes.md) adds
to the OR mask; its counterpart clears bits from the AND mask.

In practice this ROM barely stretches it. Every one of the seven POKEY effects
executes exactly one such instruction, with the same operand, requesting the
same single bit: `$20`, use the fast 1.79 MHz clock for channel 3. The effects
chip test executes none at all and leaves the masks at their reset values, so
nothing it plays contributes a bit of its own. Nothing in Gauntlet II ever vetoes
anything.

That single operand is worth a second look, because six of the seven effects do
not play on channel 3. "No Potions" runs on chip channel 2 and still asks for
channel 3's clock. Whoever wrote the sounds appears to have copied one setup
block into all seven and never varied the operand, which does no harm and does
nothing.

The bits that actually matter are not requested by anyone. The pair comparison
in the next section ORs in the joined-mode bit *and* the matching fast-clock bit
after the masks have been combined: `$28` for the upper pair, `$50` for the
lower one. So a sound gets both 16-bit precision and the 1.79 MHz clock by
asking for two adjacent channels, not by asking for a bit.

## Pitch: the divider table

Somewhere the engine has to turn a note number into a divider, and the ROM has a
table for it: sixteen-bit values indexed by note, starting at `$5A35`.

| Note | As a pitch | Divider | Resulting frequency |
|---:|---|---:|---:|
| 1 | C0 | 54,728 | 16.35 Hz |
| 13 | C1 | 27,360 | 32.70 Hz |
| 25 | C2 | 13,677 | 65.40 Hz |
| 37 | C3 | 6,835 | 130.79 Hz |
| 49 | C4, middle C | 3,414 | 261.59 Hz |
| 61 | C5 | 1,703 | 523.33 Hz |
| 73 | C6 | 848 | 1,046.65 Hz |
| 85 | C7 | 421 | 2,090.86 Hz |
| 97 | C8 | 207 | 4,181.71 Hz |

Read it as a countdown. The chip loads the stored number plus seven, counts it
down at 1.79 MHz, and flips its output every time it reaches zero. Two flips make
one cycle, so the pitch is the clock divided by twice the count. Bigger number,
lower pitch. The relationship is inverse, which is why the values halve every
twelve rows: an octave up is half the wait.

Entries 1 to 97 are a full chromatic scale, eight octaves, and they assume the
joined 16-bit mode from the previous section. Dividers of 54,728 do not fit in
eight bits. The table's consumer can index as far as note 127, but the entries
past 97 are not dividers at all: entry 97 ends at `$5AF8` and `$5AF9` is the
start of the YM2151's key-code table, so anything beyond that is one table read
through the other. Nothing in this ROM indexes that far.

The scale is also a nice illustration of where integer arithmetic starts to hurt.
Down at C0 the divider is five figures long and the rounding error is a
hundredth of a cent. Up at C7 the divider is 421, one step is worth about four
cents, and the best available value lands two cents flat. By the top of the table
the worst note is nearly four cents off. This is the detuning the POKEY is famous
for, and it is not a flaw in the chip so much as a consequence of choosing a
pitch by picking a whole number.

There is a catch, and Chapters 8 and 10 have already given it away. No sequence
in Gauntlet II plays a note on a POKEY channel. All eleven POKEY records use
rests, and their pitch comes entirely from frequency envelopes stepping the
divider directly. The table is complete, correct, and reachable by code that
nothing calls. Somebody built the POKEY side of this engine expecting to write
tunes on it.

## Nine writes and out

At the end of the sweep the routine has four frequency values, four control
values, and one AUDCTL byte. It writes them through the indirect pointer:

```
offset 4, 6   AUDF3, AUDF4          the upper pair's dividers
offset 5, 7   AUDC3, AUDC4          the upper pair's volume and distortion
offset 8      AUDCTL                the combined mode byte
offset 0, 2   AUDF1, AUDF2          the lower pair's dividers
offset 1, 3   AUDC1, AUDC2          the lower pair's volume and distortion
```

Nine stores. The upper pair is written first because it was arbitrated first,
AUDCTL goes out in the middle once both pairs have contributed their masks, and
the lower pair follows. The whole wrapper, including all nine writes, is under
190 cycles of a 1.79 MHz processor, and it happens 120 times a second whether or
not anything is playing.

The POKEY never says no. There is no busy flag, no handshake, no waiting. Write
the byte and it is done. [Chapter 12](12_driving_the_ym2151.md) is about a chip
that behaves very differently, and the difference shapes the code around it.

## What the POKEY is actually for

Eight commands reach this path in the entire game:

| Command | Sound | Physical channel | Distortion |
|---|---|---:|---|
| `$05` | Effects chip test | 0, 1, 2, 3 | `$A0` |
| `$43` | Unable to Join In | 0 | `$40` |
| `$44` | No Potions | 1 | `$40` |
| `$45` | Axe | 0 | `$60` |
| `$46` | Fireball | 1 | `$80` |
| `$47` | Sword | 2 | `$80`, then `$00` |
| `$48` | Arrow | 3 | `$C0`, then `$80` |
| `$49` | Lobber Throwing Rock | 3 | `$E0`, then `$00` |

Seven effects and one diagnostic, out of 62 sounds and 219 commands. Every one
of the seven is a single record on a single channel, and every one of them is
built the same way: set the fast clock, name a volume envelope, name a frequency
envelope, switch to POKEY mode, zero the base volume, choose a distortion, rest.
Six setup instructions and one or two rests, six or eight bytes of envelope, and
the sound makes itself.

"No Potions" is the shortest of them, and it is worth reading in full because
every number in it can be checked against the audio:

```
SET_CTRL_BITS $20      use the fast clock for channel 3
SET_VOL_ENV   $657B    volume curve: 2 sweeps of +44, then 18 of 0
SET_FREQ_ENV  $657F    pitch curve: 2 sweeps of +16, then 18 of 0
SWITCH_POKEY  $00      this channel drives the POKEY
SET_VOLUME    $00      start from silence
SET_DISTORTION $40     5-bit into 4-bit polynomial: a hard rasp
REST          $00 $0A  hold for 320 duration units
CHAIN                  end
```

The rest's duration works out to twenty sweeps at the default tempo, by the
POKEY rule from [Chapter 8](08_sequence_language_time.md): the control byte times
32, divided by the tempo. Both envelopes are two records that run for two sweeps
and then eighteen. Twenty and twenty. The sequence and the envelopes were written
to finish together, and the sound is a 167-millisecond burst of rasp that snaps
to full volume in two sweeps and stops dead.

> **Try it yourself**
>
> ```bash
> uv run gauntlet_disasm.py soundrom.bin --cmd 0x44 --csv hw_docs/soundcmds.csv
> uv run gauntlet_disasm.py soundrom.bin --sfx-wav 0x44 --csv hw_docs/soundcmds.csv
> ```
>
> The first prints the eight instructions above. The second reports `41 IRQ
> services` and `201 register writes`, which is the arithmetic of this chapter
> made visible: 41 interrupts give 21 POKEY ticks at nine writes each, plus the
> twelve the audio reset of [Chapter 5](05_waking_up.md) performs before anything
> starts playing. 21 × 9 + 12 = 201, exactly. The
> resulting `sfx_0x44.wav` is 1.171 seconds long, of which the sound occupies the
> first fifth and the rest is the tail the renderer adds. Measure the peak in each
> 8.3 ms window with the snippet from
> [Chapter 10](10_shaping_the_sound.md) and you get a flat-topped rectangle
> exactly twenty windows wide.
>
> Then do the same with `--sfx-wav 0x46`, the fireball. That one reports 741
> register writes over 161 services, and 81 × 9 + 12 comes to 741 again. Its
> peaks climb through eight distinct
> levels and back down, one per volume-envelope step, while the frequency envelope
> drags the divider under it.

## What you now know

- On every POKEY tick — every other IRQ — the engine walks four physical lists, runs the sequence
  engine down each one, and produces one candidate frequency, control byte, and
  pair of masks per channel.
- The highest-priority candidate on a channel wins, and a global threshold can
  silence the winner without stopping the sound.
- The four channels are arbitrated as two pairs, and when the higher-numbered
  channel of a pair wins or ties, the pair is joined into one 16-bit counter.
- AUDCTL is built by OR-ing every channel's requested bits together and then
  filtering the result through every channel's permitted bits.
- A table at `$5A35` converts note numbers to 16-bit dividers, chromatically from
  C0 to C8 across entries 1 to 97, with an inverse relationship that leaves the
  top of the range a few cents out. Entries past 97 overlap the key-code table
  and are not dividers. No sound in this ROM reaches any of it.
- Nine stores end the sweep: four dividers, four control bytes, and AUDCTL. The
  chip accepts all of them immediately.
- Eight commands use this whole path, and seven of them are one record with six
  setup instructions and a rest.

## Where this leads

[Chapter 12](12_driving_the_ym2151.md) takes the other branch of the same
dispatcher. Eight channels instead of four, a 42-byte instrument definition
instead of a three-bit distortion field, a chip that has to be asked before every single
write, and a volume control that is not a volume control.

## Going deeper

- [`docs/04_subsystems.md`](../docs/04_subsystems.md) — the POKEY pipeline, pair
  arbitration, mask combination, and cycle counts.
- [`docs/05_data_reference.md`](../docs/05_data_reference.md) — the note lookup
  view and the hardware dispatch tables.
- [`hw_docs/POKEY.md`](../hw_docs/POKEY.md) — the chip's registers, distortion
  settings, and AUDCTL bits.
- [`docs/generated/pokey_control_catalog.csv`](../docs/generated/pokey_control_catalog.csv)
  — every AUDCTL bit with its meaning and whether this ROM selects it.
- [`docs/generated/pitch_conversion_catalog.csv`](../docs/generated/pitch_conversion_catalog.csv)
  — the divider table's extent, tuning model, and reachability.
- [`docs/generated/physical_output_catalog.csv`](../docs/generated/physical_output_catalog.csv)
  — the routines on both output paths, block by block.
