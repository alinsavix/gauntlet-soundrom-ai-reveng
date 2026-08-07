# 07 — Function and Entry-Point Index

## Classification policy

The old “51+ complete function list” mixed callable subroutines, vector entries,
tail-jump destinations, opcode handlers, and internal labels. This index keeps
those classes separate. Bounds remain provisional unless a start/end pair was
verified by control flow.

The fresh client-managed traversal checkpoint is machine-readable in
`generated/cpu_control_flow_batches.csv` and
`generated/cpu_traversal_state.csv`. Seventy successful batches have been
saved; each contains at most 64 instructions.

## Vector and reset entries

| Address | Name | Entry kind | Status |
|---:|---|---|---|
| `$5A25` | reset handler | RESET vector | Prefix verified; full bounds provisional |
| `$57B0` | NMI handler | NMI vector | Bounded listing verified through `$5832` |
| `$4187` | IRQ handler | IRQ/BRK vector | Bounded listing verified through `$41C7` |

## Boot, main loop, and utilities

| Address | Current name | Role | Confidence |
|---:|---|---|---|
| `$4002` | initialization | RESET tail-jump entry; RAM/ROM tests and system initialization | Verified entry kind; full bounds incomplete |
| `$40C8` | main loop | Tail-jump entry from boot and normal-loop body | Verified entry kind; full bounds incomplete |
| `$4142` | RAM error classifier | Classify fatal/recoverable RAM-test failures | Verified |
| `$415F` | checksum region | Accumulate/check ROM region | Strongly supported |
| `$4183` | IRQ-ack helper | Write `$1830`, return | Strongly supported |
| `$41C8` | audio update | Callable from IRQ; exits by tail-jump to `$5894` | Verified entry/exit kind |
| `$41E6` | clear/reinitialize audio | Clear channel state; initialize POKEY/YM | Strongly supported |
| `$4295` | channel-list init | Build 199-record pool | Strongly supported |
| `$42C6` | context allocation | Pop one four-byte context record from the free list | Verified |
| `$42D7` | state-record pointer | Compute four-byte record pointer | Strongly supported |
| `$42F9` | list unlink | Remove record/list element | Strongly supported |
| `$432E` | command dispatcher | Type/parameter two-level dispatch | Strongly supported |

## Command handler entries

| Type | Address | Current role | Selected by commands? |
|---:|---:|---|---|
| 0 | `$4347` | Set global filter from shifted parameter | Yes: `$01,$02` |
| 1 | `$434C` | Set workspace byte from sliding selector/value pair | No |
| 2 | `$4359` | Add sliding-pair value to workspace byte | No |
| 3 | `$4369` | Target-minus-one dispatch | Yes: `$00` |
| 4 | `$4374` | Kill channels by status match | No |
| 5 | `$438D` | Stop sound via command-table indirection | Yes: `$21,$2F,$39` |
| 6 | `$43AF` | Soft-kill every node in selected physical chain | No |
| 7 | `$44DE` | Shared POKEY/YM2151 sequence command | Yes: 62 commands |
| 8 | `$4445` | Queue output byte for main CPU | Yes: `$DA` |
| 9 | `$43D4` | Fade specific sound | Yes: `$3C` |
| 10 | `$440B` | Fade by status match | Yes: `$41` |
| 11 | `$4439` | Filter/dispatch TMS5220 speech | Yes: 141 commands |
| 12 | `$4461` | Apply validated safe opcode to matching active channels | No |
| 13 | `$4619` | Update mixer/control value | Yes: `$D6-$D9` |
| 14 | `$4618` | Null RTS | No |

Table order is by handler type, not ascending address.
The fixed-point catalog records only `handler_table_type_N` as the source for
each of types 1/2/4/6/12/14, and the exhaustive command table selects none.
Their configured dormancy and functional semantics are Verified; whether they
were development leftovers or intended for another ROM revision cannot be
recovered from this image alone.

## Core sequence/channel entries

| Address | Current name | Role | Confidence |
|---:|---|---|---|
| `$4651` | channel state machine | Timers, note/opcode processing, envelopes, stopping | Broad role verified; internal boundaries incomplete |
| `$4B6B` | signed fade/ramp processor | Scale signed ramp, accumulate fraction, apply volume/TL delta | Verified |
| `$4C16` | YM winner-state preparation | Stage base TL/live transforms and split KC/KF delta | Verified |
| `$4D02` | POKEY pair/status-lane mix | Status-bit lane staging, filter, independent-versus-joined output selection | Verified |
| `$4DFC` | POKEY update/write | One function through `$4E67`; `$4E1B` is internal | Strongly supported |
| `$4E68` | YM operator writer | Write operator/channel register set | Strongly supported |
| `$4FD6` | YM channel update | Iterate eight YM channels/registers | Strongly supported |
| `$4FF0` | YM ready wait | Busy poll and timeout flag | Strongly supported |
| `$500D` | physical-device dispatcher | Select pointer/type and tail-jump to device update | Strongly supported |
| `$5029` | opcode dispatcher | Target-minus-one dispatch for `$80-$BA` | Verified |
| `$5047` | advance/read sequence | Increment pointer and fetch byte | Verified |
| `$5059` | find active command | Search 30 logical channels | Verified; configured dormant caller |
| `$506F` | dispatch by type | Select handler target | Verified; configured dormant caller |
| `$5181` | apply signed channel volume delta | Update POKEY base volume or tail into YM TL application | Verified |
| `$5444` | variable classifier | Map bytecode variable index to state | Verified |
| `$558F` | load YM voice | Load 28-byte FM register image | Verified |
| `$5676` | indirect YM register write | Winner-gated register/data/shadow write | Verified |
| `$5715` | apply YM carrier-TL delta | Saturating signed adjustment under algorithm carrier mask | Verified |
| `$5755` | reload YM operator TL bases | Restore four voice TLs, then apply attenuation lookup | Verified |

