# Appendix C — The Bytecode Opcode Reference

All 59 instructions of the sequence language, `$80` through `$BA`.
[Chapter 9](09_sequence_language_opcodes.md) explains how they are decoded and
what the carry flag contract between a handler and the interpreter means.

**Operands** is how many bytes follow the opcode. Two-byte operands are 16-bit
addresses, stored low byte first. The indexed jumps are marked *variable* because
their operand is a packed table of targets whose length depends on the mask that
precedes them.

**Scope** says whether the instruction means the same thing on both chips. "Both"
means the handler does not branch on the channel's chip. "Differs" means the
POKEY and YM2151 paths do different work.

**Uses** counts how many times the instruction appears across all 2,166 decoded
sequence instructions in the ROM. A dash means no sound in Gauntlet II ever
executes it. Thirty-three of the 59 carry a dash.

---

## Tempo, volume, and pitch settings

| Opcode | Name | Operands | Scope | What it does | Uses |
|---|---|---:|---|---|---:|
| `$80` | SET_TEMPO | 1 | Differs | Set the channel's tempo. The operand is shifted right twice first, so a byte gives a tempo of 0 to 63 | 106 |
| `$81` | ADD_TEMPO | 1 | Differs | Add to the tempo with plain eight-bit arithmetic and no shift, so an operand of `$FF` subtracts one | 50 |
| `$82` | SET_VOLUME | 1 | Differs | On POKEY, set the base volume. On the YM2151, reload all four operator levels from the instrument record and apply an attenuation taken from a sixteen-step curve | 109 |
| `$83` | ADD_VOLUME | 1 | Differs | On POKEY, add to the base volume. On the YM2151, apply a signed delta to the carrier levels | — |
| `$84` | SET_TRANSPOSE | 1 | Differs | Replace the constant added to every note's pitch | 46 |
| `$85` | ADD_TRANSPOSE | 1 | Differs | Add to that constant | — |
| `$A0` | YM_FREQ_OFFSET | 1 | YM2151 | Set the pitch offset folded into the channel's key fraction | 88 |
| `$A7` | FREQ_ADD | 1 | YM2151 | Add a signed amount to the channel's frequency | 19 |

## Envelopes and shaping

| Opcode | Name | Operands | Scope | What it does | Uses |
|---|---|---:|---|---|---:|
| `$86` | SET_FREQ_ENV | 2 | Both | Point the channel at a frequency envelope in ROM | 13 |
| `$87` | SET_VOL_ENV | 2 | Both | Point the channel at a volume envelope in ROM | 13 |
| `$8A` | SET_DISTORTION | 1 | Differs | Set the distortion nibble that is OR'd into the POKEY control byte, and the shape-table selector | 18 |
| `$97` | FADEOUT_ENV | 1 | Differs | Fade this channel out from here, by writing the same five fields the fade command writes. The operand is ignored | 5 |
| `$A2` | YM_VOL_ENV_NEG | 1 | YM2151 | Move the volume-envelope position negative | — |
| `$A3` | YM_VOL_ENV_SUB | 1 | YM2151 | Subtract from the YM volume with clamping | 14 |
| `$A4` | VAR_LOAD | 2 | Differs | Load the amount and rate that drive a volume ramp | 44 |
| `$A6` | YM_SHIFT_LEFT | 1 | YM2151 | Shift the staged level value left | 4 |
| `$A8` | SET_FREQ_ENV_LOOP | 1 | Differs | Set the frequency envelope's loop control | — |
| `$A1` | YM_CARRIER_TL_DELTA | 1 | YM2151 | Negate the signed operand and add it, with saturation, to the total level of every carrier the current algorithm selects | 31 |

## Chip mode and control bits

| Opcode | Name | Operands | Scope | What it does | Uses |
|---|---|---:|---|---|---:|
| `$8B` | SET_CTRL_BITS | 1 | Differs | OR bits into the channel's request mask for the chip's mode register | 7 |
| `$9B` | CLR_CTRL_BITS | 1 | Differs | Clear bits from the channel's permission mask for the same register | — |
| `$90` | SWITCH_POKEY | 1 | Differs | Mark this channel as a POKEY channel by clearing its type bit | 13 |
| `$91` | SWITCH_YM2151 | 1 | Differs | Mark this channel as a YM2151 channel and synchronize from the operand | — |
| `$9C` | FORCE_POKEY | 1 | Differs | Force and resynchronize POKEY mode | — |
| `$8C` | SET_VIBRATO | 1 | Differs | Set the channel's vibrato depth. Allocation zeroes that depth and nothing else writes it, so the YM2151 interpolation block it feeds never runs | — |

## Instruments and register blocks

| Opcode | Name | Operands | Scope | What it does | Uses |
|---|---|---:|---|---|---:|
| `$9D` | SET_VOICE | 2 | YM2151 | Load an instrument: copy 28 bytes of the named 42-byte record into the chip's registers and initialize the channel's level bookkeeping from the rest. The most-used instruction in the ROM | 147 |
| `$9E` | YM_LOAD_ENV | 2 | YM2151 | Read the five auxiliary bytes at the record's offset `$24` and write YM registers `$18`, `$19`, and `$1B` | 14 |
| `$9F` | YM_LOAD_REG | 2 | YM2151 | Read the single auxiliary byte at the record's offset `$29` and write YM register `$0F` | 2 |

