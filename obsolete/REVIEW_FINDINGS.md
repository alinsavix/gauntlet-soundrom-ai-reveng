# Validation Review of Gauntlet Sound ROM Documentation

**Date**: 2026-05-01
**Method**: Fresh radare2 disassembly compared against REPORT.md, REPORT_SUMMARY.md, MEMMAP.md.

This document collects errors, inconsistencies, missing knowledge, and undocumented
corner cases found during a thorough re-review of the project documentation.

---

## Executive Summary

Significant findings, in rough order of impact:

1. **Commands 0x03, 0x06, 0x07 are NOT "silently ignored"** — they're special
   status-query NMI handlers. Cmd 3 returns coin/LED state ($44), cmd 6 echoes
   the max-command sentinel ($DB = 219), cmd 7 returns error flags ($02) AND
   re-arms two watchdog bits. The REPORT explicitly listed these as "unknown
   purpose" but the answer is in the ROM.

2. **`error_flags` ($02) bit semantics are documented wrong**. Bits 0 and 2 are
   not RAM/general errors — they're heartbeat watchdog bits set by NMI cmd 7
   and cleared by main_loop / IRQ. Bits 3-7 (RAM page errors, 3 ROM-checksum
   regions) are not documented at all.

3. **Opcode jump table mismapping affects gauntlet_disasm.py**. ROM has
   opcode 0x8C → SET_VIBRATO at $51E2; the doc and disassembler say
   CLR_CTRL_BITS at $51CB. ROM has 0x9B → CLR_CTRL_BITS at $51CB; the doc
   and disassembler call it "SET_VAR_NAMED". A "SET_VAR_NAMED" opcode does
   not exist. Both bytes 0x8C and 0x9B occur ~50 times each in real music
   sequences, so the disassembler mislabels them.

4. **Music sequence data starts at 0x873D, not 0x8700**. The 60 bytes
   0x8700-0x873C are still part of `music_seq_lengths`. Multiple table sizes
   in MEMMAP are off by 2-3x (sfx_priority is 182B not 62B; music tables are
   141B not 219B; music_seq_ptrs/lengths are 378B not 184B).

5. **`hw_channel_types[YM2151] = 0x02, not 0x03`**. Verified by reading the
   table directly and by the seq_var_classifier and channel_state_machine
   testing against `CMP #$02`.

6. **Hardware register $1031 is undocumented** (set/cleared around TMS5220
   streaming in `init_sound_state` and `sound_status_update`). Possibly
   aliased to $1030 with different bit semantics.

7. **NMI bulk-data path (PATH A) is dead code** — `nmi_mode_flag` ($0213) is
   only ever written as 0xFF, so the `(nmi_buffer_ptr),Y` path at the top of
   the NMI handler never executes.

8. **`sound_status_update` is far more complex than documented**: it's a
   state machine that handles TMS5220 reset countdown, ready-watchdog,
   sequence streaming, music kickoff via the TMS5220 "Speak External" command
   ($60), speech queue dequeue, and idle-detection re-init.

9. **`speech_queue_enqueue` priority pre-emption flushes the queue** before
   inserting a higher-priority command. Currently-streaming speech keeps
   playing, but everything queued behind it is dropped.

10. **`clear_sound_buffers` does full hardware re-init**: POKEY AUDF/AUDC/
    AUDCTL/SKCTL writes, YM2151 KEY-OFF for all 8 channels, plus the doc's
    documented buffer clearing. The "Zero buffers" name is a major
    understatement.

11. **`pokey_update_registers` and `pokey_write_registers` are one function**,
    not two. Only one entry point at $4DFC; no JSR or branch targets $4E1B.

12. **`channel_list_init` builds a 199-record pool**, not 30. The state
    record area at $093D+ is dynamically allocated for sequence chaining
    (PUSH_SEQ, PUSH_SEQ_EXT) up to ~199 records deep.

13. **The `$13` "music filter threshold" affects POKEY SFX too**, not just
    music. Setting `$13 = 0xF0` (silent mode via cmd 0x01) silences all
    POKEY channels because their max status (priority * 4 + 1 = 61) is
    below 0xF0.

14. **`handler_type_3` has 4 sub-targets**, not 1. Its dispatch table at
    $5FA0 overlaps the NMI dispatch table at $5FA2 — handler_type_3 has one
    extra entry prepended ($41E6 = clear_sound_buffers). Only the first
    entry is reachable in practice (cmd 0).

15. **`handler_stop_sound` does double-indirection**: parameter is another
    command number; the handler looks up that command's parameter (the
    actual sound ID) and stops channels playing it. Cmd 0x21 stops the
    sound played by cmd 0x20, etc.

16. Many small things: bit-7 of music_flags swaps the TMS5220 oscillator
    pitch on a per-command basis (audible pitch shift); seq_var_classifier
    index 5 reads POKEY $180A (hardware random number generator); $5874-$5893
    is referenced data (zero-envelope used by init_sound_state), not
    "padding"; the table at $6559 (handler_match) is at $6559 not $655C
    as the doc claims; sfx_data_ptrs A/B split is by high bit of offset,
    not "primary/alternate" semantic; etc.

The full list (with assembly evidence) is below. Total: **~50 distinct issues**.

---

## 1. Errors / corrections

### 1.1 `error_flags` ($02) bit definitions are wrong/incomplete

**Documented (MEMMAP.md and REPORT_SUMMARY.md):**
> 0x02 | error_flags | Error flags: bit 0=RAM error, bit 1=YM2151 timeout, bit 2=general error

**Actual usage** (verified by tracing every read/write of `$02`):

