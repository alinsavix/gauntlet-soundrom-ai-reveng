# Appendix E — Using `gauntlet_disasm.py`

Every "Try it yourself" box in this book runs one tool. This appendix is its
complete reference.

## Getting set up

**The ROM is not in this repository.** The code is still Atari's, so you have to
supply it. The sound board carries two EPROMs; concatenate them, first one first,
to get the 48 KB image everything here calls `soundrom.bin`.

| Part number | Board location | Size | SHA-1 |
|---|---|---|---|
| 136043-1120 | 16R | 16 KB | `045ad571db34ef870b1bf003e77eea403204f55b` |
| 136043-1119 | 16S | 32 KB | `6d0d8493609974bd5a63be858b045fe4db35d8df` |

```bash
cat 136043-1120 136043-1119 > soundrom.bin
```

The result is exactly 49,152 bytes with SHA-1
`a9795393899fd20ce23ef98811195b9406485ed0`. Check it before going further:

```bash
sha1sum soundrom.bin
```

On macOS that is `shasum -a 1 soundrom.bin`. There is a second check worth
running, because it is the same one the board runs on itself: each 16 KB third of
the image sums to `$FF` modulo 256.

```bash
python -c "
rom = open('soundrom.bin','rb').read()
for third in range(3):
    chunk = rom[third*16384:(third+1)*16384]
    print(hex(0x4000 + third*0x4000), hex(sum(chunk) % 256))
"
```

Put the file in the root of this repository.

**The tool needs nothing else installed.** `gauntlet_disasm.py` is one
self-contained Python file with inline dependency metadata naming NumPy, so `uv`
fetches NumPy the first time you run it and never asks again. It needs Python 3.10
or later.

```bash
uv run gauntlet_disasm.py soundrom.bin --list
```

That exact form works on Windows, macOS, and Linux. Every command in this book is
written to be pasted verbatim.

**One extra thing is needed for YM2151 audio.** Rendering music compiles the
bundled YMFM chip model from `ymfm_renderer.cpp`, so those specific commands need
a C++14 compiler on your path. The tool looks for `clang++`, then `g++`, then
`c++`, builds once, and reuses the result. Everything else in this appendix runs
without a compiler.

**Names are optional but worth having.** The human descriptions ("Food Eaten",
"NEEDS FOOD, BADLY.") live in a separate file that the tool will use if you point
at it. Its automatic search does not look in `hw_docs/`, so pass the path:

```bash
uv run gauntlet_disasm.py soundrom.bin --list --csv hw_docs/soundcmds.csv
```

Without it every command still resolves; the description column is just blank.

---

## Reading the ROM

### `--list`

Every command from `$00` to `$DA`, one per line, with its handler type,
parameter, sequence pointer, chain length, subsystem, and description. Start
here.

```bash
uv run gauntlet_disasm.py soundrom.bin --list --csv hw_docs/soundcmds.csv
```

```
0x04      7  Type  7 (POKEY/YM2151 Sequence)  0x00    $690C    8   MUSIC  Music Chip Test
0x05      7  Type  7 (POKEY/YM2151 Sequence)  0x01    $6838    4     SFX  Effects Chip Test
0x08     11  Type 11 (TMS5220 Speech)  0x00    $873D    -  SPEECH  Speech Chip Test
```

### `--cmd N`

Disassemble one command. Accepts hexadecimal (`0x0D`) or decimal (`13`). For a
type-7 sound it prints a header with the priority and record offset, then one
block per channel in the chain, with every instruction decoded and annotated.

```bash
uv run gauntlet_disasm.py soundrom.bin --cmd 0x0D --csv hw_docs/soundcmds.csv
```

```
=== Command 0x0D: "Food Eaten" (SFX) ===
Handler: Type 7 (POKEY/YM2151 Sequence) | Param: 0x06 | Priority: 2 | Channel: 0x08 | Offset: 0x1D | Channels: 2
Notes: 6 | Est. play time: 0.5s (0:00)

--- Channel 1/2: hw=0x08, priority=2, offset=0x1D ---
Sequence @ $7FB5:
  $7FB5:  9D 34 72       SET_VOICE $7234  ; -> $7234
  $7FB8:  80 99          SET_TEMPO $99
  $7FBA:  82 0D          SET_VOLUME $0D
  $7FBC:  00 0A          REST $00, 32nd
  $7FBE:  1F 09          NOTE F#2 ($1F), sixteenth
```

For a speech command it prints the pointer, the length, and the metadata instead.
For a control command it prints the handler type and parameter and stops, which
is the correct answer: those commands have no sequence data.

