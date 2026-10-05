"""Curses front end for Cold Watch: screens, input and the fixed-step loop."""
import curses
import json
import os
import time

from .constants import DIFFICULTY, TICK
from . import render
from .world import World

HIGH_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "highscore.json")

MOVES = {
    curses.KEY_UP: (0, -1), curses.KEY_DOWN: (0, 1), curses.KEY_LEFT: (-1, 0), curses.KEY_RIGHT: (1, 0),
    ord("w"): (0, -1), ord("s"): (0, 1), ord("a"): (-1, 0), ord("d"): (1, 0),
    ord("W"): (0, -1), ord("S"): (0, 1), ord("A"): (-1, 0), ord("D"): (1, 0),
}


def load_high():
    try:
        with open(HIGH_PATH) as fh:
            return int(json.load(fh).get("high", 0))
    except (OSError, ValueError, AttributeError):
        return 0


def save_high(score):
    try:
        with open(HIGH_PATH, "w") as fh:
            json.dump({"high": int(score)}, fh)
    except OSError:
        pass


class App:
    def __init__(self, stdscr, sound=False, level=2, seed=None):
        self.scr = stdscr
        self.bell = sound
        self.level = level
        self.seed = seed
        self.high = load_high()
        self.frame = 0
        render.init_colors()
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        stdscr.keypad(True)
        stdscr.nodelay(True)

    # ------------------------------------------------------------ utils
    def ring(self):
        if self.bell:
            curses.beep()

    def drain(self):
        keys = []
        while True:
            k = self.scr.getch()
            if k == -1:
                return keys
            keys.append(k)

    def sleep_frame(self, started):
        delay = TICK - (time.monotonic() - started)
        if delay > 0:
            time.sleep(delay)
        self.frame += 1

    def wait_any_key(self, draw):
        """Show an overlay until a key is pressed. Returns the key."""
        while True:
            started = time.monotonic()
            if not render.too_small(self.scr):
                draw()
                self.scr.refresh()
            keys = [k for k in self.drain() if k != curses.KEY_RESIZE]
            if keys:
                return keys[0]
            self.sleep_frame(started)

    # ---------------------------------------------------------- screens
    def run(self):
        while True:
            action = self.title()
            if action == "quit":
                return self.high
            while True:
                result = self.play()
                if result != "again":
                    break
            if result == "quit":
                return self.high

    def title(self):
        while True:
            started = time.monotonic()
            if not render.too_small(self.scr):
                render.draw_title(self.scr, self.frame, self.level, self.high, DIFFICULTY[self.level]["name"])
            for k in self.drain():
                if k in (ord("1"), ord("2"), ord("3")):
                    self.level = k - ord("0")
                elif k in (ord(" "), ord("\n"), curses.KEY_ENTER):
                    return "play"
                elif k in (ord("h"), ord("H"), ord("?")):
                    self.wait_any_key(lambda: render.draw_help(self.scr))
                elif k in (ord("b"), ord("B")):
                    self.bell = not self.bell
                elif k in (ord("q"), ord("Q"), 27):
                    return "quit"
            self.sleep_frame(started)

    def play(self):
        w = World(self.level, self.seed)
        overlay = None
        acc = 0.0
        last = time.monotonic()
        new_high = False
        while True:
            started = time.monotonic()
            acc += started - last
            last = started

            moved = False
            for k in self.drain():
                if k == curses.KEY_RESIZE:
                    continue
                if w.state != "PLAY":
                    if k == ord(" "):
                        return "again"
                    if k in (ord("t"), ord("T"), 27):
                        return "title"
                    if k in (ord("q"), ord("Q")):
                        return "quit"
                    continue
                if overlay == "pause":
                    if k in (ord("p"), ord("P"), 27):
                        overlay = None
                    elif k in (ord("q"), ord("Q")):
                        return "title"
                    continue
                if overlay in ("roster", "help"):
                    overlay = None
                    continue
                if k in MOVES:
                    if not moved:
                        moved = w.move_player(*MOVES[k]) or True
                elif k == ord(" "):
                    w.scan()
                elif k in (ord("e"), ord("E")):
                    w.eject()
                elif k in (ord("f"), ord("F")):
                    w.fuel_action()
                elif k in (ord("n"), ord("N")):
                    overlay = "roster"
                elif k in (ord("h"), ord("H"), ord("?")):
                    overlay = "help"
                elif k in (ord("p"), ord("P"), ord("q"), ord("Q")):
                    overlay = "pause"
                elif k in (ord("b"), ord("B")):
                    self.bell = not self.bell

            # fixed-step simulation, frozen while an overlay is up
            if overlay is None and w.state == "PLAY":
                while acc >= TICK:
                    w.update(TICK)
                    acc -= TICK
            else:
                acc = 0.0

            for ev in w.events:
                if ev == "bell":
                    self.ring()
                elif ev == "flash":
                    w.flash_frames = 6
            w.events.clear()

            if w.state != "PLAY" and not new_high and w.score > self.high:
                new_high = True
                self.high = w.score
                save_high(w.score)

            if not render.too_small(self.scr):
                render.draw_game(self.scr, w, self.frame, self.high, self.bell)
                if overlay == "pause":
                    render.draw_pause(self.scr)
                elif overlay == "roster":
                    render.draw_roster(self.scr, w)
                elif overlay == "help":
                    render.draw_help(self.scr)
                if w.state != "PLAY":
                    render.draw_end(self.scr, w, self.frame, self.high, new_high)
                self.scr.refresh()
            if w.flash_frames > 0:
                w.flash_frames -= 1
            self.sleep_frame(started)
