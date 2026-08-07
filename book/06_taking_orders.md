# Chapter 6 — Taking Orders: Commands from the Main CPU

*Before this chapter: [Chapters 1](01_two_computers.md) to
[5](05_waking_up.md).*

The game program's entire contribution to the food blip is one store
instruction. It writes `$0D` to a hardware address and carries on moving
monsters. Somewhere in the next few microseconds the sound board has to notice
the byte, work out that it names a sound rather than a question, and get it into
a queue, all without disturbing the note it is already in the middle of playing.
This chapter follows one byte from the moment it lands to the moment the right
routine picks it up.

## How a command arrives

The main CPU writes to a single address. The sound board's hardware does two
things with that write, at the same instant: it captures the byte in a latch that
the sound CPU can read at `$1010`, and it pulls the sound CPU's NMI line.

That pairing is the whole protocol on the sound-board side. The byte is already
safe in the latch before the sound CPU has even begun to react, so there is no
window in which the signal arrives and the data has not. There is no length to
agree on and ordinary sound commands receive no individual acknowledgement.

There is still flow control on the other side of the latch. The main CPU checks
the mailbox's full flag before writing. Its nonblocking sender reports
accepted-or-busy; gameplay code queues a busy command and retries it on later
frames, while a blocking helper simply keeps trying. “One-byte protocol”
describes what crosses the hardware boundary, not an unguarded store-and-forget
policy in the game program.

The word non-maskable from [Chapter 4](04_heartbeat.md) matters here. The sound
CPU cannot defer an NMI, so the handler can begin at any instruction boundary in
the program: in the middle of the sequence interpreter, in the middle of the
allocator's linked-list surgery, in the middle of the IRQ. Anything the handler
touches, it might be touching underneath code that was halfway through changing
it.

The ROM's answer to that hazard is to make the handler do almost nothing. It
saves the registers it uses, reads the latch, decides between two possible
fates for the byte, and returns. For the great majority of commands, "decides"
means putting the byte in a queue.

## Answer now, or queue for later

Three of the 219 commands are questions rather than sounds, and a question is
useless if the answer takes a few milliseconds to arrive. The NMI handler
therefore consults a 219-byte table, one entry per command number, which says
only whether this command is ordinary or special.

| Command | Question | Answer |
|---|---|---|
| `$03` | What is the coin door doing? | The four cached switch fields |
| `$06` | Can the sound CPU answer the operator's ping? | The fixed number `$DB` |
| `$07` | Are you healthy? | The error-flag byte, and both heartbeat bits get armed |

`$06` is worth a second look. `$DB` is 219, the first byte outside this ROM's
command range. The reply routine does not calculate it from a table size—it
loads the literal `$DB`—but the companion OS stores the reply and uses it as the
operator sound selector's exclusive upper bound. The selector therefore ends at
`$DA`. So `$DB` is both the successful ping response and a command-count/end
sentinel, not an unexplained diagnostic byte.

The other 216 commands take the ordinary path. The handler drops the byte into a
queue and returns immediately. Every decision about what the byte means, which
chip it belongs to, and what has to be stopped to make room for it happens later,
in the main loop, where taking a few hundred microseconds costs nothing.

```mermaid
flowchart TD
    Write["Main CPU writes one byte"] --> HW["Hardware latches it<br/>and raises NMI"]
    HW --> Check{"Ordinary, or<br/>one of the three<br/>questions?"}
    Check -->|"question"| Reply["Answer immediately<br/>and return"]
    Check -->|"ordinary"| Queue["Put it in the ring<br/>buffer and return"]
    Queue --> Loop["Main loop takes one<br/>per pass"]
```

*The interrupt's only job is to get the byte off the latch and out of the way.
Real work happens in the main loop.*

## What a ring buffer is

The queue is sixteen bytes of RAM plus two positions: one saying where the next
arriving byte goes, one saying where the next byte to be handled comes from.
Both positions count upward and wrap around to zero when they run off the end,
which is why the arrangement is called a **ring buffer**.

