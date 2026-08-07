# 02 — CPU Memory Map

## Address-space overview

| Range | Use | Confidence |
|---|---|---|
| `$0000-$00FF` | Zero-page state and pointers | Verified |
| `$0100-$01FF` | 6502 stack | Verified |
| `$0200-$0FFF` | Queues, channel arrays, operator state, workspace | Verified in broad structure |
| `$1000-$1FFF` | Sparse board and sound-device I/O | Verified |
| `$2000-$3FFF` | Unmapped/unused by known program paths | Strong inference |
| `$4000-$FFFF` | 48 KiB ROM | Verified |

## Important zero-page variables

| Address | Name | Meaning | Confidence |
|---:|---|---|---|
| `$00` | `boot_nmi_latch` / `irq_frame_counter` | Boot indirect-write exit signal, later IRQ counter | Verified |
| `$01` | `initialization_flag` | Selects early versus normal IRQ behavior | Verified |
| `$02` | `error_flags` | Heartbeats and RAM/ROM/YM errors | Verified |
| `$04-$05` | `boot_nmi_write_ptr` | Live during boot `$0213=0` indirect-write window | Verified mechanics; role Strong inference |
| `$08-$09` | `hardware_ptr` | Indirect POKEY/YM2151 base pointer | Verified |
| `$0E-$0F` | utility pointer | Used by initialization/list helpers | Verified, semantics vary |
| `$10-$13` | utility/filter state | `$13` is global sound/speech filter threshold | Verified |
| `$18-$27` | sequence variable workspace | Indices 6..21 from classifier | Verified |
| `$28` | speech mixer field | Combined into `$1020` output | Verified |
| `$29` | effects/music mixer fields | Written to `$1020` | Verified |
| `$2A` | mixer/timing countdown | IRQ-decremented | Verified |
| `$2B-$2C` | speech stream pointer | Current TMS5220 LPC byte pointer | Verified |
| `$2D-$2E` | speech bytes remaining | Current LPC byte length | Verified |
| `$2F` | speech state | `$80` kickoff, `$FF` streaming, countdown states | Verified |
| `$30-$35` | speech control | Includes watchdog, reset, and current priority `$35` | Partly verified |
| `$36-$44` | coin/control state | Inputs, pulse states, and cached status `$44` | Partly verified |

Speech control is now consumer-resolved more precisely: `$30` is the
active-low-ready watchdog phase, `$31-$32` are metadata/mixer scratch, `$33`
is a frame-counter-relative scheduled reset deadline, `$34` caches the speech
clock-control byte, and `$35` is current/queued priority. `$2F` states are 0
idle, `$80` Speak External kickoff, `$FF` payload streaming, and `$11..0`
post-length drain.

### Error flags at `$02`

| Bit | Meaning |
|---:|---|
| 0 | Main-loop heartbeat; armed by NMI command 7, cleared by main loop |
| 1 | YM2151 busy timeout |
| 2 | IRQ heartbeat; armed by NMI command 7, cleared by IRQ |
| 3 | Walking-bit RAM failure in page 8+ |
| 4 | Walking-bit RAM failure in pages 2..7 |
| 5 | ROM checksum failure for `$C000-$FFFF` |
| 6 | ROM checksum failure for `$8000-$BFFF` |
| 7 | ROM checksum failure for `$4000-$7FFF` |

## Queues and global RAM

| Range | Meaning |
|---|---|
| `$0200-$020F` | 16-entry incoming command ring |
| `$0210/$0211` | Incoming ring read/write positions |
| `$0212/$0213` | Boot indirect-write index/mode; normal command mode is `$0213=$FF` |
| `$0214-$0223` | 16-byte output staging buffer for main CPU |
| `$0224-$0226` | Output-buffer state/pointers |
| `$0832/$0833` | Eight-slot speech queue read/write positions; pointer equality means empty, so usable capacity is seven |
| `$0834-$083B` | Eight physical speech-command slots (seven usable at once) |
| `$083C-$089F` | YM2151 operator/output workspace |
| `$093D+4(n-1)` | 198 four-byte records used by sequence push/pop chaining; the free list built at `$4295` reaches only records 1..134 (see below) |

### Context-pool free-list extent