Two labels in that output are worth knowing. `Est. play time` is a mean-timing
estimate, not an exact figure, for the reason
[Chapter 8](08_sequence_language_time.md) gives about carried remainders. For a
sound that loops forever the tool says "decoded loop prefix" instead, because
there is no play time to report.

### `--addr ADDR`

Disassemble a raw sequence at any address, without going through the command
tables. Useful for following a jump target or looking at something nothing points
at.

```bash
uv run gauntlet_disasm.py soundrom.bin --addr 0x80DA
```

```
Sequence @ $80DA:

  $80DA:  9D 6A 6F       SET_VOICE $6F6A  ; -> $6F6A
  $80DD:  80 A0          SET_TEMPO $A0
  $80DF:  00 01          REST $00, whole
  $80E1:  00 00          CHAIN  ; end of sequence
```

That is the unreferenced sequence from
[Chapter 17](17_open_questions.md), which no command can reach.

### `--range START-END`

Disassemble a run of commands in one go.

```bash
uv run gauntlet_disasm.py soundrom.bin --range 0x43-0x49 --csv hw_docs/soundcmds.csv
```

### `--all`

Disassemble every command that has sequence data. Long. Redirect it to a file.

### `--score N`

Lay a sound's channels out side by side against a time axis, tracker-style. This
is the view that makes an arrangement legible.

```bash
uv run gauntlet_disasm.py soundrom.bin --score 0x42 --csv hw_docs/soundcmds.csv
```

```
    Time | Ch1 (YM)    | Ch2 (YM)    | Ch3 (YM)    | Ch4 (YM)    | Ch5 (YM)    |
---------+-------------+-------------+-------------+-------------+-------------+
   0.00s | --- Q       | B4  Q       | G4  Q       | E4  Q       | E2  Q       |
   0.36s | B5  8th     | --- H       | --- H       | --- H       | --- H       |
   0.55s | A5  8th     |   |         |   |         |   |         |   |         |
```

A `|` continues a note that is still sounding. `---` is a rest. The times use the
same mean model as `--cmd`, so they are close and not exact.

---

## Exporting

### `--midi N` and `--midi-out FILE`

Write a sound out as a Standard MIDI File, one track per channel. The default
output name is `command_0xNN.mid`.

```bash
uv run gauntlet_disasm.py soundrom.bin --midi 0x3B --midi-out theme.mid --csv hw_docs/soundcmds.csv
```

```
Exported command "Gauntlet II Theme Song / Secret Room" as MIDI:
  Channels: 8 | Notes: 185 | Est. play time: 24.4s (0:24)
```

Pitches use the `MIDI = ROM note + 11` convention from
[Chapter 8](08_sequence_language_time.md). Note values above 97 are outside the
chromatic part of the table, so they are omitted from the MIDI rather than
exported as misleading high notes. Timing is the mean model again, which makes
the export a good structural picture and a poor stopwatch.

### `--speech-wav N`

Synthesize a spoken phrase through the tool's port of MAME's TMS5220 model.
8 kHz output. No compiler needed.

```bash
uv run gauntlet_disasm.py soundrom.bin --speech-wav 0x5A --csv hw_docs/soundcmds.csv
```

```
Speech command 0x5A "NEEDS FOOD, BADLY.":
  LPC data: $94AE (324 bytes)
  Samples: 12200 (1.52s @ 8000 Hz)
  Output: speech_0x5A.wav
```

The renderer plays every phrase at the normal clock, so the 27 phrases with the
squeak flag set come out at the pitch they were recorded rather than the pitch a
cabinet plays them at.

### `--sfx-wav N`

Render a POKEY sound. This is not an approximation of what the ROM does: the tool
executes the ROM's own reset, dispatcher, allocator, and interrupt service, and
captures the register writes the 6502 actually performs.

```bash
uv run gauntlet_disasm.py soundrom.bin --sfx-wav 0x47 --csv hw_docs/soundcmds.csv
```

```
Rendered command 0x47 "Sword":
  Backend: ROM-driven 6502 -> POKEY (237 register writes)
  IRQ services: 49
  Samples: 53115 (1.204s @ 44100 Hz)
```

The "IRQ services" figure is how many interrupts were simulated, and the register
writes are the ROM's own. A second of tail is added so the sound can ring out.

### `--music-wav N`

The same thing on the other chip, with the register writes fed to the bundled
YMFM core. **This one needs the C++14 compiler.**

```bash
uv run gauntlet_disasm.py soundrom.bin --music-wav 0x0D --csv hw_docs/soundcmds.csv
```