Its virtue is that the producer and the consumer never have to agree on timing.
The interrupt writes at whatever moment the game happens to speak. The main loop
reads whenever it gets round to it. Neither one waits for the other, and neither
one needs to know the other's exact timing, because the two positions carry the
current state between them. When they are equal, the queue is empty.

There is a limit hidden in that simple representation. Because equal positions
mean empty, the sixteen-byte array can hold at most fifteen pending commands. If
a new arrival would make the write position catch the read position, the NMI
handler advances the read position first, silently discarding the oldest pending
command, and then stores the new one. The newest command wins and no overflow
flag is raised.

Fifteen pending commands is still generous for this application. A burst of four
players all firing at once is four commands, and the main loop drains one command
per pass while running hundreds of passes per second. The overflow rule is the
last-resort behavior if that assumption is ever exceeded.

## Two lookups turn a byte into an action

Here is the part of the design that explains why one program can drive every
noise in the game.

The main loop takes one byte from the ring and reads it as an index into two
parallel 219-byte tables. The first table gives a **handler type**, a number from
0 to 14 saying what kind of job this is. The second gives a **parameter**, a
single byte whose meaning depends entirely on which handler type came out of the
first table. The type then selects one of fifteen routines from a jump table, and
that routine runs with the parameter in hand.

```mermaid
flowchart LR
    Byte["Command byte<br/>$0D"] --> T["Type table<br/>-> 7"]
    Byte --> P["Parameter table<br/>-> $06"]
    T --> Jump["Jump table<br/>15 entries"]
    Jump --> H["Play-a-sound handler"]
    P --> H
    H --> Sound["Sound $06 starts"]
```

*Two table reads and one indexed jump. Command `$0D` is nothing more than row 13
of two arrays.*

Both lookups are guarded. A command value of `$DB` or higher is rejected before
either table is touched, and a handler type of 15 or higher is rejected before
the jump. Neither rejection can happen with this ROM's tables, which is the
point: the guard exists so that a garbled byte on the latch cannot send the CPU
to an address made of whatever bytes happened to follow the table.

The payoff of the arrangement is worth stating plainly. Adding a new sound to
Gauntlet II means writing an entry in each of two tables and adding a description
of the sound to the data further along in the ROM. The 6502 code is not touched.
Every one of the 216 queued commands runs the same nine routines.

## The nine kinds of job

Fifteen slots exist in the jump table. Nine of them have commands pointing at
them.

| Type | What it does | Commands |
|---:|---|---:|
| 7 | Play a sound: effects and music alike | 62 |
| 11 | Speak a phrase | 141 |
| 5 | Stop a named sound | 3 |
| 9 | Fade a named sound | 1 |
| 10 | Fade everything of a given kind | 1 |
| 13 | Set the mixer levels | 4 |
| 0 | Set the global priority threshold | 2 |
| 8 | Queue a byte back to the main CPU | 1 |
| 3 | Reinitialize all audio state | 1 |

Two of those rows account for 203 of the 216 queued commands. Type 7 is
[Chapter 7](07_command_to_channel.md) through
[Chapter 12](12_driving_the_ym2151.md); type 11 is
[Chapter 13](13_speaking.md). The remaining seven rows are the whole of the
board's control surface, and this chapter finishes them off.

The other six slots in the jump table hold real, finished routines that no
command in the table selects. They can apply a bytecode instruction to every
live channel matching a description, silence channels by category, and set
workspace variables from a small table of records that is entirely zeros in this
ROM. [Chapter 17](17_open_questions.md) says what is known about them.

## Stopping and fading

A stop command does not carry a channel number or a voice number, because the
main CPU does not know any. It carries the number of another command.

Command `$21` has parameter `$20`. The handler reads command `$20` out of the
same two tables the dispatcher just used, checks that it is a type-7 sound, and
extracts its parameter. Then it walks all thirty logical channels and marks every
one that is currently playing that sound as finished. Command `$20` is "Death
Touches Player", so `$21` is the instruction to stop it.

| Command | Stops | Sound |
|---|---|---|
| `$21` | `$20` | Death Touches Player |
| `$2F` | `$2E` | Player Touches Force Field |
| `$39` | `$37` | Slow Motion |

