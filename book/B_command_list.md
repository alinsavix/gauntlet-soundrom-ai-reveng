# Appendix B — The Complete Command List

All 219 command values the main CPU can send, in order.

**Command** is the byte written to the sound board's mailbox.
[Chapter 1](01_two_computers.md) explains the `$` notation and
[Chapter 6](06_taking_orders.md) explains how the byte becomes an action.

**Sound or phrase** is what the command means in the game. Speech text in
quotation marks is the wording of the recording, as far as the surviving command
list records it.

**Job** is the handler type in plain language. The type number itself lives in
[`docs/generated/command_catalog.csv`](../docs/generated/command_catalog.csv).

**Chip** names the device that ends up making the noise. Control and status
commands make none, so the column is blank for them.

**Detail** gives the chain length for a sound (see
[Chapter 7](07_command_to_channel.md)), the stream length for a phrase (see
[Chapter 13](13_speaking.md)), and the target or effect for everything else.

Where the surviving sound command list says "Not Used", this table says "no known
game use". The ROM entry itself is valid and reachable; what is unknown is
whether the game program ever emits it.

| Command | Sound or phrase | Job | Chip | Detail |
|---|---|---|---|---|
| `$00` | Reinitialize all audio state; the only way to silence a chip test | Reinitialize all audio |  |  |
| `$01` | Mute the board | Set global threshold |  | threshold 240 |
| `$02` | Unmute the board | Set global threshold |  | threshold 0 |
| `$03` | Question: what is the coin door doing? | Answered by the interrupt |  | answers with four cached input fields |
| `$04` | Music Chip Test | Play a sound | YM2151 | 8 records |
| `$05` | Effects Chip Test | Play a sound | POKEY | 4 records |
| `$06` | Question: which sound ROM are you? | Answered by the interrupt |  | answers `$DB` |
| `$07` | Question: are you healthy? | Answered by the interrupt |  | answers with the error flags, then arms both heartbeats |
| `$08` | Speech Chip Test | Speak a phrase | TMS5220 | 247 bytes |
| `$09` | Warrior Joins In | Play a sound | YM2151 | 3 records |
| `$0A` | Valkyrie Joins In | Play a sound | YM2151 | 4 records |
| `$0B` | Wizard Joins In | Play a sound | YM2151 | 8 records |
| `$0C` | Elf Joins In | Play a sound | YM2151 | 2 records |
| `$0D` | Food Eaten | Play a sound | YM2151 | 2 records |
| `$0E` | Red Player Exits | Play a sound | YM2151 | 2 records |
| `$0F` | Blue Player Exits | Play a sound | YM2151 | 2 records |
| `$10` | Yellow Player Exits | Play a sound | YM2151 | 2 records |
| `$11` | Green Player Exits | Play a sound | YM2151 | 2 records |
| `$12` | Doors Open | Play a sound | YM2151 | 8 records |
| `$13` | Player Takes Key | Play a sound | YM2151 | 2 records |
| `$14` | Warrior Dies | Play a sound | YM2151 | 2 records |
| `$15` | Valkyrie Dies | Play a sound | YM2151 | 2 records |
| `$16` | Wizard Dies | Play a sound | YM2151 | 2 records |
| `$17` | Elf Dies | Play a sound | YM2151 | 2 records |
| `$18` | Red Player's Heartbeat | Play a sound | YM2151 | 2 records |
| `$19` | Blue Player's Heartbeat | Play a sound | YM2151 | 2 records |
| `$1A` | Yellow Player's Heartbeat | Play a sound | YM2151 | 2 records |
| `$1B` | Green Player's Heartbeat | Play a sound | YM2151 | 2 records |
| `$1C` | Message Appears on Screen | Play a sound | YM2151 | 2 records |
| `$1D` | Potion Used / Shot | Play a sound | YM2151 | 8 records |
| `$1E` | Monster Hits Player | Play a sound | YM2151 | 2 records |
| `$1F` | Ghost Hits Player | Play a sound | YM2151 | 2 records |
| `$20` | Death Touches Player | Play a sound | YM2151 | 2 records |
| `$21` | Death Silencer | Stop a named sound |  | stops `$20` |
| `$22` | Red Coin Slot | Play a sound | YM2151 | 2 records |
| `$23` | Blue Coin Slot | Play a sound | YM2151 | 2 records |
| `$24` | Yellow Coin Slot | Play a sound | YM2151 | 2 records |
| `$25` | Green Coin Slot | Play a sound | YM2151 | 2 records |
| `$26` | Treasure / Potion Taken | Play a sound | YM2151 | 2 records |
| `$27` | Trap / Walls Turn to Exits | Play a sound | YM2151 | 8 records |
| `$28` | Transporter | Play a sound | YM2151 | 8 records |
| `$29` | Thief Warning | Play a sound | YM2151 | 8 records |
| `$2A` | Treasure Chest Opens | Play a sound | YM2151 | 1 record |
| `$2B` | Cyclical Walls | Play a sound | YM2151 | 1 record |
| `$2C` | Shots Reflecting | Play a sound | YM2151 | 1 record |
| `$2D` | Mugger Warning | Play a sound | YM2151 | 1 record |
| `$2E` | Player Touches Force Field | Play a sound | YM2151 | 1 record |
| `$2F` | Force Field Silencer | Stop a named sound |  | stops `$2E` |
| `$30` | Secret Wall Shot | Play a sound | YM2151 | 1 record |
| `$31` | Exit Moving | Play a sound | YM2151 | 1 record |
| `$32` | High Tone Stun Tile | Play a sound | YM2151 | 1 record |
| `$33` | Medium Tone Stun Tile | Play a sound | YM2151 | 1 record |
| `$34` | Low Tone Stun Tile | Play a sound | YM2151 | 1 record |
| `$35` | Player Touches IT | Play a sound | YM2151 | 1 record |
| `$36` | Acid Puddle Slimes Player | Play a sound | YM2151 | 1 record |
| `$37` | Slow Motion | Play a sound | YM2151 | 1 record |
| `$38` | End of Slow Motion | Play a sound | YM2151 | 1 record |
| `$39` | Slow Motion Silencer | Stop a named sound |  | stops `$37` |
| `$3A` | Player Shoots Dragon | Play a sound | YM2151 | 1 record |
| `$3B` | Gauntlet II Theme Song / Secret Room | Play a sound | YM2151 | 8 records |
| `$3C` | Theme Song Fade Out | Fade a named sound |  | fades `$3B` |
| `$3D` | Treasure Room Music (4 Players) | Play a sound | YM2151 | 8 records |
| `$3E` | Treasure Room Music (3 Players) | Play a sound | YM2151 | 8 records |
| `$3F` | Treasure Room Music (2 Players) | Play a sound | YM2151 | 8 records |
| `$40` | Treasure Room Music (1 Player) | Play a sound | YM2151 | 8 records |
| `$41` | Treasure Room Music Fade Out | Fade by category |  | fades status class 2 |
| `$42` | Music at Beginning of Each Level | Play a sound | YM2151 | 5 records |
| `$43` | Unable to Join In | Play a sound | POKEY | 1 record |
| `$44` | No Potions | Play a sound | POKEY | 1 record |
| `$45` | Axe | Play a sound | POKEY | 1 record |
| `$46` | Fireball | Play a sound | POKEY | 1 record |
| `$47` | Sword | Play a sound | POKEY | 1 record |
| `$48` | Arrow | Play a sound | POKEY | 1 record |
| `$49` | Lobber Throwing Rock | Play a sound | POKEY | 1 record |
| `$4A` | "ONE" | Speak a phrase | TMS5220 | 140 bytes |
| `$4B` | "TWO" | Speak a phrase | TMS5220 | 116 bytes |
| `$4C` | "THREE" | Speak a phrase | TMS5220 | 137 bytes |
| `$4D` | "FOUR" | Speak a phrase | TMS5220 | 132 bytes |
| `$4E` | "FIVE" | Speak a phrase | TMS5220 | 149 bytes |
| `$4F` | "SIX" | Speak a phrase | TMS5220 | 88 bytes |
| `$50` | "SEVEN" | Speak a phrase | TMS5220 | 119 bytes |
| `$51` | "EIGHT" | Speak a phrase | TMS5220 | 71 bytes |
| `$52` | "NINE" | Speak a phrase | TMS5220 | 146 bytes |
| `$53` | "TEN" | Speak a phrase | TMS5220 | 111 bytes |
| `$54` | "ZERO" | Speak a phrase | TMS5220 | 153 bytes |
| `$55` | "TRY AND FIND THE WAY OUT!" | Speak a phrase | TMS5220 | 414 bytes |
| `$56` | "WELCOME TO THE TREASURE ROOM." | Speak a phrase | TMS5220 | 455 bytes |
| `$57` | "YOU HAVE FOUND MY TREASURE." | Speak a phrase | TMS5220 | 374 bytes |
| `$58` | "TRY THIS LEVEL NOW!" | Speak a phrase | TMS5220 | 401 bytes |
| `$59` | "WELCOME" | Speak a phrase | TMS5220 | 181 bytes |
| `$5A` | "NEEDS FOOD, BADLY." | Speak a phrase | TMS5220 | 324 bytes |
| `$5B` | "YOUR LIFE FORCE IS RUNNING OUT!" | Speak a phrase | TMS5220 | 496 bytes |
| `$5C` | "ALL YOUR POWERS WILL BE LOST!" | Speak a phrase | TMS5220 | 355 bytes |
| `$5D` | "IS ABOUT TO DIE!" | Speak a phrase | TMS5220 | 287 bytes |
| `$5E` | "LET'S SEE YOU GET OUT OF HERE!" | Speak a phrase | TMS5220 | 406 bytes |
| `$5F` | "I'VE NOT SEEN SUCH BRAVERY!" | Speak a phrase | TMS5220 | 485 bytes |
| `$60` | "THAT WAS A HEROIC EFFORT!" | Speak a phrase | TMS5220 | 350 bytes |
| `$61` | "SOMEONE SHOT THE FOOD." | Speak a phrase | TMS5220 | 397 bytes |
| `$62` | "HEE HEE HEE HEE HEE HEE HEE" (Thief, high pitched) | Speak a phrase | TMS5220 | 200 bytes |
| `$63` | "YOU CAN'T CATCH ME!" (Thief, high pitched) | Speak a phrase | TMS5220 | 216 bytes |
| `$64` | "HA HA HA HA" (Thief, low pitched) | Speak a phrase | TMS5220 | 172 bytes |
| `$65` | "YOU CAN'T CATCH ME!" (Thief, low pitched) | Speak a phrase | TMS5220 | 193 bytes |
| `$66` | "HEH HEH" | Speak a phrase | TMS5220 | 122 bytes |
| `$67` | "HA HA" | Speak a phrase | TMS5220 | 103 bytes |
| `$68` | "HAH HAW HAH HAW" | Speak a phrase | TMS5220 | 243 bytes |
| `$69` | "MMM..MM" (Wizard) | Speak a phrase | TMS5220 | 177 bytes |
| `$6A` | "ARGH" (Wizard) | Speak a phrase | TMS5220 | 143 bytes |
| `$6B` | "MMHH.." (Wizard) | Speak a phrase | TMS5220 | 115 bytes |
| `$6C` | "URGH" (Wizard) | Speak a phrase | TMS5220 | 108 bytes |
| `$6D` | "OOH" (Wizard) | Speak a phrase | TMS5220 | 108 bytes |
| `$6E` | "OW" (Wizard) | Speak a phrase | TMS5220 | 77 bytes |
| `$6F` | "AHH" (Wizard) | Speak a phrase | TMS5220 | 108 bytes |
| `$70` | "SAYS YOU" (Wizard) | Speak a phrase | TMS5220 | 149 bytes |
| `$71` | "MMM...YES" (Wizard) | Speak a phrase | TMS5220 | 246 bytes |
| `$72` | "SO YOU SEE" (Wizard) | Speak a phrase | TMS5220 | 163 bytes |
| `$73` | "CAN YOU SEE?" (Wizard) | Speak a phrase | TMS5220 | 191 bytes |
| `$74` | "PERISH YE" (Wizard) | Speak a phrase | TMS5220 | 200 bytes |
| `$75` | "UH" (Wizard) | Speak a phrase | TMS5220 | 87 bytes |
| `$76` | "EEH EEH EEH EEH" (Elf) | Speak a phrase | TMS5220 | 127 bytes |
| `$77` | "MMMM.." (Elf) | Speak a phrase | TMS5220 | 165 bytes |
| `$78` | "ARGH" (Elf) | Speak a phrase | TMS5220 | 83 bytes |
| `$79` | "OOH" (Elf) | Speak a phrase | TMS5220 | 58 bytes |
| `$7A` | "OOH" (Elf) | Speak a phrase | TMS5220 | 71 bytes |
| `$7B` | "AAH" (Elf) | Speak a phrase | TMS5220 | 68 bytes |
| `$7C` | "UH" (Elf) | Speak a phrase | TMS5220 | 46 bytes |
| `$7D` | "OOOH" (Elf) | Speak a phrase | TMS5220 | 83 bytes |
| `$7E` | "OW" (Elf) | Speak a phrase | TMS5220 | 96 bytes |
| `$7F` | "YEOW" (Elf) | Speak a phrase | TMS5220 | 171 bytes |
| `$80` | "OOOOH" (Elf) | Speak a phrase | TMS5220 | 165 bytes |
| `$81` | "OB" (Warrior) | Speak a phrase | TMS5220 | 71 bytes |
| `$82` | "OORUB" (Warrior) | Speak a phrase | TMS5220 | 115 bytes |
| `$83` | "OW" (Warrior) | Speak a phrase | TMS5220 | 83 bytes |
| `$84` | "OH" (Warrior) | Speak a phrase | TMS5220 | 77 bytes |
| `$85` | "OOH" (Warrior) | Speak a phrase | TMS5220 | 83 bytes |
| `$86` | "UH" (Warrior) | Speak a phrase | TMS5220 | 102 bytes |
| `$87` | "UHHHH.." (Warrior) | Speak a phrase | TMS5220 | 246 bytes |
| `$88` | "URRPPP" (Warrior) | Speak a phrase | TMS5220 | 127 bytes |
| `$89` | "OH" (Valkyrie) | Speak a phrase | TMS5220 | 71 bytes |
| `$8A` | "GULP" (Valkyrie) | Speak a phrase | TMS5220 | 52 bytes |
| `$8B` | "YOU JUST SHOT THE POTION!" | Speak a phrase | TMS5220 | 334 bytes |
| `$8C` | "YOUR SHOTS NOW STUN OTHER PLAYERS." | Speak a phrase | TMS5220 | 496 bytes |
| `$8D` | "NOW HAS" | Speak a phrase | TMS5220 | 211 bytes |
| `$8E` | "LIMITED INVISIBILITY" | Speak a phrase | TMS5220 | 322 bytes |
| `$8F` | "EXTRA ARMOR" | Speak a phrase | TMS5220 | 208 bytes |
| `$90` | "EXTRA SPEED" | Speak a phrase | TMS5220 | 249 bytes |
| `$91` | "EXTRA MAGIC POWER" | Speak a phrase | TMS5220 | 310 bytes |
| `$92` | "EXTRA SHOT POWER" | Speak a phrase | TMS5220 | 275 bytes |
| `$93` | "EXTRA SHOT SPEED" | Speak a phrase | TMS5220 | 299 bytes |
| `$94` | "EXTRA FIGHT POWER" | Speak a phrase | TMS5220 | 324 bytes |
| `$95` | "ERR" (Wizard) | Speak a phrase | TMS5220 | 90 bytes |
| `$96` | "EHRR" (Wizard) | Speak a phrase | TMS5220 | 102 bytes |
| `$97` | "ERSH" (Wizard) | Speak a phrase | TMS5220 | 107 bytes |
| `$98` | "DON'T SHOOT YOUR FRIENDS ON THIS LEVEL." | Speak a phrase | TMS5220 | 485 bytes |
| `$99` | "YOUR SHOTS NOW HURT OTHER PLAYERS." | Speak a phrase | TMS5220 | 454 bytes |
| `$9A` | "SHOT THE FOOD." | Speak a phrase | TMS5220 | 241 bytes |
| `$9B` | "FIND THE HIDDEN POTION." | Speak a phrase | TMS5220 | 342 bytes |
| `$9C` | "SHOT THE POTION!" | Speak a phrase | TMS5220 | 213 bytes |
| `$9D` | "REMEMBER, DON'T SHOOT FOOD." | Speak a phrase | TMS5220 | 406 bytes |
| `$9E` | "SHOTS DO NOT HURT OTHER PLAYERS - YET." | Speak a phrase | TMS5220 | 490 bytes |
| `$9F` | "HAS EATEN ALL THE FOOD LATELY." | Speak a phrase | TMS5220 | 351 bytes |
| `$A0` | "BETTER LUCK NEXT TIME." | Speak a phrase | TMS5220 | 279 bytes |
| `$A1` | "BETTER HURRY!" | Speak a phrase | TMS5220 | 196 bytes |
| `$A2` | "TIME IS RUNNING OUT!" | Speak a phrase | TMS5220 | 298 bytes |
| `$A3` | "TIME'S ON MY SIDE." | Speak a phrase | TMS5220 | 381 bytes |
| `$A4` | "CAN YOU MAKE IT?" | Speak a phrase | TMS5220 | 212 bytes |
| `$A5` | "JUST KIDDING." | Speak a phrase | TMS5220 | 213 bytes |
| `$A6` | "FOOLED YOU!" | Speak a phrase | TMS5220 | 163 bytes |
| `$A7` | "LOOKS LIKE YOU LOSE!" | Speak a phrase | TMS5220 | 327 bytes |
| `$A8` | "DON'T SHOOT THE POTION!" | Speak a phrase | TMS5220 | 269 bytes |
| `$A9` | "YUM" (Valkyrie) | Speak a phrase | TMS5220 | 171 bytes |
| `$AA` | "OW" (Valkyrie) | Speak a phrase | TMS5220 | 110 bytes |
| `$AB` | "OUCH" (Valkyrie) | Speak a phrase | TMS5220 | 101 bytes |
| `$AC` | "UH" (Valkyrie) | Speak a phrase | TMS5220 | 66 bytes |
| `$AD` | "OOH" (Valkyrie) | Speak a phrase | TMS5220 | 85 bytes |
| `$AE` | "OOOH" (Valkyrie) | Speak a phrase | TMS5220 | 102 bytes |
| `$AF` | "OWW" (Valkyrie) | Speak a phrase | TMS5220 | 110 bytes |
| `$B0` | "YOW" (Valkyrie) | Speak a phrase | TMS5220 | 128 bytes |
| `$B1` | "AAHH" (Valkyrie) | Speak a phrase | TMS5220 | 115 bytes |
| `$B2` | "OH" (Valkyrie) | Speak a phrase | TMS5220 | 140 bytes |
| `$B3` | "HOO" (Valkyrie) | Speak a phrase | TMS5220 | 127 bytes |
| `$B4` | "UGH" (Valkyrie) | Speak a phrase | TMS5220 | 158 bytes |
| `$B5` | "AHHHHH" (Valkyrie) | Speak a phrase | TMS5220 | 303 bytes |
| `$B6` | "KILL THIEF TO RECOVER STOLEN ITEM." | Speak a phrase | TMS5220 | 433 bytes |
| `$B7` | "SOME WALLS MAY BE DESTROYED." | Speak a phrase | TMS5220 | 434 bytes |
| `$B8` | "TRAPS MAKE WALLS DISAPPEAR." | Speak a phrase | TMS5220 | 417 bytes |
| `$B9` | "UGHHH" (Elf) | Speak a phrase | TMS5220 | 315 bytes |
| `$BA` | "AHHHH" (Wizard) | Speak a phrase | TMS5220 | 202 bytes |
| `$BB` | "OOOOOH" (Warrior) | Speak a phrase | TMS5220 | 478 bytes |
| `$BC` | "AHHH" (Elf) | Speak a phrase | TMS5220 | 328 bytes |
| `$BD` | "RED WARRIOR" | Speak a phrase | TMS5220 | 203 bytes |
| `$BE` | "RED VALKYRIE" | Speak a phrase | TMS5220 | 226 bytes |
| `$BF` | "RED WIZARD" | Speak a phrase | TMS5220 | 190 bytes |
| `$C0` | "RED ELF" | Speak a phrase | TMS5220 | 187 bytes |
| `$C1` | "BLUE WARRIOR" | Speak a phrase | TMS5220 | 208 bytes |
| `$C2` | "BLUE VALKYRIE" | Speak a phrase | TMS5220 | 203 bytes |
| `$C3` | "BLUE WIZARD" | Speak a phrase | TMS5220 | 221 bytes |
| `$C4` | "BLUE ELF" | Speak a phrase | TMS5220 | 173 bytes |
| `$C5` | "YELLOW WARRIOR" | Speak a phrase | TMS5220 | 240 bytes |
| `$C6` | "YELLOW VALKYRIE" | Speak a phrase | TMS5220 | 231 bytes |
| `$C7` | "YELLOW WIZARD" | Speak a phrase | TMS5220 | 215 bytes |
| `$C8` | "YELLOW ELF" | Speak a phrase | TMS5220 | 191 bytes |
| `$C9` | "GREEN WARRIOR" | Speak a phrase | TMS5220 | 240 bytes |
| `$CA` | "GREEN VALKYRIE" | Speak a phrase | TMS5220 | 275 bytes |
| `$CB` | "GREEN WIZARD" | Speak a phrase | TMS5220 | 224 bytes |
| `$CC` | "GREEN ELF" | Speak a phrase | TMS5220 | 180 bytes |
| `$CD` | "SOME WALLS ARE INVISIBLE" | Speak a phrase | TMS5220 | 367 bytes |
| `$CE` | "EXITS MAY MOVE AROUND" | Speak a phrase | TMS5220 | 318 bytes |
| `$CF` | "REFLECTIVE SHOTS" | Speak a phrase | TMS5220 | 216 bytes |
| `$D0` | "TEMPORARY TRANSPORTABILITY" | Speak a phrase | TMS5220 | 316 bytes |
| `$D1` | "TEMPORARY REPULSIVENESS" | Speak a phrase | TMS5220 | 325 bytes |
| `$D2` | "THIS TREASURE CHEST IS LOCKED." | Speak a phrase | TMS5220 | 336 bytes |
| `$D3` | "IS IT" | Speak a phrase | TMS5220 | 91 bytes |
| `$D4` | "IS NOW IT" | Speak a phrase | TMS5220 | 244 bytes |
| `$D5` | Dragon Roar | Speak a phrase | TMS5220 | 155 bytes |
| `$D6` | Mixer preset: effects off; no known game use | Set the mixer |  | effects 0 of 3 |
| `$D7` | Mixer preset: effects low; no known game use | Set the mixer |  | effects 1 of 3 |
| `$D8` | Mixer preset: effects medium; no known game use | Set the mixer |  | effects 2 of 3 |
| `$D9` | Mixer preset: effects full; no known game use | Set the mixer |  | effects 3 of 3 |
| `$DA` | Send a proof-of-life byte; no known game use | Queue a reply byte |  | replies `$55` |

