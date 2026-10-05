"""Headless exercise of the simulation: a chore-doing bot plays every difficulty."""
import random

from .constants import CRATE_TILES, GEN_TILES, TELL_FOLLOW, TELL_HEATER, TELL_NOBUNK, TICK
from .world import World, adjacent, bfs_path, passable


def step_bot(w, rng, plan):
    """A simple player: keep the generator fed, scan whoever is handy, chase a revealed alien."""
    revealed = [c for c in w.crew_alive() if c.revealed]
    if revealed:
        target = revealed[0]
        if adjacent(w.player, target.pos):
            w.eject()
            return
        goal = target.pos
    elif w.carrying:
        goal = (28, 12)                     # beside the generator
        if any(adjacent(w.player, t) for t in GEN_TILES):
            w.fuel_action()
            return
    elif w.power < 65 and w.fuel_crate > 0:
        goal = (17, 14)                     # beside the crate
        if any(adjacent(w.player, t) for t in CRATE_TILES):
            w.fuel_action()
            return
    else:
        near = w.near_crew()
        if near and w.scans > 0 and w.power > 50 and w.time > 90 and rng.random() < 0.01 and not near[0].cleared:
            w.scan()
            return
        if plan["wander"] is None or w.player == plan["wander"]:
            plan["wander"] = rng.choice([c.pos for c in w.crew_alive()])
        goal = plan["wander"]
    path = bfs_path(w.player, goal)
    if path:
        w.move_player(path[0][0] - w.px, path[0][1] - w.py)


def run_selftest(seed=None):
    rng = random.Random(seed)
    failures = 0
    outcomes = {"WIN": 0, "LOSE": 0, "TIMEOUT": 0}
    # aggregated tell statistics: [alien total, human total, human count]
    stats = {
        TELL_HEATER: {"alien": 0.0, "human": 0.0, "n": 0, "trials": 0},
        TELL_NOBUNK: {"alien": 0.0, "human": 0.0, "n": 0, "trials": 0},
        TELL_FOLLOW: {"alien": 0.0, "human": 0.0, "n": 0, "trials": 0},
    }
    for level in (1, 2, 3):
        for trial in range(6):
            w = World(level, rng.randrange(10 ** 6))
            alien = w.alien
            plan = {"wander": None}
            steps = 0
            shadow = {c.idx: 0 for c in w.crew}
            while w.state == "PLAY" and steps < 15000:
                steps += 1
                if steps % 2 == 0:          # bot moves at half the player's top speed
                    step_bot(w, rng, plan)
                w.update(TICK)
                mark = alien.follow
                if mark and mark.alive and w.shift == "WORK":
                    for c in w.crew_alive():
                        if c is not mark and c.room == mark.room:
                            shadow[c.idx] += 1
                for c in w.crew:
                    assert passable(c.pos), "%s off the floor at %s" % (c.name, c.pos)
                assert passable(w.player)
                assert 0 <= w.power <= 100 and w.heat <= 70
            hours = max(1.0, w.time / 60.0)
            humans = w.humans_alive()
            long_enough = alien.night_ticks >= 2 * int(25 / TICK)   # at least two full nights
            if TELL_HEATER in alien.tells and long_enough:
                stats[TELL_HEATER]["alien"] += alien.heater_visits / hours
                stats[TELL_HEATER]["trials"] += 1
                for h in humans:
                    stats[TELL_HEATER]["human"] += h.heater_visits / hours
                    stats[TELL_HEATER]["n"] += 1
            if TELL_NOBUNK in alien.tells and long_enough:
                stats[TELL_NOBUNK]["alien"] += alien.night_out_ticks / alien.night_ticks
                stats[TELL_NOBUNK]["trials"] += 1
                for h in humans:
                    stats[TELL_NOBUNK]["human"] += h.night_out_ticks / max(1, h.night_ticks)
                    stats[TELL_NOBUNK]["n"] += 1
            if TELL_FOLLOW in alien.tells and alien.follow and long_enough:
                stats[TELL_FOLLOW]["alien"] += shadow[alien.idx] / steps
                stats[TELL_FOLLOW]["trials"] += 1
                for h in humans:
                    if h is not alien.follow:
                        stats[TELL_FOLLOW]["human"] += shadow[h.idx] / steps
                        stats[TELL_FOLLOW]["n"] += 1
            state = w.state if w.state != "PLAY" else "TIMEOUT"
            outcomes[state] += 1
            print("level %d trial %d: alien=%-3s %-7s t=%4.0fs day=%d taken=%d scans_left=%d power=%3d "
                  "heat=%2d crate=%2d tells=%s | %s" % (
                      level, trial, alien.name, state, w.time, w.day, len(w.taken), w.scans, w.power,
                      w.heat, w.fuel_crate, "+".join(sorted(t.split()[0] for t in alien.tells)),
                      w.end_reason))
    # The alien must stand out statistically, but not absolutely.
    for tell, st in stats.items():
        if not st["n"] or not st["trials"]:
            print("no long game exercised the tell: %s" % tell)
            continue
        human_avg = st["human"] / st["n"]
        alien_avg = st["alien"] / st["trials"]
        if tell == TELL_HEATER:
            ok = alien_avg < human_avg * 0.6
            print("heater visits/min   alien %.2f  human %.2f  %s" % (alien_avg, human_avg, "ok" if ok else "FAIL"))
        elif tell == TELL_NOBUNK:
            ok = alien_avg > human_avg * 1.8
            print("night out of bunk   alien %.0f%%  human %.0f%%  %s" % (100 * alien_avg, 100 * human_avg, "ok" if ok else "FAIL"))
        else:
            ok = alien_avg > human_avg * 1.5
            print("time in mark's room alien %.0f%%  human %.0f%%  %s" % (100 * alien_avg, 100 * human_avg, "ok" if ok else "FAIL"))
        failures += not ok
    # scripted checks of the endings
    w = World(2, 1)
    w.px, w.py = w.alien.pos
    w.eject()
    assert w.state == "WIN" and "GUT CALL" in w.end_reason, "gut-call eject should win"
    w = World(2, 1)
    human = w.humans_alive()[0]
    w.px, w.py = human.pos
    w.eject()
    assert w.state == "LOSE", "ejecting a human should lose"
    w = World(2, 1)
    w.px, w.py = w.alien.pos
    w.scan()
    assert w.alien.revealed and w.alien.task == "FLEE" and w.scans == 2 and w.power == 80
    for _ in range(50):
        w.update(TICK)
    assert passable(w.alien.pos)
    unreachable = [p for p in [(3, 3), (10, 3), (33, 3), (5, 14), (19, 13), (28, 13)]
                   if bfs_path((18, 8), p) is None]
    if unreachable:
        print("FAIL: unreachable spots", unreachable)
        failures += 1
    print("outcomes:", outcomes)
    print("selftest %s" % ("FAILED" if failures else "passed"))
    return 1 if failures else 0