The three sounds with a stop command are the three that outlast the event they
belong to. Two of them genuinely never end: "Player Touches Force Field" and
"Slow Motion" both reach a backward jump and loop forever, as
[Chapter 9](09_sequence_language_opcodes.md) shows. "Death Touches Player" is
technically finite — a repeat count of ten around a sustained whole note, which
runs 53 seconds and then stops — but no player is ever in contact with Death for
anything like that long, so in practice it behaves the same way: it plays until
the game says stop. Everything else in the ROM ends on its own, near enough to
when the thing that caused it ends.

Fading is the same idea with a gentler ending. Command `$3C` names command `$3B`,
the theme song, and instead of marking its channels finished it marks them
*fading* and hands each one a downward volume ramp.
[Chapter 10](10_shaping_the_sound.md) is about what happens next. Command `$41`
works from a category rather than a name: it fades every logical channel whose
status field carries a particular value, which is how the treasure-room music
stops without the game having to know which of its four variants is playing.

One command sits outside all of this. `$00` reruns the whole audio reset from
[Chapter 5](05_waking_up.md), clearing every channel and resetting both chips.
It is the only thing in the command set that will silence a chip test, because
the chip tests loop forever and no stop command names them.

## Talking back

Replies use a second queue, sixteen bytes of RAM with its own position
counters. A handler that wants to say something puts a byte in the buffer and
returns. The main loop, on each pass, checks the status bit that says whether the
main CPU has collected the previous reply; if it has, and something is waiting,
the main loop writes one byte to `$1000`. That write latches the byte and
interrupts the 68010, so the reply gets picked up promptly.

Only one command uses this path. `$DA` queues the value `$55`, which the game
can then read back as proof that a command travelled all the way through the ring
buffer, the dispatcher, and the reply queue. Specifically, handler type 8 at
`$4445` inserts `$55` into the sound CPU's sixteen-byte outgoing ring. The main
loop later writes it to `$1000`, where it is latched for the main CPU. `$DA`
does not make a sound. The three direct questions bypass the buffer entirely
and write to `$1000` from inside the interrupt.

The sound language described in [Chapter 9](09_sequence_language_opcodes.md) has
an instruction that queues a byte the same way, so a piece of music could in
principle signal the game when it reached a particular bar. No sound in this ROM
uses it.

## The mixer and the global filter

Four commands set the three analog volume levels from
[Chapter 2](02_tour_of_the_board.md). Handler type 13 at `$4619` splits the
parameter into two RAM shadows: `$28 = parameter & $E0` holds the speech field,
while `$29 = parameter & $1F` holds the effects and music fields. When speech is
idle, the handler writes `$29` to `$1020`, deliberately leaving speech muted.
When a phrase starts, the speech machinery writes `$28 | $29` instead. The
handler defers an immediate `$1020` write when the speech state in `$2F`
overlaps the active mixer bits, so the speech level and stream change together.

The four parameters are more specific than "presets" suggests:

| Command | Parameter | Speech | Effects | Music |
|---|---|---:|---:|---:|
| `$D6` | `$E7` | 7 | 0 | 7 |
| `$D7` | `$EF` | 7 | 1 | 7 |
| `$D8` | `$F7` | 7 | 2 | 7 |
| `$D9` | `$FF` | 7 | 3 | 7 |

Speech and music stay at full level in all four. The only thing these commands
change is the effects level, across its whole range from off to full. An
operator adjusting the cabinet is turning a physical trimmer; these four commands
are the board's own control over how loud the sound effects sit against the
music. They neither start nor stop a sequence. In particular, `$D6` mutes the
effects path in the analog mix; active effects continue advancing and can become
audible again if another preset restores their level.

The companion game ROM sends `$D7` during the level-start screen, selecting
effects level 1. An exhaustive static trace of the game-side `sound_play` and
`sound_speech_play` producers finds no ordinary-gameplay emitter for
`$D6,$D8,$D9`, or `$DA`; `$D7` is the contrasting literal at game `$44F68`.
The OS operator sound test can select and send every command from `$08` through
`$DA`, so it exposes all four mixer presets and the `$DA` return-path test.

