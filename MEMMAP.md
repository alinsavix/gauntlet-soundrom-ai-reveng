# Gauntlet Sound ROM - Memory Map

**ROM File**: `soundrom.bin` (48KB, 0xC000 bytes)
**Architecture**: 6502 CPU
**CPU Address Range**: 0x4000-0xFFFF

---

## 1. RAM (0x0000-0x0FFF)

### 1.1 Zero Page (0x0000-0x00FF)

| Address | Name | Purpose |
|---------|------|---------|
| 0x00 | irq_frame_counter | IRQ frame counter, incremented each IRQ; bit 0 selects POKEY (odd) vs YM2151 (even) |
| 0x01 | init_complete_flag | Initialization complete flag (0=not ready, nonzero=ready) |
| 0x02 | error_flags | Error flags (see table below). Bits 0/2 are heartbeat watchdogs; bits 3-7 are sticky error indicators. |
| 0x03 | cmd_param_temp | Temporary storage for command parameter |
| 0x04-0x05 | nmi_buffer_ptr | NMI buffer pointer (16-bit) |
| 0x06-0x07 | seq_data_ptr | Sequence data base pointer (used by `LDA ($06),Y`) |
| 0x08-0x09 | hw_indirect_ptr | Hardware indirect pointer (POKEY/YM2151 base address for `STA ($08),Y`) |
| 0x0D | ym2151_timeout_flag | YM2151 timeout bypass flag (bit 7: skip delay) |
| 0x0E-0x0F | utility_ptr | Utility pointer / checksum address pointer |
| 0x10 | checksum_page_count | Checksum page counter |
| 0x11 | checksum_expected | Expected checksum / channel index save |
| 0x13 | music_filter_threshold | Music filter comparison threshold |
| 0x14 | linked_list_head | Linked list head pointer for channel management |
| 0x15-0x16 | channel_state_ptr | Computed channel state record pointer (16-bit) |
| 0x17 | chain_present_flag | Chain-present flag (0xFF=chained, 0x00=not chained) |
| 0x18-0x27 | seq_var_workspace | Sequence variable workspace (accessible by variable classifier indices 6-21) |
| 0x28 | master_speech_vol | Master speech volume (high 3 bits of mixer) |
| 0x29 | master_eff_music_vol | Master effects+music volume (low 5 bits of mixer) |
| 0x2A | timer_countdown | Timer countdown (decremented in IRQ; on expiry, writes $29 to 0x1020) |
| 0x2B-0x2C | music_seq_ptr | Music/speech sequence data pointer (16-bit) |
| 0x2D-0x2E | music_seq_length | Music/speech sequence length (16-bit) |
| 0x2F | music_active_flag | Music/speech active flag (0x00=idle, 0x80=playing, 0xFF=ending) |
| 0x30 | music_state_a | Music state variable A (initialized to 0xFF) |
| 0x31-0x32 | music_index_calc | Music index calculation workspace (16-bit) |
| 0x34 | music_status_bits | Music status bits (bit 7 = special mode; written to 0x1033) |
| 0x35 | music_tempo | Music tempo value |
| 0x36-0x39 | coin_led_accum | Coin counter LED pulse accumulators (4 channels, used by `control_register_update` second path) |
| 0x3E-0x41 | coin_led_envelope | Coin counter LED envelope states (attack/decay values, AND'd with 0x1F) |
| 0x42 | coin_led_frame_ctr | Coin counter LED frame counter (incremented each call; LSB selects normalization pass) |
| 0x44 | coin_led_output | Coin counter/LED combined output byte (bit-mapped to 4 channels via masks at 0x83A4) |

**Error flags ($02) bit assignments** (verified by tracing all reads/writes):

| Bit | Mask | Meaning | Set by | Cleared by |
|-----|------|---------|--------|------------|
| 0 | 0x01 | Heartbeat: "main_loop alive" — set when NMI cmd 7 reports flags, cleared each main_loop iteration | NMI handler 2 ($44AD) | main_loop ($4104) |
| 1 | 0x02 | YM2151 timeout — set after `ym2151_wait_ready` exhausts 255 polls | `ym2151_wait_ready` ($5005) | `clear_sound_buffers` ($4284) |
| 2 | 0x04 | Heartbeat: "IRQ alive" — also set during init while waiting for first IRQ | init_main timeout ($40C2), NMI 2 ($44AD) | IRQ handler ($418E) |
| 3 | 0x08 | Walking-bit RAM test failed for page 8+ | `ram_error_handler` X≥8 path ($4151) | (sticky) |
| 4 | 0x10 | Walking-bit RAM test failed for pages 2-7 (this path **overwrites** $02) | `ram_error_handler` X<8 path ($414B) | (sticky) |
| 5 | 0x20 | ROM checksum failed for region 0xC000-0xFFFF | `checksum_region` ($417C) | (sticky) |
| 6 | 0x40 | ROM checksum failed for region 0x8000-0xBFFF | `checksum_region` ($417C) | (sticky) |
| 7 | 0x80 | ROM checksum failed for region 0x4000-0x7FFF | `checksum_region` ($417C) | (sticky) |

NMI command 7 (status query) reads $02, sends it to the main CPU, then re-arms
bits 0 and 2. The next IRQ clears bit 2; the next main_loop iteration clears
bit 0. So if the main CPU polls again and sees bit 2 still set, the IRQ is
not running (sound CPU dead-IRQ). If bit 0 is still set, main_loop is stuck.

### 1.2 Stack (0x0100-0x01FF)

Standard 6502 stack. Initialized to 0x01FF on reset.

### 1.3 Command Buffer (0x0200-0x0226)

| Address | Name | Purpose |
|---------|------|---------|
| 0x0200-0x020F | cmd_circular_buf | Circular command queue (16 entries, 1 byte each) |
| 0x0210 | cmd_read_ptr | Command buffer read pointer |
| 0x0211 | cmd_write_ptr | Command buffer write pointer |
| 0x0212 | nmi_buf_state | **Dead** — used only by the unreachable PATH A in the NMI handler (bulk-write to ($04),Y). |
| 0x0213 | nmi_mode_flag | Selects NMI behavior: 0xFF (normal validate-and-buffer), 0 (PATH A, dead). Always set to 0xFF in practice. |
| 0x0214-0x0223 | output_buf | Output buffer to main CPU (16 entries) |
| 0x0224 | output_read_ptr | Output buffer read pointer |
| 0x0225 | output_write_ptr | Output buffer write pointer |
| 0x0226 | output_overflow_flag | Output buffer overflow flag (0x80=overflow) |
| 0x0227 | sfx_data_offset_save | Saved SFX data offset during channel allocation |

### 1.4 Sound Channel State (0x0228-0x080F)

30 logical channels, each with 48 state arrays. Arrays are indexed by channel number X (0-29).
Note that the linked-next array at $07E6 actually has **42 entries** (X=0..41) — the
first 30 are channel "next" pointers; entries 30-41 ($0804-$080F) are list HEADS,
one for each of the 12 hardware sub-channels (4 POKEY + 8 YM2151), used by the
SFX preemption logic in handler_type_7.

| Array Base | Name | Purpose |
|-----------|------|---------|
| 0x0228+X | chan_active_cmd | Active command ID (0xFF=dead, 0xFE=special marker) |
| 0x0246+X | chan_seq_ptr_lo | Sequence pointer low byte |
| 0x0264+X | chan_seq_ptr_hi | Sequence pointer high byte |
| 0x0282+X | chan_base_freq_lo | Base frequency low byte |
| 0x02A0+X | chan_base_freq_hi | Base frequency high byte (YM2151 only) |
| 0x02BE+X | chan_pri_timer_lo | Primary timer low (note duration countdown) |
| 0x02DC+X | chan_pri_timer_hi | Primary timer high |
| 0x02FA+X | chan_sec_timer_lo | Secondary timer low (envelope trigger countdown) |
| 0x0318+X | chan_sec_timer_hi | Secondary timer high |
| 0x0336+X | chan_current_note | Current note data (raw byte 1 from sequence) |
| 0x0390+X | chan_status | Channel status (0=inactive; bit 0=type; priority encoded) |
| 0x03AE+X | chan_dist_shape | Distortion shape index (into table at 0x5C8F) |
| 0x03CC+X | chan_ctrl_mask | Control AND mask (AUDCTL) |
| 0x03EA+X | chan_ctrl_bits | Control OR bits (AUDCTL) |
| 0x0408+X | chan_base_volume | Base volume (0x00-0x0F) |
| 0x0426+X | chan_vol_env_ptr_lo | Volume envelope pointer low byte |
| 0x0444+X | chan_vol_env_ptr_hi | Volume envelope pointer high byte |
| 0x0462+X | chan_freq_env_ptr_lo | Frequency envelope pointer low byte |
| 0x0480+X | chan_freq_env_ptr_hi | Frequency envelope pointer high byte |
| 0x049E+X | chan_vol_env_pos | Volume envelope position |
| 0x04BC+X | chan_vol_env_frame | Volume envelope frame counter |
| 0x04DA+X | chan_vol_env_mod | Volume envelope modulation accumulator |
| 0x04F8+X | chan_vol_env_loop | Volume envelope loop counter |
| 0x0516+X | chan_freq_env_pos | Frequency envelope position |
| 0x0534+X | chan_freq_env_frame | Frequency envelope frame counter |
| 0x0552+X | chan_freq_accum_lo | Frequency accumulator low (24-bit pitch) |
| 0x0570+X | chan_freq_accum_mid | Frequency accumulator mid |
| 0x058E+X | chan_freq_accum_hi | Frequency accumulator high |
| 0x05AC+X | chan_freq_env_loop | Frequency envelope loop counter |
| 0x05CA+X | chan_tempo | Tempo/speed (higher = faster; subtracted from duration each frame) |
| 0x05E8+X | chan_transpose | Transpose offset (added to note values) |
| 0x0606+X | chan_repeat_state | Repeat state |
| 0x0624+X | chan_repeat_counter | Repeat counter |
| 0x0642+X | chan_dist_mask | Distortion mask (OR'd with volume output) |
| 0x0660+X | chan_vibrato_depth | Vibrato depth |
| 0x067E+X | chan_porta_delta_lo | Portamento delta low byte |
| 0x069C+X | chan_porta_delta_hi | Portamento delta high byte |
| 0x06BA+X | chan_seg_chain_a | Segment chain A (linked list for multi-segment sequences) |
| 0x06D8+X | chan_seg_chain_b | Segment chain B |
| 0x06F6+X | chan_ext_chain_ctr | Extended chain counter |
| 0x0714+X | chan_env_counter_lo | Envelope counter low |
| 0x0732+X | chan_env_counter_hi | Envelope counter high |
| 0x0750+X | chan_env_rate_lo | Envelope rate low |
| 0x076E+X | chan_env_rate_hi | Envelope rate high |
| 0x078C+X | chan_env_frac | Envelope fractional accumulator |
| 0x07AA+X | chan_gp_register | General-purpose register (used by opcodes) |
| 0x07C8+X | chan_reg_shadow | Register shadow |
| 0x07E6+X | chan_linked_next | Linked list next pointer (0=end of list); X=0..29 channels, X=30..41 hardware-channel list heads (POKEY 1-4, YM2151 1-8) |

### 1.5 Work Area (0x0810-0x083B)

| Address | Name | Purpose |
|---------|------|---------|
| 0x0810 | work_channel_index | Current channel index save |
| 0x0811-0x0813 | work_misc | Miscellaneous work bytes; 0x0813 = channel type (0=POKEY, 1=YM2151) |
| 0x0814-0x0815 | work_sel_status | Selected channel status (after mix) |
| 0x0816 | work_sel_freq_alt | Selected alternate frequency |
| 0x0817 | work_volume | Volume/control byte output (POKEY AUDCx or YM2151 TL) |
| 0x0818 | work_volume_2 | Volume second value |
| 0x0819 | work_freq_lo | Frequency low byte output |
| 0x081A | work_freq_hi | Frequency high byte output (YM2151) |
| 0x081B | work_porta_lo | Portamento low (frequency fine adjust) |
| 0x081C | work_saved_chan_x | Saved current channel index during chaining |
| 0x081D | work_channel_type | Channel hardware type (0=POKEY, 2=YM2151) |
| 0x081E-0x0821 | work_extra_params | Additional params (POKEY distortion / YM2151 DT/MUL) |
| 0x0822-0x0825 | work_audctl_bits | AUDCTL mask bits |
| 0x0826 | work_vol_env_copy | Volume envelope position copy |
| 0x082F | work_update_flag | "Update needed" flag (1=write to hardware) |
| 0x0830-0x0831 | work_match_val | Match value for channel search / dispatch parameter |
| 0x0832 | speech_queue_read | Speech queue read pointer |
| 0x0833 | speech_queue_write | Speech queue write pointer |
| 0x0834-0x083B | speech_queue_buf | Speech command queue (8 entries, circular) |

### 1.6 YM2151 Operator Shadow Area (0x083C-0x089F)

| Address | Name | Purpose |
|---------|------|---------|
| 0x083C | ym_channel_num | Current YM2151 channel number (0-7) |
| 0x083D+0x08 | ym_shadow_key_on | Key On register shadow |
| 0x083D+0x20 | ym_shadow_dt2_conn | DT2/connection per channel (reg 0x20+ch) |
| 0x083D+0x28 | ym_shadow_noise | Noise/LFO per channel (reg 0x28+ch) |
| 0x083D+0x30 | ym_shadow_dt1_mul | DT1/MUL per channel (reg 0x30+ch) |
| 0x083D+0x38 | ym_shadow_tl | Total Level per channel (reg 0x38+ch) |
| 0x083D+0x40-0x78 | ym_shadow_ops | Operator parameters (4 ops x 8 regs each) |

### 1.7 Channel State Records (0x093D+)

Computed by `channel_state_ptr_calc`: `address = 0x093D + (channel - 1) * 4`

| Offset | Purpose |
|--------|---------|
| +0 | Next-channel link (linked list traversal) |
| +1-2 | Saved sequence pointer (16-bit) |
| +3 | Repeat/loop counter |

---

## 2. Hardware I/O (0x1000-0x1FFF)

### 2.1 Main CPU Interface

| Address | R/W | Name | Purpose |
|---------|-----|------|---------|
| 0x1000 | W | data_output | Data output to main CPU. Write triggers IRQ to main CPU + latches data byte. |
| 0x1002 | W | init_byte_2 | Init handshake byte (value 0x33 written once during `init_hardware_regs`). Possibly aliased to $1000. Unverified. |
| 0x1003 | W | init_byte_1 | Init handshake byte (value 0xFF written once). Possibly aliased to $1000. Unverified. |
| 0x100B | W | init_byte_3 | Init handshake byte (value 0x00 written once). Possibly aliased to $1000. Unverified. |
| 0x100C | W | init_byte_4 | Init handshake byte (value 0x22 written once). Possibly aliased to $1000. Unverified. |
| 0x1010 | R | cmd_input | Command input from main CPU. Hardware-latched simultaneously with NMI trigger. |
| 0x1020 | R | coin_status | Coin slot status. Bits 0-3: coin slots 1-4 (active low). |
| 0x1020 | W | volume_mixer | Volume mixer. Bits 7-5: speech (TMS5220, 8 levels). Bits 4-3: effects (POKEY, 4 levels). Bits 2-0: music (YM2151, 8 levels). |

### 2.2 Status/Control Register (0x1030)

| Address | R/W | Name | Bit Map |
|---------|-----|------|---------|
| 0x1030 | R | status_read | Bit 4: self-test enable (active low). Bit 5: TMS5220 ready (active low). Bit 6: sound output buffer full ($1000 has data waiting for main CPU). Bit 7: main CPU output buffer full (data waiting at $1010). Bits 0-3 unused (coins are at $1020 R, not here). |
| 0x1030 | W | ym2151_reset | Bit 7 = music (YM2151) reset, active low. Other bits don't-care. Used during boot handshake (FF/00/FF) to synchronize with main CPU. |

### 2.3 Hardware Output Registers ($1031-$1035)

Per the system schematic, all five registers are STROBE outputs where bit 7
carries the actual signal. The sound CPU reads back $1031 to preserve other
bits during read-modify-write sequences.

| Address | R/W | Name | Purpose |
|---------|-----|------|---------|
| 0x1031 | R/W | tms5220_write | TMS5220 "Speech Write" strobe (bit 7, active low). Set high before writing data to $1820, then driven low to latch. Manipulated by `init_sound_state` and `sound_status_update`. |
| 0x1032 | W | tms5220_reset | TMS5220 chip reset strobe (bit 7, active low). Used during boot init AND mid-operation by `sound_status_update`'s reset countdown ($33). |
| 0x1033 | W | speech_squeak | TMS5220 oscillator clock control (bit 7: low = 650kHz clock, high = standard). Bit 7 of `music_flags[cmd]` ($643F) selects pitch on a per-command basis (audible voice-pitch shift). |
| 0x1034 | W | coin_counter_right | Right coin counter solenoid (bit 7, active high). Drives the cabinet's mechanical coin counter. Written only in `control_register_update` PATH 2 (self-test mode). |
| 0x1035 | W | coin_counter_left | Left coin counter solenoid (bit 7, active high). Same as $1034 but for left counter. |

### 2.5 POKEY (0x1800-0x180F)

Accessed via indirect addressing through zero-page pointer (0x08-0x09 = 0x1800).

| Address | Name | Purpose |
|---------|------|---------|
| 0x1800 | AUDF1 | Channel 1 frequency |
| 0x1801 | AUDC1 | Channel 1 control (bits 7-4: volume, bits 3-0: distortion) |
| 0x1802 | AUDF2 | Channel 2 frequency |
| 0x1803 | AUDC2 | Channel 2 control |
| 0x1804 | AUDF3 | Channel 3 frequency |
| 0x1805 | AUDC3 | Channel 3 control |
| 0x1806 | AUDF4 | Channel 4 frequency |
| 0x1807 | AUDC4 | Channel 4 control |
| 0x1808 | AUDCTL | Audio control register (clock dividers, high-pass filters) |

### 2.6 YM2151 (0x1810-0x1811)

| Address | R/W | Name | Purpose |
|---------|-----|------|---------|
| 0x1810 | W | ym2151_reg_sel | Register select (written via `STY $1810`) |
| 0x1811 | W | ym2151_data | Data write (written via `STA $1811`) |
| 0x1811 | R | ym2151_status | Status read (bit 7: busy flag; polled by `ym2151_wait_ready`) |

### 2.7 TMS5220 (0x1820)

| Address | R/W | Name | Purpose |
|---------|-----|------|---------|
| 0x1820 | W | tms5220_data | Speech data input. LPC bytes streamed by `sound_status_update`. The "Speak External" command byte ($60) is written to put the chip in FIFO mode at the start of every music/speech sequence. |

### 2.8 IRQ Acknowledge (0x1830)

| Address | R/W | Name | Purpose |
|---------|-----|------|---------|
| 0x1830 | W | irq_ack | IRQ acknowledge. Write resets 6502 IRQ line (value is don't-care). |

---

## 3. ROM (0x4000-0xFFFF)

### 3.1 ROM Region Overview

| Range | Size | Contents |
|-------|------|----------|
| 0x4000-0x5CFF | ~7.5 KB | Code (functions, handlers, state machine) |
| 0x5D00-0x6FFF | ~5 KB | Data tables (command dispatch, SFX metadata) |
| 0x7000-0x86FF | ~6 KB | POKEY SFX sequence data |
| 0x8700-0xACFF | ~10 KB | YM2151 music sequence data |
| 0xAD00-0xFECD | ~21 KB | TMS5220 speech LPC data |
| 0xFECE-0xFFF5 | 296 B | Unused (zero-padded) |
| 0xFFF6-0xFFF9 | 4 B | Mystery bytes (`8C FF 00 00`), unreferenced |
| 0xFFFA-0xFFFF | 6 B | 6502 interrupt vectors |

### 3.2 Functions in ROM

#### System & Boot

| Address | Name | Purpose |
|---------|------|---------|
| 0x4002 | init_main | Main initialization: stack setup, RAM test, hardware init, enable IRQ |
| 0x4142 | ram_error_handler | Handle RAM test failures |
| 0x415F | checksum_region | Verify memory integrity via multi-page checksum |
| 0x41E6 | clear_sound_buffers | Zero all sound channel buffers and build free-channel list |
| 0x5833 | init_sound_state | Initialize sound system state variables and pointers |
| 0x5A0B | init_hardware_regs | Initialize hardware control registers (0x1000-0x100C) |
| 0x5A25 | reset_handler | Reset vector entry point; waits for main CPU ready signal on 0x1030 |

#### Main Loop & Dispatch

| Address | Name | Purpose |
|---------|------|---------|
| 0x40C8 | main_loop | Main execution loop; polls command buffer and dispatches |
| 0x432E | command_dispatcher | Two-level command dispatch (219 commands -> 15 handler types) |

#### Interrupt Handlers

| Address | Name | Purpose |
|---------|------|---------|
| 0x4183 | irq_ack_write | Simple wrapper: `STA $1830; RTS` (IRQ acknowledge) |
| 0x4187 | irq_handler | Real-time audio processing at ~240Hz |
| 0x41C8 | irq_audio_update | Audio update subroutine called from IRQ: 3x status + alternating channel + 1x status |
| 0x57B0 | nmi_handler | Command input from main CPU (event-driven) |
| 0x57F0 | nmi_command_input | Validate and buffer commands from NMI |

#### Command Handlers (Type 0-14)

| Address | Name | Handler Type | Purpose |
|---------|------|-------------|---------|
| 0x4347 | handler_type_0 | 0 | Parameter shift (ASL A x2); commands 0x01-0x02 |
| 0x434C | handler_type_1 | 1 | Set variable from data table (reserved, never dispatched) |
| 0x4359 | handler_type_2 | 2 | Add to variable from data table (reserved, never dispatched) |
| 0x4369 | handler_type_3 | 3 | Jump table dispatch for special commands; command 0x00 |
| 0x4374 | handler_kill_by_status | 4 | Kill channels by status pattern match (reserved, never dispatched) |
| 0x438D | handler_stop_sound | 5 | Stop specific named sound; commands 0x21, 0x2F, 0x39 |
| 0x43AF | handler_stop_chain | 6 | Stop channel chain by group (reserved, never dispatched) |
| 0x43D4 | handler_fadeout_sound | 9 | Fade out specific sound; command 0x3C ("Theme Fade Out") |
| 0x440B | handler_fadeout_by_status | 10 | Fade out by status match; command 0x41 ("Treasure Fade Out") |
| 0x4439 | handler_type_11 | 11 | YM2151 music/speech entry; ~112 commands (0x08, 0x4A-0xD5) |
| 0x4445 | handler_type_8 | 8 | Queue commands to main CPU output buffer; command 0xDA |
| 0x4461 | handler_channel_control | 12 | Complex channel manipulation (reserved, never dispatched) |
| 0x44DE | handler_type_7 | 7 | Main POKEY SFX handler with priority system; ~90 commands |
| 0x4618 | handler_type_14 | 14 | Null handler (single RTS; reserved, never dispatched) |
| 0x4619 | handler_type_13 | 13 | Update volume mixer register 0x1020; commands 0xD6-0xD9 |

#### Channel Management

| Address | Name | Size | Purpose |
|---------|------|------|---------|
| 0x4295 | channel_list_init | 49B | Build free-channel linked list (1->2->...->N->0) |
| 0x42C6 | channel_list_follow | 17B | Follow linked-list pointer to next channel |
| 0x42D7 | channel_state_ptr_calc | 34B | Compute ZP pointer to channel's 4-byte state record |
| 0x42F9 | channel_list_unlink | 53B | Remove channel from active linked lists |
| 0x500D | channel_dispatcher | ~40B | Route to POKEY/YM2151/RAM based on channel index (X=0->POKEY, X=1->YM2151) |
| 0x5059 | channel_find_active_cmd | 22B | Search for channel playing specific command |
| 0x506F | channel_dispatch_by_type | 12B | Dispatch handler by type from opcode table |

#### Core State Machine

| Address | Name | Size | Purpose |
|---------|------|------|---------|
| 0x4651 | channel_state_machine | ~1300B | Core engine: sequence interpreter, envelope processing, frame-by-frame playback for all channel types |

#### Sequence Engine

| Address | Name | Size | Purpose |
|---------|------|------|---------|
| 0x5029 | seq_opcode_dispatch | 30B | Bytecode interpreter: dispatch 59 opcodes (0x80-0xBA) via jump table at 0x507B |
| 0x5047 | seq_advance_read | 18B | Advance 16-bit sequence pointer and read next byte (19 callers, most-called function) |
| 0x5181 | channel_apply_volume | 22B | Apply volume adjustment to channel output |
| 0x5444 | seq_var_classifier | 109B | Map variable index to channel state array for read/write |

#### POKEY Pipeline

| Address | Name | Size | Purpose |
|---------|------|------|---------|
| 0x4B6B | envelope_process_freq | 171B | Frequency envelope: 24-bit pitch modulation via envelope shape tables |
| 0x4D02 | pokey_channel_mix | 250B | Mix two channel groups, select highest-priority output per physical channel |
| 0x4DFC | pokey_update_registers | 77B | Orchestrate POKEY channel processing (2 pairs x mix + write) |
| 0x4E1B | pokey_write_registers | 77B | Write computed values to physical POKEY AUDFx/AUDCx/AUDCTL registers |

#### YM2151 Pipeline

| Address | Name | Size | Purpose |
|---------|------|------|---------|
| 0x4C16 | ym2151_update_channel_state | 236B | Copy channel state to operator shadow area + vibrato processing |
| 0x4E68 | ym2151_write_operator | ~140B | Write 3-5 YM2151 registers per channel (operator config, key on, noise) |
| 0x4FD6 | ym2151_channel_update | ~26B | Loop over 8 YM2151 channels, calling write_operator for each |
| 0x4FF0 | ym2151_wait_ready | ~30B | Busy-wait for YM2151 ready (polls bit 7 of 0x1811; timeout after 255 checks) |
| 0x558F | ym2151_load_voice | 132B | Load complete FM voice/instrument definition (patch) to all 4 operators |
| 0x5614 | seq_op_ym_write_regs | 65B | Sequence opcode: write YM2151 register block from sequence data |
| 0x5656 | seq_op_ym_write_single | 28B | Sequence opcode: write single YM2151 register |
| 0x5676 | ym2151_write_reg_indirect | 20B | Generic YM2151 register write with shadow storage |
| 0x568A | seq_op_ym_set_algorithm | 37B | Sequence opcode: set YM2151 algorithm/feedback |
| 0x56AF | ym2151_sub_detune | 45B | Subtract from YM2151 detune value |
| 0x5715 | ym2151_apply_detune | ~64B | Apply pitch/detune adjustment to all 4 operators |
| 0x5755 | ym2151_reload_vol_env | 59B | Reload volume envelope base from voice definition |

#### Music/Speech

| Address | Name | Purpose |
|---------|------|---------|
| 0x5932 | music_speech_handler | Main music/speech playback: load sequence, calculate volume, start playback |

#### Status & Control

| Address | Name | Purpose |
|---------|------|---------|
| 0x5894 | sound_status_update | Stream speech data to TMS5220 (0x1820), manage speech queue at 0x0832-0x083B |
| 0x59E2 | speech_queue_enqueue | Priority-based circular queue enqueue for speech/sound commands. Uses $0832/$0833 read/write indices, $0834-$083B buffer, $35 priority. Called via JMP from `music_speech_handler`. |
| 0x8381 | control_register_update | Coin counter LED controller (190 bytes, 0x8381-0x843E). Two paths: (1) When bit 4 of $1030 is clear: maps coin inputs to LED state via $44 using inline masks. (2) When bit 4 is set: 4-channel attack/decay envelope processor using $36-$39 accumulators, $3E-$41 envelope states, $42 frame counter. Writes combined outputs to $1034 and $1035. Inline data table at 0x83A4-0x83AB. |

### 3.3 Data Tables in ROM

#### Command Dispatch Tables

| Address | Name | Size | Format | Purpose |
|---------|------|------|--------|---------|
| 0x4633 | handler_addr_table | **30B** | 16-bit LE addr-1 pairs (15 entries, no sentinel) | Handler type -> function address (RTS dispatch trick: stored value = target - 1). The 16th entry would overlap the start of `channel_state_machine` at $4651. |
| 0x5D0F | nmi_validation_table | 219B | 1 byte/cmd | NMI behavior. Bit 7 set (e.g., 0xFF) = store in `cmd_circular_buf`. 0x00..0x02 = immediate NMI dispatch via `nmi_dispatch_table`. Other low values = silently dropped (writes 0xDB sentinel to buffer). Only entries [3]=0, [6]=1, [7]=2 are non-0xFF. |
| 0x5DEA | cmd_type_map | 219B | 1 byte/cmd | Command number -> handler type (0x00-0x0E valid, 0xFF=no handler). Commands 3, 6, 7 map to 0xFF here but are handled by NMI directly (see nmi_validation_table). |
| 0x5EC5 | cmd_param_table | 219B | 1 byte/cmd | Command parameter loaded into A before handler call |
| 0x5FA0 | handler3_dispatch_table | 8B | 4 x 16-bit LE addr-1 | Handler type 3 sub-targets: $41E6, $843F, $44B8, $44A8. The last 3 entries OVERLAP `nmi_dispatch_table` at $5FA2. Only param 0 ($41E6 = `clear_sound_buffers`) is reachable in practice (cmd 0). |
| 0x5FA2 | nmi_dispatch_table | 6B | 3 x 16-bit LE addr-1 | NMI immediate dispatch: $843F (cmd 3 = read $44 to main CPU), $44B8 (cmd 6 = echo $DB sentinel), $44A8 (cmd 7 = read $02 + arm watchdog). |

#### POKEY/YM2151 SFX Metadata Tables

These tables use **two-level indirection**: command -> `sfx_data_offset[cmd]` -> all
other tables. The first two are indexed by command parameter (62 entries).
The remaining tables are indexed by the offset (up to 182 entries).

| Address | Name | Size | Format | Purpose |
|---------|------|------|--------|---------|
| 0x5FA8 | sfx_data_offset | 62B | 1 byte/sound | SFX command parameter -> data offset (0..181). Indirect into the priority/channel/chain/ptr tables. |
| 0x5FE6 | sfx_flags | 62B | 1 byte/sound | Behavior flags (0xFF=immediate play/no dup check, 0x00=check for duplicates) |
| 0x6024 | sfx_priority | **182B** | 1 byte/offset | Interrupt priority (0x00=lowest, 0x0F=highest). Some entries hold non-priority values (up to 0x3F) — purpose unclear. |
| 0x60DA | sfx_channel_map | **182B** | 1 byte/offset | Hardware channel index (0..11): 0..3 = POKEY ch 1-4, 4..11 = YM2151 ch 1-8. |
| 0x6190 | sfx_data_ptrs_a | 256B | 16-bit pairs (raw offset addressed) | Sound sequence data pointers for offsets 0x00-0x7F. |
| 0x6290 | sfx_data_ptrs_b | 108B | 16-bit pairs (raw offset addressed) | Sound sequence data pointers for offsets 0x80-0xB5. The "_a" / "_b" split is by high bit of offset, NOT primary/alternate. |
| 0x62FC | sfx_chain_offsets | 182B | 1 byte/entry | Multi-channel chaining: `chain_offsets[offset]` = next offset for additional channels (0x00=end). Allows a single command to allocate up to 8 channels. |

#### YM2151 Music/Speech Metadata Tables

These tables are indexed by **command parameter** (`cmd_param_table[cmd]`), not by
command number. Music/speech commands map to parameters 0..140 (cmd 0x08 = param 0;
cmds 0x4A..0xD5 = params 1..140). So all three command-indexed tables are 141 bytes
each, NOT 219.

| Address | Name | Size | Format | Purpose |
|---------|------|------|--------|---------|
| 0x63B2 | music_seq_index | **141B** | 1 byte/param | Parameter -> sequence index (0..188). Indirect into the seq_ptrs / seq_lengths tables. |
| 0x643F | music_flags | **141B** | 1 byte/param | Bit 7: TMS5220 squeak/oscillator pitch (writes through to $1033 via $34); bits 0-3: per-command volume reduction (subtract from effects+music vol) |
| 0x64CC | music_tempo | **141B** | 1 byte/param | Tempo seed value. Also serves as the filter threshold input (`handler_type_11` rejects commands whose tempo < `music_filter_threshold` ($13)). Mostly 0x00 = default. |
| 0x8449 | music_seq_ptrs | **378B** | 16-bit LE pairs (189 entries) | Pointers to music/speech note sequence data. Indexed by `seq_idx * 2`. |
| 0x85C3 | music_seq_lengths | **378B** | 16-bit LE pairs (189 entries) | Sequence length/loop parameters. Extends through $873C. |

#### Sequence Engine Tables

| Address | Name | Size | Format | Purpose |
|---------|------|------|--------|---------|
| 0x507B | opcode_jump_table | 118B | 59 x 16-bit LE addr-1 | Sequence opcode handlers (0x80-0xBA); stored as target-1 for RTS dispatch |
| 0x5A35 | ym2151_freq_table | 256B | 128 x 16-bit LE | Note number -> YM2151 frequency parameter. Note 0=rest; note 0x46 (70)=A4 (440Hz). MIDI note = ROM note - 1. |
| 0x5C5F | duration_table | 32B | 16 x 16-bit LE | Musical note durations in fixed-point (index 0-15; see format below) |
| 0x5C7F | freq_env_shape_table | ~16B | 1 byte/entry | Frequency envelope shape multipliers (0xFF=envelope finished) |
| 0x5C8F | vol_env_shape_table | ~16B | 1 byte/entry | Volume envelope distortion shapes (RAM-initialized at boot) |

**Duration Table (0x5C5F) values**:

| Index | Value | Musical Duration |
|-------|-------|-----------------|
| 0x0 | 0x0000 | Immediate/rest |
| 0x1 | 0x1E00 | Whole note |
| 0x2 | 0x0F00 | Half note |
| 0x3 | 0x0780 | Quarter note |
| 0x4 | 0x03C0 | Eighth note |
| 0x5 | 0x0A00 | Dotted half |
| 0x6 | 0x0500 | Dotted quarter |
| 0x7 | 0x0280 | Dotted eighth |
| 0x8 | 0x0600 | Triplet half |
| 0x9 | 0x01E0 | Sixteenth note |
| 0xA | 0x00F0 | Thirty-second note |
| 0xB | 0x0078 | Sixty-fourth note |
| 0xC | 0x003C | 128th note |
| 0xD | 0x0140 | Dotted sixteenth |
| 0xE | 0x00A0 | Dotted thirty-second |
| 0xF | 0x0300 | Triplet quarter |

#### Hardware Configuration Tables

Each table is **4 bytes**, not 8 (the address $57B0 is the start of `nmi_handler`,
the target of NMI vector $FFFA — there is no room for 8-byte tables).
The "ptr_lo" and "ptr_hi" arrays overlap by 2 bytes since they're at +0 and +2.

| Address | Name | Size | Format | Purpose |
|---------|------|------|--------|---------|
| 0x57A8 | hw_ptr_table_lo | 4B | 1 byte/channel | Channel index -> hardware base address low byte (0=0x00, 1=0x10, 2=0x18, 3=0x18) |
| 0x57AA | hw_ptr_table_hi | 4B | 1 byte/channel | Channel index -> hardware base address high byte (0=0x18, 1=0x18, 2=0x00, 3=0x02) |
| 0x57AC | hw_channel_types | 4B | 1 byte/channel | Hardware chip type. Values: 0x00=POKEY, **0x02=YM2151** (NOT 0x03), 0x1E=RAM workspace, 0x22=RAM buffer. The `channel_state_machine` and `seq_var_classifier` test against `CMP #2` for YM2151 channels. |
| 0x57AE | hw_channel_config | 4B (overlapping) | 1 byte/channel | Additional channel parameters (register base offsets), accessed as `$57AE,Y` from `handler_stop_chain` and the YM2151 pipeline. |

**Hardware pointer resolution**:

| Index | Pointer | Target |
|-------|---------|--------|
| 0 | 0x1800 | POKEY base |
| 1 | 0x1810 | YM2151 base |
| 2 | 0x0018 | RAM workspace |
| 3 | 0x0218 | RAM buffer |

#### YM2151 Operator Tables

| Address | Name | Size | Format | Purpose |
|---------|------|------|--------|---------|
| 0x5AF9 | ym_operator_params | ~64B | 1 byte/entry | Noise/LFO settings per operator configuration |
| 0x57A0 | ym_algo_op_mask | ~8B | 1 byte/algo | Operator mask per algorithm (for detune application) |

#### Control Register Inline Data

| Address | Name | Size | Format | Purpose |
|---------|------|------|--------|---------|
| 0x83A4-0x83A7 | coin_led_on_masks | 4B | 1 byte/channel | Bit masks for LED "on" states: `40 10 04 01` (channels 0-3) |
| 0x83A8-0x83AB | coin_led_field_masks | 4B | 1 byte/channel | Bit masks for field isolation: `C0 30 0C 03` (channels 0-3) |

#### Initialization Data

| Address | Name | Size | Format | Purpose |
|---------|------|------|--------|---------|
| 0x5F20 | init_data_table | ~100B | Sequential bytes | Initialization values (0x12-0x75) used during boot |
| 0x6559 | handler_match_table | 3 bytes/record | 3-field records | Per-entry: +0/+1 are read by `handler_type_1`/`handler_type_2`, +2 is read by `handler_channel_control`. Old doc listed base as $655C, but actual base is $6559. |

#### NMI Dispatch Targets

| Index | Address | Purpose |
|-------|---------|---------|
| 0 | 0x843F | NMI dispatch handler 0 |
| 1 | 0x44B8 | NMI dispatch handler 1 |
| 2 | 0x44A8 | NMI dispatch handler 2 |

### 3.4 Sound Data Regions

| Range | Size | Contents |
|-------|------|----------|
| 0x6800-0x83FF | ~7 KB | POKEY/YM2151 SFX sequence data (2-byte frames: freq/opcode + duration/envelope). End at $83FF inferred from `sfx_data_ptrs_a/b` values. |
| 0x873D-0xACFF | ~10 KB | YM2151 music sequence data (starts at **0x873D**, NOT 0x8700; the bytes 0x8700-0x873C are the tail of `music_seq_lengths`). Same 2-byte frame format and shared bytecode engine as SFX. |
| 0xAD00-0xFECD | ~21 KB | TMS5220 speech LPC data (bit-packed Linear Predictive Coding frames, terminated by 0xFx end-of-frame markers) |

### 3.5 Interrupt Vectors

| Address | Name | Target |
|---------|------|--------|
| 0xFFFA | NMI vector | 0x57B0 (nmi_handler) |
| 0xFFFC | RESET vector | 0x5A25 (reset_handler) |
| 0xFFFE | IRQ vector | 0x4187 (irq_handler) |

### 3.6 Unused ROM Space (~334 bytes total)

| Address | Size | Fill Pattern | Context |
|---------|------|-------------|---------|
| 0x5874-0x5893 | 32 B | 0xFF (erased EPROM) | This block is **referenced** as a 32-byte fake sequence by `init_sound_state` (sets $2B-$2C = $5874, $2D-$2E = $0020). Functionally silence/idle data, but addressed by code. |
| 0x6000-0x6023 | 36 B | 0xFF (erased EPROM) | Before `sfx_priority` table (0x6024). Unreferenced by any code. |
| 0x8447-0x8448 | 2 B | `94 FF` | Between NMI handler 0 (ends 0x8446) and `music_seq_ptrs` table (starts 0x8449). Unreferenced. |
| 0xFECE-0xFFF5 | 296 B | 0x00 (zero-padded) | Between end of speech LPC data and interrupt vectors. ROM build tool padding. |
| 0xFFF6-0xFFF9 | 4 B | `8C FF 00 00` | Between zero padding and interrupt vectors. Not standard 6502 vectors. Unreferenced. |

**Note**: Several regions that appear to contain 0xFF or 0x00 runs are actually legitimate data:
- 0x5D17-0x5DE9: 0xFF bytes in `nmi_validation_table` (value means "store in buffer")
- 0x5FE6-0x5FFE: 0xFF bytes in `sfx_flags` table (value means "immediate play")
- 0x5C8F: 32 zero bytes in `vol_env_shape_table` (legitimate zero envelope values)

---

## 4. Sequence Data Format

All sound channels (POKEY SFX, YM2151 music, TMS5220 speech) use the same 2-byte frame format, interpreted by `channel_state_machine` (0x4651).

### Frame Format

```
Byte 0 (Frequency/Opcode):
  0x00-0x7F: Note/frequency value (bit 7 clear)
  0x80-0xBA: Sequence opcode (bit 7 set; dispatched via jump table at 0x507B)
  0xBB-0xFF: End-of-sequence marker (channel stops)

Byte 1 (Duration/Envelope) -- present only when Byte 0 is a note (0x00-0x7F):
  Bits 0-3: Duration index (into table at 0x5C5F, 16 entries)
  Bits 4-5: Division control (affects secondary envelope timer rate)
  Bit 6:    Dotted note flag (x1.5 duration multiplier)
  Bit 7:    Sustain flag (sets secondary timer = 0x7F; note rings until next note)

  Value 0x00: Channel chain -- load next segment from linked list
```

### Sequence Opcodes (59 opcodes, 0x80-0xBA)

Verified against the actual jump table at $507B by reading every entry and
disassembling each handler. Many opcodes branch on the channel hardware type
($081D: 0=POKEY, 2=YM2151) and do completely different things on each chip.

| Opcode | Handler | Name | Args | Description |
|--------|---------|------|------|-------------|
| 0x80 | 0x5173 | SET_TEMPO | 1 | tempo ($05CA,X) = arg >> 2 |
| 0x81 | 0x516A | ADD_TEMPO | 1 | tempo += arg (8-bit wrapping) |
| 0x82 | 0x5192 | SET_VOLUME | 1 | POKEY: chan_base_volume = arg. YM2151: JMP `ym2151_reload_vol_env` ($5755). Skipped if active_cmd == $FE. |
| 0x83 | 0x517A | ADD_VOLUME | 1 | POKEY: chan_base_volume += arg. YM2151: JMP `ym2151_apply_detune` ($5715). Skipped if active_cmd == $FE. |
| 0x84 | 0x51AE | SET_TRANSPOSE | 1 | chan_transpose ($05E8,X) = arg |
| 0x85 | 0x51AA | ADD_TRANSPOSE | 1 | chan_transpose += arg |
| 0x86 | 0x515F | SET_FREQ_ENV | 2 | chan_freq_env_ptr ($0462/$0480,X) = 16-bit address |
| 0x87 | 0x5154 | SET_VOL_ENV | 2 | chan_vol_env_ptr ($0426/$0444,X) = 16-bit address |
| 0x88 | 0x50F1 | RESET_TIMER | 1 | Clear primary timer; advance/handle repeat counter |
| 0x89 | 0x514B | SET_REPEAT | 1 | chan_repeat_counter ($0624,X) = arg; clear repeat_state |
| 0x8A | 0x51B3 | SET_DISTORTION | 1 | chan_dist_mask ($0642,X) = arg |
| 0x8B | 0x51B7 | SET_CTRL_BITS | 1 | POKEY: chan_ctrl_mask OR arg. YM2151: chan_ctrl_bits OR (arg with bits 0/3 conditioned on $081E). |
| 0x8C | 0x51E2 | **SET_VIBRATO** | 1 | chan_vibrato_depth ($0660,X) = arg |
| 0x8D | 0x51E6 | **PUSH_SEQ** | 2 | Allocate channel record, save chan_seg_chain_a + seq_ptr, jump to 16-bit target |
| 0x8E | 0x5214 | **PUSH_SEQ_EXT** | 1 | Start repeat loop: allocate record, save state including $06D8/$06F6, set new counter = arg |
| 0x8F | 0x523F | **POP_SEQ** | 1 (ignored) | If inside loop: dec counter, restore seq_ptr to loop start; when counter hits 0, pop and continue. No-op if no loop. |
| 0x90 | 0x54CC | SWITCH_POKEY | 1 | Clear bit 0 of chan_status; sync $0811[0] = 0 |
| 0x91 | 0x54E5 | SWITCH_YM2151 | 1 | Set bit 0 of chan_status; $0813 = 1; $0811[1] = arg |
| 0x92-0x95 | 0x4719 | NOP | 1 | Dispatcher consumes 1 byte; common return path |
| 0x96 | 0x54F4 | QUEUE_OUTPUT | 1 | JSR `handler_type_8` ($4445) — queue arg to main-CPU output buffer |
| 0x97 | 0x54F9 | FADEOUT_ENV | 1 (ignored) | Reset envelope state ($0714/$078C/$0750=0; $076E=$D0; $0732=$02); set active_cmd = $FE |
| 0x98 | 0x4719 | NOP | 1 | (same as 0x92-0x95) |
| 0x99 | 0x5515 | SET_SEQ_PTR | 2 | Unconditional jump: chan_seq_ptr = 16-bit target |
| 0x9A | 0x5524 | PLAY_MUSIC_CMD | 1 | Trigger music: if `music_tempo[arg]` >= `$13` filter, JSR `music_speech_handler` |
| 0x9B | 0x51CB | **CLR_CTRL_BITS** | 1 | POKEY: chan_ctrl_mask AND ~arg. YM2151: chan_ctrl_bits AND ($F6 OR ~arg) — only bits 0/4 can be cleared. |
| 0x9C | 0x54B1 | FORCE_POKEY | 1 | Clear $0813 = 0; force-sync $0811[0] = arg |
| 0x9D | 0x5535 | SET_VOICE | 2 | Load YM2151 voice/instrument definition (FM patch) from 16-bit pointer |
| 0x9E | 0x5613 | YM_LOAD_ENV | 2 | Load YM2151 envelope from arg pointer + $24 |
| 0x9F | 0x5655 | YM_LOAD_REG | 2 | Load YM2151 register block from arg pointer + $29 |
| 0xA0 | 0x568A | YM_FREQ_OFFSET | 1 | YM2151 only, also skipped if `chain_present_flag` ($17) != 0: shift arg << 6, add to base freq |
| 0xA1 | 0x5715 | YM_DETUNE_NEG | 1 | YM2151 only: negate arg, apply as detune via `ym2151_apply_detune` |
| 0xA2 | 0x56CB | YM_VOL_ENV_NEG | 1 | YM2151 only: chan_vol_env_pos ($049E,X) = -arg |
| 0xA3 | 0x56AF | YM_VOL_ENV_SUB | 1 | YM2151 only: chan_vol_env_pos -= arg, with overflow clamp to $7F |
| 0xA4 | 0x5271 | VAR_LOAD | 2 | Load pair: $11 = arg1; chan_env_rate_hi ($076E,X) = arg2; if active_cmd == $FE, abort |
| 0xA5 | 0x4719 | NOP | 1 | (same as 0x92-0x95) |
| 0xA6 | 0x5703 | YM_SHIFT_LEFT | 1 | YM2151 only: ASL A on arg, store somewhere |
| 0xA7 | 0x56DC | FREQ_ADD | 1 | YM2151 only: signed-extend arg to 16-bit, add to chan_base_freq |
| 0xA8 | 0x5711 | SET_FREQ_ENV_LOOP | 1 | chan_freq_env_loop ($05AC,X) = arg |
| 0xA9 | 0x529E | REG_ADD | 1 | gp_reg ($07AA,X) += arg, also stored to reg_shadow ($07C8,X) |
| 0xAA | 0x52AA | REG_SUB | 1 | gp_reg -= arg, mirror to reg_shadow |
| 0xAB | 0x52B4 | REG_AND | 1 | gp_reg &= arg, mirror |
| 0xAC | 0x52BA | REG_OR | 1 | gp_reg \|= arg, mirror |
| 0xAD | 0x52C0 | REG_XOR | 1 | gp_reg ^= arg, mirror |
| 0xAE | 0x5320 | COND_JUMP_REG_Z | 2-2N | If gp_reg == 0: jump (16-bit). Else: skip (gp_reg-1) extra frames, then jump. |
| 0xAF | 0x5347 | COND_JUMP_INC | 2-2N | Like 0xAE + INC gp_reg (one-shot decay loop primitive) |
| 0xB0 | 0x5375 | VAR_STORE | 1 | If arg in 6..21: store gp_reg to seq_var_workspace[arg-6] ($0018+,Y) |
| 0xB1 | 0x53C2 | VAR_APPLY_YM | 1 | YM2151 only: apply gp_reg to selected register based on arg (0..4) |
| 0xB2 | 0x53FB | VAR_CLASSIFY_LOAD | 1 | JSR `seq_var_classifier`, store result in gp_reg + reg_shadow |
| 0xB3 | 0x52C6 | SHIFT_REG_RIGHT | 1 | Shift gp_reg right by N (controlled by arg) |
| 0xB4 | 0x52F3 | SHIFT_REG_LEFT | 1 | Shift gp_reg left by N |
| 0xB5 | 0x5410 | COND_JUMP_EQ | 3 | classify + jump if classified == 0 (var idx + 16-bit address) |
| 0xB6 | 0x5417 | COND_JUMP_NE | 3 | classify + jump if classified != 0 |
| 0xB7 | 0x541E | COND_JUMP_PL | 3 | classify + jump if classified positive (bit 7 clear) |
| 0xB8 | 0x5425 | COND_JUMP_MI | 3 | classify + jump if classified negative (bit 7 set) |
| 0xB9 | 0x5401 | REG_CLASSIFY_SUB | 1 | reg_shadow ($07C8,X) = gp_reg - classify(arg) |
| 0xBA | 0x5404 | REG_SUB_STORE | 1 | reg_shadow = gp_reg - arg |

### Timing Formula

```
seconds = (duration_table[byte1 & 0x0F] * (1.5 if bit 6 set else 1.0)) / tempo / 120
```

SET_TEMPO stores `arg >> 2` as tempo. Each frame (120Hz), tempo is subtracted from the note's duration timer.

### Note-to-Pitch Mapping

- MIDI note = ROM note value - 1
- Note 0x46 (70 decimal) = MIDI 69 = A4 (440Hz)
- Note 0 = rest/silence
- Chromatic scale with ratio 2^(1/12) between consecutive entries

---

## 5. Command Map Summary

219 commands (0x00-0xDA) dispatched through the two-level table system.

| Range | Handler Type | Category | Count |
|-------|-------------|----------|-------|
| 0x00 | 3 (jump dispatch) | System: stop all sounds (calls `clear_sound_buffers`) | 1 |
| 0x01-0x02 | 0 (param shift) | System: silent mode ($13=0xF0) / noisy mode ($13=0x00) | 2 |
| 0x03, 0x06-0x07 | (NMI direct) | **Status queries** — handled by NMI dispatch, not the main_loop dispatcher. Cmd 3: read $44 (coin/LED state). Cmd 6: echo $DB sentinel (max valid command count). Cmd 7: read $02 (error flags) + arm watchdog bits 0/2. | 3 |
| 0x04-0x05 | 7 (POKEY SFX) | Self-test: music chip, effects chip | 2 |
| 0x08 | 11 (music/speech) | Self-test: speech chip | 1 |
| 0x09-0x20 | 7 (POKEY SFX) | Sound effects | ~24 |
| 0x21 | 5 (stop sound) | Stop specific sound | 1 |
| 0x22-0x2E | 7 (POKEY SFX) | Sound effects | ~13 |
| 0x2F | 5 (stop sound) | Stop specific sound | 1 |
| 0x30-0x38 | 7 (POKEY SFX) | Sound effects | ~9 |
| 0x39 | 5 (stop sound) | Stop specific sound | 1 |
| 0x3A-0x3B | 7 (POKEY SFX) | Sound effects (including Theme Song) | 2 |
| 0x3C | 9 (fadeout) | Theme fade out | 1 |
| 0x3D-0x40 | 7 (POKEY SFX) | Sound effects (treasure rooms) | 4 |
| 0x41 | 10 (fadeout by status) | Treasure fade out | 1 |
| 0x42-0x49 | 7 (POKEY SFX) | Sound effects | ~8 |
| 0x4A-0xD5 | 11 (music/speech) | Music tracks and speech phrases | 112 |
| 0xD6-0xD9 | 13 (control reg) | Volume mixer control | 4 |
| 0xDA | 8 (output queue) | Queue data to main CPU | 1 |

Reserved handler types (code exists but no commands route to them): 1, 2, 4, 6, 12, 14.