Fresh incoming-edge evidence classifies `$4B6B`, `$4C16`, `$5029`, and
`$558F` as callable subroutines. In contrast, `$4719`, `$4809`, `$49A5`,
`$4B45`, and `$4B5D` are internal basic-block labels reached by branches or
tail jumps inside the channel state machine; they are not independent
functions.

The continued traversal verifies `$4D02` as callable from JSR sites
`$4E0F/$4E36` and `$4E68` as callable from `$4FE4`. `$4DFC/$4FD6` are Verified
tail-jump destinations selected by callable dispatcher `$500D`, not ordinary
subroutines. `$5029/$506F` are callable indirect dispatchers that synthesize
returns from ROM target tables. `$5181` is callable with a tail exit to
`$5715`.

The support-staging pass gives `$4B6B-$4D01` contiguous six-block coverage.
`$4B6B` preserves X and caller `$11`; `$4C16` preserves X and gates shared
hardware-shadow writes on `$17=0`. Exact reads, writes, exits, and configured
dormancy are in `support_staging_catalog.csv`.

`$5755` is now Verified as a tail-jump entry from `$51A0` and tails onward to
`$5715`. The NMI vector path reaches `$582D`, which synthesizes a dispatch
return from the `$5FA2` target table; `$582D` is an NMI indirect-dispatch block,
not a callable function. `$5894` has both JSR callers and tail-jump callers and
is classified accordingly.

The consumer pass extends `$5755` through `$578F`: `$578D` tail-jumps to
`$5715` after a carrier-attenuation table read at `$5790,Y`. `$5774` is inside
its four-operator reload loop, not an end boundary. The former `$5715` detune
label is Contradicted: the routine changes mode-overloaded operator TL bases,
not pitch state. `$5029` now also has a Verified exact target-minus-one/carry
dispatch contract in the generated handler catalog.

The vector/call/table-derived CPU queue is now drained. The 59-entry bytecode
opcode table resolves to 54 unique handler starts: `$4719` and `$5715` were
already visited through ordinary CPU flow, and the remaining 52 starts are now
explicitly queued as `bytecode_handler` entries for the final bounded pass.

The handler pass has now visited all 52 newly seeded starts. The external queue
is empty. `cpu_traversal_audit.py` merges these entries with every saved direct
branch/fallthrough target into `generated/cpu_entry_catalog.csv`: 458 classified
entries, including 307 internal basic-block labels. Shared handler suffixes and
tail entries are recorded without being promoted to separate functions.

## Initialization and main-loop entries

| Address | Current name | Role | Confidence |
|---:|---|---|---|
| `$4002` | RESET body | Reset YM, choose normal versus self-test initialization | Verified |
| `$402C` | zero-page RAM diagnostic | Walking-one/complement test, fatal on mismatch | Verified |
| `$4057` | paged RAM diagnostic | Test pages `$01-$0F`, classify failures | Verified |
| `$408F` | ROM diagnostic / IRQ sync | Three checksums and first initialization IRQ wait | Verified |
| `$40C8` | common initialization | Install queues, mixer, NMI mode, and sound devices | Verified |
| `$4104` | main loop | Drain one output and dispatch one input per iteration | Verified |
| `$4142` | RAM error classifier | Fatal page 1; classify later RAM banks | Verified |
| `$415F` | ROM checksum helper | Sum 64 pages modulo 256, require `$FF` | Verified |
| `$4183` | IRQ acknowledge helper | Write caller A to `$1830`, RTS | Verified |

Exact block contracts, clobbers, RAM/hardware effects, and exits are generated
in `initialization_main_catalog.csv`.

## IRQ and command-control entries

