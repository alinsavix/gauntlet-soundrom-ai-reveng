# *How Gauntlet II Makes Noise* — Book Outline and Author's Brief

> **This is a historical working specification, not prose, and it is not part
> of the current book.** Its general overview, intended audience, organization,
> and style instructions are still largely useful, but some technical details
> and chapter-specific directions are outdated. Those specifics were corrected
> while writing and auditing the finished text. Do not use this file to
> regenerate factual content without checking the corresponding finished
> chapter and the ROM-derived evidence. The current book is the seventeen
> numbered chapters and six appendices listed in [`README.md`](README.md).

---

# Part 0 — Author's Brief

## 0.1 What we are making

A readable, chapter-structured book that explains how the Gauntlet II arcade
game's sound hardware and sound-CPU program work, aimed at someone who has
never seen 6502 assembly or an arcade board.

The repository already contains a complete, rigorous technical reference in
`docs/`. That material is correct but nearly unreadable unless you already know
the answer. **This book is the readable counterpart, not a replacement.** Nothing
new is being discovered here; everything written must trace back to `docs/`.

## 0.2 Audience

A **hobbyist programmer**. Assume they know:

- variables, loops, functions, arrays, lookup tables
- memory, bits, bytes, hexadecimal notation
- the general idea that a program is instructions plus data

Assume they do **not** know:

- 6502 assembly, or any assembly
- what an interrupt is, what a memory-mapped device is, what a zero page is
- FM synthesis, LPC speech coding, or how a POKEY makes a tone
- anything about arcade board architecture
- anything about Gauntlet's internals

Every one of those unfamiliar concepts must be introduced in plain language at
the first point the book needs it, and then reused freely afterward.

## 0.3 Voice and altitude — the single most important rule

Explain **what the system does and why**, using the code as evidence rather than
as the subject. Prefer a labelled table, a short pseudocode block, or a sentence
of plain English over a listing of instructions.

**Do not write like this:**

> The type-7 handler at `$44DE` loads the parameter into Y, reads
> `$5FA8,Y` to obtain the starting record offset, then indexes `$6024,X`,
> `$60DA,X`, `$6190,X`/`$6191,X`, and `$62FC,X` to obtain priority, hardware
> channel, sequence pointer, and next link, before entering the allocation
> scan at `$44FD` with the interrupt mask set via PHP/SEI.

**Write like this:**

> Each sound is described by one or more *records*. A record is a row in a
> five-column table stored in ROM:
>
> | Column | Meaning |
> |---|---|
> | Priority | How important this sound is; used to decide what gets cut off |
> | Channel | Which of the twelve hardware voices it wants |
> | Sequence | Where its "sheet music" begins in ROM |
> | Next | The next record in this sound, or *stop* |
>
> A sound effect such as "player takes key" is a single record. The theme song
> is a chain of eight, one per YM2151 voice — the game asks for one sound and
> gets a whole eight-part arrangement.

Addresses may appear, but only when they help the reader find something in the
ROM or in `docs/`. They must never carry the explanation. A good ratio is at
most one or two addresses per page of prose, usually in a table cell rather
than in a sentence.

## 0.4 Code in the book

- **Pseudocode is the default.** Python-flavoured or plain-language, whichever
  reads better. Keep blocks under ~20 lines.
- **Real 6502 assembly is allowed only when the trick *is* the point** — for
  example the ROM's synthesized jump-table dispatch (it pushes a
  target-minus-one address onto the stack and `RTS`es into the handler), which
  cannot be explained honestly without showing it. Expect at most **three or
  four** such moments in the entire book. Annotate every line when you do.
- **Show real ROM tables as tables**, with labelled rows and columns and a
  sentence explaining how to read them. The duration table, the POKEY volume
  shapes, and the YM instrument record layout are all far clearer as a grid
  than as prose.

## 0.5 Diagrams

