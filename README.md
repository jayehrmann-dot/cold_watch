# Cold Watch

Outpost 9, seventy-one degrees south, deep winter. Something came back with
the ice cores, and now it looks like one of your six crew. You are the station
keeper: haul fuel to the generator so the place stays warm, watch how people
behave, and use a scanner with only a few charges to prove who the impostor
is. Every scan burns power you need for heat. Atari 2600 looks, one screen,
inside your terminal.

```bash
./play.sh
```

or `python3 -m coldwatch` from this folder. Add `--sound` for a terminal bell
on scans, alarms and disappearances, `--level 1|2|3` to preselect a
difficulty, or `--seed N` for a repeatable station. `--selftest` plays a dozen
games headlessly and prints what happened. Needs Python 3 (ships with macOS)
and a terminal at least 80 columns by 24 rows. Eight colours are enough.

## Controls

| Key | Action |
| --- | --- |
| ARROWS, W A S D | move |
| SPACE | scan the crewmate next to you (one charge and 20 power) |
| E | eject the crewmate next to you out the airlock |
| F | take a fuel cell at the storage crate, or load it at the generator |
| N | crew roster |
| P | pause (Q from the pause screen returns to the title) |
| H, ? | controls and legend |
| B | toggle the terminal bell |
| 1 2 3 | pick EASY, NORMAL or HARD on the title screen |

A revealed alien is always the target when you press E or SPACE next to a
group, and the scanner skips anyone it has already cleared.

## The game

The station is eight rooms: HEATER, BUNKS, LAB and COMMS along the top, a
long HALL, then MESS, STORAGE and GENERATOR along the bottom. Crew are
lettered blocks (A for ADA, B for BO, C for CY, D for DEE, E for ELI, F for
FAY). You are the white block marked ME. When sprites share a cell they
flicker, the way the 2600 did it.

- **Shifts.** A WORK shift lasts 45 seconds, a REST shift 25. On WORK, each
  crewmate goes to their duty room and sometimes wanders to the mess or hall.
  On REST, everyone goes to their bunk.
- **Cold.** Crew get cold over time, faster when the station heat drops. A cold
  human walks to the heater room, stands beside the red-and-yellow heater for
  a few seconds, then goes back to work.
- **The alien** behaves almost like a human, but it has one to three
  tendencies depending on difficulty:
  - it hardly ever warms up at the heater (it shrugs the cold off in the mess
    or just toughs it out),
  - it keeps turning up in whatever room one particular crewmate is in,
  - it turns in at rest shift and then keeps getting up to wander.

  None of these is absolute. The alien forgets itself now and then and acts
  like everyone else, and humans have off days too: they sometimes skip the
  heater, drop in on a friend, or get up at night for a few seconds. The
  difference is how often. Count over several shifts rather than reacting to
  one odd moment. On HARD the alien slips more often and the humans are
  quirkier.
- **Disappearances.** If the alien is alone in a room with exactly one human
  and you are not in that room, after a few seconds that human goes missing.
  The log tells you where they were last seen; whoever else was in that room
  is worth a hard look. The alien never acts while you are in the room, and
  it waits a while between attacks. Lose three crew and the station fails.
- **Power and heat.** Power drains constantly. While there is power, heat holds
  at 70. At zero power the heat falls, and at zero heat you lose. The storage
  crate (yellow) holds a limited number of fuel cells; carry one at a time to
  the generator (green) with F. Each cell is worth 30 power. The crate does
  not refill, so the station has a clock on it.
- **Scanning.** Stand next to someone and press SPACE. A human is marked with
  a lowercase letter from then on. An alien is revealed, blinks red, and runs
  from you. Corner it and press E.
- **Ejecting.** E on an unrevealed crewmate is a gut call. Right, and you win
  with a bonus. Wrong, and the crew turns on you.

| Difficulty | Tells | Scans | Fuel cells | Power drain | Alien patience | Alien slips | Human quirks |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EASY | 3 | 4 | 12 | slow | long | 15% | 6% |
| NORMAL | 2 | 3 | 10 | medium | medium | 30% | 12% |
| HARD | 1 | 2 | 8 | fast | short | 45% | 18% |

**Scoring.** One point per second survived and 100 per fuel cell loaded.
Ejecting the alien adds 3000, plus 1000 per surviving human, 500 per unused
scan charge, 10 per point of power and 100 per fuel cell still in the crate.
A correct gut call adds 2000 more. The high score is saved in
`highscore.json` next to this file.

## Tips

- Spend the first work shift just watching. Who went to the heater, and who
  has not been once in two shifts? Who was standing in the generator room
  with no business there, again?
- The rest shift is a good check, not a perfect one. A human gets up for a
  few seconds and comes straight back. The alien stays out, and does it most
  nights.
- One odd moment is noise. Two is a lean. Three is a scan.
- A scan of someone you already suspect is a scan wasted. Scan to split the
  field, or to confirm before you eject.
- You cannot babysit everyone and ferry fuel at the same time. Load fuel in
  bursts while the crew are bunched together.
- When the alien is revealed, drive it into a dead end: COMMS and the heater
  room are small.