## Control flow

| Opcode | Name | Operands | Scope | What it does | Uses |
|---|---|---:|---|---|---:|
| `$99` | SET_SEQ_PTR | 2 | Both | Replace the sequence pointer with a 16-bit address. All five uses in the ROM jump backwards to form a loop | 5 |
| `$8D` | PUSH_SEQ | 2 | Both | Call a subsequence, pushing a return record from the pool. The `xx 00` marker returns from it | — |
| `$8E` | PUSH_SEQ_EXT | 1 | Differs | Open a counted repeat block, borrowing a pool record to hold the return point and the outer count | 23 |
| `$8F` | POP_SEQ | 1 | Differs | Close a counted repeat block: decrement, rewind if more remain, otherwise return the record and continue. The operand is ignored | 23 |
| `$AE` | COND_JUMP_REG_Z | variable | Differs | Index an inline table of 16-bit targets by the channel's register and jump to the entry found. Never falls through | 34 |
| `$AF` | COND_JUMP_INC | variable | Differs | The same, then increment the register so the next visit takes the following entry | — |
| `$B5` | COND_JUMP_EQ | 3 | Differs | Compare the register against a classified value and jump if equal | — |
| `$B6` | COND_JUMP_NE | 3 | Differs | Jump if not equal | — |
| `$B7` | COND_JUMP_PL | 3 | Differs | Jump if the result is not negative | — |
| `$B8` | COND_JUMP_MI | 3 | Differs | Jump if the result is negative | — |
| `$88` | RESET_TIMER | 1 | Differs | Reset the channel's timer and repeat state | — |
| `$89` | SET_REPEAT | 1 | Differs | Set the channel's repeat counter directly | — |

## Variables and arithmetic

| Opcode | Name | Operands | Scope | What it does | Uses |
|---|---|---:|---|---|---:|
| `$B2` | VAR_CLASSIFY_LOAD | 1 | Both | Load a named piece of state into the register: this channel's volume, tempo, or transpose, the POKEY's hardware random number, one of the sixteen shared workspace bytes, or the register's own shadow | 10 |
| `$B0` | VAR_STORE | 1 | Differs | Store the register into one of the sixteen shared workspace bytes | 9 |
| `$B1` | VAR_APPLY_YM | 1 | Differs | Apply the register to a YM2151 destination | — |
| `$AB` | REG_AND | 1 | Differs | AND an immediate value into the register. Used only to mask a random number down to a table index | 43 |
| `$A9` | REG_ADD | 1 | Differs | Add an immediate value to the register | — |
| `$AA` | REG_SUB | 1 | Differs | Subtract an immediate value from the register | — |
| `$AC` | REG_OR | 1 | Differs | OR an immediate value into the register | — |
| `$AD` | REG_XOR | 1 | Differs | Exclusive-OR an immediate value into the register | — |
| `$B3` | SHIFT_REG_RIGHT | 1 | Differs | Shift the register right | — |
| `$B4` | SHIFT_REG_LEFT | 1 | Differs | Shift the register left | — |
| `$B9` | REG_CLASSIFY_SUB | 1 | Differs | Set the shadow to the register minus a classified value | — |
| `$BA` | REG_SUB_STORE | 1 | Differs | Set the shadow to the register minus an immediate value | — |

## Crossing out of the sound engine

| Opcode | Name | Operands | Scope | What it does | Uses |
|---|---|---:|---|---|---:|
| `$96` | QUEUE_OUTPUT | 1 | Differs | Queue a byte back to the main CPU through the reply buffer, so a piece of music could signal the game | — |
| `$9A` | PLAY_SPEECH_CMD | 1 | Differs | Trigger a speech command from inside a sequence, so a piece of music could talk | — |

## Instructions that do nothing

| Opcode | Name | Operands | Scope | What it does | Uses |
|---|---|---:|---|---|---:|
| `$92` | NOP | 1 | Differs | Consume the operand and return | — |
| `$93` | NOP | 1 | Differs | Consume the operand and return | — |
| `$94` | NOP | 1 | Differs | Consume the operand and return | — |
| `$95` | NOP | 1 | Differs | Consume the operand and return | — |
| `$98` | NOP | 1 | Differs | Consume the operand and return | — |
| `$A5` | NOP | 1 | Differs | Consume the operand and return | — |

All six share one handler, which is the common return path the other instructions
tail into.

---

## Two things that are not opcodes

A first byte below `$80` is a note or a rest, followed by one control byte. A
first byte of `$BB` or above stops the channel. Neither goes through the opcode
table, and neither is counted here.
[Chapter 8](08_sequence_language_time.md) covers both.

## Where this comes from

- [`docs/06_sequence_engine.md`](../docs/06_sequence_engine.md) — the opcode
  table, the dispatch mechanism, the control-flow model, and the variable
  classifier.
- [`docs/generated/bytecode_handler_catalog.csv`](../docs/generated/bytecode_handler_catalog.csv)
  — all 59 handlers with resolved addresses, operand widths, and chip scope.
- [`docs/generated/type7_sequence_catalog.csv`](../docs/generated/type7_sequence_catalog.csv)
  — every decoded instruction in the ROM, which is where the use counts come
  from.
- [`docs/generated/type7_control_flow_catalog.csv`](../docs/generated/type7_control_flow_catalog.csv)
  — every jump, repeat, and indexed target.
