"""The Cold Watch simulation: station, crew behaviour and the alien.

No curses in here. The renderer reads this state; the self-test drives it
headlessly.
"""
import random
from collections import deque

from .constants import (
    ALL_TELLS, BENCH, BENCH_TILES, BUNK, BUNK_TILES, CONSOLE, CONSOLE_TILES, CRATE,
    CRATE_TILES, CREW_DEFS, CREW_MOVE_TICKS, DIFFICULTY, DOOR, DOORS,
    FLEE_MOVE_TICKS, FLOOR, FUEL_POWER, GEN, GEN_TILES, GRACE, GUT_CALL_BONUS,
    HEATER, HEATER_DOOR_WAIT, HEATER_SPOTS, HEATER_TILES, HEAT_FALL, HEAT_RISE,
    HUMAN_WANDER_ROOMS, MAP_H, MAP_W, MAX_HEAT, MAX_POWER, MESS_SPOTS, MIN_CREW,
    NIGHT_WANDER_ROOMS, PASSABLE, PLAYER_START, REST_LEN, ROOMS, SCAN_COST,
    TABLE, TABLE_TILES, TELL_FOLLOW, TELL_HEATER, TELL_NOBUNK, WALL, WIN_BONUS,
    WORK_LEN,
)


# ------------------------------------------------------------------ map ----
def build_map():
    grid = [[WALL] * MAP_W for _ in range(MAP_H)]
    for x0, y0, x1, y1 in ROOMS.values():
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                grid[y][x] = FLOOR
    for x, y in DOORS:
        grid[y][x] = DOOR
    for tiles, ch in (
        (HEATER_TILES, HEATER), (GEN_TILES, GEN), (BENCH_TILES, BENCH),
        (CONSOLE_TILES, CONSOLE), (TABLE_TILES, TABLE), (CRATE_TILES, CRATE),
        (BUNK_TILES, BUNK),
    ):
        for x, y in tiles:
            grid[y][x] = ch
    return grid


def build_room_lookup():
    lookup = {}
    for name, (x0, y0, x1, y1) in ROOMS.items():
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                lookup[(x, y)] = name
    return lookup


GRID = build_map()
ROOM_OF = build_room_lookup()


def passable(pos):
    x, y = pos
    return 0 <= x < MAP_W and 0 <= y < MAP_H and GRID[y][x] in PASSABLE


def neighbors(pos):
    x, y = pos
    return ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))


def bfs_path(start, goal):
    """Shortest list of steps from start to goal, [] if there, None if unreachable."""
    if start == goal:
        return []
    prev = {start: None}
    queue = deque([start])
    while queue:
        cur = queue.popleft()
        if cur == goal:
            break
        for nxt in neighbors(cur):
            if nxt not in prev and passable(nxt):
                prev[nxt] = cur
                queue.append(nxt)
    if goal not in prev:
        return None
    path = []
    cur = goal
    while cur != start:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return path


def bfs_distances(start):
    dist = {start: 0}
    queue = deque([start])
    while queue:
        cur = queue.popleft()
        for nxt in neighbors(cur):
            if nxt not in dist and passable(nxt):
                dist[nxt] = dist[cur] + 1
                queue.append(nxt)
    return dist


def adjacent(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1])) <= 1


# ----------------------------------------------------------------- crew ----
class Crew:
    def __init__(self, idx, name, role, work, bunk, rng):
        self.idx = idx
        self.name = name
        self.role = role
        self.work = work
        self.bunk = bunk
        self.x, self.y = work
        self.alive = True
        self.is_alien = False
        self.tells = set()
        self.follow = None
        self.revealed = False
        self.cleared = False
        self.cold = rng.uniform(0, 70)
        self.cold_rate = rng.uniform(2.0, 3.2)
        self.task = "DUTY"
        self.wait = 0.0
        self.goal = None
        self.path = []
        self.path_goal = None
        self.move_tick = 0
        self.heater_visits = 0
        self.nights_in_bunk = 0
        self.night_ticks = 0        # rest-shift ticks sampled
        self.night_out_ticks = 0    # ...of which spent away from the bunk

    @property
    def pos(self):
        return (self.x, self.y)

    @property
    def room(self):
        return ROOM_OF.get(self.pos)

    def status(self):
        if not self.alive:
            return "MISSING"
        if self.revealed:
            return "ALIEN!"
        if self.cleared:
            return "SCANNED HUMAN"
        return "OK"