The layout of this tail therefore looks deliberate rather than like padding:
`$D6-$D9` cover all four values of the two-bit effects field, `$DA` exercises
the queued sound-to-main return path, and `$06` returns the exclusive bound
`$DB`, one byte beyond the final command. That diagnostic/service-interface
purpose is a strong inference from the code; the ROM cannot tell us whether
`$D8/$D9` were also reserved for abandoned gameplay features.

The last pair of control commands does something more drastic. Commands `$01` and
`$02` set a single global threshold, computed as the parameter times four.

| Command | Parameter | Threshold |
|---|---:|---:|
| `$01` | `$3C` | 240 |
| `$02` | `$00` | 0 |

Speech compares its raw priority against the threshold, so `$01` rejects every
phrase: the largest speech priority is 64. Type-7 synthesis takes a less obvious
route. Allocation encodes a record of priority *p* as a status value of
`4*p + 1`; `SWITCH_POKEY` clears the low two status bits, while YM2151 channels
normally retain them. The output routines compare that encoded status, not the
raw priority, with the threshold.

The distinction matters at the top of the range. `$01` suppresses every POKEY
effect, every speech phrase, and most YM2151 sounds, but the theme at priority 61
has status 245 and the four coin-slot sounds at priority 63 have status 253.
Those five YM2151 sounds survive a threshold of 240. Command `$01` is therefore
a high global filter, not a true whole-board mute. `$02` clears the threshold so
all candidates pass again.

> **Try it yourself**
>
> ```bash
> uv run gauntlet_disasm.py soundrom.bin --cmd 0x03 --csv hw_docs/soundcmds.csv
> uv run gauntlet_disasm.py soundrom.bin --cmd 0x0D --csv hw_docs/soundcmds.csv
> uv run gauntlet_disasm.py soundrom.bin --cmd 0x5A --csv hw_docs/soundcmds.csv
> ```
>
> Three commands, three different fates. `$03` reports `Type 255
> (Invalid/Unused)` with no data at all, because it never reaches the main
> dispatcher; the interrupt answered it and the type table was free to say
> nothing. `$0D` reports `Type 7`, parameter `$06`, and two channels of decoded
> music. `$5A` reports `Type 11`, parameter `$11`, and 324 bytes of speech data
> from an entirely different part of the ROM. Notice that the tool prints the
> parameter for all three: it is the same byte from the same table each time, and
> only the handler type decides what it means.

## What you now know

- Once the hardware accepts a command byte, it is latched and signalled by the
  same event, so it cannot be missed between that signal and the sound CPU's read.
- The interrupt answers three questions on the spot and queues everything else in
  a sixteen-slot ring buffer that holds at most fifteen pending commands.
- Two parallel 219-byte tables turn a command into a handler type and a
  parameter; the type selects one of fifteen routines.
- Nine handler types are used; type 7 covers 62 sounds and type 11 covers 141
  spoken phrases.
- Stop and fade commands name another command rather than a channel, and the
  handler resolves it through the same tables.
- Commands `$01` and `$02` raise and clear a global threshold. The high setting
  suppresses speech and most synthesized sounds, but the theme and coin-slot
  sounds remain eligible.

## Where this leads

[Chapter 7](07_command_to_channel.md) picks up the moment the type-7 handler
starts work. One parameter has to become up to eight simultaneous parts, spread
across a chip that only has eight, while whatever was already playing keeps
playing or gets thrown off.

## Going deeper

- [`docs/08_command_reference.md`](../docs/08_command_reference.md) — the command
  space, handler distribution, and every control command.
- [`docs/04_subsystems.md`](../docs/04_subsystems.md) — the main loop, the NMI
  input path, and the output queue.
- [`docs/05_data_reference.md`](../docs/05_data_reference.md) — the validation,
  type, parameter, and handler-target tables with their exact extents.
- [`docs/generated/command_catalog.csv`](../docs/generated/command_catalog.csv)
  — all 219 commands as rows.
- [`docs/generated/nmi_protocol_catalog.csv`](../docs/generated/nmi_protocol_catalog.csv)
  — the NMI paths block by block.
- [`docs/generated/control_plane_catalog.csv`](../docs/generated/control_plane_catalog.csv)
  — every handler's exact reads and writes.
