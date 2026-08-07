# Appendix D — Reference Tables

The tables worth having open while reading. Each one says how to read it and
which chapter explains what it is for.

---

## D.1 The address space

The sound CPU's complete address space, in address order. The sparse I/O holes
are shown explicitly; the three sixteen-byte mailbox/mixer blocks are mirrors
because the hardware does not decode their low four address bits.
[Chapter 2](02_tour_of_the_sound_hardware.md).

| Range | Size | Contents |
|---|---:|---|
| `$0000`–`$00FF` | 256 B | Zero page: frame counter, error flags, pointers, speech state, coin filters |
| `$0100`–`$01FF` | 256 B | The 6502 stack |
| `$0200`–`$020F` | 16 B | Incoming command ring buffer |
| `$0210`–`$0211` | 2 B | The ring's read and write positions |
| `$0212`–`$0213` | 2 B | Boot indirect-write index and mode; `$0213` is `$FF` in normal operation ([Chapter 17](17_open_questions.md)) |
| `$0214`–`$0223` | 16 B | Outgoing reply buffer |
| `$0224`–`$0227` | 4 B | Reply-buffer state and positions |
| `$0228`–`$080F` | 1,512 B | The thirty parallel logical-channel arrays, ending with twelve physical list heads at `$0804`–`$080F` |
| `$0810`–`$082F` | 32 B | Physical-output scratch: candidates, masks, the YM level-transform chain, and the key event bits |
| `$0830`–`$0831` | 2 B | No documented consumer |
| `$0832`–`$083B` | 10 B | Speech queue and its positions |
| `$083C`–`$089F` | 100 B | YM2151 operator workspace |
| `$08A0`–`$093C` | 157 B | No documented consumer |
| `$093D`–`$0C54` | 792 B | The context-record pool: 198 four-byte records, of which the free list reaches 134 (see below) |
| `$0C55`–`$0FFF` | 939 B | Unused |
| `$1000`–`$100F` | 16 B | Writes mirror `$1000`: sound-to-main latch and main-CPU interrupt |
| `$1010`–`$101F` | 16 B | Reads mirror `$1010`: main-to-sound command latch |
| `$1020`–`$102F` | 16 B | Reads and writes mirror `$1020`: coin inputs on read, volume mixer on write |
| `$1030` | 1 B | Board status on read; YM2151 reset on write |
| `$1031` | 1 B | TMS5220 write strobe |
| `$1032` | 1 B | TMS5220 reset |
| `$1033` | 1 B | TMS5220 clock selection |
| `$1034`–`$1035` | 2 B | Right and left mechanical coin-counter outputs |
| `$1036`–`$17FF` | 1,994 B | Unmapped by the hardware |
| `$1800`–`$180F` | 16 B | POKEY |
| `$1810`–`$1811` | 2 B | YM2151 |
| `$1812`–`$181F` | 14 B | Unmapped by the hardware |
| `$1820` | 1 B | Speech data |
| `$1821`–`$182F` | 15 B | Unmapped by the hardware |
| `$1830` | 1 B | Interrupt acknowledge |
| `$1831`–`$1FFF` | 1,999 B | Unmapped by the hardware |
| `$2000`–`$3FFF` | 8 KB | Nothing wired up |
| `$4000`–`$FFFF` | 48 KB | ROM |

**The context pool is smaller than it looks.** Initialization walks `$093D`
writing each record's "next" field, and its loop bound stops after record 198.
The instruction that then writes the list's terminating zero is meant to step
back one record and mark the last one, which would leave 198 records with 197
allocatable. It adjusts its pointer by 260 bytes instead of 4, so the zero lands
on record 134. Records 135 to 198 keep valid links and nothing can ever reach
them: the free list walked from its head is 134 records long, of which 133 can
be allocated and the last is the sentinel. Executing the ROM's own initializer
confirms it. Nothing in Gauntlet II comes close to needing 133 simultaneous
contexts, so the shortfall has no audible consequence.

## D.2 The hardware window at `$1000`