# ---------------------------------------------------------------- world ----
class World:
    def __init__(self, difficulty=2, seed=None):
        self.rng = random.Random(seed)
        self.level = difficulty
        self.diff = DIFFICULTY[difficulty]
        self.crew = [
            Crew(i, name, role, work, BUNK_TILES[i], self.rng)
            for i, (name, role, work) in enumerate(CREW_DEFS)
        ]
        self.alien = self.rng.choice(self.crew)
        self.alien.is_alien = True
        self.alien.tells = set(self.rng.sample(ALL_TELLS, self.diff["tells"]))
        if TELL_FOLLOW in self.alien.tells:
            self.alien.follow = self.rng.choice([c for c in self.crew if c is not self.alien])

        self.px, self.py = PLAYER_START
        self.power = MAX_POWER
        self.heat = MAX_HEAT
        self.scans = self.diff["scans"]
        self.fuel_crate = self.diff["fuel"]
        self.carrying = False
        self.time = 0.0
        self.day = 1
        self.shift = "WORK"
        self.shift_left = WORK_LEN
        self.score = 0
        self._score_acc = 0.0
        self.state = "PLAY"          # PLAY, WIN, LOSE
        self.end_reason = ""
        self.hunt = 0.0
        self.hunt_cd = GRACE
        self.taken = []
        self.log = []
        self.events = []             # one-shot cues for the renderer ("bell", "flash")
        self.flash_frames = 0
        self.warned_power = False
        self.warned_heat = False
        for c in self.crew:
            self.decide(c)
        self.msg("DAY 1. WORK SHIFT. ONE OF THEM IS NOT HUMAN.", "info")

    # ---------------------------------------------------------- helpers
    @property
    def player(self):
        return (self.px, self.py)

    def msg(self, text, kind="info"):
        self.log.append((text, kind))
        del self.log[:-40]

    def cue(self, name):
        self.events.append(name)

    def humans_alive(self):
        return [c for c in self.crew if c.alive and not c.is_alien]

    def crew_alive(self):
        return [c for c in self.crew if c.alive]

    def random_spot(self, room):
        spots = [p for p, r in ROOM_OF.items() if r == room and GRID[p[1]][p[0]] == FLOOR]
        return self.rng.choice(spots)

    def near_crew(self):
        """Crew within one tile of the player, nearest first."""
        near = [c for c in self.crew_alive() if adjacent(c.pos, self.player)]
        # A revealed alien always comes first, then anyone not yet scanned, then nearest.
        near.sort(key=lambda c: (not c.revealed, c.cleared, abs(c.x - self.px) + abs(c.y - self.py)))
        return near

    # ---------------------------------------------------------- crew AI
    def slips(self):
        """The alien forgets itself and behaves like a human this time."""
        return self.rng.random() < self.diff["slip"]

    def quirk(self):
        """A human does something a little odd this time."""
        return self.rng.random() < self.diff["quirk"]

    def near_spot(self, target, radius, avoid_heater=False):
        """A floor tile in the target's room within radius, or outside the heater door."""
        room = ROOM_OF.get(target)
        if avoid_heater and room == "HEATER":
            return HEATER_DOOR_WAIT
        spots = [p for p, r in ROOM_OF.items()
                 if r == room and passable(p) and GRID[p[1]][p[0]] == FLOOR
                 and abs(p[0] - target[0]) + abs(p[1] - target[1]) <= radius]
        return self.rng.choice(spots) if spots else target

    def decide(self, c):
        rng = self.rng
        if c.revealed:
            c.task, c.goal, c.wait = "FLEE", None, 0.0
            return
        if self.shift == "REST":
            self.decide_rest(c)
            return
        if c.cold >= 100:
            c.task, c.wait = "WARM", rng.uniform(5, 8)
            skip_heater = (c.is_alien and TELL_HEATER in c.tells and not self.slips()) or \
                          (not (c.is_alien and TELL_HEATER in c.tells) and self.quirk())
            if skip_heater:
                # Shrug the cold off at the mess tables, or just tough it out at work.
                if rng.random() < 0.5:
                    c.goal = rng.choice(MESS_SPOTS)
                else:
                    c.cold = 35.0
                    c.task, c.goal, c.wait = "DUTY", c.work, rng.uniform(8, 15)
            else:
                c.goal = rng.choice(HEATER_SPOTS)
            return
        if c.is_alien and TELL_FOLLOW in c.tells and c.follow and c.follow.alive and not self.slips():
            c.task = "FOLLOW"
            c.goal = self.near_spot(c.follow.pos, self.diff["shadow"], TELL_HEATER in c.tells)
            c.wait = rng.uniform(2.0, 4.0)
            return
        if not c.is_alien and self.quirk():
            # A social call: drift over to wherever someone else is for a bit.
            others = [o for o in self.crew_alive() if o is not c]
            if others:
                mark = rng.choice(others)
                c.task, c.goal, c.wait = "WANDER", self.near_spot(mark.pos, 3), rng.uniform(4, 8)
                return
        if rng.random() < 0.2:
            c.task, c.goal, c.wait = "WANDER", self.random_spot(rng.choice(HUMAN_WANDER_ROOMS)), rng.uniform(4, 8)
            return
        c.task, c.goal, c.wait = "DUTY", c.work, rng.uniform(8, 15)

    def decide_rest(self, c):
        """Rest shift. Humans sleep, with the odd trip to the mess. The bunk-shy alien
        turns in and then keeps getting up, unless it remembers to behave."""
        rng = self.rng
        bunk_shy = c.is_alien and TELL_NOBUNK in c.tells
        if c.task == "REST" and c.pos == c.bunk:
            # Woke up on purpose: go for a walk.
            if bunk_shy:
                rooms = [r for r in NIGHT_WANDER_ROOMS if not (r == "HEATER" and TELL_HEATER in c.tells)]
                c.task, c.goal, c.wait = "WANDER", self.random_spot(rng.choice(rooms)), rng.uniform(8, 16)
            else:
                c.task, c.goal, c.wait = "WANDER", rng.choice(MESS_SPOTS), rng.uniform(3, 6)
            return
        # Heading to (or back to) the bunk. Decide now whether tonight is restless.
        c.task, c.goal = "REST", c.bunk
        if bunk_shy and not self.slips():
            c.wait = rng.uniform(4, 12)
        elif not bunk_shy and self.quirk():
            c.wait = rng.uniform(6, 14)
        else:
            c.wait = 9999.0

    def update_crew(self, c, dt):
        if not c.alive:
            return
        chill = 1.0 + max(0.0, MAX_HEAT - self.heat) / 30.0
        if c.task == "REST" and c.pos == c.bunk:
            c.cold = max(0.0, c.cold - 5 * dt)
        else:
            c.cold += c.cold_rate * chill * dt
        if c.task == "FLEE":
            self.flee_step(c)
            return
        at_goal = c.goal is None or c.pos == c.goal
        if at_goal:
            if c.task == "WARM":
                c.cold = max(0.0, c.cold - 30 * dt)
            elif c.cold >= 100 and c.task in ("DUTY", "WANDER", "FOLLOW"):
                self.decide(c)
                return
            c.wait -= dt
            if c.wait <= 0:
                if c.task == "WARM":
                    c.cold = 0.0
                    if c.room == "HEATER":
                        c.heater_visits += 1
                self.decide(c)
        else:
            if c.task == "FOLLOW" and c.follow and ROOM_OF.get(c.goal) != ROOM_OF.get(c.follow.pos):
                c.goal = self.near_spot(c.follow.pos, self.diff["shadow"], TELL_HEATER in c.tells)
            c.move_tick += 1
            if c.move_tick >= CREW_MOVE_TICKS:
                c.move_tick = 0
                self.step_toward(c)

    def step_toward(self, c):
        if c.path_goal != c.goal or not c.path:
            path = bfs_path(c.pos, c.goal)
            if path is None:          # nowhere to go: give up on this goal
                c.goal = c.pos
                c.path = []
                return
            c.path, c.path_goal = path, c.goal
        if c.path:
            c.x, c.y = c.path.pop(0)

    def flee_step(self, c):
        c.move_tick += 1
        if c.move_tick < FLEE_MOVE_TICKS:
            return
        c.move_tick = 0
        dist = bfs_distances(self.player)
        options = [p for p in neighbors(c.pos) if passable(p)] + [c.pos]
        self.rng.shuffle(options)
        c.x, c.y = max(options, key=lambda p: dist.get(p, 0))

    # ------------------------------------------------------- the alien
    def update_hunt(self, dt):
        a = self.alien
        if not a.alive or a.revealed:
            return
        if self.hunt_cd > 0:
            self.hunt_cd -= dt
            return
        room = a.room
        humans_here = [c for c in self.humans_alive() if c.room == room]
        if room is not None and len(humans_here) == 1 and ROOM_OF.get(self.player) != room:
            self.hunt += dt
            if self.hunt >= self.diff["hunt"]:
                self.take(humans_here[0], room)
        else:
            self.hunt = max(0.0, self.hunt - 2 * dt)

    def take(self, victim, room):
        victim.alive = False
        self.taken.append(victim)
        self.hunt = 0.0
        self.hunt_cd = self.diff["cooldown"]
        self.msg("** %s IS MISSING **" % victim.name, "alert")
        self.msg("LAST SEEN: %s" % room, "alert")
        self.cue("bell")
        self.cue("flash")
        if self.alien.follow is victim:
            others = [c for c in self.humans_alive()]
            self.alien.follow = self.rng.choice(others) if others else None
        if len(self.humans_alive()) < MIN_CREW:
            self.lose("TOO FEW CREW LEFT TO RUN THE STATION.")

    # --------------------------------------------------------- station
    def update_station(self, dt):
        self.power = max(0.0, self.power - self.diff["drain"] * dt)
        if self.power > 0:
            self.heat = min(MAX_HEAT, self.heat + HEAT_RISE * dt)
        else:
            self.heat -= HEAT_FALL * dt
        if self.power < 25 and not self.warned_power:
            self.warned_power = True
            self.msg("POWER LOW. FEED THE GENERATOR.", "warn")
            self.cue("bell")
        if self.power >= 40:
            self.warned_power = False
        if self.heat < 30 and not self.warned_heat:
            self.warned_heat = True
            self.msg("STATION FREEZING!", "alert")
            self.cue("bell")
        if self.heat >= 45:
            self.warned_heat = False
        if self.heat <= 0:
            self.heat = 0.0
            self.lose("THE STATION FROZE.")

    def change_shift(self):
        if self.shift == "WORK":
            self.shift, self.shift_left = "REST", REST_LEN
            self.msg("REST SHIFT. CREW TO BUNKS.", "info")
        else:
            for c in self.crew_alive():
                if c.pos == c.bunk:
                    c.nights_in_bunk += 1
            self.shift, self.shift_left = "WORK", WORK_LEN
            self.day += 1
            self.msg("DAY %d. WORK SHIFT." % self.day, "info")
        for c in self.crew_alive():
            if not c.revealed:
                if self.shift == "WORK":
                    c.cold *= 0.3
                self.decide(c)

    # ------------------------------------------------------------ tick
    def update(self, dt):
        if self.state != "PLAY":
            return
        self.time += dt
        self.shift_left -= dt
        if self.shift_left <= 0:
            self.change_shift()
        self.update_station(dt)
        for c in self.crew:
            self.update_crew(c, dt)
        self.update_hunt(dt)
        if self.shift == "REST":
            for c in self.crew_alive():
                c.night_ticks += 1
                c.night_out_ticks += c.pos != c.bunk
        self._score_acc += dt
        while self._score_acc >= 1.0:
            self._score_acc -= 1.0
            self.score += 1

    # -------------------------------------------------- player actions
    def move_player(self, dx, dy):
        nxt = (self.px + dx, self.py + dy)
        if passable(nxt):
            self.px, self.py = nxt
            return True
        return False

    def scan(self):
        near = self.near_crew()
        if not near:
            self.msg("NO ONE IN SCANNER RANGE.", "warn")
            return
        if self.scans <= 0:
            self.msg("SCANNER EMPTY.", "warn")
            return
        if self.power < SCAN_COST:
            self.msg("NOT ENOUGH POWER TO SCAN.", "warn")
            return
        target = near[0]
        self.scans -= 1
        self.power -= SCAN_COST
        self.cue("bell")
        if target.is_alien:
            target.revealed = True
            self.decide(target)
            self.msg("SCAN: %s IS THE ALIEN! CORNER IT. PRESS E." % target.name, "alert")
            self.cue("flash")
        else:
            target.cleared = True
            self.msg("SCAN: %s IS HUMAN. %d CHARGE%s LEFT." % (
                target.name, self.scans, "" if self.scans == 1 else "S"), "info")

    def eject(self):
        near = self.near_crew()
        if not near:
            self.msg("NO ONE CLOSE ENOUGH TO EJECT.", "warn")
            return
        target = near[0]
        if target.is_alien:
            bonus = WIN_BONUS + len(self.humans_alive()) * 1000 + self.scans * 500
            bonus += int(self.power) * 10 + self.fuel_crate * 100
            gut = not target.revealed
            if gut:
                bonus += GUT_CALL_BONUS
            self.score += bonus
            self.win("%s WENT OUT THE AIRLOCK. %s" % (
                target.name, "A GUT CALL, AND YOU WERE RIGHT." if gut else "THE STATION IS SAFE."))
        else:
            self.lose("%s WAS HUMAN. THE CREW TURNS ON YOU." % target.name)

    def fuel_action(self):
        p = self.player
        at_crate = any(adjacent(p, t) for t in CRATE_TILES)
        at_gen = any(adjacent(p, t) for t in GEN_TILES)
        if self.carrying and at_gen:
            self.carrying = False
            self.power = min(MAX_POWER, self.power + FUEL_POWER)
            self.score += 100
            self.msg("FUEL LOADED. POWER %d." % int(self.power), "info")
            self.cue("bell")
        elif not self.carrying and at_crate:
            if self.fuel_crate <= 0:
                self.msg("THE FUEL CRATE IS EMPTY.", "alert")
            else:
                self.fuel_crate -= 1
                self.carrying = True
                self.msg("FUEL CELL TAKEN. %d LEFT IN THE CRATE." % self.fuel_crate, "info")
        elif self.carrying:
            self.msg("LOAD THE CELL AT THE GENERATOR (GREEN, LOWER RIGHT).", "warn")
        else:
            self.msg("FUEL IS IN THE STORAGE CRATE (YELLOW, LOWER MIDDLE).", "warn")

    # -------------------------------------------------------- endings
    def win(self, reason):
        self.state = "WIN"
        self.end_reason = reason
        self.cue("bell")

    def lose(self, reason):
        if self.state != "PLAY":
            return
        self.state = "LOSE"
        self.end_reason = reason
        self.cue("bell")

    def reveal_lines(self):
        a = self.alien
        lines = ["THE ALIEN WAS %s." % a.name]
        for tell in ALL_TELLS:
            if tell not in a.tells:
                continue
            if tell == TELL_HEATER:
                lines.append("IT HARDLY EVER WENT TO THE HEATER (%d VISIT%s)." % (
                    a.heater_visits, "" if a.heater_visits == 1 else "S"))
            elif tell == TELL_FOLLOW:
                who = a.follow.name if a.follow else "A CREWMATE"
                lines.append("IT KEPT TURNING UP WHEREVER %s WAS." % who)
            elif tell == TELL_NOBUNK:
                pct = 100 * a.night_out_ticks // max(1, a.night_ticks)
                lines.append("IT WAS OUT OF ITS BUNK %d%% OF THE NIGHT." % pct)
        return lines