| Address | Current name | Role | Confidence |
|---:|---|---|---|
| `$4187` | IRQ entry | Early IRQ, BRK recovery, or normal audio/board service | Verified |
| `$41C8` | IRQ audio service | Four speech calls around alternating device sweep | Verified |
| `$41E6` | global audio reset | Rebuild pools, clear channels, reset both chips | Verified |
| `$4295` | context-pool initialization | Link 198 four-byte records; misplaced sentinel leaves 133 usable | Verified |
| `$42C6` | context allocation | Pop one record ID or return zero | Verified |
| `$42D7` | context address | Map record ID to `$093D+4*(ID-1)` | Verified |
| `$42F9` | channel context free | Return both owned chains to pool | Verified |
| `$432E` | command dispatcher | Validate and synthesize type-table dispatch | Verified |
| `$44DE` | type-7 allocator | Admit, initialize, sort, replace, and chain records | Verified |
| `$4619` | mixer-control handler | Split speech/effects/music fields | Verified |

The 29-row `control_plane_catalog.csv` covers every byte through the handler
table ending at `$4650`, including active and dormant handler spans.

## Speech and board-control entries

| Address | Current name | Role | Confidence |
|---:|---|---|---|
| `$5833` | initialize speech/audio state | Set dummy stream and control state | Strongly supported |
| `$5894` | speech status/update | Ready watchdog, queue dequeue, FIFO streaming | Strongly supported |
| `$5932` | start/queue speech | Metadata lookup, clock, volume, playback state | Strongly supported |
| `$59E2` | speech enqueue | Atomic 8-slot/7-item ring; full rejects before priority, otherwise higher priority flushes queue | Verified |
| `$5A0B` | boot mailbox burst | Writes `$FF,$33,$00,$22,$0F` to `$1003/$1002/$100B/$100C/$1000`, all aliases of the one sound→main latch | Verified; vestigial Atari System 1 6522-VIA speech init |

The speech consumer pass verifies `$5894` as a callable IRQ-time state machine
with a watchdog tail-jump to `$5833`, `$5932` as immediate-start versus enqueue
dispatch, `$5939` as the interrupt-masked metadata/kickoff block, and `$59E2`
as a callable interrupt-masked queue transaction. Exact block contracts and
RAM effects are in `speech_lifecycle_catalog.csv`.
| `$8381` | board/coin control | Self-test direct cache or normal filtered counter state | Strongly supported |
| `$843F` | NMI query 3 handler | Queue cached `$44`, then tail to NMI restore | Verified |
| `$44A8` | NMI query 7 handler | Return/arm error heartbeats | Strongly supported |
| `$44B8` | NMI query 6 handler | Return `$DB` | Strongly supported |
| `$44C8` | send byte to main CPU | Output-latch helper | Strongly supported |

The board-control pass verifies `$8381-$843E` as one IRQ-called routine with
self-test-active direct block `$8388-$83A3`, normal/inactive filter block
`$83AC-$83F7`, and shared pulse/output block `$83F8-$843E`. It has one RTS per
mode and no subroutine calls. Generated block and transition catalogs record
its exact state effects.

Fresh traversal classification: `$44A8/$44B8` are NMI table-dispatch entries,
while `$44C8` is a callable subroutine reached by JSR. Command-handler entries
such as `$44DE` are table-dispatch entries and must not be counted as ordinary
callable functions merely because they end in RTS.

## Sequence-opcode entries

Opcode targets are bytecode-dispatch entries, not conventional 6502 functions.
Their addresses and meanings are listed in [Sequence engine](06_sequence_engine.md).

## Callable-contract completion

Consumer-led decomposition now strengthens `$4651`: its direct JSR callers are
`$4D36`, `$4D84`, and `$4E7A`; the shared suffix at `$4B5D` either tail-loops
to `$4651` with the next linked logical channel or returns at `$4B6A`.
`$4719`, `$4809`, `$49A5`, `$4B45`, and `$4B5D` are confirmed internal
blocks/shared suffixes. The generated 14-row channel-engine catalog records
roles, assumptions, exits, clobbers, RAM effects, confidence, and next tests.


The completion audit requires these fields for each externally meaningful entry:

- proven start and exclusive end;
- incoming JSR/JMP/vector/table references;
- return, tail-call, and non-returning exits;
- register and flag clobbers;
- zero-page/RAM inputs and outputs;
- interrupt-safety and reentrancy notes;
- reachability under this ROM's table configuration.

The bounded direct-target and table-target inventory has reached a fixed point,
and semantic range catalogs own every executable byte in both code islands.
`cpu_entry_contract_catalog.csv` now supplies all listed fields for all 61
vector, callable, tail, table, list-follow, and synthesized-dispatch entries;
the generated audit reports zero missing contracts. Runtime path frequencies
and any indirect target class absent from the verified ROM tables still require
an execution trace.

The physical-output pass verifies `$4D02` as POKEY physical-pair/status-lane arbitration called at
`$4E0F/$4E36`, `$4DFC` as the POKEY tail-dispatch entry, `$4E68` as one-channel
YM output called at `$4FE4`, `$4FD6` as the eight-channel YM tail-dispatch
entry, `$4FF0` as the shared busy-wait subroutine, and `$500D` as the callable
hardware dispatcher. Detailed contracts and effects are generated in
`physical_output_catalog.csv`.
