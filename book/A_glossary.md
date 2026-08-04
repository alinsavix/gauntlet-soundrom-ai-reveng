# Appendix A — Glossary

Every term this book gives a specific meaning to, alphabetically, with the
chapter that introduces it. General computing vocabulary is included alongside
the Gauntlet-specific words, because the audience for this book is not assumed to
have met interrupts or fixed-point arithmetic before.

---

**6502.** The eight-bit processor on the sound board. It has one accumulator, two
index registers, a 256-byte stack at a fixed address, and no multiply
instruction. [Chapter 1](01_two_computers.md).

**68010.** The sixteen-bit Motorola processor that runs the game itself. This book
calls it the **main CPU** and never discusses its program.
[Chapter 1](01_two_computers.md).

**Active low.** A hardware signal whose meaningful state is a zero bit rather than
a one. The self-test switch and the speech chip's ready line are both active low,
so the interesting condition is the bit being clear.
[Chapter 2](02_tour_of_the_board.md).

**Algorithm.** On the YM2151, one of eight fixed wiring patterns connecting the
four operators of a channel. The algorithm decides which operators modulate which
and which ones reach the output. [Chapter 3](03_three_sound_chips.md).

**Attack, decay, sustain, release.** The four phases of an FM operator's own
volume envelope, built into the chip and configured by four bytes of the
instrument record. Not to be confused with the software envelopes of
[Chapter 10](10_shaping_the_sound.md). [Chapter 3](03_three_sound_chips.md).

**AUDC.** A POKEY control register, one per channel. The low four bits are volume
and the top three bits select the distortion.
[Chapter 3](03_three_sound_chips.md).

**AUDCTL.** The POKEY's single mode register. It selects clock speeds, joins
channels into pairs, enables high-pass filters, and chooses the polynomial length.
[Chapter 11](11_driving_the_pokey.md).

**AUDF.** A POKEY frequency register, one per channel. It holds the divider the
chip counts down from, so a larger value gives a lower pitch.
[Chapter 3](03_three_sound_chips.md).

**Carrier.** An FM operator whose output leaves the chip and is heard. Attenuating
a carrier makes the channel quieter. Which of the four operators are carriers
depends on the algorithm. [Chapter 12](12_driving_the_ym2151.md).

**Cent.** One hundredth of a semitone, used in this book to measure how far a
chip's actual pitch falls from equal temperament.
[Chapter 11](11_driving_the_pokey.md).

**Chain.** The linked run of records that makes up one sound. A chain is between
one and eight records long, and each record becomes one voice.
[Chapter 7](07_command_to_channel.md).

**Chip test.** One of the three diagnostic sounds a technician can trigger from
the self-test screen: command `$04` for the YM2151, `$05` for the POKEY, and `$08`
for the speech chip. [Chapter 14](14_chip_tests.md).

**Command.** One of the 219 byte values the main CPU can send to the sound board.
A command names a sound, a phrase, or a control action, and carries no other
information. [Chapter 1](01_two_computers.md).

**Distortion.** The POKEY's timbre control, held in the top three bits of AUDC. It
selects which combination of shift-register polynomial counters gates the
channel's output, producing buzzes and noise rather than clean tones.
[Chapter 3](03_three_sound_chips.md).

**Division field.** Bits 5 and 4 of a note's control byte. On a YM2151 channel it
does two jobs: a value of 1 halves the note's sounding length, and the field also
indexes a four-entry table of level biases.
[Chapter 8](08_sequence_language_time.md).

**Dotted.** Bit 6 of a note's control byte, which adds half the note's duration
again, exactly as a dot does in written music.
[Chapter 8](08_sequence_language_time.md).

**Duration table.** Sixteen 16-bit values in ROM, indexed by the low nibble of a
note's control byte, giving note lengths from a whole note down to a
hundred-twenty-eighth. [Chapter 8](08_sequence_language_time.md) and
[Appendix D](D_reference_tables.md).

**Envelope.** A stored curve that changes volume or pitch over time, applied one
step per sweep. Volume envelope records are two bytes; frequency envelope records
are three. [Chapter 10](10_shaping_the_sound.md).

**Equal temperament.** The standard tuning system in which an octave is divided
into twelve equally spaced semitones. Used here as the reference the two chips'
pitches are measured against. [Chapter 11](11_driving_the_pokey.md).

**Fade.** A request to move a channel's volume by a total amount at a given rate,
implemented with fixed-point arithmetic so it can move less than one step per
sweep. [Chapter 10](10_shaping_the_sound.md).

**Fixed-point.** Representing a fractional number as an integer with an implied
binary point. The fade machinery keeps whole volume steps in one byte and
two-hundred-and-fifty-sixths of a step in another.
[Chapter 10](10_shaping_the_sound.md).

**FM synthesis.** Frequency modulation synthesis, in which one oscillator wobbles
another's pitch fast enough that the result is heard as a change of timbre.
[Chapter 3](03_three_sound_chips.md).