```
Rendered command 0x0D "Food Eaten":
  Backend: ROM-driven 6502 -> YM2151/YMFM (463 register writes)
  IRQ services: 116
  Samples: 65442 (1.484s @ 44100 Hz)
```

### `--render-wav N`

Look at the command's handler type and pick the right renderer automatically.
Handy when you do not want to remember which chip a sound uses.

### The batch flags

`--speech-all`, `--sfx-all`, `--music-all`, and `--render-all` export everything
of their kind. Each has a default output directory, overridable with `--out-dir`.

| Flag | Default directory |
|---|---|
| `--speech-all` | `speech/` |
| `--sfx-all` | `sfx/` |
| `--music-all` | `music/` |
| `--render-all` | `rendered/` |

### The output options

| Flag | Effect |
|---|---|
| `--out FILE` | Output path for a single WAV or MIDI export |
| `--out-dir DIR` | Output directory for a batch export |
| `--sample-rate HZ` | WAV rate for POKEY and YM2151 output. Default 44,100. Speech is always 8,000 |
| `--max-seconds S` | Cap on type-7 render length, including loops. Default 30. Raise it for long music, lower it to sample a looping sound quickly |
| `--csv FILE` | Path to the sound command list. Use `hw_docs/soundcmds.csv` |

---

## What the renderers do and do not model

The type-7 WAV path is the strongest claim this tooling makes, so it is worth
being precise about its edges.

**What is the ROM's own work.** The reset routine, the command dispatcher, the
type-7 allocator, the interrupt service at the measured rate, the carried timer
arithmetic, bytecode dispatch, repeats, envelope stepping, priority arbitration,
POKEY joined-mode selection, the YM2151 total-level transforms, keying, and every
hardware register write. All of that is executed rather than reimplemented.

**What is somebody else's model.** The POKEY sound comes from one shared
four-channel emulator. The YM2151 sound comes from the bundled YMFM core, which
is an independent implementation that knows nothing about Gauntlet.

**What is not modelled at all.** The cabinet's analog mixer, its filtering, and
the relative levels of the three sources. Each renderer produces one chip on its
own and normalizes it, so a WAV from this tool is a clean laboratory recording of
one voice group rather than a recording of a machine.

**One thing is arbitrary.** The POKEY's random number generator gets a
deterministic seed, so the three sounds that branch on it always take the same
branch here. On a real board the outcome depends on how long the machine has been
powered up. [Chapter 9](09_sequence_language_opcodes.md) names the three sounds.

---

## Regenerating the catalogs

The `docs/generated/*.csv` files this book cites are produced by the scripts in
`utility/`, and they are the row-level evidence behind most of the numbers in
these chapters. You do not need to run them to read the book. You do need to run
them if you want to verify something yourself, or if you change the analysis.

They differ from the disassembler in three ways.

They are not self-contained. Each one imports `gauntlet_disasm`, so the repository
root has to be on `PYTHONPATH`:

```bash
PYTHONPATH=. uv run --with numpy python utility/rom_table_audit.py soundrom.bin --csv out/type11_speech_catalog.csv
```

They take an explicit output path for every catalog they generate, and most
generate several. Running one without those paths prints a usage message naming
all of them.

Several need reference sources as well as the ROM, because they check the ROM's
behaviour against an independent implementation. The pitch audit wants the YMFM
sources under `ymfm/src/`; the timing audit wants MAME's TMS5220 device core,
which is in `mame_refs/`:

```bash
PYTHONPATH=. uv run --with numpy python utility/timing_clock_audit.py soundrom.bin \
  --clock-csv out/timing_clock_catalog.csv \
  --cycle-csv out/timing_cycle_catalog.csv \
  --duration-csv out/timing_duration_trace_catalog.csv \
  --loop-csv out/timing_loop_trace_catalog.csv \
  --articulation-csv out/timing_articulation_trace_catalog.csv \
  --tms-ref mame_refs/tms5220.cpp \
  --tms-header-ref mame_refs/tms5220.h
```

Every one of these scripts validates a set of instruction-byte anchors against
the ROM before it writes anything, and refuses to produce output if an anchor
does not match. That is deliberate: a catalog is only meaningful if the bytes it
was derived from are the bytes you have. If a script complains about an anchor,
check your ROM image before you check the script.

The complete set of invocations, with every argument, is in
[`docs/09_analysis_method.md`](../docs/09_analysis_method.md).
[`docs/generated/README.md`](../docs/generated/README.md) says which script
produces which file and what each file contains.