| Bit | Mask | Meaning | Set by | Cleared by |
|-----|------|---------|--------|------------|
| 0 | 0x01 | "main_loop alive" watchdog (set by NMI 2 reporting, cleared each main_loop iter) | NMI handler 2 (`$44AD`) | `main_loop` (`$4104`) |
| 1 | 0x02 | YM2151 timeout (255 wait cycles exceeded) | `ym2151_wait_ready` (`$5005`) | `clear_sound_buffers` (`$4284`) |
| 2 | 0x04 | "IRQ alive" watchdog (set by NMI 2 reporting AND init timeout, cleared each IRQ) | `init_main` timeout (`$40C2`), NMI 2 (`$44AD`) | IRQ handler (`$418E`) |
| 3 | 0x08 | RAM walking-bit failed for page 8+ | `ram_error_handler` (`$4151`) | (never) |
| 4 | 0x10 | RAM walking-bit failed for pages 2-7 (this path **overwrites** $02, doesn't OR) | `ram_error_handler` (`$414B/$4153`) | (never) |
| 5 | 0x20 | ROM checksum failed for region 0xC000-0xFFFF | `checksum_ram` (`$417C`) | (never) |
| 6 | 0x40 | ROM checksum failed for region 0x8000-0xBFFF | `checksum_ram` (`$417C`) | (never) |
| 7 | 0x80 | ROM checksum failed for region 0x4000-0x7FFF | `checksum_ram` (`$417C`) | (never) |

The docs map bits 0/1/2 incorrectly (bits 0 and 2 are heartbeats not "RAM error"/"general error"),
and don't mention bits 3-7 at all.

NMI handler 2 (`$44A8`) reads $02, sends it to the main CPU as a status report,
then immediately re-arms bits 0 and 2 via `LDA $02 / ORA #$04 / ORA #$01 / STA $02`.
Main loop and IRQ then race to clear them — if main_loop has stalled, bit 0 stays set;
if IRQ has stalled, bit 2 stays set. This is a watchdog the main CPU can poll.

### 1.2 `ram_error_handler` ($4142) detail

The handler has three paths, but the third one **overwrites** $02 (LDA #$10/STA $02),
clobbering any previously set error bits when X is in range [2,7]. For X >= 8 it OR's
in bit 3 instead, preserving prior bits. For X == 1 (stack page), it jumps to a hard
error infinite loop at $4157 (`STA $1000` with A=$10, then `JMP $`).

### 1.3 `checksum_ram` is checking ROM, not RAM

Despite the name, `checksum_ram` (0x415F) is called three times in `init_main` with
arguments that cause it to checksum **ROM** regions, not RAM:

```
LDX #$40                    ; X = page 0x40
LDA #$80; JSR $415F          ; sums 64 pages from 0x40-0x7F (ROM 0x4000-0x7FFF)
LDA #$40; JSR $415F          ; sums 64 pages from 0x80-0xBF (ROM 0x8000-0xBFFF)
LDA #$20; JSR $415F          ; sums 64 pages from 0xC0-0xFF (ROM 0xC000-0xFFFF)
```

Each call sums 16K of bytes and checks if the total equals 0xFF (single-byte additive
checksum). The mask in A (0x80, 0x40, 0x20) selects which error bit to set on failure
(into bits 7, 6, 5 of $02).

The function name "checksum_ram" is misleading. Better name: `checksum_region` or
`rom_checksum`. The data passes are not "RAM/ROM integrity" — they are specifically
**ROM checksum** of the three 16K banks of the 48K ROM.

### 1.4 `clear_sound_buffers` does much more than its name suggests

The function (0x41E6) does (verified by full disassembly):

1. PHP/SEI to disable interrupts during init
2. JSR `channel_list_init` (rebuild free segment-record list)
3. Clear output buffer pointers ($0224, $0225, $0226)
4. Clear speech queue pointers ($0832, $0833)
5. Clear linked-next array $07E6+X for X=0..0x29 (42 entries — see issue 1.5)
6. Clear five state arrays (status $0390, base_freq_lo $0282, base_freq_hi $02A0, base_volume $0408, dist_mask $0642) for X=0..0x1D (30 entries)
7. **Initialize POKEY hardware**: writes 0 to AUDCTL ($1808) and AUDFx/AUDCx for all 4 channels ($1800-$1807). Also writes 0 then 3 to SKCTL ($180F). The POKEY init at offset $0F via `STA ($08,X)` is unusual and **not documented** anywhere.
8. **Initialize YM2151 hardware**: turns off all 8 channels by selecting register 0x08 (KON) and writing channel numbers 7..0 to silence each.
9. Clear YM2151 timeout flag (bit 1 of $02)

The doc summary says "Zero all sound channel buffers and build free-channel list" — this
massively understates what the function does. It's effectively a "cold reset all sound
hardware + clear state" routine.

### 1.5 The `$07E6` array is cleared with 42 entries, not 30

In `clear_sound_buffers`:
```
LDX #0x29       ; X = 41
.loop: STA $07E6,X
       DEX
       BPL .loop
```

This zeros 42 bytes ($07E6 through $080F). The MEMMAP documents `$07E6+X` (chan_linked_next)
as a 30-entry array (X=0..29 → $07E6..$0803). The clear loop overwrites 12 extra bytes
into the work area (which starts at $0810). Either:
- the array is actually 42 entries (and MEMMAP undercounts), or
- the cleanup is sloppy (zeros work-area bytes that don't matter because they get
  rewritten).

The next bytes after `$0803` are `$0804` through `$080F`, which MEMMAP doesn't show as
having any specific purpose (gap before work_channel_index at `$0810`). I believe the
loop uses 0x29+1=42 because it needs to also zero the small headroom past the channel
arrays — but this should be documented.

### 1.6 `reset_handler` size

REPORT_SUMMARY.md lists reset_handler as "46" bytes; it's actually 12 bytes
(0x5A25-0x5A30). The 4 zero bytes at 0x5A31-0x5A34 are padding before the YM2151
frequency table at 0x5A35.

### 1.7 IRQ handler clears bit 2 of $02 unconditionally before checking init_complete

The IRQ handler ($4187) flow:
1. PHA/TXA/PHA, CLD, STA $1830 (IRQ ack)
2. **Always** clears bit 2 of $02 (heartbeat watchdog)
3. THEN checks $01 (init_complete_flag): if 0, INC $00 and exit (no audio)

So the heartbeat watchdog runs even before init is complete — main CPU can rely on
bit 2 being cleared as soon as the first IRQ fires.

### 1.8 BRK detection in IRQ uses stack-relative read

The BRK check (`AND #$10` at 0x41A1) works by reading the saved processor flags from
the stack. After PHA (A) / TXA / PHA (X), the original P register pushed by the IRQ
sequence is at SP+3 in zero-page-relative terms. The code does `TSX / LDA $0103,X`
to read it. This is subtle and worth documenting — most readers wouldn't know that the
IRQ handler reads back the pushed P register from the stack.

If BRK is detected, the handler does NOT return via RTI — it resets the stack
(`LDX #$FF / TXS`) and `JMP $40EC` which re-enters main_loop initialization at the
`init_sound_state` step. This effectively recovers from a BRK by re-initing.

### 1.9 `channel_list_init` builds 199-record list, not 30

The function (0x4295) iterates X from 2 up to 199 (CPX #$C8 = 200), writing each
channel's "next" link. The exit clears the last record's link to mark end-of-list.
Result: a free list of channel state records (0x093D + (n-1)*4, n=1..199).

The MEMMAP only mentions "Channel state records (0x093D+)" without a count. The actual
pool is **199 records**, not 30. These records support sequence chaining/PUSH_SEQ
operations and are allocated/freed dynamically as music plays.

The earlier exit condition (`CMP $16; BEQ` when high byte == 0x0F) is a safeguard
that never triggers in practice, since CPX #$C8 hits first.

### 1.10 NMI dispatch behavior for commands 3, 6, 7 — REPORT IS WRONG

REPORT_SUMMARY.md says:
> Commands 0x03, 0x06, 0x07: Map to handler type 0xFF (no handler, silently ignored).
> Whether these are reserved placeholders, development artifacts, or intercepted by
> the main CPU before reaching the sound board is unknown.

This is **incorrect**. Commands 3, 6, 7 are **special status-query commands** that
trigger immediate NMI dispatch handlers via `nmi_validation_table` ($5D0F):

| Cmd | $5D0F[cmd] | NMI Dispatch | Effect |
|-----|------------|--------------|--------|
| 3 | 0x00 | $843F | Read coin/LED state ($44) → main CPU |
| 6 | 0x01 | $44B8 | Echo back 0xDB (max valid command count = 219) → main CPU |
| 7 | 0x02 | $44A8 | Read error flags ($02) → main CPU + re-arm bits 0/2 of $02 (watchdog) |

These commands take a different code path than buffered commands. They never reach
the `command_dispatcher` (which would reject them via `cmd_type_map[3,6,7] = 0xFF`).
Instead, the NMI handler intercepts them and dispatches directly via the table at
$5FA2.

The watchdog mechanism for $02 bits 0 and 2 (see issue 1.1) is the reason these
commands exist: the main CPU sends command 7, sees the error flags, then can
later send another command 7 to verify whether main_loop and IRQ are still alive
(by checking which heartbeat bits got cleared since last query).

### 1.11 NMI dispatch handler 0 ($843F) reads $44 (coin/LED)

This handler was never explained. It's `LDA $44 / JSR $44C8 / JMP $581E` — it reads
the current coin counter / LED output byte ($44) and sends it to the main CPU via
`$1000`. So command 3 lets the main CPU poll the sound board's view of the coin slot
inputs and LED state.

### 1.12 `nmi_validation_table` (0x5D0F) classification — DOC IS WRONG

REPORT_SUMMARY.md says:
> 0x5D0F | nmi_validation_table | NMI command validation (0xFF=store in buffer, 0x00-0x02=immediate NMI dispatch)

The actual NMI handler test is `BPL` after `LDA $5D0F,X` — i.e., bit 7 of the table
byte. The classification is:

| Value | Bit 7 | Behavior |
|-------|-------|----------|
| 0x80-0xFF | set | Store command byte in `cmd_circular_buf` ($0200,Y) for later main-loop dispatch |
| 0x00-0x02 | clear | Immediate NMI dispatch via $5FA2 + (val * 2) |
| 0x03-0x7F | clear | Treated as invalid: writes default `0xDB` sentinel into the buffer (which `command_dispatcher` will silently reject), then exits |

The doc's "0xFF means store in buffer" should be "any byte with bit 7 set means store
in buffer." In practice, only 0xFF and 0x00/0x01/0x02 appear in this table, so the
distinction is academic — but the actual test is bit 7, not equality with 0xFF.

### 1.13 NMI handler PATH A is dead code

The NMI handler at 0x57B0 first reads `$0213` (nmi_mode_flag) and branches based on it:

- `$0213 == 0`: PATH A — read $1010 and write to `(nmi_buffer_ptr + state),Y`
  via $04-$05 indirect pointer. Includes elaborate bit-7-of-counter wraparound.
- `$0213 == 0xFF`: PATH B — validate and dispatch via $5D0F table (the documented path)
- Other: discard

`$0213` is **only ever set to 0xFF**:
- `init_main` sets it to 0xFF at 0x40D2 (`STX $0213` with X=0xFF)
- NMI dispatch handler exit at 0x44C3 sets it to 0xFF (`LDA #0xFF / STA $0213`)

There is **no path** in code that sets `$0213` to 0. So PATH A — the
"nmi_buffer_ptr at $04-$05" mechanism — is dead code that never executes. It's
likely a vestige of a planned bulk-data-upload mode (e.g., for streaming audio data
into RAM via NMI-driven writes). The zero-page slots `$04-$05` (`nmi_buffer_ptr`)
and `$0212` (`nmi_buf_state`) are similarly never used in practice.

### 1.14 Hardware register $1031 is undocumented

The MEMMAP and REPORT_SUMMARY do not mention `$1031`. It is read+written in:

- `init_sound_state` ($5846/$584B): `LDA $1031 / ORA #$80 / STA $1031` — set bit 7
- `sound_status_update` when TMS5220 not ready ($58CD/$58D3): same — set bit 7
- `sound_status_update` after writing speech data ($5929/$592A): `LDA $1031 / AND #$7F / STA $1031` — clear bit 7

The pattern (set bit 7 before TMS5220 op, clear it after) suggests it controls some
kind of TMS5220 enable/strobe signal or output-buffer-busy indicator.

It might also be aliased to $1030 (low addr bit not decoded) — in which case writes
to $1030/$1031 share semantics. Worth checking against the schematic.

### 1.15 `init_hardware_regs` ($5A0B): writes 5 magic bytes to "main CPU output"

```
LDA #$FF / STA $1003   ; alias of $1000?
LDA #$33 / STA $1002   ; alias of $1000?
LDA #$00 / STA $100B   ; alias of $1000?
LDA #$22 / STA $100C   ; alias of $1000?
LDA #$0F / STA $1000   ; main CPU output
```

If the addresses $1002/$1003/$100B/$100C really are aliases of $1000 (low 4 bits not
decoded, as the doc claims), this writes the 5-byte sequence `FF 33 00 22 0F` to the
main CPU output port in rapid succession. The meaning of this pattern is undocumented
— it may be an init handshake the main CPU consumes byte-by-byte.

If the addresses are NOT aliases (the alias claim is unverified — each is written
exactly once, only here), each is a separate hardware register with its own purpose.

The fact that the doc lists these as "data_output_alias_N" without verification, and
that the init values look like specific magic bytes, suggests the alias claim should
be reviewed against the schematic.

### 1.16 `sound_status_update` is far more complex than documented

REPORT/MEMMAP describe `sound_status_update` ($5894) as "Stream speech data to TMS5220
(0x1820), manage speech queue at 0x0832-0x083B." It actually does:

1. **TMS5220 reset countdown** via `$33`: when `($33 - frame_counter) == 8`, write
   `STA $1032` to reset the TMS5220 chip. This is a periodic mid-operation reset
   mechanism, not just at boot.
2. **TMS5220 ready watchdog** via `$30`: every other frame, XOR `frame_counter >> 1`
   with `$30`. If they match, JMP back into `init_sound_state` ($5833). When `$30`
   has bit 7 set (initial state $FF), increment instead of XOR.
3. **TMS5220 not-ready recovery**: when bit 5 of $1030 is clear, set $30 = $FF, set
   bit 7 of $1031, and either dequeue speech queue (if $2F == 0) or stream sequence
   bytes.
4. **Speech queue dequeue**: if no active stream (`$2F == 0`) and the queue is
   non-empty, advance `$0832`, load command from `$0834,Y`, and JMP into
   `music_speech_handler` ($5939, **not** $5932) to start the new stream.
5. **Sequence streaming**: when `$2F` is the magic value `$FF` (set when length
   expires), read next byte from `($2B),Y` and write to TMS5220 ($1820). When length
   expires, sets timer `$2A = $19` and resets `$2F = $11`.
6. **Music kickoff special**: when `$2F == $80` (just after `music_speech_handler`
   set it), the INY makes Y=$81. The handler writes `$60` to TMS5220 ($1820)
   and sets `$2F = $FF`. The byte `$60` is the TMS5220 "Speak External" command,
   meaning the TMS5220 will subsequently consume LPC bytes from its FIFO.

The `$2F` "active flag" doc only mentions states 0x00/0x80/0xFF but the actual
states are 0x00 (idle), 0x11 (just-restarted after length expire), 0x80 (music
kickoff requested), 0x81 (music kickoff in progress, transient), 0xFF (streaming),
plus arbitrary values seen during the decrement-and-write-zero path.

### 1.17 `music_speech_handler` dispatch has TWO entry points

REPORT shows `music_speech_handler` at $5932 as the entry. But the function actually
has two entries:

- **$5932**: Main entry (called from `handler_type_11` at $4441 and from `seq_op`
  music command). Checks `$2F` first — if active, JMP to `speech_queue_enqueue`
  ($59E2) to queue. If idle, fall through to $5939.
- **$5939**: "Force start, skipping queue check" entry, used by `sound_status_update`
  when the TMS5220 finishes a phrase and dequeues the next command. This bypasses
  the active-flag check because we know the TMS5220 just became idle.

The doc treats $5932 and $5939 as the same routine, but they have different semantics
for callers.

### 1.18 `music_speech_handler` writes `$1033` based on bit 7 of `$643F[cmd]`

The handler reads `music_flags[cmd]` ($643F,Y), and if bit 7 is set, sets bit 7 of
`$34` (and clears it otherwise). Then writes the resulting `$34` to `$1033`
(speech_squeak — TMS5220 oscillator frequency).

**Effect**: bit 7 of music_flags selects between two TMS5220 oscillator frequencies
on a per-command basis. The doc mentions "bit 7: special mode" but doesn't connect
this clearly to the TMS5220 oscillator pitch change.

This means **every** music/speech command can swap the TMS5220 voice pitch — making
some phrases sound higher or lower. This is a real audible effect that's not
documented.

### 1.19 `music_speech_handler` volume calculation details

The volume calc at $59A8-$59DD applies bit-shifted reductions of `music_flags[cmd]`
low 4 bits to BOTH music and effects volume:

- `music_volume_out = max(0, ($29 & 0x07) - (flags_low4 >> 1))`
- `effects_volume_out = max(0, (($29 & 0x18) >> 3) - (flags_low4 >> 2))`

Then combines: `$1020 = ($28 & 0xE0) | (eff << 3) | mus`

The doc says "bits 0-3: volume calculation params" but doesn't specify the formula.
Notable: speech volume from `$28` is **not reduced** — only effects and music are
attenuated when music plays.

### 1.20 `speech_queue_enqueue` has priority pre-emption that flushes the queue

REPORT mentions the priority comparison but **not** that higher-priority commands
flush the entire queue before being enqueued:

```
CPX $35              ; compare priority X with current $35
BCC exit             ; X < $35: too low priority, drop silently
BEQ store_normal     ; X == $35: queue normally
; X > $35: HIGHER priority — pre-empt
PHA
LDA $0833 / STA $0832  ; advance read ptr to write ptr (FLUSH QUEUE)
PLA
; fall through to normal store
```

So a higher-priority speech command **discards all pending lower-priority
speech** before entering the queue. The currently-streaming speech is NOT killed
— but everything queued behind it is.

This subtlety affects gameplay perception (e.g., critical "WIZARD NEEDS FOOD"
warnings might preempt queued chat).

### 1.21 `handler_type_3` has 4 sub-targets, not 1

REPORT says handler_type_3 only handles command 0. But the dispatch logic at $4369
loads from `$5FA0 + (param * 2)`, and there are **4 valid entries**:

| Param | $5FA0+param*2 | Target | Function |
|-------|---------------|--------|----------|
| 0 | $5FA0 | $41E6 | clear_sound_buffers |
| 1 | $5FA2 | $843F | (NMI 0) read $44 to main CPU |
| 2 | $5FA4 | $44B8 | (NMI 1) echo $DB to main CPU |
| 3 | $5FA6 | $44A8 | (NMI 2) read error flags + watchdog |

`$5FA0` is the SAME data block as the NMI dispatch table at `$5FA2` — they OVERLAP
(handler_type_3 has one extra entry at $5FA0 prepended).

In practice only command 0 maps to handler_type_3 (with param 0 → clear_sound_buffers).
Params 1-3 are never reached via the dispatcher, but the code paths exist as a
ROM-saving overlap with the NMI dispatch table.

### 1.22 `handler_type_8` overflow flag

When the output buffer is full, sets `$0226 = $80` (bit 7 = overflow indicator).
The overflow flag is never explicitly cleared by code — it stays sticky. The
main_loop's writer loop at $4127 checks for empty buffer (read == write ptr) but
doesn't react to or clear the overflow flag. The flag exists as a status indicator
the main CPU could theoretically read, but no NMI handler sends it.

So `output_overflow_flag` is set but apparently never observed. Possibly a debug
artifact or intended for an unimplemented status query.

### 1.23 `handler_stop_sound` ($438D) double-indirection

The handler does NOT directly stop a sound named in its parameter. It interprets
the parameter as **another command number**, looks up that command's handler type
(must be type 7) and parameter (the actual sound ID), and stops channels playing
that sound ID.

This means commands 0x21, 0x2F, 0x39 each "stop" the sound that the previous
command (0x20, 0x2E, 0x38) plays:

- `$5EC5[0x21] = 0x20` → stop the sound that cmd 0x20 plays
- `$5EC5[0x2F] = 0x2E` → stop the sound that cmd 0x2E plays
- `$5EC5[0x39] = 0x37` → stop the sound that cmd 0x38 plays (note: 0x37, not 0x38, so this is a separate sound from the immediately-preceding command)

This indirection is not described anywhere.

### 1.24 `handler_type_0` shifts the param BY 2, not by 4

REPORT_SUMMARY says "handler_type_0 | Parameter shift (ASL A × 2)" — that's
ambiguous. The actual code is:

```
0x4347: ASL A   ; *2
0x4348: ASL A   ; *4
0x4349: STA $13 ; music_filter_threshold = param * 4
```

So the parameter is multiplied by 4, then stored as the music filter threshold.
The doc reads "ASL A × 2" which could mean either "ASL A done twice" (correct) or
"ASL A is parameter × 2" (incorrect). Worth clarifying.

The threshold filters music commands: `handler_type_11` rejects commands whose
`music_tempo[cmd]` ($64CC) is less than `$13`.

- cmd 0x01 (param 0x3C → $13 = 0xF0): "silent mode" — only commands with very high
  tempo values pass
- cmd 0x02 (param 0x00 → $13 = 0x00): "noisy mode" — all commands pass

This filter mechanism is not explained in REPORT.

## 2. Sequence engine errors

### 2.1 OPCODE JUMP TABLE — multiple addresses are mis-mapped to opcodes

The opcode jump table at $507B is **2 bytes off** in REPORT_SUMMARY for opcodes
0x8C-0x8F. The doc and `gauntlet_disasm.py` agree with each other but **both
disagree with the actual ROM**. Verified by direct reading of the table bytes
(`px 32 @ 0x507B`) and decoding the handler at each target.

Actual ROM-correct mapping:

| Opcode | Address | Operation |
|--------|---------|-----------|
| 0x80 | $5173 | SET_TEMPO |
| 0x81 | $516A | ADD_TEMPO |
| 0x82 | $5192 | SET_VOLUME |
| 0x83 | $517A | SET_VOLUME_CHK |
| 0x84 | $51AE | ADD_TRANSPOSE |
| 0x85 | $51AA | NOP_FE_CHECK |
| 0x86 | $515F | SET_FREQ_ENV |
| 0x87 | $5154 | SET_VOL_ENV |
| 0x88 | $50F1 | RESET_TIMER |
| 0x89 | $514B | SET_REPEAT |
| 0x8A | $51B3 | SET_DISTORTION (STA $0642,X) |
| 0x8B | $51B7 | SET_CTRL_BITS (OR into $03EA,X with YM-specific bit-twiddling) |
| 0x8C | $51E2 | **SET_VIBRATO** (STA $0660,X = chan_vibrato_depth) |
| 0x8D | $51E6 | **PUSH_SEQ** |
| 0x8E | $5214 | **PUSH_SEQ_EXT** |
| 0x8F | $523F | **POP_SEQ** |
| 0x90 | $54CC | SWITCH_POKEY |
| 0x91 | $54E5 | SWITCH_YM2151 |
| 0x92-0x95 | $4719 | NOP |
| 0x96 | $54F4 | QUEUE_OUTPUT |
| 0x97 | $54F9 | RESET_ENVELOPE |
| 0x98 | $4719 | NOP |
| 0x99 | $5515 | SET_SEQ_PTR |
| 0x9A | $5524 | PLAY_MUSIC_CMD |
| 0x9B | $51CB | **CLR_CTRL_BITS** (EOR #FF + AND $03CC,X with YM-specific path) |
| 0x9C | $54B1 | FORCE_POKEY |
| 0x9D | $5535 | SET_VOICE |
| 0x9E | $5613 | YM_LOAD_ENV (CLC; ADC #$24; ...) |
| 0x9F | $5655 | YM_LOAD_REG (CLC; ADC #$29; ...) |
| 0xA0 | $568A | (looks like YM_SET_ALGO or ADD_FREQ — `LDY $17`) |
| 0xA1 | $5715 | YM_DETUNE_NEG / apply detune |
| 0xA2 | $56CB | (regop) |
| 0xA3 | $56AF | (regop / sub_detune) |
| 0xA4 | $5271 | VAR_LOAD |
| 0xA5 | $4719 | NOP |
| 0xA6 | $5703 | SHIFT_LEFT |
| 0xA7 | $56DC | FREQ_ADD |

REPORT-incorrect entries:
- **DOC 0x8C → $51CB (CLR_CTRL_BITS)**: actually $51CB is opcode 0x9B; opcode 0x8C is at $51E2 (SET_VIBRATO).
- **DOC 0x8D → $51E2 (SET_VIBRATO)**: actually $51E2 is opcode 0x8C.
- **DOC 0x8E → $51E6 (PUSH_SEQ)**: actually $51E6 is opcode 0x8D.
- **DOC 0x8F → $5214 (PUSH_SEQ_EXT)**: actually $5214 is opcode 0x8E.
- **DOC: opcode 0x8F = POP_SEQ at unspecified address**: actually 0x8F → $523F.
- **DOC 0x9B → $51CB (SET_VAR_NAMED)**: actually $51CB is **CLR_CTRL_BITS**, not "set named variable". The same address is documented twice with different names (once for opcode 0x8C, once for 0x9B).
- DOC 0x9E → $5614 (off by one — actual table entry resolves to $5613, which is the CLC instruction; doc skips the CLC).

The disassembler script `gauntlet_disasm.py` has the same wrong mapping (opcode 0x8C→CLR_CTRL_BITS, 0x9B→SET_VAR_NAMED) hardcoded at lines 2507/2522. Music sequences that use bytes 0x8C or 0x9B as opcodes are misinterpreted.

I confirmed bytes 0x8C and 0x9B do appear in actual sequence data:
- 0x8C: 54 occurrences in music region (0x8700-0xACFF), 9 in SFX region
- 0x9B: 50 occurrences in music region, 2 in SFX region

So this is not an academic error — it directly affects MIDI export accuracy and any tracker-style score view.

### 2.2 No "SET_VAR_NAMED" opcode exists

The table has no entry that performs "set named variable via classifier". The
opcode 0x9B at $51CB is `CLR_CTRL_BITS`. The "SET_VAR_NAMED" name in the doc
appears to be a fabrication — there's no opcode that does what the doc describes
(setting a named variable through `seq_var_classifier`).

The variables ARE accessed via `seq_var_classifier` ($5444), but only by the
conditional branch opcodes (0xB5-0xB8, 0xB9-0xBA) and a few ALU opcodes. Setting
a named variable directly is not in the opcode set.

### 2.3 `seq_var_classifier` mapping for index 0-5 is undocumented in detail

The classifier ($5444) maps indexes:

| Index | POKEY ch ($081D=0) | YM2151 ch ($081D=2) |
|-------|--------------------|--------------------|
| 0 | chan_base_volume ($0408) | (no-op — just LDY $11 / RTS, A unchanged) |
| 1 | chan_tempo ($05CA) | chan_tempo ($05CA) |
| 2 | chan_transpose ($05E8) | chan_transpose ($05E8) |
| 3 | chan_reg_shadow ($07C8) (fallback) | chan_vol_env_pos ($049E) |
| 4 | chan_reg_shadow ($07C8) (fallback) | chan_base_volume ($0408) |
| 5 | **POKEY $180A (RANDOM)** | **POKEY $180A (RANDOM)** |
| 6-21 | seq_var_workspace ($0018+(idx-6)) | same |
| 22+ | chan_reg_shadow ($07C8) | same |

**Notable**: Index 5 reads from POKEY's random number generator ($180A). This is
hardware-direct random access for sequence-level randomization (e.g., random pitch
variation, random sample selection). Not documented anywhere.

YM2151 index 0 is a NOP (returns A unchanged). This is asymmetric and worth
documenting.

### 2.4 `seq_opcode_dispatch` ($5029) channel-kill on bad opcode

The dispatcher checks `CMP #$BB`; if A >= 0xBB, it kills the channel by setting
`$0228,X = $FF` and returns with carry clear. This is documented, but worth
emphasizing: any byte >= 0xBB encountered as an opcode kills the channel.

This is the "end-of-sequence" behavior — composers used 0xFF (or any value
>= 0xBB) as a track terminator. Including 0xBB through 0xFE as terminators is
useful information for the disassembler.

### 2.5 `channel_state_machine` channel type detection uses 0x02, not 0x03

The state machine and `seq_var_classifier` test `$081D == 2` for YM2151 channels.
MEMMAP says hw_channel_types values are `0x00=POKEY, 0x03=YM2151`, but the actual
table at $57AC is `00 02 1E 22` — so YM2151 type is **0x02, not 0x03**. The values
0x1E (channel 2) and 0x22 (channel 3) are RAM workspace types.

The MEMMAP claim:
> 0x57AC | hw_channel_types | 8 B | Hardware chip type (0x00=POKEY, 0x03=YM2151)

is wrong on two counts:
1. The size is 4 bytes, not 8 (the table $57AC-$57AF is followed at $57B0 by
   `nmi_handler` code).
2. YM2151 type is 0x02, not 0x03.

### 2.6 `channel_state_machine` BRK-like behavior on dead channels

When `$0228,X == $FF` (active_cmd marker for "dead"), the state machine still
runs the timer but produces no output, and may chain through linked-list cleanup
at `$4809`. Worth documenting as the "channel-cleanup path."

### 2.7 The channel state record pool at $093D+ is used by PUSH_SEQ/PUSH_SEQ_EXT/POP_SEQ

The 199-record pool built by `channel_list_init` (issue 1.9) is consumed by:

- **PUSH_SEQ** (0x8D): allocates a record, saves current `chan_seg_chain_a` ($06BA)
  and `chan_seq_ptr` ($0246/$0264). Sets `chan_seg_chain_a` to the new record's
  index. Loads new sequence pointer from sequence args.
- **PUSH_SEQ_EXT** (0x8E): allocates a record, saves current `chan_seg_chain_b`
  ($06D8), `chan_seq_ptr`, and `chan_ext_chain_ctr` ($06F6) loop counter.
- **POP_SEQ** (0x8F): if `chan_seg_chain_b` ($06D8) is non-zero, decrements the
  loop counter ($06F6); when counter is non-zero, restores the saved seq_ptr
  (looping back). When counter reaches zero, follows the chain to pop the
  saved state and continues past the loop.
- **CHAIN byte (byte 0 == 0x00)**: when the engine reads a byte0==0x00 instead
  of an opcode/note, it treats this as "return from PUSH_SEQ" — pops back to
  the caller's seq_ptr.

The MEMMAP names the channel state arrays `chan_seg_chain_a` ($06BA) and
`chan_seg_chain_b` ($06D8) but doesn't connect them to PUSH_SEQ vs PUSH_SEQ_EXT.

## 3. Other issues / missing knowledge

### 3.1 Hardware register addresses 0x1002, 0x1003, 0x100B, 0x100C

These are claimed as aliases of $1000 in the doc, but each is written exactly
once during `init_hardware_regs` ($5A0B) with specific values (0xFF, 0x33, 0x00,
0x22, 0x0F). The "alias" claim is unverified.

### 3.2 Hardware register $1031 is undocumented

See issue 1.14. Setting/clearing bit 7 of $1031 around TMS5220 streaming.

### 3.3 NMI bulk-data path (PATH A) is dead code

See issue 1.13. Possibly vestigial.

### 3.4 `handler_addr_table` size is 30 bytes, not 32

REPORT_SUMMARY says 32B (16 entries with sentinel). Actual is 30B (15 entries,
no sentinel). The 16th would-be entry overlaps with the first instruction of
`channel_state_machine` at $4651.

### 3.5 The `$5874-$5893` "padding" is actually data referenced by `init_sound_state`

`init_sound_state` ($5833) sets `$2B-$2C = $5874` and `$2D-$2E = $0020` — i.e.,
the 32-byte block at $5874 is loaded as a "fake sequence" of length 32 for the
TMS5220 streaming path.

It IS just `0xFF 0xFF...` bytes (silence/inactive markers), so the "unused
padding" classification in MEMMAP is functionally correct, but the bytes are
explicitly addressed as data. Worth noting that the address $5874 is referenced
in code, even if the data itself is zero/all-FF.

### 3.6 cmd_param_table for stop commands

The values for commands 0x21, 0x2F, 0x39:
- $5EC5[0x21] = 0x20 (stop sound played by cmd 0x20)
- $5EC5[0x2F] = 0x2E (stop sound played by cmd 0x2E)
- $5EC5[0x39] = 0x37 (stop sound played by cmd 0x38 — note: 0x37, not 0x38)

The "stop" is referenced by **command number that plays the sound**, not by sound
ID directly. The handler does double-indirection through cmd_type_map and
cmd_param_table.

### 3.7 `nmi_validation_table` ($5D0F) entries 3, 6, 7 indicate dispatch indices

Confirmed by reading the table:
- $5D0F[3] = 0x00 → NMI dispatch handler 0
- $5D0F[6] = 0x01 → NMI dispatch handler 1
- $5D0F[7] = 0x02 → NMI dispatch handler 2

All other entries are 0xFF (store in buffer).

### 3.8 Inverted logic of init_main bit-4 check

`init_main` checks bit 4 of $1030 (self-test):
- **Bit 4 set** (self-test enabled): ZERO the zero page, JSR irq_ack, JMP main_loop. Skips RAM walking-bit test, ROM checksum, etc.
- **Bit 4 clear** (normal): full walking-bit RAM test on ALL pages 0-15, then 3 ROM checksums.

So self-test mode is the **less thorough** boot path on the sound CPU — because the main CPU is presumably running its own diagnostics in self-test, and doesn't want the sound CPU to also do extensive RAM testing (which would slow boot).

The doc says "RAM Test (conditional): Check bit 4 of 0x1030; If set: Simple clear; If clear: Walking-bit test" which is technically right but worth flagging that the inverted relationship is intentional, not a bug.

### 3.9 The TMS5220 $60 byte = "Speak External" command

`sound_status_update` writes `$60` to $1820 (TMS5220) when `$2F` becomes $80 then
$81 (transient state during music start). This is the TMS5220's "Speak External"
command, which puts the chip in FIFO mode where it consumes LPC bytes from
subsequent writes.

Worth documenting that this is part of the standard TMS5220 init sequence —
the "Speak External" command must be sent before LPC data streaming.

## 4. Data table size errors

Many table sizes in MEMMAP.md and REPORT_SUMMARY.md are off by 2-3x.

### 4.1 SFX tables $6024 and $60DA are 182 bytes, not 62

| Table | Doc size | Actual size | Indexed by |
|-------|----------|-------------|------------|
| `sfx_data_offset` ($5FA8) | ~62B | 62B (62 entries) ✓ | command number |
| `sfx_flags` ($5FE6) | ~62B | 62B ✓ | command number |
| `sfx_priority` ($6024) | ~62B | **182B** (182 entries) | sfx_data_offset value (0-181) |
| `sfx_channel_map` ($60DA) | ~62B | **182B** | sfx_data_offset value |
| `sfx_chain_offsets` ($62FC) | ~180B | 182B ✓ | sfx_data_offset value |

`sfx_data_offset[command]` returns a value 0-181, used to index the
priority/channel_map/chain tables. Multiple commands can share an offset (e.g.,
single-channel SFX have one offset; multi-channel SFX point at chained offsets
that walk the table).

### 4.2 SFX pointer tables $6190 and $6290

`sfx_data_ptrs_a` ($6190) and `sfx_data_ptrs_b` ($6290) are accessed via
`LDA $6190,X / LDA $6191,X` where X is `sfx_data_offset[command]` (0-181).
**The pointer pairs are not aligned to 2-byte boundaries** — they're indexed
by raw byte offset. This is unusual.

Doc claims:
- sfx_data_ptrs_a: ~200B (~100 entries) — actual: 256B (variable-size entries)
- sfx_data_ptrs_b: ~200B — actual: 108B

The actual layout:
- $6190-$628F: 256 bytes (`sfx_data_ptrs_a` + alternates)
- $6290-$62FB: 108 bytes (`sfx_data_ptrs_b`)
- $62FC-$63B1: 182 bytes (`sfx_chain_offsets`)
- (then unused $63A0-$63B1 may be zero padding visible in the bytes)

### 4.3 Music tables (music_seq_index, music_flags, music_tempo) are 141 bytes, not 219

| Table | Doc size | Actual size | Indexed by |
|-------|----------|-------------|------------|
| `music_seq_index` ($63B2) | 219B | **141B** | `cmd_param_table[cmd]` (0-140) |
| `music_flags` ($643F) | 219B | **141B** | parameter (0-140) |
| `music_tempo` ($64CC) | 219B | **141B** | parameter (0-140) |

These tables are indexed by **command parameter** (`$5EC5[cmd]`), not by command
number directly. Music/speech commands (handler type 11) span 141 distinct
commands (0x08, 0x4A-0xD5), with parameters 0-140 mapped directly via
`cmd_param_table`.

The doc's "1 byte/cmd" indexing is wrong — it's "1 byte/param".

### 4.4 Music sequence pointers/lengths (music_seq_ptrs, music_seq_lengths) — sizes wrong

The doc claims:
- `music_seq_ptrs` ($8449): ~184B (~92 entries)
- `music_seq_lengths` ($85C3): ~184B (~92 entries)

Actual:
- `music_seq_ptrs` ($8449): **378 B (189 entries)** = 0x8449 to 0x85C2
- `music_seq_lengths` ($85C3): **378 B (189 entries)** = 0x85C3 to 0x873C

These tables are indexed by `music_seq_index[parameter]`, which has values
ranging 0-188 (max 188).

### 4.5 Music sequence DATA starts at 0x873D, not 0x8700

The doc says music sequence data is at 0x8700-0xACFF. Actually it starts at
0x873D — the bytes 0x8700-0x873C are part of `music_seq_lengths`.

Verified by examining the minimum value across all 189 entries of
`music_seq_ptrs`: the min is 0x873D. So music data must begin at 0x873D.

This means the "music sequence data 0x8700-0xACFF" claim in MEMMAP and the
disassembler's data-extraction code are wrong by 0x3D bytes.

### 4.6 Total ROM space accounting is off

The doc gives this summary:
> 0x4000-0x5CFF: ~7.5 KB Code
> 0x5D00-0x6FFF: ~5 KB Data tables (command dispatch, SFX metadata)
> 0x7000-0x86FF: ~6 KB POKEY SFX sequence data
> 0x8700-0xACFF: ~10 KB YM2151 music sequence data

Per my findings:
- The "code" region 0x4000-0x5CFF is correct, but ends with the duration table
  at 0x5C5F-0x5C8F (envelope tables) and the YM2151 freq table at 0x5A35.
- Data tables span 0x5D00-0x65A8 (cmd dispatch, SFX, music tables).
- The handler_match_table at 0x6559 actually starts at 0x6559 (not 0x655C as
  the doc says — see issue 4.7).
- POKEY SFX data: presumably starts somewhere in 0x6800-0x83FF region.
- YM2151 music data: starts at 0x873D (not 0x8700).

### 4.7 `handler_match_table` is at 0x6559, not 0x655C

REPORT_SUMMARY says `handler_match_table` is at 0x655C. But `handler_type_1` and
`handler_type_2` access it via `$6559,Y` and `$655A,Y` (3-byte interleaved
records starting at $6559). And `handler_channel_control` uses `$655B,X`
(third field).

So the table starts at $6559 with 3-byte records:
- offset 0: index/key field (read by type 1/2)
- offset 1: value field (read by type 1/2)
- offset 2: secondary field (read by handler_channel_control)

The MEMMAP entry at $655C is one byte off from the actual base.

### 4.8 hw_channel_types and hw_channel_config sizes are 4 bytes, not 8

| Table | Doc size | Actual size |
|-------|----------|-------------|
| `hw_ptr_table` ($57A8) | 8B (interleaved) | 8B (4 channels × 2 bytes) ✓ |
| `hw_channel_types` ($57AC) | 8B | **4B** ($57AC-$57AF) |
| `hw_channel_config` ($57AE) | 8B | overlaps with `hw_channel_types[2..3]` and following bytes |

The address $57B0 is the start of `nmi_handler` (target of NMI vector $FFFA).
There is no room for 8-byte tables at $57AC and $57AE — there's only 4 bytes
of space. The values at $57AC-$57AF are: `00 02 1E 22`.

`hw_channel_types` values:
- $57AC = 0x00 (POKEY)
- $57AD = 0x02 (YM2151) — not 0x03 as the doc says!
- $57AE = 0x1E (RAM type 1)
- $57AF = 0x22 (RAM type 2)

The seq_var_classifier and channel_state_machine test against `0x02` for
YM2151 — confirming the type is 2, not 3.

Whether `hw_channel_config` is a separate table or just additional bytes that
happen to be read at $57AE,Y (in handler_stop_chain and YM2151 pipeline) is
ambiguous.

### 4.9 SFX pointer A/B split is by HIGH BIT of offset, not "primary/alternate"

REPORT_SUMMARY says:
> sfx_data_ptrs_a | Primary sound sequence data pointers
> sfx_data_ptrs_b | Alternate sound sequence data pointers

The actual selection in `handler_type_7` at $45B5-$45BF is:

```
TXA          ; X = sfx_data_offset
ASL A        ; bit 7 → carry
TAX
BCS use_b    ; if offset >= 128 (bit 7 set), use _b table
LDA $6190,X  ; else use _a table
```

So the two tables form a single conceptual 182-entry table, split into:
- `$6190` covers offsets 0x00-0x7F (128 entries × 2 bytes = 256 bytes)
- `$6290` covers offsets 0x80-0xB5 (54 entries × 2 bytes = 108 bytes)

There is no "primary vs alternate" semantic — both halves are equal partners,
just split at the high-bit boundary so an 8-bit X register can address each
half by `sfx_data_offset & 0x7F`.

## 5. POKEY pipeline issues

### 5.1 `pokey_update_registers` and `pokey_write_registers` are ONE function

REPORT_SUMMARY lists:
- 0x4DFC | pokey_update_registers | 77B
- 0x4E1B | pokey_write_registers | 77B

These are NOT separate functions. The code from $4DFC to $4E67 is a single
function (108 bytes total), with no JSR or branch targeting $4E1B as an entry
point. There's just code flow from $4DFC straight through.

There's also no JSR $4E1B anywhere in the ROM. The only call site for $4DFC is
the `JMP $4DFC` at $5023 (in channel_dispatcher).

The "two function" claim is a documentation artifact — perhaps the analyst
saw the structure as "orchestrate + write" and split it conceptually, but the
ROM has them inlined as one function.

### 5.2 POKEY init writes magic 0/3 to SKCTL ($180F) — undocumented

In `clear_sound_buffers` at $4234-$4245, the code writes 0 then 3 to POKEY's
SKCTL register at $180F. The pattern is:

```
; Set up indirect pointer to $180F
LDA #$0F; ADC $08; STA $08      ; $08 += 0x0F → $08 now points to $180F

LDX #$00
TXA                              ; A = 0
STA ($08,X)                      ; write 0 to $180F
ADC #$01                         ; A = 1
CMP #$03                         ; not 3 yet
BNE -                            ; loop until A = 3
STA ($08,X)                      ; write 3 to $180F
```

This is part of the standard POKEY initialization sequence (writes 0 to SKCTL
to reset, then 3 to enable normal operation modes). Not documented anywhere in
the project notes.

### 5.3 `pokey_channel_mix` filter check uses `$13` (music_filter_threshold)

In `pokey_channel_mix` at $4D3F, the code does `CMP $13` against the channel
status (priority * 4 + 1 encoding) and skips channels whose status is below
`$13`. This is the SAME `$13` set by `handler_type_0` (silent/noisy mode).

This means the silent/noisy mode toggle affects POKEY SFX as well as YM2151
music. With `$13 = 0xF0` (silent mode), no POKEY SFX can play either, since
their status max is `15*4+1 = 61`, way below 0xF0.

The doc treats `$13` as a music-only filter, but it actually silences POKEY
SFX too.

### 5.4 Channel status encoding: priority * 4 + 1

`handler_type_7` at $45A6-$45A9 computes:
```
LDA priority    ; (from $6024,X)
ASL A           ; * 2
SEC             ; carry = 1
ROL A           ; * 2 + 1
STA $0390,Y     ; channel_status = (priority << 2) | 1
```

The doc says "priority encoded" but doesn't give the formula. It is:
**status = (priority << 2) | 1**

The | 1 means bit 0 of channel_status is always 1 for SFX channels. This
explains why `channel_state_machine` reads `$0390,X / AND #$01 / STA $0813`
and gets either 0 (inactive/uninitialized) or 1 (SFX active).

For music channels (which go through different code paths), bit 0 might
have a different meaning.

## 6. YM2151 pipeline issues

### 6.1 `channel_dispatcher` type 3 → POKEY is dead code

In `channel_dispatcher` at $501D-$5026:

```
BEQ $5023      ; if type == 0, JMP $4DFC (POKEY)
CMP #$03
BNE $5026      ; if type != 3, JMP $4FD6 (YM2151)
JMP $4DFC      ; (type == 3 case): JMP POKEY
```

So both type 0 and type 3 go to POKEY. Type 1, 2, and any other value → YM2151.

The actual `hw_channel_types` values are 0x00, 0x02, 0x1E, 0x22. **Type 3
never appears**, so the type-3-→-POKEY branch is dead code. Probably vestigial
from a development build where YM2151 had different type encoding.

### 6.2 YM2151 init in `clear_sound_buffers` silences all 8 channels via reg 0x08

The init sequence at $425E-$4280 selects YM2151 register $08 (KON = Key On/Off)
and writes channel numbers 7..0 in sequence, turning off all 8 channels'
oscillators. This is undocumented init behavior worth noting.

The protocol relies on the YM2151's register-select latch persisting between
data writes, so only one register select ($08) is needed for 8 sequential data
writes.

## 7. Verification of the disassembler tool (gauntlet_disasm.py)

The disassembler script has the following errors that affect output:

### 7.1 Wrong opcode mappings

Lines 2507/2522 of `gauntlet_disasm.py`:
- `0x8C: ("CLR_CTRL_BITS", ...)` — should be `SET_VIBRATO`
- `0x9B: ("SET_VAR_NAMED", ...)` — should be `CLR_CTRL_BITS`

There's also no entry for opcode 0x8F = POP_SEQ being labeled correctly
in the dispatcher logic (lines 2142-2168 do reference 0x8F as POP_SEQ,
but the table at 2510 says POP_SEQ is at 0x8F — which actually agrees with
ROM. So the dispatcher logic for 0x8C/0x8D is wrong but for 0x8E/0x8F is
right).

### 7.2 Wrong table sizes (cosmetic only)

The disassembler doesn't iterate through whole tables to find boundaries —
it just indexes into them via base + offset. So the wrong sizes in the
documentation don't affect the disassembler's behavior.

### 7.3 Music data start at 0x8700 vs 0x873D

The disassembler doesn't hardcode a "music data start" — it reads the
seq_ptr table to find where each sequence starts. So the wrong "0x8700"
claim doesn't affect output.

## 8. Summary of severity

**Critical (affects disassembler output / understanding of code)**:
- 2.1: opcode 0x8C/0x9B mismapping in both REPORT and disassembler
- 1.1: error_flags bit definitions wrong
- 1.10: NMI commands 3/6/7 are status queries, not "silently ignored"
- 4.5: Music sequence data starts at 0x873D, not 0x8700
- 1.16: `sound_status_update` is 5x more complex than documented

**Important (significant doc errors)**:
- 4.1, 4.3, 4.4: SFX/music table sizes off by 2-3x
- 4.8: hw_channel_types YM2151 = 0x02 not 0x03
- 1.4: `clear_sound_buffers` does full hardware init, not just buffer clear
- 1.13: NMI PATH A is dead code
- 1.14: $1031 register undocumented
- 5.1: pokey_update/write_registers are one function

**Minor (small inaccuracies, naming, missing details)**:
- 1.6: reset_handler size
- 1.7: IRQ clears bit 2 unconditionally
- 1.18: bit 7 of music_flags affects TMS5220 oscillator
- 1.20: speech_queue priority pre-emption flushes queue
- 1.23: handler_stop_sound double-indirection
- 2.3: seq_var_classifier index 5 = POKEY random
- 2.5: channel type detection (0x02 not 0x03)
- 3.5: $5874-$5893 is intentionally referenced data, not padding
- 4.7: handler_match_table base is $6559, not $655C
- 4.9: sfx_data_ptrs_a/b split by high bit, not primary/alt
- 5.2: POKEY SKCTL init undocumented
- 5.3: $13 affects POKEY SFX too
- 5.4: channel status encoding formula
- 6.1: type 3 → POKEY is dead code
- 6.2: YM2151 init detail