**Frame.** One 25-millisecond unit of encoded speech, holding a source type, an
amplitude, a pitch, and up to ten filter coefficients. Frames are variable-length
in bits. [Chapter 3](03_three_sound_chips.md).

**Free list.** A way of managing a pool of identical records in which every unused
record points at the next unused one, so taking and returning a record are each a
couple of instructions with no searching.
[Chapter 5](05_waking_up.md).

**Handler type.** Which of the fifteen kinds of job a command is, read from a
219-byte table. Nine of the fifteen are used.
[Chapter 6](06_taking_orders.md).

**Hexadecimal.** Base sixteen, written in this book with a leading dollar sign in
the convention of 6502 assembly language. `$3B` means the same as `0x3B`.
[Chapter 1](01_two_computers.md).

**Instrument.** See **voice**.

**Interrupt.** A hardware signal that makes the CPU stop what it is doing, run a
fixed routine, and then resume exactly where it was, with no register or flag
disturbed. [Chapter 4](04_heartbeat.md).

**IRQ.** The sound board's regular interrupt, derived from the video circuitry and
arriving about 240 times a second. It can be held off temporarily by a processor
flag. [Chapter 4](04_heartbeat.md).

**Joined mode.** A POKEY arrangement in which two adjacent channels form one
16-bit counter, giving far finer pitch resolution than eight bits allow.
[Chapter 11](11_driving_the_pokey.md).

**Jump table.** An array of addresses indexed by a number, so that a value selects
which routine runs. This ROM has one for handler types and one for sequence
opcodes, and reaches both with the same stack trick.
[Chapter 6](06_taking_orders.md) and
[Chapter 9](09_sequence_language_opcodes.md).

**Key code.** The YM2151's pitch register: three bits of octave plus four bits of
semitone, with four codes per octave unused.
[Chapter 12](12_driving_the_ym2151.md).

**Key fraction.** The YM2151's fine-tuning register, six bits dividing one
semitone into sixty-four parts. [Chapter 12](12_driving_the_ym2151.md).

**Key on, key off.** Striking and releasing a YM2151 note. Striking restarts every
operator's envelope; releasing lets them run down.
[Chapter 12](12_driving_the_ym2151.md).

**Logical channel.** One of thirty sounds-in-progress tracked in RAM. Logical
channels compete for twelve physical ones.
[Chapter 7](07_command_to_channel.md).

<!-- TODO: Define this as an in-progress voice or type-7 record instance, not a
     whole sound. One sound may occupy several logical channels. -->

**LPC.** Linear predictive coding, the speech compression scheme the TMS5220 uses.
Instead of a waveform it stores a frame-by-frame description of a vocal tract.
[Chapter 3](03_three_sound_chips.md).

**Main CPU.** The 68010 running the game. [Chapter 1](01_two_computers.md).

**Mask accumulation.** Combining independent requests for a shared set of flag
bits by OR-ing everyone's requests together and then AND-ing the result with
everyone's permissions. [Chapter 11](11_driving_the_pokey.md).

**Memory-mapped I/O.** Wiring a chip so that certain addresses select its
registers, which makes controlling hardware indistinguishable from reading and
writing memory. [Chapter 2](02_tour_of_the_board.md).

**MIDI offset.** The relationship between this ROM's note numbering and MIDI's:
MIDI note = ROM note + 11, so ROM note 49 is middle C.
[Chapter 8](08_sequence_language_time.md).

**Modulator.** An FM operator whose output feeds another operator's input rather
than the chip's output. Attenuating a modulator changes timbre.
[Chapter 3](03_three_sound_chips.md).

**NMI.** The non-maskable interrupt, raised on the sound board whenever the main
CPU writes a command. It cannot be deferred, so its handler must be safe to run at
any instruction boundary. [Chapter 4](04_heartbeat.md).

**Opcode.** One instruction of the sequence language, a byte in the range `$80` to
`$BA`. There are 59, of which 26 are used.
[Chapter 9](09_sequence_language_opcodes.md) and
[Appendix C](C_opcode_reference.md).

**Operator.** One of the four sine oscillators in a YM2151 channel, each with its
own envelope, frequency multiple, and total level.
[Chapter 3](03_three_sound_chips.md).

**Parameter.** The second byte a command resolves to, read from a table parallel
to the handler-type table. Its meaning depends entirely on the handler type.
[Chapter 6](06_taking_orders.md).

**Phase accumulator.** A timing technique in which the leftover from one interval
is carried into the next rather than discarded, so a long run of intervals holds
an exact average even when no single interval is exact.
[Chapter 8](08_sequence_language_time.md).

**Phrase.** One recorded speech utterance. The ROM holds 141 of them.
[Chapter 13](13_speaking.md).

**Physical channel.** One of the twelve real chip voices: four on the POKEY,
numbered 0 to 3, and eight on the YM2151, numbered 4 to 11.
[Chapter 7](07_command_to_channel.md).

**POKEY.** Atari's four-channel sound chip, which makes tones by counting a clock
down and flipping an output. It also supplies the board's hardware random number
generator. [Chapter 3](03_three_sound_chips.md).