- Mermaid fenced blocks (` ```mermaid `), because the repo already uses them
  and they render on GitHub.
- **Simple.** A diagram with more than about ten boxes has failed. Prefer three
  small diagrams to one large one.
- `docs/04_subsystems.md` and `docs/06_sequence_engine.md` already contain
  accurate diagrams. Reuse their *content*, but redraw them with friendly
  labels — replace `$4187` with `IRQ handler`, `$500D` with `hardware
  dispatcher`, and so on.
- Every diagram needs a caption sentence saying what the reader should take
  away from it.

## 0.6 Certainty policy — read this twice

The reference docs use an evidence vocabulary: **Verified**, **Strong
inference**, **Hypothesis**, **Unknown**, **Contradicted**.

The book's chapters 1–15 are written **as settled fact, with no hedging**. To
make that honest, the writer must filter:

| Source doc says | Book chapters 1–15 |
|---|---|
| Verified | State it plainly. |
| Strong inference | State it plainly. |
| Hypothesis | **Do not use.** Omit, or hand it to Chapter 17. |
| Unknown | **Do not use.** Hand it to Chapter 17. |
| Contradicted | **Never repeat the old claim**, not even to correct it. |

Never use the words "Verified", "Strong inference", "Hypothesis", or
"Contradicted" as jargon in chapters 1–15. Never write "we believe", "it
appears that", "it is likely that", or "the analysis suggests". If a claim
needs a hedge, it belongs in Chapter 17 instead.

Chapters 16 and 17 are the only place the uncertainty and the reverse
engineering process are discussed, and there the hedging is the point.

## 0.7 Source hierarchy — where facts come from

**Use these:**

| Source | Use it for |
|---|---|
| `docs/01_hardware.md` … `docs/10_known_issues.md` | **Canonical.** Every factual claim in the book must be supported here. |
| `docs/generated/*.csv` | Row-level data: exact command lists, chains, speech metadata, tables. Best source for appendices. |
| `hw_docs/POKEY.md`, `hw_docs/YM2151.md`, `hw_docs/operation.txt` | Chip behaviour and board wiring, from datasheets and schematics. |
| `soundcmds.csv` | Human names for sounds ("Elf Dies", "WELCOME TO THE TREASURE ROOM."). Note: has stray tabs/quotes; clean them up when quoting. |
| `mame_refs/`, `ymfm/` | How the chips actually behave, when you need to explain *why* a register does what it does. |
| `gauntlet_disasm.py` | Ground truth for the "Try it yourself" boxes. Run commands before printing them. |
| `README.md` (repo root) | Project backstory, ROM part numbers/checksums, the $50 anecdote — material for Chapter 1 and Chapter 16. |

**Do NOT use as sources:**

- `REPORT.md`, `REPORT_SUMMARY.md` — historical work logs containing
  superseded and internally contradictory conclusions. They are explicitly
  obsolete per `docs/README.md`.
- `REVIEW_FINDINGS.md`, `MEMMAP.md` — older artifacts, superseded by `docs/`.
- `docs/NEXT_STEPS.md` — an internal handoff document; useful only as a
  pointer to which `docs/` chapter is authoritative.

If `docs/` and any other file disagree, `docs/` wins. If two `docs/` chapters
disagree, flag it in a `<!-- TODO -->` comment rather than guessing.

## 0.8 House style and conventions

- **Hex notation:** the book uses the ROM-world convention `$3B`, introduced
  once in Chapter 1 with a sentence explaining it means the same thing as
  `0x3B`. Be consistent thereafter. The `$3B` form is the standard normally used
  in 6502 assembly language. 
- **Rounded numbers in prose, exact numbers in tables.** Write "about 240 times
  a second" in a sentence; put `239.6909904 Hz` in a table if the exact figure
  matters. Never open a chapter with a nine-significant-figure number.
- **Canonical vocabulary** — use these terms and no synonyms:

  | Term | Means |
  |---|---|
  | **main CPU** | The 68010 running the game itself |
  | **sound CPU** | The 6502 in the sound subsystem on the main circuit board |
  | **command** | One of the 219 byte values the main CPU can send |
  | **handler type** | Which of the 15 kinds of job a command is |
  | **record** | One row of the type-7 sound description tables |
  | **chain** | The linked run of records that makes up one sound |
  | **sequence** | The bytecode "sheet music" a record points at |
  | **opcode** | One instruction of that bytecode language ( `$80`–`$BA` ) |
  | **logical channel** | One of 30 in-progress voices tracked in RAM |
  | **physical channel** | One of 12 real chip voices (4 POKEY + 8 YM2151) |
  | **sweep** | One pass in which the interrupt updates every voice of one chip |
  | **tick** | One sweep interval, about 8.3 ms |
  | **envelope** | A stored curve that changes volume or pitch over time |
  | **voice / instrument** | A 42-byte YM2151 FM patch definition |
  | **phrase** | One recorded speech utterance |

- **Never anthropomorphize the analysis.** No "Claude found", "the AI
  discovered", "we then realized" in chapters 1–15. Chapter 16 is where the
  process gets discussed.
- **Chapter cross-references** are links: `[Chapter 4](04_heartbeat.md)`.

## 0.9 Chapter structure — every chapter follows this shape

1. **Title** (`# Chapter N — Title`)
2. **"Before this chapter"** — one or two lines naming the earlier chapters
   whose ideas are assumed. Chapter 1 says "nothing".
3. **Opening hook** — one short paragraph tying the chapter to something the
   reader can hear or picture in the actual game.
4. **Body** — the bullets listed in Part 1 of this outline, in order, each
   expanded into one or more sections with `##` headings.
5. **"Try it yourself"** — a boxed exercise (see §0.10). Required in every
   chapter where one is specified below.
6. **"What you now know"** — three to six one-line takeaways.
7. **"Where this leads"** — one or two lines pointing at the next chapter.
8. **"Going deeper"** — a short list of the `docs/` chapters and
   `docs/generated/*.csv` files covering the same ground, for readers who want
   the rigorous version.

## 0.10 "Try it yourself" boxes

Format: a `> **Try it yourself**` blockquote containing one bash fenced block
and two to four sentences describing what the reader should see or hear, and
what to notice about it.

Mandatory practical notes to state **once**, in Chapter 1, and then rely on:

- The ROM is **not** in this repository, for copyright reasons, and will not
  ship with the book. Chapter 1 must explain building `soundrom.bin` from the
  two Atari part numbers listed in the repo `README.md`, and give the expected
  SHA-1 so the reader can check it. Write every box on the assumption that the
  reader has to supply the ROM themselves before anything will run.
- The tool is self-contained: it needs no `PYTHONPATH` setting and no files
  from `utility/`, and `uv` fetches its one dependency (numpy) automatically.
  Run it from the repo root:

  ```bash
  uv run gauntlet_disasm.py --list
  ```

  This same plain form works on Windows, macOS, and Linux alike; every later
  box should use it so it works when pasted.
- WAV rendering of YM2151 material compiles the bundled YMFM core, so a local
  C++14 compiler is needed for those specific boxes. Say so where it first
  matters (Chapter 12), not in every box.

**The writer must actually run every command before printing it**, and describe
the real output rather than an imagined one. A working copy of the ROM *is*
available in the authoring environment — it sits in the repo root as an
untracked `soundrom.bin`, the same name Chapter 1 tells the reader to build —
so commands can be pasted into a box exactly as run, and there is never a
reason to guess at output.

## 0.11 Length budget

| Section | Target |
|---|---|
| Chapters 1–3 (orientation) | 2,000–2,500 words each |
| Chapters 4–13 (the machinery) | 2,500–4,000 words each |
| Chapter 14 (chip tests) | 3,000–4,000 words |
| Chapter 15 (case studies) | 4,000–5,000 words |
| Chapters 16–17 (about the work) | 1,500–2,500 words each |
| Appendices | As long as the data requires |
| **Total** | **~45,000 words**, plus appendices |

## 0.12 Files to produce

```
book/
  README.md                  ← table of contents + "how to read this book"
  01_two_computers.md
  02_tour_of_the_sound_hardware.md
  03_three_sound_chips.md
  04_heartbeat.md
  05_waking_up.md
  06_taking_orders.md
  07_command_to_channel.md
  08_sequence_language_time.md
  09_sequence_language_opcodes.md
  10_shaping_the_sound.md
  11_driving_the_pokey.md
  12_driving_the_ym2151.md
  13_speaking.md
  14_chip_tests.md
  15_case_studies.md
  16_how_this_was_figured_out.md
  17_open_questions.md
  A_glossary.md
  B_command_list.md
  C_opcode_reference.md
  D_reference_tables.md
  E_using_the_tool.md
  F_where_to_look_next.md
```

Write chapters **in order**. Each chapter may assume everything in the previous
ones and must not assume anything from later ones.

## 0.13 Author-to-agent comments

The author may leave batch-edit instructions in chapter prose as Markdown HTML
comments beginning with `AGENT:`:

```markdown
<!-- AGENT: Rewrite this paragraph in plainer language. -->
```

When asked to process the agent comments, search the requested scope for every
`<!-- AGENT:` comment, carry out each instruction in context, and remove
comments that have been resolved. Leave a comment in place when it explicitly
asks to be preserved or when it cannot be resolved without the author's
judgment, and report any such comments at the end. These comments do not replace
the formal `**[image needed]**` and `**[needs verification]**` draft markers.

## 0.14 Additional Style Notes

No antithesis. No corrective negation. No paragraph pinning. No parataxis. No summary beats. No rhetorical crutches. No negative parallelisms. No negative anaphoras. No contrasting pairs. No rule of three. No em dashes. No throat-clearing openers. No landing sentences. No setup/payoff constructions. No parallel sentence structures within a paragraph. Vary sentence length unpredictably. No stacked noun phrases. No filler intensifiers (genuinely, really, truly, actually). No corporate-register verbs (leverage, underscore, reflect). No nominalization. No hedging qualifiers. No performed enthusiasm.

<!-- TODO: Reconcile "No em dashes" with the required `# Chapter N — Title`
     format in section 0.9 and the existing chapter/appendix titles. -->

Items that need verification or author input, you can mark them with `**[needs verification]**`. Places where the author needs to provide an image can be marked with a blockquote beginning with `**[image needed]**` that describes what the image should show. These markers are draft-only, the finished book should contain zero such markers. 

---

# Part 1 — Chapter Outline

---

## Chapter 1 — Two Computers in One Cabinet

*Before this chapter: nothing.*

Orientation. Establishes the central surprising fact — sound is a whole second
computer — and gets the reader set up to follow along.

- **Why an arcade game needs a second computer for sound.** The 68010 running
  the game cannot spare the attention: sound needs servicing hundreds of times
  per second, forever, while the game is busy moving monsters. So Atari gave
  the sound its own 6502, its own RAM, its own ROM, and its own three sound
  chips, and connected the two computers by a single one-byte mailbox. State
  explicitly that this is a largely independent subsystem on the same large
  circuit board as the rest of the game, not a separate sound board.
- **The one-byte conversation.** The entire vocabulary between the two
  computers is 219 command numbers, plus a handful of status bytes coming back.
  When you eat food in Gauntlet II, the game writes one byte — and everything
  else in this book is what happens next. Introduce `$0D` ("Food Eaten") as the
  running toy example.
- **The three ways this subsystem makes sound**, one sentence each: POKEY for
  simple electronic tones and noise, YM2151 for FM synthesis, TMS5220 for
  speech. Note up front that the obvious guess ("POKEY does effects, YM does
  music") turns out to be wrong, and the book will show why — a hook for
  Chapter 3.
- **Notation and setup.** Hex notation `$3B`; the fact that the ROM is a single
  48 KB file that the CPU sees at addresses `$4000`–`$FFFF`; how to build
  `soundrom.bin` from the two Atari EPROM images and verify its SHA-1; how to
  run the disassembler (the plain `uv run` form from §0.10 — no path setup).
- **How to read this book.** The four-part arc: the machine (2–4), waking up
  and taking orders (5–6), making a sound (7–13), watching it happen (14–15).
  A one-paragraph note that a rigorous companion reference lives in `docs/`.

> **Try it yourself:** `--list` to see all 219 commands scroll past. Ask the
> reader to find `$0D`, `$3B`, and `$5A` and notice the three different
> subsystems.

*Sources: repo `README.md`, `hw_docs/operation.txt`, `docs/01_hardware.md`,
`docs/08_command_reference.md`, `soundcmds.csv`.*

---

## Chapter 2 — A Tour of the Sound Hardware

*Before this chapter: 1.*

What the sound CPU can see and touch. This chapter teaches memory-mapped I/O,
which everything later depends on.

- **The 6502 has a 16-bit address space containing RAM, ROM, and hardware
  registers.** Assume the reader already understands memory addresses and focus
  on the mapping: writing to `$1800` changes the pitch of a POKEY tone rather
  than storing a byte in RAM. This is memory-mapped I/O, and it is how the CPU
  controls every sound chip.
- **The map.** A single labelled diagram plus a table: RAM `$0000`–`$0FFF`,
  the hardware window `$1000`–`$1035` and `$1800`–`$1830`, a large unused hole,
  and 48 KB of ROM filling `$4000`–`$FFFF` — code *and* every note, instrument,
  and recorded word in the game. Emphasize the proportion: about 30 KB of that
  ROM is speech recordings.
- **The wall of mailboxes at `$1000`.** How the two computers actually talk:
  `$1010` is where an incoming command appears, `$1000` is where a reply goes
  out, `$1030` is a set of flag bits answering "is there a command waiting?",
  "did my last reply get picked up?", "is the speech chip ready?", "is the
  self-test switch set to its test position?".
- **The volume knobs the software controls.** Writing to `$1020` sets three
  independent volume levels — speech, effects, music — packed into one byte
  (3 bits, 2 bits, 3 bits). Show the bit layout as a labelled diagram. This is
  a genuine analog mixer being driven digitally.
- **The odd jobs.** The same sound subsystem also drives the two mechanical
  coin counters and reads the coin switches. It is worth saying plainly that the sound CPU is
  the machine's coin accountant as well as its orchestra; Chapter 4 explains
  why that ended up here.
- **RAM: 4 KB of scratch paper.** Preview only, not detail — the zero page as
  the CPU's fastest 256 bytes, and the fact that most of the rest holds thirty
  parallel arrays describing sounds in progress. Chapter 7 fills this in.

> **Try it yourself:** Check the file size and SHA-1 of `soundrom.bin`; confirm
> it is exactly 49,152 bytes, and work out from Chapter 2's map that file
> offset 0 is CPU address `$4000`.

*Sources: `docs/01_hardware.md`, `docs/02_memory_map.md`,
`docs/03_rom_structure.md`, `hw_docs/operation.txt`.*

---

## Chapter 3 — Meet the Three Sound Chips

*Before this chapter: 1–2.*

Conceptual, not register-level. The reader should finish able to *hear* the
difference in their head and know which chip is responsible for a given noise
in the game.

- **POKEY: counting down to a square wave.** Explain the divider model from
  first principles — a fast clock, a counter, a flip on each underflow, so a
  smaller number means a higher pitch. Four channels; each has a frequency byte
  (AUDF) and a control byte (AUDC) holding volume in the low nibble and
  waveform/distortion in the high nibble. Explain what "distortion" means here:
  the output is filtered through shift-register polynomial counters, giving
  buzzes and noise rather than clean tones. Mention the two useful extras
  Gauntlet uses: joining two channels into one 16-bit counter for low, precise
  pitches, and the free hardware random number generator at `$180A`.
- **YM2151: FM synthesis, or one wave bending another.** Explain frequency
  modulation with a picture rather than an equation: a *modulator* oscillator
  wobbles the pitch of a *carrier* oscillator thousands of times a second, and
  the result is heard as a change of timbre rather than of pitch. Four
  operators per channel; eight ways of wiring them together (the *algorithms*),
  from a four-deep stack to four independent sine waves. Each operator has its
  own ADSR envelope and its own volume ("total level"). Eight channels. Note
  that a channel's whole personality is one 42-byte block of numbers.
- **TMS5220: speech by describing a throat.** Explain LPC as compression by
  simulation — instead of storing the recorded waveform, store a
  frame-by-frame description of a buzz or hiss plus a ten-stage filter that
  shapes it into a vowel or consonant. This is why 30 KB of ROM holds around
  200 phrases, and why it sounds like that. Note the chip has a small internal
  FIFO and tells the CPU when it is hungry.
- **The actual division of labour, which is not the obvious one.** Deliver the
  Chapter 1 promise with numbers: of the 182 sound records in the ROM, only 11
  target the POKEY — commands `$05` and `$43`–`$49`. Everything else, music and
  the great majority of sound effects alike, goes through the YM2151. The
  POKEY's real specialities here are a handful of noisy effects and the random
  number generator.
- **Why these three chips.** Brief: each was chosen for what it does cheaply.
  Nothing here can play a sampled recording, so every sound is either
  synthesized on the fly or spoken by the LPC chip.

> **Try it yourself:** Render one POKEY effect, one YM effect, and one spoken
> phrase to WAV (`--sfx-wav`, `--music-wav`, `--speech-wav`) and listen to the
> three textures back to back.

*Sources: `hw_docs/POKEY.md`, `hw_docs/YM2151.md`, `mame_refs/pokey.txt`,
`mame_refs/tms5220.txt`, `ymfm/`, `docs/01_hardware.md`,
`docs/04_subsystems.md`.*

---

## Chapter 4 — The Heartbeat: Interrupts and the Eight-Millisecond Tick

*Before this chapter: 1–3.*

The single most load-bearing chapter in the book. Every timing statement later
is measured in the units defined here.

- **What an interrupt is.** For a reader who has never met one: a hardware
  signal that makes the CPU drop what it is doing, run a fixed routine, and
  resume exactly where it left off. Introduce the two the sound CPU uses and
  keep them straight for the rest of the book: **IRQ**, the regular metronome,
  and **NMI**, "the main CPU just said something".
- **The metronome comes from the video circuitry.** The IRQ is derived from the
  screen's scanline counter, firing four times per frame — about 240 times a
  second. Make the point that the sound subsystem's sense of time is borrowed
  from the picture: this is why the music is locked to the video rate.
- **Alternating sweeps, and where "8.3 ms" comes from.** Each interrupt updates
  *one* chip, alternating: odd ticks sweep the four POKEY channels, even ticks
  sweep the eight YM2151 channels. So each chip is fully refreshed about 120
  times a second — once every 8.3 ms. Establish this as **the tick**, the
  fundamental grain of everything in Chapters 7–12: no note can start, stop, or
  change more precisely than this.
- **Speech gets serviced four times per interrupt.** Roughly 960 opportunities
  per second to hand the speech chip its next byte, because the speech chip
  consumes bytes faster and on its own schedule. Explain that these are
  *attempts*: the chip refuses when its buffer is full.
- **What else rides on the interrupt.** The same routine debounces the coin
  switches, steps the mechanical coin-counter pulses, and clears the watchdog
  heartbeat bits that let the main CPU tell whether the sound subsystem is alive.
  Explain the coin-counter pulse shaping (a solenoid needs a stretched pulse,
  not a flick) and the two-mode split between self-test and normal operation.
- **The budget question.** Roughly 7,500 CPU cycles fit in one interval, and a
  quiet board uses about a fifth of them. Mention what a heavy moment costs
  (the first tick of the four-channel POKEY chip test slightly overruns) and
  why the design survives it — a late interrupt stays pending and is serviced
  immediately afterwards rather than being lost. Keep this qualitative;
  the arithmetic belongs in `docs/`.

> **Try it yourself:** `--score 0x3B` and observe every event landing on a
> multiple of the tick. Compute the theme's length in ticks and in seconds.

*Sources: `docs/01_hardware.md` (clock tree), `docs/04_subsystems.md` (IRQ
service, board/coin control), `docs/06_sequence_engine.md` (timing).*

---

## Chapter 5 — Waking Up: Reset and Self-Test

*Before this chapter: 1–4.*

Power-on to ready. Also the natural place to explain how the board reports its
own health.

- **The first thing the CPU does is wait.** At reset, the 6502 reads its
  starting address from the last bytes of ROM, and the routine there spins
  until a status pattern at `$1030` says the rest of the board has settled.
  Only then does the real initialization begin. Good place to explain reset
  vectors generally.
- **Two very different boot paths.** The maintained self-test switch is mounted
  inside the cabinet; it is not a button the operator holds. In its normal
  position, boot is fast: clear RAM, set up, go. In its test position, the board
  runs a full diagnostic first. Show this as a small flowchart.
- **The RAM test: walking a single one.** Explain the walking-bit technique in
  plain language — write a value with exactly one bit set, read it back, rotate
  the bit, repeat, then repeat with everything inverted. This catches stuck
  bits and shorted address lines that a simple "write 0, read 0" would miss.
  Note the two severities: a failure in the first two pages is fatal, because
  the CPU cannot even keep a stack there, so the board reports `$10` to the
  main CPU and stops. A failure anywhere else sets a flag and carries on.
- **The ROM test: three checksums that must come out to `$FF`.** Add up every
  byte in each 16 KB third, modulo 256; the ROM was built so the answer is
  exactly `$FF`. Explain why this is the cheapest possible integrity check and
  what it does and does not catch.
- **The error-flag byte.** One byte at `$02` carries eight independent bits:
  three ROM-region failures, two RAM-region failures, a YM2151 timeout, and two
  heartbeat bits. Show it as a labelled bit table. Explain the heartbeat
  protocol: the main CPU sends command `$07`, which both reports the flags and
  *arms* two bits; the main loop and the interrupt each clear their own bit, so
  if either has died, the next `$07` reveals it. This is a watchdog built out
  of one byte.
- **Setting the table.** What initialization builds before the first command
  arrives: cleared channel arrays, a free pool of 197 small linked-list records,
  both sound chips reset and silenced, the speech chip primed with a dummy
  stream, and the incoming-command mailbox switched into its normal mode.

> **Try it yourself:** Verify the three ROM checksums by hand with a few lines
> of Python over `soundrom.bin` — each third should sum to `$FF` mod 256. It is
> a satisfying way to prove the ROM image is genuine.

*Sources: `docs/04_subsystems.md` (boot), `docs/02_memory_map.md` (error
flags), `docs/07_function_index.md` (initialization entries),
`docs/generated/initialization_main_catalog.csv`.*

---

## Chapter 6 — Taking Orders: Commands from the Main CPU

*Before this chapter: 1–5.*

The command pipeline, from a single byte to the right handler.

- **How a command arrives.** The main CPU writes one byte; the hardware
  simultaneously latches it and fires the NMI. Emphasize why this pairing
  matters: once the hardware accepts a byte, it cannot be missed between the
  signal and the read. Qualify the game side: it checks the mailbox-full flag,
  queues ordinary commands that get a busy result, and retries them later;
  ordinary sound commands have no individual response acknowledgement.
- **Answer now, or queue for later.** The NMI routine looks the command up in a
  219-entry table that says "ordinary" or "answer immediately". Three commands
  are answered on the spot because they are questions, not sounds: `$03` (what
  is the coin/switch state?), `$06` (operator-test selector-bound query, with a
  fixed `$DB` reply used as the exclusive upper bound), and `$07` (report your
  error flags and re-arm the heartbeats). Everything else is dropped into a 16-slot
  ring buffer that can hold fifteen pending commands, and the interrupt returns
  immediately — the interrupt must be short, so the *work* happens in the main
  loop.
- **What a ring buffer is,** for readers who haven't met one: a fixed array
  plus a read position and a write position that wrap around, letting a
  producer and a consumer run at different speeds without either waiting.
- **Two lookups turn a byte into an action.** The main loop pulls one command
  from the ring and reads two parallel 219-byte tables: one gives a *handler
  type* (0–14), one gives a *parameter*. The type selects one of fifteen
  routines from a jump table; the parameter tells that routine which sound.
  Show this as a small diagram and stress the payoff: adding a sound means
  editing tables, not code.
- **The fifteen handler types, and the nine that are used.** A table with a
  plain-language column: play a sound (type 7, 62 commands), speak (type 11,
  141 commands), stop a named sound, fade a named sound, fade everything
  matching a condition, set the mixer, set a global loudness filter, queue a
  byte back to the main CPU, and full reset. Note that six more types are
  fully implemented but no command selects them — leftovers, and Chapter 17
  says what is known about them.
- **Talking back.** The reply path: a 16-byte outgoing buffer, a wait for the
  previous reply to be collected, then a write to `$1000` that interrupts the
  main CPU. Note that a *sequence* can also queue a byte this way — the music
  itself can signal the game.
- **The volume and filter commands.** `$D6`–`$D9` set mixer presets; `$01` and
  `$02` set a global loudness threshold that suppresses anything quieter than
  it. The threshold uses encoded type-7 status rather than raw synthesis
  priority: `$01` suppresses speech and most sounds, but the theme and four
  coin-slot sounds survive. Round out the chapter by connecting these to the
  `$1020` mixer from Chapter 2.

> **Try it yourself:** `--cmd 0x03`, `--cmd 0x0D`, `--cmd 0x5A` — three
> commands, three completely different handler types. Note how the tool reports
> each one's type and parameter.

*Sources: `docs/08_command_reference.md`, `docs/04_subsystems.md` (main loop,
NMI, output queue), `docs/05_data_reference.md` (dispatch tables),
`docs/generated/command_catalog.csv`.*

---

## Chapter 7 — From Command to Channel

*Before this chapter: 1–6.*

The allocation layer: how "play sound `$3B`" becomes up to eight simultaneous
voices, and what happens when the board runs out.

- **A sound is a chain of records.** Introduce the five parallel ROM tables as
  one five-column table (as in §0.3). A command's parameter picks a starting
  row; each row's "next" column links to another, up to eight deep, and a zero
  ends the chain. Give the distribution: 22 sounds are a single record, 24 are
  two, and twelve — the music — are full eight-record chains.
- **Thirty logical channels for twelve physical ones.** The key abstraction of
  the whole ROM. RAM tracks up to **30** sounds-in-progress, but the chips only
  have **12** real voices (4 POKEY + 8 YM2151). Each physical voice owns a
  priority-sorted linked list of the logical channels that want it; on each
  sweep the whole list is updated, but only the front of the list is actually
  heard. Diagram this — it is the single idea that makes Chapters 11 and 12
  make sense.
- **Why update sounds nobody can hear?** Because when the loud sound ends, the
  quiet one underneath must already be at the right place in its music, not
  starting from the beginning. Say this explicitly; it is the design's cleverest
  and least obvious decision.
- **Priority, preemption, and running out.** Each record carries a priority.
  Insertion is sorted. If all 30 logical slots are busy, the allocator may evict
  the lowest-priority channel on the requested physical voice, and only if the
  newcomer ranks at least as high. Equal priority *replaces* — which is why
  re-triggering the same effect restarts it instead of layering it.
- **The little pool of four-byte records.** The engine keeps 197 reusable
  four-byte blocks for bookkeeping (subsequence returns and repeat counters).
  Explain free-list allocation in two sentences, and note that freeing a
  channel returns its blocks.
- **Doing it without tearing.** Insertions and removals happen with interrupts
  briefly disabled, because the interrupt is walking those same lists 120 times
  a second. Use this to teach the general hazard in one short paragraph.
- **Where the sound goes next.** Every record names a physical channel (0–3
  POKEY, 4–11 YM2151) and a sequence pointer. That pointer is the subject of
  the next two chapters.

> **Try it yourself:** `--cmd 0x3B` and count the eight records with their
> channels and priorities; compare with `--cmd 0x0D`, a single record. Then
> look at `docs/generated/type7_chain_catalog.csv` for the full picture.

*Sources: `docs/04_subsystems.md` (type-7 subsystem), `docs/05_data_reference.md`
(type-7 tables), `docs/02_memory_map.md` (channel arrays),
`docs/08_command_reference.md` (allocation), `docs/generated/type7_chain_catalog.csv`.*

---

## Chapter 8 — The Sequence Language, Part 1: Notes, Rests, and Time

*Before this chapter: 1–7.*

The reveal: the ROM contains a small custom programming language, and every
sound in the game is a program written in it. This chapter covers the data
half — notes and time.

- **Atari wrote a language instead of writing sounds.** Frame it that way. A
  sequence is a byte stream, interpreted one instruction at a time by a routine
  that runs inside the interrupt. Introduce the three-way split of the first
  byte, as a table: `$00`–`$7F` is a note or rest, `$80`–`$BA` is an opcode,
  `$BB`–`$FF` means stop.
- **A note is two bytes.** The first is the pitch, the second packs four
  separate fields — duration index, a secondary division field, a "dotted"
  bit, and a "sustain" bit. Draw the byte as eight labelled boxes and walk
  through one real example. This is a good place to observe that music notation
  concepts (dotted notes, sustain, tempo) are literally encoded in the format.
- **The duration table.** Sixteen 16-bit values in ROM, indexed by the low
  nibble. Print the whole table with a musical interpretation column (whole,
  half, quarter, …) so the reader can see it is a real note-length table. Then
  the modifiers: the dotted bit adds half the duration, and the secondary field
  can halve the note's *sounding* length to produce staccato.
- **How duration becomes time, and why it isn't simple division.** Each channel
  has a *tempo* value. On every tick, the tempo is subtracted from the channel's
  timer; the next event happens when the timer goes negative. Crucially, the
  overshoot is carried into the next note rather than discarded — so a sequence
  never drifts, even when durations don't divide evenly by tempo. Explain the
  phase-accumulator idea plainly; it is why `ceil(duration/tempo)` gives the
  wrong answer and why the exported MIDI timing is approximate.
- **Two timers per note: when it stops and when the next starts.** The primary
  timer schedules the *next event*; the secondary timer schedules *key-off*, a
  little earlier, which is what makes notes sound articulated instead of glued
  together. Work through the real example from the music chip test: a note
  active for 58 of its 60 ticks, leaving a two-tick gap. Sustained notes skip
  this entirely.
- **Ending, and chaining.** A note byte followed by a duration byte of zero is
  not a zero-length note — it is the end/return marker. If the sequence was
  called as a subroutine, it returns; otherwise the channel stops. Set up
  Chapter 9's control flow.
- **Pitch.** Note values are chromatic semitone numbers; the ROM's numbering is
  offset from MIDI by 11, so ROM note 49 is MIDI 60, middle C. POKEY and
  YM2151 turn that number into hardware values in completely different ways —
  Chapters 11 and 12.

> **Try it yourself:** `--cmd 0x42` (level-opening music) and read the decoded
> notes and durations; then `--score 0x42` to see them laid out in time.

*Sources: `docs/06_sequence_engine.md` (stream format, timing),
`docs/05_data_reference.md` (duration table),
`docs/generated/timing_duration_trace_catalog.csv`.*

---

## Chapter 9 — The Sequence Language, Part 2: The Opcodes

*Before this chapter: 1–8.*

The code half of the language: 59 instructions that make it a real programming
language rather than a note list.

- **How an instruction is decoded.** Byte, then zero to three operands, then
  a table lookup that jumps to the handler. This is the one place where showing
  real assembly earns its keep: the ROM's dispatcher doubles the opcode, pushes
  a target-minus-one address, and `RTS`es into the handler — a stack trick that
  is a genuinely clever way to do a computed jump on a chip with no such
  instruction. Show it, annotate it, and note it is the same trick used for the
  command dispatcher in Chapter 6.
- **Setting the channel's state.** The unglamorous majority: tempo, volume,
  transpose, distortion, repeat count, control bits, envelope pointers. Group
  them into a table with plain-language descriptions rather than listing all
  59 individually (Appendix C has the complete list). Point out that "set" and
  "add" variants exist for most of them, which is what makes gradual changes
  possible.
- **Control flow: this is a real language.** Subroutine call and return
  (`$8D`, and the `xx 00` marker from Chapter 8) so a repeated phrase is stored
  once. Counted repeat blocks (`$8E`/`$8F`) using the four-byte record pool
  from Chapter 7. Unconditional jump (`$99`) forming loops — every piece of
  looping music in the game is one of five such back-edges. Diagram these.
- **Variables, arithmetic, and conditionals.** Each channel has a general
  register plus a sixteen-slot shared workspace. Opcodes add, subtract, AND,
  OR, XOR, and shift. A "classifier" opcode loads a *named* value into the
  register — the channel's own tempo, transpose, volume, or envelope position.
  Compare-and-branch opcodes jump on equal, not-equal, positive, or negative.
  Say the conclusion plainly: sequences can make decisions about themselves
  while they play.
- **Randomness, and the jump table trick.** The classifier can read the POKEY's
  hardware random number generator, and the indexed-jump opcodes (`$AE`/`$AF`)
  use that value to pick from a table of targets. This is how a few effects get
  variation — `$2B` picks one of four notes, `$2C` and `$3A` one of sixteen.
  Note that most uses of the indexed jump have exactly one entry and are simply
  an ordinary jump.
- **Chip-specific opcodes.** The same language drives both chips, but some
  instructions only make sense on one. YM-only: load an instrument, adjust
  operator levels, load register blocks. Note the overloading trick that keeps
  RAM small — four per-channel bytes hold envelope pointers in POKEY mode and
  four operator volumes in YM mode. Also note `$9A`, which lets a sequence
  trigger speech: music can talk.
- **Instructions that exist but are never used.** A short, honest paragraph: a
  vibrato opcode with no caller, several no-ops. Details go to Chapter 17.

> **Try it yourself:** `--cmd 0x1C` shows a counted repeat; `--cmd 0x2C` shows
> a random branch; `--cmd 0x2E` shows an infinite loop. Three opcodes, three
> completely different behaviours.

*Sources: `docs/06_sequence_engine.md` (opcode reference, control-flow model,
variable classifier), `docs/generated/bytecode_handler_catalog.csv`,
`docs/generated/type7_control_flow_catalog.csv`.*

---

## Chapter 10 — Shaping the Sound: Envelopes, Ramps, and Distortion

*Before this chapter: 1–9.*

What happens on the ticks *between* notes. This is where a sequence stops
sounding like a player piano.

- **The problem an envelope solves.** A note that switches on at full volume
  and off again sounds like a beep. Real instruments swell, decay, and wobble.
  Since the engine already visits every channel 120 times a second, it can
  nudge volume and pitch a little on each visit — for free.
- **Volume envelopes: a list of "change this much, this many times".** Two-byte
  records: a signed delta and a repeat count. Show a real envelope from the ROM
  as a table and a small ASCII/mermaid shape. Explain the terminators: an
  all-zero record ends the envelope, and an `$FF` count introduces a loop
  control that rewinds to an earlier record — which is how a sustained
  tremolo is stored in six bytes.
- **Frequency envelopes: the same idea applied to pitch.** Three-byte records,
  because the pitch delta is 16-bit. These are what produce the sweeps, chirps,
  and zaps. Note that all thirteen uses in the ROM are on POKEY channels.
- **Distortion shapes: a curve library.** Eight 16-step signed trajectories in
  ROM, selected by bits of the note's control byte, stepping through phases
  that saturate at the end. Print the table as an 8×16 grid — it is one of the
  most visually satisfying tables in the ROM — and note which five rows the
  game actually uses.
- **Fades and ramps: volume changes measured in fractions.** The fade commands
  (`$3C`, `$41`) and the fade opcode hand a channel a signed amount and a rate.
  Because a fade may need to move less than one volume step per tick, the
  engine keeps a fractional remainder and applies whole steps only when they
  accumulate. Explain fixed-point arithmetic in three sentences using this as
  the example — sixteen rate settings, dividing by 2 through 256, plus one
  special "count down and stop" setting.
- **Where the shaping lands.** On POKEY, all of this ends up in one nibble of
  volume and one nibble of waveform. On the YM2151, volume shaping means
  changing operator *total levels*, and because of the FM algorithms, changing
  a modulator's level changes timbre rather than loudness. Preview both, then
  hand off to Chapters 11 and 12.

> **Try it yourself:** Render one POKEY effect to WAV and view the waveform;
> the envelope's staircase should be visible as a series of ~8 ms steps.

*Sources: `docs/06_sequence_engine.md`, `docs/05_data_reference.md`
(volume shapes, fade rates), `docs/04_subsystems.md` (fade/ramp staging),
`docs/generated/type7_envelope_catalog.csv`,
`docs/generated/volume_shape_catalog.csv`, `docs/generated/fade_rate_catalog.csv`.*

---

## Chapter 11 — Driving the POKEY

*Before this chapter: 1–10.*

The last few inches of the POKEY path: from four prepared logical channels to
nine actual register writes.

- **The sweep.** Every other tick, the engine walks four physical lists, runs
  the sequence engine for every logical channel on each, and produces one
  candidate frequency/volume/control set per physical voice.
- **Choosing a winner, and the global filter.** Within a physical voice, the
  highest priority wins. Additionally, a global threshold silences any winner
  whose encoded status falls below it — this is what commands `$01` and `$02`
  set. The high setting silences all configured POKEY effects but is not a
  whole-board mute.
- **The pair trick.** POKEY's channels can be joined into pairs to form 16-bit
  counters, giving much finer and lower pitches than 8 bits allow. The engine
  processes physical channels in pairs but arbitrates two internal lanes chosen
  by status bit 0: independent 8-bit output versus a joined candidate. If the
  joined lane wins or ties, it selects joined mode. Explicitly warn that equal
  priorities on the two physical channels do not cause joining; command `$05`
  demonstrates that they remain independent.
- **Building the AUDCTL byte.** Each logical channel contributes AND and OR
  masks; the final control byte is everything OR'd together and then filtered
  by everything AND'd together. Explain this mask-accumulation pattern once —
  it is a common trick for combining independent requests. Note that in
  practice the sequences only ever request the high-speed clock bit, and the
  joined-mode bits come from the pair arbitration above.
- **Pitch: the divider table.** A 128-entry table of 16-bit divider values,
  chromatic through note 97. Show a short excerpt with note names and resulting
  frequencies and explain the inverse relationship (bigger number = lower
  pitch) and why equal temperament comes out slightly off.
- **Nine writes and out.** Four frequency registers, four control registers,
  one AUDCTL, written through an indirect pointer. Close by naming the eight
  POKEY commands in the whole game (`$05` and `$43`–`$49`) — one chip test and
  seven effects — so the reader ends the chapter knowing exactly what the POKEY
  is responsible for.

> **Try it yourself:** `--cmd 0x44` then `--sfx-wav 0x44`. Read the sequence,
> hear the result, and identify the frequency envelope's sweep in the audio.

*Sources: `docs/04_subsystems.md` (POKEY pipeline), `docs/05_data_reference.md`
(note lookup), `hw_docs/POKEY.md`, `mame_refs/pokey.txt`,
`docs/generated/pokey_control_catalog.csv`.*

---

## Chapter 12 — Driving the YM2151

*Before this chapter: 1–11.*

The busier of the two paths, and the one that carries almost all of Gauntlet
II's sound.

- **The sweep, and the busy problem.** On the alternate ticks, the engine
  visits all eight YM channels. Unlike POKEY, the YM2151 must be asked before
  every single register write whether it is ready; the code polls a status bit,
  and gives up after 255 tries, setting an error flag. Explain why a chip has a
  busy flag at all, and why a bounded retry loop matters inside an interrupt.
- **An instrument is 42 bytes.** Walk the record layout as a labelled table:
  four channel-level bytes (algorithm/feedback, pitch, key fraction, LFO
  routing), then six bytes each for the four operators (detune/multiple,
  level, attack, decay, sustain/release, and so on), then a tail of
  level-transform descriptors. The ROM holds 55 of these; 39 are used by name.
  This is the chapter's centrepiece — the reader should come away able to read
  a real instrument out of the ROM.
- **Loading a voice.** The `$9D` opcode copies a 28-byte register image to the
  chip in one go. Point out the economy of the design: a single two-byte
  instruction in the sequence completely redefines what that voice sounds like.
- **Volume on an FM chip is not a volume knob.** Making a YM channel quieter
  means raising the *total level* attenuation of only its **carrier**
  operators, and which operators are carriers depends on the algorithm — so the
  ROM keeps an eight-entry mask table, one row per algorithm. Adjusting a
  modulator instead would change the timbre. This is the single most
  counter-intuitive thing in the chapter; give it space, with a diagram of two
  contrasting algorithms.
- **The attenuation curve, and the transform chain.** Volume changes are not
  linear: the ROM indexes a sixteen-step signed attenuation curve, and the
  instrument's tail bytes chain each operator's correction into the next
  through a 256-entry lookup. Explain what this achieves — a musically even
  fade — without reproducing the arithmetic.
- **Pitch: key code and key fraction.** A note becomes a *key code* (octave +
  one of twelve semitone slots, with four unused codes per octave — explain
  that oddity) plus a *key fraction* for fine tuning. Give the accuracy result
  as a concrete payoff: the eight test notes come out within about half a cent
  of equal temperament.
- **Keying on and off.** A small set of flag bits decides, per tick, whether to
  release the previous note, refresh pitch and levels, or strike a new note.
  Tie this back to the secondary timer from Chapter 8 — that is what triggers
  key-off, and that is what makes phrasing audible.

> **Try it yourself:** `--cmd 0x3D` (treasure room) to see voice loads and
> level changes, then `--music-wav 0x3D` to hear it. Note the compiler
> requirement from §0.10 here.

*Sources: `docs/04_subsystems.md` (YM pipeline), `docs/05_data_reference.md`
(YM tables), `docs/06_sequence_engine.md` (voice loaders), `hw_docs/YM2151.md`,
`ymfm/`, `docs/generated/ym_voice_field_catalog.csv`,
`docs/generated/ym_voice_record_catalog.csv`,
`docs/generated/ym_pitch_validation_catalog.csv`.*

---

## Chapter 13 — Speaking: The TMS5220 Path

*Before this chapter: 1–12.*

A completely separate pipeline, and a good contrast: no bytecode, no channels,
just a queue and a byte pump.

- **Speech skips everything.** Say plainly what type 11 does *not* use: no
  sequence engine, no logical channels, no envelopes. A speech command resolves
  through three parallel 141-entry tables to a pointer, a length, a clock flag,
  and a priority — and then it is just bytes.
- **The corpus.** 189 streams occupying about 30 KB — nearly two-thirds of the
  whole ROM — laid out end to end with no gaps. 141 are real phrases; the other
  48 are one-byte "stop immediately" streams. Give the reader the memorable
  fact that Gauntlet II devotes more ROM to talking than to everything else
  combined, and quote a few phrase names from the command list.
- **Priority and the queue.** Eight physical slots provide seven usable queue
  entries because pointer equality means empty. Full is checked before
  priority, so even a higher-priority arrival is rejected when seven phrases
  wait. If room exists, a *higher*-priority phrase discards everything waiting
  but does **not** interrupt what is currently being spoken. Equal priority
  appends; lower priority is dropped. Use the urgent phrases (`$A1`–`$A6`,
  "Better hurry!") as the concrete example of the high-priority group.
- **The streaming state machine.** Four states — idle, kickoff, streaming,
  drain — driven by the four service calls per interrupt from Chapter 4. On
  kickoff the CPU sends the chip's "speak external" command; while streaming it
  hands over one byte each time the chip says it is ready. Diagram the state
  machine.
- **The seventeen zeroes at the end.** When the data runs out, the code writes
  seventeen zero bytes before going idle. The reason is genuinely interesting:
  the chip has a 16-byte input buffer and aborts speech if that buffer empties
  before it reaches the encoded stop frame — so the padding is exactly enough
  to push the real ending through. A nice example of software shaped by a
  hardware quirk.
- **When the chip stops answering.** A watchdog counts service attempts where
  the chip never signals ready; after about 32 ticks (roughly a seventh of a
  second) the code resets and reinitializes the speech chip mid-phrase.
- **The clock flag.** 27 of the 141 phrases set a flag that switches the speech
  chip's oscillator to a faster divider — a deliberate pitch-up effect ("squeak"
  in the schematics). List which groups of commands use it.

> **Try it yourself:** `--speech-wav 0x5A` ("NEEDS FOOD, BADLY.") and
> `--speech-wav 0xA2` ("TIME IS RUNNING OUT!"), then compare a normal phrase
> against one of the `$80`-flagged squeak phrases.

*Sources: `docs/04_subsystems.md` (type-11 subsystem), `docs/05_data_reference.md`
(speech metadata), `docs/01_hardware.md`, `mame_refs/tms5220.txt`,
`docs/generated/type11_speech_catalog.csv`,
`docs/generated/speech_lifecycle_catalog.csv`.*

---

## Chapter 14 — The Chip Tests: Three Guided Walkthroughs

*Before this chapter: 1–13.*

The first payoff chapter. The three self-test commands are the simplest
complete examples of each path, and walking them start to finish consolidates
everything so far.

- **Why start here.** These sequences were written to be obvious — they exist
  to let a technician confirm each chip works. They are the cleanest teaching
  material in the ROM.
- **Command `$04`, the music chip test.** An eight-record chain covering all
  eight YM2151 channels. Trace it fully: allocation of eight logical channels,
  the voice load, and the eight-note scale — C4, D4, E4, F4, G4, A4, B4, C5 —
  with each channel running exactly twice as long as the one before it (120,
  240, 360 … 840 ticks; 1.0 to 7.0 seconds). Explain that the staircase makes
  a fault audible: a dead channel is a missing step. Finish with the eighth
  channel's sustained note looping forever.
- **Command `$05`, the effects chip test.** Four POKEY records. Trace
  allocation into four logical slots and four physical lists, the setup opcodes
  that establish envelopes and distortion, and two channels that loop
  indefinitely on a 30-tick cycle. This is the place to show a real
  loop-control record (`$FF FF 06`) doing its rewind, since Chapter 10
  introduced the idea abstractly.
- **Command `$08`, the speech chip test.** The very first stream in the corpus.
  Trace it through Chapter 13's state machine: queue, kickoff, byte pump,
  seventeen zeroes, idle.
- **What the tests reveal about the design.** Short closing section: all three
  take completely different routes through the ROM, yet all three start as one
  byte in the same mailbox. Reprise the whole pipeline in one diagram.

> **Try it yourself:** All three, disassembled and rendered:
> `--cmd 0x04 / --music-wav 0x04`, `--cmd 0x05 / --sfx-wav 0x05`,
> `--cmd 0x08 / --speech-wav 0x08`.

*Sources: `docs/08_command_reference.md` (diagnostic commands),
`docs/06_sequence_engine.md` (traced timings), `docs/04_subsystems.md`,
`docs/03_rom_structure.md`.*

---

## Chapter 15 — Case Studies: Three Sounds, End to End

*Before this chapter: 1–14.*

The full-strength payoff chapter. Three real game sounds, each traced from the
main CPU's single byte to air, with the *reason* for each design decision
called out.

- **"Food Eaten" (`$0D`) — the simplest real effect.** One byte, one record,
  one YM voice. Follow it through NMI, ring buffer, dispatcher, allocation,
  the sequence's voice load and short note run, key-off, and channel release.
  Keep this section deliberately brisk — the reader should be able to predict
  most of it now, and noticing that is the point.
- **"Needs food, badly." (`$5A`) — the speech path.** Follow the entirely
  different route: table lookup to a pointer and length, priority check against
  what is already speaking, queue, then roughly 900 interrupt services pumping
  bytes into the speech chip. Show the arithmetic connecting stream length to
  spoken duration. Contrast explicitly with the first case study — same
  mailbox, no shared machinery at all.
- **The Gauntlet II theme (`$3B`) — eight voices at once.** The showpiece. The
  eight-record chain across all eight YM channels; the per-channel tempo; the
  subroutine calls that let a repeated phrase be stored once; the loop that
  makes it play until stopped; a channel-by-channel description of the
  arrangement (which channel is bass, which is melody). Include a rendered
  score excerpt and the MIDI export. Note honestly, once, that MIDI timing is a
  close approximation rather than exact, and why (Chapter 8's carried
  remainder).
- **What happens when they collide.** Close by triggering all three at once
  conceptually: the theme holds eight YM channels, the effect wants one, the
  speech is independent. Walk the priority arbitration and show which sound
  wins, which is preempted, and which quietly keeps playing underneath — the
  Chapter 7 idea, now with real numbers behind it. This is the moment the whole
  design should click.

> **Try it yourself:** `--midi 0x3B --midi-out theme.mid`, then open the result
> in any DAW or MIDI player and look at the eight tracks.

*Sources: everything; especially `docs/generated/type7_chain_catalog.csv`,
`docs/generated/type7_sequence_catalog.csv`,
`docs/generated/type11_speech_catalog.csv`, `soundcmds.csv`.*

---

## Chapter 16 — How This Was Figured Out

*Before this chapter: 1–15.*

The making-of chapter. First place in the book where hedging and process are
allowed and expected.

- **The starting point.** A 48 KB binary blob, no source, no labels, no
  symbols, and a schematic. Explain what "reverse engineering a ROM" actually
  involves: there is no marker saying where code ends and data begins, and the
  same bytes can be both.
- **The method that worked: follow the consumer.** The central technique — do
  not ask "what is this data?", ask "what code reads it, and what does that
  code do with the value?". Illustrate with a real reversal from this project:
  a table long labelled a frequency table turned out to be an operator-level
  transform, because the code reading it wrote the result to level registers,
  not pitch registers.
- **Cross-checking against independent implementations.** How MAME's POKEY and
  TMS5220 cores and the YMFM library were used as oracles — the ROM's intent
  can be confirmed by running its register writes through a known-good chip
  model and checking the result is music.
- **Executing the ROM to check the reading.** The strongest validation
  available: `gauntlet_disasm.py` runs the actual 6502 code — the real
  scheduler, the real interpreter, the real register writes — and produces
  audio. If the theme song comes out recognizable, the understanding is right.
  Mention the moment this failed: the theme first came out three seconds long
  because the record chaining was misread as two channels instead of eight.
- **The evidence discipline.** Explain the Verified / Strong inference /
  Hypothesis / Unknown ladder used throughout `docs/`, and be explicit that
  chapters 1–15 of this book were filtered to the top two rungs — so the reader
  knows what the confident tone was resting on.
- **That it was mostly done by an AI.** State it plainly and without hype, with
  the honest details from the repo `README.md`: the cost, the small number of
  human corrections needed, and what those corrections were. This is part of
  the project's story and the reader deserves it.

*Sources: `docs/09_analysis_method.md`, `docs/README.md` (evidence vocabulary),
repo `README.md`, `prompting/PROMPT.md`, `prompting/PLAN.md`.*

---

## Chapter 17 — What We Still Don't Know

*Before this chapter: 1–16.*

The honest ledger. Keep it interesting rather than apologetic — each unknown is
a small mystery, and the reader now knows enough to appreciate them.

- **The vestigial boot burst.** Five specific bytes are written to five
  addresses that Gauntlet II decodes as one sound→main latch. The schematic,
  MAME, companion game ROM, and Atari System 1 map identify the routine as
  leftover 6522 speech-VIA initialization; none of the intermediate bytes is
  consumed by Gauntlet II.
- **The six unused handler types.** Fully implemented, fully understood
  routines that no command selects: apply an opcode to matching live channels,
  kill channels by status, set workspace values. Describe what each would have
  done, and note the two possibilities (development leftovers, or a feature
  used by a different game on the same board) that cannot be distinguished from
  one ROM image.
- **The alternate boot command mode.** The companion OS intentionally writes
  startup command `$00` while sound reset is asserted. During a narrow
  diagnostic window, a delivered NMI would write it through a zeroed RAM
  pointer instead of queueing it. Only reset/latch/NMI delivery timing remains;
  that needs a bus or cycle-accurate board trace, not more main-CPU disassembly.
- **Small unexplained things.** One byte in every 42-byte instrument record
  that no code ever reads; 15 instruments and one complete sequence with no
  reference pointing at them; about 300 bytes of apparently unused ROM; four
  bytes just before the interrupt vectors.
- **Things only a real machine can answer.** Where the exact boundary sits
  between "definitely correct" and "correct as far as we can prove": the real
  duration of a YM2151 busy wait, exactly how the analog mixer sums the three
  sources, and the true cabinet wiring of the coin inputs.
- **How you could help.** Short and practical: a logic-analyzer capture from a
  real board, another revision of the sound ROM, or original Atari source would
  each close specific items. The main CPU's operator sound test exposes the four
  formerly uncertain commands, so all available static emitter questions are
  closed.

*Sources: `docs/10_known_issues.md` (use the P0/P1/P2 items, skipping any
marked Resolved), `docs/03_rom_structure.md` (unused space),
`docs/generated/external_question_catalog.csv`.*

---

# Part 2 — Appendices

## Appendix A — Glossary

Every term from §0.8's vocabulary table plus every piece of jargon introduced in
the book, each defined in one or two sentences with a pointer to the chapter
that introduces it. Alphabetical. Include the general computing terms the
audience may not have (interrupt, memory-mapped I/O, ring buffer, jump table,
free list, fixed-point, phase accumulator, envelope, LPC, FM operator).

## Appendix B — The Complete Command List

All 219 commands as one sortable table: number, in-game meaning, handler type
in plain language, which chip, and chain length or phrase text.

Build from `docs/generated/command_catalog.csv` joined with
`soundcmds.csv`. **Clean the legacy CSV's stray tabs and quotation
errors** when transcribing; do not change any numeric IDs. Where the legacy CSV
says "Not Used", distinguish gameplay from operator-test use. In particular,
`$D7` is used by `show_level_start_screen`, and `$D6,$D8,$D9,$DA` are selectable
through the OS sound test even though the legacy list says they are not used.

## Appendix C — The Bytecode Opcode Reference

All 59 opcodes `$80`–`$BA`: opcode, name, operand count, plain-language
description, and which chips it applies to. A "never used by any sound in this
ROM" column. Derive from `docs/06_sequence_engine.md` and
`docs/generated/bytecode_handler_catalog.csv`.

## Appendix D — Reference Tables

The tables a reader will want to look up while reading, each with a caption
explaining how to read it:

- the memory map (RAM, hardware, ROM regions)
- the error-flag bits
- the 16-entry duration table with musical interpretations
- the 8×16 POKEY volume-shape grid
- the 16-entry fade-rate table
- an excerpt of the POKEY note-divider table with note names and frequencies
- the YM2151 key-code mapping and the `MIDI = ROM note + 11` convention
- the 42-byte YM instrument record layout, offset by offset
- the clock tree: master clock down to each device and each service rate

## Appendix E — Using `gauntlet_disasm.py`

The complete tool reference: building `soundrom.bin` from the two EPROM images
with expected checksums, the fact that the script is a single self-contained
file (numpy is its only dependency and `uv` installs it), the C++ compiler
requirement for YM rendering, and every flag with an example and a description
of its output. Also a short section on the `utility/*_audit.py` scripts and the
`docs/generated/*.csv` files they produce, for readers who want to regenerate
the data themselves — noting that those scripts, unlike the disassembler, do
still need `PYTHONPATH=utility` for their shared `mos6502_cycle` helper.

## Appendix F — Where to Look Next

A cross-reference table mapping each book chapter to the `docs/` chapters and
`docs/generated/*.csv` files covering the same ground rigorously, so a reader
who wants proof of any claim knows exactly where to go. Include a short warning
that `REPORT.md` and `REPORT_SUMMARY.md` are historical work logs containing
superseded conclusions and should not be used as reference.

---

# Part 3 — Per-Chapter Delivery Checklist

Before considering any chapter finished, confirm:

- [ ] Opens with "Before this chapter" and a concrete hook from the actual game.
- [ ] Every unfamiliar concept is introduced before it is used.
- [ ] No claim rests on a source marked Hypothesis, Unknown, or Contradicted.
- [ ] No hedging language anywhere in chapters 1–15.
- [ ] No evidence-vocabulary jargon in chapters 1–15.
- [ ] Assembly appears only where the trick itself is the subject, and is
      annotated line by line.
- [ ] Every diagram has ten boxes or fewer and a caption.
- [ ] Every ROM table shown is a real table with labelled rows and columns.
- [ ] Every "Try it yourself" command was actually run, and the described
      output matches reality.
- [ ] Vocabulary matches §0.8 exactly; no synonyms crept in.
- [ ] Ends with "What you now know", "Where this leads", and "Going deeper".
- [ ] Word count within the §0.11 budget.