## Summary

| Job | Commands |
|---|---:|
| Speak a phrase | 141 |
| Play a sound | 62 |
| Set the mixer | 4 |
| Stop a named sound | 3 |
| Answered by the interrupt | 3 |
| Set global threshold | 2 |
| Reinitialize all audio | 1 |
| Fade a named sound | 1 |
| Fade by category | 1 |
| Queue a reply byte | 1 |
| **Total** | **219** |

Of the 62 sounds, eight go to the POKEY (`$05` and `$43` through `$49`) and the
other 54 go to the YM2151. No sound uses both chips.

## Where this comes from

- [`docs/generated/command_catalog.csv`](../docs/generated/command_catalog.csv)
  — every command as a row, with handler type, parameter, chain length, and
  speech metadata.
- [`docs/generated/type7_chain_catalog.csv`](../docs/generated/type7_chain_catalog.csv)
  — the 182 records behind the 62 sounds.
- [`docs/generated/type11_speech_catalog.csv`](../docs/generated/type11_speech_catalog.csv)
  — the 141 phrases with pointers, lengths, frame counts, clock flags, and
  priorities.
- [`hw_docs/soundcmds.csv`](../hw_docs/soundcmds.csv) — the surviving human-written
  command list this table's descriptions come from.
- [`docs/08_command_reference.md`](../docs/08_command_reference.md) — the command
  space and handler distribution.