**Polynomial counter.** A shift register cycling through a long pseudo-random
sequence. The POKEY gates its output through these to produce distortion and
noise. [Chapter 3](03_three_sound_chips.md).

**Priority.** The number every sound carries, from 2 to 63 for type-7 sounds, used
to decide which sound is heard when several want the same voice and which speech
phrase outranks which. [Chapter 7](07_command_to_channel.md).

**Record.** One row of the type-7 sound description tables, carrying a priority, a
physical channel, a sequence pointer, and a link to the next record. The ROM has
182. [Chapter 7](07_command_to_channel.md).

**Reset vector.** The two bytes at the very top of the address space that tell a
6502 where to start executing at power-on. The ROM also holds vectors for IRQ and
NMI. [Chapter 5](05_waking_up.md).

**Ring buffer.** A fixed array plus a read position and a write position that wrap
around, letting a producer and a consumer run at different speeds without either
waiting. [Chapter 6](06_taking_orders.md).

**Self-test.** The diagnostic mode entered by holding a switch inside the coin
door at power-on. It runs a full RAM test and three ROM checksums before booting.
[Chapter 5](05_waking_up.md).

**Sequence.** The bytecode "sheet music" a record points at: a stream of notes,
rests, and opcodes interpreted one instruction at a time by a routine inside the
interrupt. [Chapter 8](08_sequence_language_time.md).

**Shape table.** Eight rows of sixteen signed values in ROM, added to a POKEY
channel's volume accumulator one step per sweep. The note path zeroes the row
index, so every POKEY sound in this ROM selects the row that is all zeros.
[Chapter 10](10_shaping_the_sound.md).

**Speak External.** The TMS5220 command, byte `$60`, that tells the chip to expect
a stream of LPC data from the CPU rather than to look up a word in its own
vocabulary ROM. [Chapter 13](13_speaking.md).

**Squeak.** The board's name for the faster speech clock divisor, selected by a
flag bit on 27 of the 141 phrases, which raises their pitch and speeds them up by
about a fifth. [Chapter 13](13_speaking.md).

**Sustain.** Bit 7 of a note's control byte. It loads the articulation timer with
a value so large it never expires, so the note is left sounding until something
else stops it. [Chapter 8](08_sequence_language_time.md).

**Sweep.** One pass in which the interrupt updates every voice of one chip. The
POKEY and the YM2151 get alternate interrupts, so each is swept about 120 times a
second. [Chapter 4](04_heartbeat.md).

**Tick.** One sweep interval, 8.344 ms. Nothing in any sound can start, stop, or
change at any moment other than a tick boundary.
[Chapter 4](04_heartbeat.md).

<!-- TODO: Scope the timing restriction to sequence-driven POKEY/YM control
     changes. Speech service and autonomous chip output are not limited to one
     event per 8.344-ms tick. -->

**TMS5220.** The Texas Instruments speech chip, which reconstructs speech from an
LPC description of a vocal tract at 8,000 samples a second.
[Chapter 3](03_three_sound_chips.md).

**Total level.** An FM operator's own attenuation, from 0 for loudest to 127 for
silent, covering about 96 decibels.
[Chapter 12](12_driving_the_ym2151.md).

**Transpose.** A per-channel constant added to every note's pitch before the
chip-specific conversion. [Chapter 9](09_sequence_language_opcodes.md).

**Type 7.** The handler type that plays a sound, covering all 62 sound effects and
pieces of music. [Chapters 7](07_command_to_channel.md) to
[12](12_driving_the_ym2151.md).

**Type 11.** The handler type that speaks a phrase, covering 141 commands.
[Chapter 13](13_speaking.md).

**Voice.** A 42-byte YM2151 patch definition. Twenty-eight of its bytes are copied
straight into chip registers and the rest is bookkeeping the ROM keeps for itself.
The ROM holds 55, of which 40 are ever reached. Also called an **instrument** in
this book. [Chapter 12](12_driving_the_ym2151.md).

<!-- TODO: "Voice" is also used throughout the chapters for a physical chip
     channel and for one part of a multi-record sound. Split these senses or
     reserve "instrument" for the 42-byte patch definition. -->

**Walking-bit test.** A RAM test that writes a value with exactly one bit set,
reads it back, then repeats with the bit rotated and with everything inverted. It
catches stuck bits and shorted data lines that a simple write-and-read-back
misses. [Chapter 5](05_waking_up.md).

**Watchdog.** A mechanism for noticing that something has stopped running. This
board has two: two bits of the error-flag byte that the main loop and the
interrupt each clear, and a counter that resets the speech chip if its ready line
stays stuck. [Chapter 5](05_waking_up.md) and
[Chapter 13](13_speaking.md).

**YM2151.** Yamaha's eight-channel FM synthesis chip, which carries almost all of
Gauntlet II's sound. [Chapter 3](03_three_sound_chips.md).

**Zero page.** The first 256 bytes of a 6502's address space. Instructions that
address them are one byte shorter and one cycle faster, so they serve as the
processor's extended register set. [Chapter 2](02_tour_of_the_board.md).