Several of these addresses do unrelated things depending on the direction of the
access. [Chapter 2](02_tour_of_the_sound_hardware.md). For the set of *values* the sound
CPU sends back through `$1000`, see
[Appendix B, Replies to the main CPU](B_command_list.md#replies-to-the-main-cpu).

| Address | Read | Write |
|---|---|---|
| `$1000`–`$100F` | | Hand a byte to the main CPU and interrupt it. The low four address bits are not decoded, so the whole block is this one latch; the boot handshake's writes to `$1002`, `$1003`, `$100B`, `$100C` all land here ([Chapter 17](17_open_questions.md)) |
| `$1010` | The command byte the main CPU last sent | |
| `$1020` | The four coin switches, active low | Set all three volume levels |
| `$1030` | Board status, see below | Reset the YM2151 |
| `$1031` | | Strobe a byte into the speech chip |
| `$1032` | | Reset the speech chip |
| `$1033` | | Select the speech chip's clock divisor |
| `$1034` | | Pulse the right coin counter |
| `$1035` | | Pulse the left coin counter |
| `$1830` | | Acknowledge the interrupt |

Board status bits read at `$1030`:

| Bit | Reads as 1 when |
|---:|---|
| 7 | A command is waiting at `$1010` |
| 6 | The last reply has not been collected |
| 5 | The speech chip is *not* ready |
| 4 | The self-test switch is in its normal position |

## D.3 The mixer byte at `$1020`

One store sets three analog volume levels. Speech and music get eight steps each;
effects get four. [Chapter 2](02_tour_of_the_sound_hardware.md).

| Bit | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
|---|---|---|---|---|---|---|---|---|
| Field | speech | speech | speech | effects | effects | music | music | music |

## D.4 The error-flag byte at `$02`

The byte the main CPU reads back from command `$07`. The top five bits can be set
by failures during the boot diagnostics and stay latched once set.
[Chapter 5](05_waking_up.md).

| Bit | Set when |
|---:|---|
| 7 | ROM checksum failed for `$4000`–`$7FFF` |
| 6 | ROM checksum failed for `$8000`–`$BFFF` |
| 5 | ROM checksum failed for `$C000`–`$FFFF` |
| 4 | Walking-bit RAM failure in pages 2 through 7 |
| 3 | Walking-bit RAM failure in page 8 or above |
| 2 | Interrupt heartbeat: armed by command `$07`, cleared by the IRQ |
| 1 | The YM2151 stopped answering after 255 polls |
| 0 | Main-loop heartbeat: armed by command `$07`, cleared by the main loop |

The game program watches only the low three bits — the two heartbeats and the
YM2151-stuck flag. Its per-frame watchdog reboots the sound subsystem if any of them
is set, and ignores the five latched self-test bits above them
([Appendix B](B_command_list.md#how-the-game-rom-uses-them)).

## D.5 The ROM

File offset 0 is CPU address `$4000`, so subtract `$4000` from any address in this
book to find it in `soundrom.bin`.
[Chapter 2](02_tour_of_the_sound_hardware.md).

| Range | Contents |
|---|---|
| `$4000`–`$5C5E` | All the 6502 code: boot, interrupts, handlers, sequence engine, output paths. Several tables sit among it, listed below |
| `$5C5F`–`$5D0E` | Durations, fade rates, and the POKEY shape table |
| `$5D0F`–`$5F9F` | The three 219-byte command tables: validation, handler type, parameter |
| `$5FA0`–`$5FA7` | Four overlapping type-3 target-minus-one words; the final three, at `$5FA2`–`$5FA7`, are also the NMI direct-dispatch target table |
| `$5FA8`–`$63B1` | The six type-7 tables: start offsets, flags, priorities, channels, sequence pointers, next links |
| `$63B2`–`$6558` | The three 141-byte speech metadata tables: index, clock flag, priority |
| `$6559`–`$655E` | Two three-byte handler-match records, all zeros, read by the dormant handler types ([Chapter 17](17_open_questions.md)) |
| `$655F`–`$8380` | Sequences, envelopes, and the 55 YM2151 instrument records, interleaved, plus the 256-byte operator level-transform lookup at `$72DC`–`$73DB` |
| `$8381`–`$8446` | The board and coin-counter routine, and the NMI direct-query handlers |
| `$8447`–`$8448` | Two unreferenced bytes, `$94 $FF`, with no known consumer |
| `$8449`–`$873C` | 189 speech stream pointers and 189 lengths |
| `$873D`–`$FECC` | The speech corpus: 30,608 bytes, gapless |
| `$FECD`–`$FFF9` | 301 bytes with no consumer: one stray `$FF`, 296 zero bytes of padding, and four bytes at `$FFF6` reading `8C FF 00 00` ([Chapter 17](17_open_questions.md)) |
| `$FFFA`–`$FFFF` | The NMI, reset, and IRQ vectors |

The tables embedded in the code region, in address order:

| Range | What it is | Section |
|---|---|---|
| `$5790`–`$579F` | The sixteen-entry YM2151 volume curve | D.14 |
| `$57A0`–`$57A7` | The eight YM2151 carrier masks, one per algorithm | D.13 |
| `$5A35`–`$5AF8` | POKEY note dividers, entries 0 to 97 | D.10 |
| `$5AF9`–`$5B5A` | YM2151 key codes by note number | D.11 |
| `$5B5B`–`$5C5A` | 256-byte YM2151 operator total-level scaling transform | — |
| `$5C5B`–`$5C5E` | The four-entry level bias table the division field selects | — |

Note that the level-transform machinery of
[Chapter 12](12_driving_the_ym2151.md) uses **two** 256-byte lookups, and they
are nowhere near each other: `$5B5B`–`$5C5A` sits at the end of the code, and
`$72DC`–`$73DB` sits in the middle of the sequence data. The second is the one
[Chapter 16](16_how_this_was_figured_out.md) tells the story about.

Each 16 KB third of the image sums to exactly `$FF` modulo 256, which is the
self-test's ROM check.

## D.6 The clock tree

Every rate on the board comes from one 14.318181 MHz crystal.
[Chapter 4](04_heartbeat.md).

| Clock or event | Derivation | Rate |
|---|---|---:|
| Master | crystal | 14,318,181 Hz |
| 6502 | master / 8 | 1,789,772.625 Hz |
| POKEY | master / 8 | 1,789,772.625 Hz |
| YM2151 | master / 4 | 3,579,545.25 Hz |
| TMS5220, normal | master / 2 / 11 | 650,826.409 Hz |
| TMS5220, squeak | master / 2 / 9 | 795,454.5 Hz |
| Video frame | 456 × 262 at master / 2 | 59.9227476 Hz |
| IRQ | 4 per frame | 239.6909904 Hz |
| POKEY sweep | IRQ / 2 | 119.8454952 Hz |
| YM2151 sweep | IRQ / 2 | 119.8454952 Hz |
| **The tick** | one sweep interval | **8.344077 ms** |
| Speech service attempts | IRQ × 4 | up to 958.7639614 Hz |

About 7,467 processor cycles fit into one interrupt interval.

## D.7 The duration table

Sixteen 16-bit values at `$5C5F`, indexed by the low nibble of a note's control
byte. Every entry is an exact fraction of the whole note's 7,680 units. The
"Sweeps" column is the length at the tempo of 16 a channel starts with; a faster
tempo divides it. [Chapter 8](08_sequence_language_time.md).

| Index | Value | Sweeps at tempo 16 | Note length | Times used |
|---:|---:|---:|---|---:|
| 0 | 0 | 0 | No time at all | 0 |
| 1 | 7,680 | 480 | Whole | 33 |
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

The note's control byte carries three more fields alongside that index:

| Bit | 7 | 6 | 5 | 4 | 3 | 2 | 1 | 0 |
|---|---|---|---|---|---|---|---|---|
| Field | sustain | dotted | division | division | duration | duration | duration | duration |

A POKEY channel ignores all of this and takes the low seven bits of the control
byte times 32. Which rule applies is decided at `$4844`, which tests two bits of
the channel's status byte before any table is read; `SWITCH_POKEY` clears both,
and every POKEY record executes it before its first event.

## D.8 The POKEY volume-shape table

Eight rows of sixteen signed bytes at `$5C8F`. One entry per sweep is added to
the channel's volume accumulator, holding on the last entry. The row and the
position within it share one byte per channel, at `$03AE`.

That byte is written on both arms of the duration branch at `$4844`. The
duration-table arm derives the row from control bits 3–5; the POKEY arm stores
zero. Only the POKEY volume path ever reads it, so every POKEY sound in this ROM
selects row 0 and the other seven rows are dormant.
[Chapter 10](10_shaping_the_sound.md).

| Row | Address | The sixteen steps | Shape |
|---:|---|---|---|
| 0 | `$5C8F` | 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 | Neutral |
| 1 | `$5C9F` | 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 | Neutral |
| 2 | `$5CAF` | 0 0 0 0 0 0 −64 −128 −128 −128 −128 −128 −128 −128 −128 −128 | Delayed cut |
| 3 | `$5CBF` | 0 0 0 −64 −128 −128 −128 −128 −128 −128 −128 −128 −128 −128 −128 −128 | Earlier cut |
| 4 | `$5CCF` | 32 32 32 32 32 32 31 29 26 22 18 12 6 3 1 0 | Slow decay |
| 5 | `$5CDF` | 32 32 32 29 22 12 4 1 0 0 0 0 0 0 0 0 | Fast decay |
| 6 | `$5CEF` | 64 64 64 64 64 64 63 59 53 45 36 24 12 4 1 0 | Slow decay, stronger |
| 7 | `$5CFF` | 64 64 64 59 45 24 4 0 0 0 0 0 0 0 0 0 | Fast decay, stronger |

## D.9 The fade-rate table

Sixteen bytes at `$5C7F`, selected by a fade's rate index. The byte says how far
to shift the signed ramp amount right before applying it, which is the same as
dividing it. Several indices give the same divisor.
[Chapter 10](10_shaping_the_sound.md).

| Index | Address | Byte | Divides the ramp by |
|---:|---|---|---|
| 0 | `$5C7F` | `$00` | 256 |
| 1 | `$5C80` | `$FF` | Special: count down and stop |
| 2 | `$5C81` | `$80` | 2 |
| 3 | `$5C82` | `$40` | 4 |
| 4 | `$5C83` | `$20` | 8 |
| 5 | `$5C84` | `$40` | 4 |
| 6 | `$5C85` | `$20` | 8 |
| 7 | `$5C86` | `$10` | 16 |
| 8 | `$5C87` | `$40` | 4 |
| 9 | `$5C88` | `$10` | 16 |
| 10 | `$5C89` | `$08` | 32 |
| 11 | `$5C8A` | `$04` | 64 |
| 12 | `$5C8B` | `$02` | 128 |
| 13 | `$5C8C` | `$08` | 32 |
| 14 | `$5C8D` | `$04` | 64 |
| 15 | `$5C8E` | `$20` | 8 |

## D.10 The POKEY note-divider table

A table of sixteen-bit values beginning at `$5A35`, indexed by note number. The
consumer can reach 128 entries, but only entries 0 to 97 physically belong to it:
entry 97 ends at `$5AF8`, and `$5AF9` is where the key-code table of D.11 begins.
Entries 98 to 127 read bytes belonging to that table and to the total-level
scaling table beyond it, so their values are an artifact of the overlap rather
than dividers. Nothing in this ROM indexes that far — the highest note the
sequences use is 95 — and the semantics of the tail are not established.

Entries 1 to 97 form a chromatic scale of eight octaves. The chip loads the value
plus seven and counts it down at the POKEY clock of 1,789,772.625 Hz, flipping
its output at each underflow, so the pitch is the clock divided by twice the
loaded count. Bigger numbers give lower pitches, and the values halve every
twelve entries. The whole table assumes the joined 16-bit mode. No sequence in
this ROM reaches it. [Chapter 11](11_driving_the_pokey.md).

The dividers were chosen against a nominal 1.790 MHz clock, so on real hardware
every note sits a systematic 0.22 cents flat of the value its author intended.
The frequencies below are what the board actually produces.

One full octave, and then every C:

| Note | Pitch | Divider | Resulting frequency | Error |
|---:|---|---:|---:|---:|
| 49 | C4 | 3,414 | 261.59 Hz | −0.26 cents |
| 50 | C♯4 | 3,222 | 277.14 Hz | −0.26 cents |
| 51 | D4 | 3,041 | 293.60 Hz | −0.39 cents |
| 52 | D♯4 | 2,870 | 311.05 Hz | −0.44 cents |
| 53 | E4 | 2,708 | 329.61 Hz | −0.10 cents |
| 54 | F4 | 2,556 | 349.16 Hz | −0.36 cents |
| 55 | F♯4 | 2,412 | 369.94 Hz | −0.25 cents |
| 56 | G4 | 2,276 | 391.98 Hz | −0.08 cents |
| 57 | G♯4 | 2,148 | 415.26 Hz | −0.18 cents |
| 58 | A4 | 2,027 | 439.96 Hz | −0.14 cents |
| 59 | A♯4 | 1,913 | 466.09 Hz | −0.29 cents |
| 60 | B4 | 1,805 | 493.87 Hz | −0.06 cents |

| Note | Pitch | Divider | Resulting frequency |
|---:|---|---:|---:|
| 1 | C0 | 54,728 | 16.35 Hz |
| 13 | C1 | 27,360 | 32.70 Hz |
| 25 | C2 | 13,677 | 65.40 Hz |
| 37 | C3 | 6,835 | 130.79 Hz |
| 49 | C4 | 3,414 | 261.59 Hz |
| 61 | C5 | 1,703 | 523.33 Hz |
| 73 | C6 | 848 | 1,046.65 Hz |
| 85 | C7 | 421 | 2,090.86 Hz |
| 97 | C8 | 207 | 4,181.71 Hz |

Across notes 1 to 97 the error runs from 3.9 cents flat at note 96 to 2.2 cents
sharp at note 93, and it is worst at the top where one step of the divider is
worth several cents.

## D.11 The YM2151 key-code consumer view

The code can index a 128-entry view beginning at `$5AF9`, but only its first 98
bytes, `$5AF9`–`$5B5A`, physically belong to the key-code table. A key code is
three bits of octave in the high nibble and a semitone slot in the low nibble,
with every fourth slot skipped because the chip's own frequency tables are
organized in groups of three. The block boundary falls between B and C, so C4
is the last entry of octave 3.

Consumer indices 98 to 127 continue through `$5B5B`–`$5B78`, aliasing the first
thirty bytes of the following total-level scaling table. Configured sequences
only use notes 13 to 95, so they never reach the aliased tail.
[Chapter 12](12_driving_the_ym2151.md).

| Note | Pitch | Key code | Octave field | Semitone field |
|---:|---|---:|---:|---:|
| 49 | C4 | `$3E` | 3 | 14 |
| 50 | C♯4 | `$40` | 4 | 0 |
| 51 | D4 | `$41` | 4 | 1 |
| 52 | D♯4 | `$42` | 4 | 2 |
| 53 | E4 | `$44` | 4 | 4 |
| 54 | F4 | `$45` | 4 | 5 |
| 55 | F♯4 | `$46` | 4 | 6 |
| 56 | G4 | `$48` | 4 | 8 |
| 57 | G♯4 | `$49` | 4 | 9 |
| 58 | A4 | `$4A` | 4 | 10 |
| 59 | A♯4 | `$4C` | 4 | 12 |
| 60 | B4 | `$4D` | 4 | 13 |
| 61 | C5 | `$4E` | 4 | 14 |

Slots 3, 7, 11 and 15 never appear. A six-bit key fraction in a second register
divides one semitone into sixty-four steps for fine tuning.

**The MIDI convention.** ROM note numbers sit eleven below MIDI's, so
`MIDI = ROM note + 11`. ROM note 49 is MIDI 60, middle C. The ROM's sequences use
64 distinct note values between 13 and 95.

## D.12 The 42-byte YM2151 instrument record

Fifty-five of these sit end to end from `$69D6`. The first 28 bytes are copied
into chip registers by the instrument-load instruction. The rest is bookkeeping
the ROM keeps for itself. [Chapter 12](12_driving_the_ym2151.md).

| Offset | Field | Register | What it sets |
|---:|---|---|---|
| `$00` | FB/CON | `$20`+ch | Feedback amount and which of the eight algorithms wires the operators |
| `$01` | KC base | `$28`+ch | A fixed key-code offset. Zero in every record |
| `$02` | KF base | `$30`+ch | A fixed key-fraction offset. Zero in every record |
| `$03` | PMS/AMS | `$38`+ch | How much the low-frequency oscillator affects pitch and amplitude |
| `$04` | M1 DT1/MUL | `$40`+ch | Detune and frequency multiple |
| `$05` | M1 TL | `$60`+ch | Total level: this operator's attenuation |
| `$06` | M1 KS/AR | `$80`+ch | Key scaling and attack rate |
| `$07` | M1 AMSEN/D1R | `$A0`+ch | Amplitude-modulation enable and first decay rate |
| `$08` | M1 DT2/D2R | `$C0`+ch | Second detune and second decay rate |
| `$09` | M1 D1L/RR | `$E0`+ch | Sustain level and release rate |
| `$0A`–`$0F` | M2 | +8 | The same six fields for operator M2 |
| `$10`–`$15` | C1 | +16 | The same six fields for operator C1 |
| `$16`–`$1B` | C2 | +24 | The same six fields for operator C2 |
| `$1C` | — | | Skipped by every consumer. Takes only the values `$00` and `$80`. Purpose unknown ([Chapter 17](17_open_questions.md)) |
| `$1D` | M1 transform | | Level-correction descriptor: two nibbles indexing two 256-byte lookup tables |
| `$1E` | M1 → M2 chain | | M1's correction source and M2's index seed |
| `$1F` | M2 transform | | As `$1D`, for M2 |
| `$20` | M2 → C1 chain | | M2's correction source and C1's index seed |
| `$21` | C1 transform | | As `$1D`, for C1 |
| `$22` | C1 → C2 chain | | C1's correction source and C2's index seed |
| `$23` | C2 transform | | As `$1D`, for C2. The channel's live volume supplies C2's correction |
| `$24` | Auxiliary | `$18` | LFO frequency, loaded by the auxiliary-block instruction |
| `$25` | Auxiliary | `$19` | One of the chip's two LFO depth values |
| `$26` | Auxiliary | `$19` | The other LFO depth value |
| `$27` | Auxiliary | `$1B` | LFO waveform |
| `$28` | Auxiliary | | Shadow byte kept in RAM after the auxiliary write |
| `$29` | Auxiliary | `$0F` | Noise enable and frequency, loaded by its own instruction |

Offsets `$00` to `$1B` are the 28 bytes that go to the chip. Offsets `$1D` to
`$23` run the level-transform chain. Offsets `$24` to `$29` are only touched when
a sequence executes one of the two auxiliary-load instructions.

## D.13 The YM2151 carrier masks

Eight bytes at `$57A0`, one per algorithm, naming the operators a volume change
should attenuate. Attenuating anything else changes the timbre instead of the
loudness. [Chapter 12](12_driving_the_ym2151.md).

| Algorithm | Carriers | Instruments using it |
|---:|---|---:|
| 0 | C2 | 3 |
| 1 | C2 | 4 |
| 2 | C2 | 3 |
| 3 | C2 | 7 |
| 4 | C1, C2 | 11 |
| 5 | M2, C1, C2 | 4 |
| 6 | M2, C1, C2 | 2 |
| 7 | M1, M2, C1, C2 | 5 |

## D.14 The YM2151 volume curve

Sixteen signed bytes at `$5790`, indexed by the low nibble of a volume
instruction's operand and applied as a carrier attenuation. Entries `$0F` down to
`$06` step by exactly 2; below that the steps widen, and `$00` drops 28 units in
one go. One step of total level is about 0.75 dB.
[Chapter 12](12_driving_the_ym2151.md).

| Operand | Byte | Curve value | Added to carrier level | Roughly |
|---:|---|---:|---:|---|
| `$0F` | `$00` | 0 | 0 | Full |
| `$0E` | `$FE` | −2 | +2 | 1.5 dB down |
| `$0D` | `$FC` | −4 | +4 | 3 dB down |
| `$0C` | `$FA` | −6 | +6 | 4.5 dB down |
| `$0B` | `$F8` | −8 | +8 | 6 dB down |
| `$0A` | `$F6` | −10 | +10 | 7.5 dB down |
| `$09` | `$F4` | −12 | +12 | 9 dB down |
| `$08` | `$F2` | −14 | +14 | 10.5 dB down |
| `$07` | `$F0` | −16 | +16 | 12 dB down |
| `$06` | `$EE` | −18 | +18 | 13.5 dB down |
| `$05` | `$EB` | −21 | +21 | 16 dB down |
| `$04` | `$E9` | −23 | +23 | 17 dB down |
| `$03` | `$E6` | −26 | +26 | 19.5 dB down |
| `$02` | `$E1` | −31 | +31 | 23 dB down |
| `$01` | `$DC` | −36 | +36 | 27 dB down |
| `$00` | `$C0` | −64 | +64 | 48 dB down |

## D.15 Type-7 priorities

Every record carries one, and the highest value wins the voice. The
value belongs to the record rather than to the command, so a multi-record sound
can occupy more than one row. All 182 records, by priority:
[Chapter 7](07_command_to_channel.md).

| Priority | Records | Commands | Sounds |
|---:|---:|---:|---|
| 63 | 8 | 4 | `$22`–`$25`, the four coin slots |
| 61 | 8 | 1 | `$3B`, the Gauntlet II theme |
| 51 | 2 | 2 | `$43` "Unable to Join In", `$44` "No Potions" |
| 32 | 8 | 4 | `$14`–`$17`, the four player deaths |
| 31 | 5 | 1 | `$42`, level-opening music |
| 30 | 8 | 4 | `$18`–`$1B`, the four player heartbeats |
| 20 | 2 | 1 | `$20` "Death Touches Player" |
| 15 | 8 | 4 | `$09`–`$0C`, two parts each of the four "Joins In" sounds |
| 14 | 5 | 3 | `$09` (1 part), `$0A` (2), `$0B` (2) |
| 13 | 4 | 1 | `$0B` "Wizard Joins In", its remaining four parts |
| 10 | 8 | 2 | `$29` "Thief Warning" (7 parts), `$2D` "Mugger Warning" (1) |
| 9 | 2 | 2 | `$38` "End of Slow Motion", `$3A` "Player Shoots Dragon" |
| 8 | 37 | 15 | Most one-shot effects, plus both chip tests `$04` and `$05` |
| 7 | 3 | 3 | `$28` and `$29`, one trailing part each; `$33` "Medium Tone Stun Tile" |
| 6 | 1 | 1 | `$27` "Trap / Walls Turn to Exits", one trailing part |
| 3 | 10 | 5 | `$0E`–`$11`, the four player exits; `$1C` "Message Appears on Screen" |
| 2 | 63 | 16 | Treasure-room music, food, keys, doors, monster hits, and `$45`–`$49` |

Six commands span more than one priority: `$09`, `$0A`, `$0B`, `$27`, `$28`, and
`$29`. Every other sound gives all of its records the same value.

Speech priorities are separate: 134 phrases at 0, one at 4, and the Dungeon
Master's six time-pressure lines at 64.

## Where this comes from

- [`docs/02_memory_map.md`](../docs/02_memory_map.md) — every RAM address and
  array base.
- [`docs/03_rom_structure.md`](../docs/03_rom_structure.md) — the region map with
  its confidence levels.
- [`docs/01_hardware.md`](../docs/01_hardware.md) — the register map and the clock
  tree.
- [`docs/05_data_reference.md`](../docs/05_data_reference.md) — the canonical
  catalog of every table in the ROM, with exact extents and consumers.
- [`docs/generated/timing_clock_catalog.csv`](../docs/generated/timing_clock_catalog.csv),
  [`fade_rate_catalog.csv`](../docs/generated/fade_rate_catalog.csv),
  [`volume_shape_catalog.csv`](../docs/generated/volume_shape_catalog.csv),
  [`pitch_conversion_catalog.csv`](../docs/generated/pitch_conversion_catalog.csv),
  [`ym_voice_field_catalog.csv`](../docs/generated/ym_voice_field_catalog.csv) —
  the row-level data behind these tables.