`$4295` links the pool by writing each record's next-ID field and advancing a
16-bit pointer by 4. Its count guard (`CMP #$C8` at `$42B4`) stops after record
198 has been linked, covering `$093D-$0C54`. The epilogue at `$42B8` then executes `DEC $16` before
`SBC #$04`, which is correct only on the `$42B1` exit, where the matching
`INC $16` has just run. On the count exit taken here, `INC $16` did not run in
the final iteration, so the pointer is adjusted by 260 rather than 4 and the
terminating zero is stored at `$0B51` — record 134 — instead of record 198.

Direct execution of `$4295` confirms the result: `$14` = 1, the chain
1→2→…→134 terminates at 134, and records 135..198 retain valid next-IDs while
being unreachable. Allocatable capacity is therefore 133 records with 134 as the
sentinel (**Verified** by execution and by the bounded listing). Configured
demand never approaches that, so there is no functional effect. The intended
shape — 198 records with 197 allocatable — is **Strong inference** from the
count guard and the single-record back-step the epilogue was clearly written to
perform.

## Logical channel arrays

The sequence engine stores 30 logical channels as parallel arrays. Each base
below is indexed by X (`0..29`).

| Base | Meaning |
|---:|---|
| `$0228` | Active command (`$FF` inactive, `$FE` fade/special) |
| `$0246/$0264` | Sequence pointer low/high |
| `$0282/$02A0` | Base frequency low/high |
| `$02BE/$02DC` | Primary timer low/high |
| `$02FA/$0318` | Secondary timer low/high |
| `$0336` | Current note data |
| `$0390` | Channel status/type bits |
| `$03AE` | Distortion shape index |
| `$03CC/$03EA` | Control AND/OR masks |
| `$0408` | Voice byte +2; base volume path and YM KF/pitch-offset base |
| `$0426/$0444` | Volume-envelope pointer |
| `$0462/$0480` | Frequency-envelope pointer |
| `$049E-$04F8` | Volume-envelope state arrays |
| `$0516-$05AC` | Frequency-envelope state arrays |
| `$05CA` | Tempo/speed |
| `$05E8` | Transpose |
| `$0606/$0624` | Repeat state/counter |
| `$0642` | Distortion mask |
| `$0660` | Vibrato depth |
| `$067E/$069C` | Portamento delta |
| `$06BA/$06D8/$06F6` | Push/extended-loop linkage and repeat state |
| `$0714-$078C` | Envelope counters/rates/fraction |
| `$07AA/$07C8` | General-purpose register and shadow |
| `$07E6` | Linked-next array |

`$07E6` has 42 meaningful entries: 30 logical-channel next links followed by
12 physical-channel list heads at `$0804-$080F` (four POKEY and eight YM2151).

Physical-output scratch `$0811-$0825` holds two candidate status lanes,
frequency/volume results, combined control masks, the current physical-list
head at `$081C`, and final pair arbitration state. `$0826-$082E` is the YM
total-level transform chain: `$0827/$0829/$082B/$082D` are M1/M2/C1/C2
descriptor bytes; `$0828/$082A/$082C` link one operator transform to the next;
`$0826` is the zero chain seed; and `$082E` is live volume. `$082F` is the YM
event-control shift register. Bit 0 requests key-off, bit 1 gates KC/TL refresh,
bit 2 requests key-on, and original bits 5..4 select the four-entry TL bias
table after two destructive memory shifts plus two accumulator shifts. Bit 3
and bits 7..6 have no current-ROM producer or consumer. These roles and the
absence of other aligned references are Verified by
`ram_state_reference_catalog.csv`.

Board-control consumers refine `$36-$44`: `$36-$39` are four pending/stretched
counter-pulse states; `$3E-$41` are four saturating input-filter accumulators;
`$42` is the filter/pulse phase counter; and `$44` contains four two-bit cached
input/event fields. `$3A-$3D` and `$43` have no aligned direct/pointer access in
all 3,199 decoded executable instructions; the only nearby indexed bases are
`$36,X` and `$3E,X`, both with Verified X=3..0 domains. They are unused zero-page
storage in this ROM, aside from blanket RAM clearing and the externally driven
boot indirect-write window.

## I/O map

See [Hardware](01_hardware.md) for direction-sensitive register semantics.

| Range | Device |
|---|---|
| `$1000-$1035` | Main-CPU interface and board controls |
| `$1800-$180F` | POKEY |
| `$1810-$1811` | YM2151 |
| `$1820` | TMS5220 data |
| `$1830` | IRQ acknowledge |

## ROM

The complete ROM-content map is maintained separately in
[ROM structure](03_rom_structure.md).
