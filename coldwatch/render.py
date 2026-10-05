"""Curses drawing for Cold Watch. Fat two-column cells, eight colours, flicker."""
import curses

from .constants import (
    BENCH, BUNK, CELL_W, CONSOLE, CRATE, DOOR, FLOOR, FONT, GEN, HEATER, HELP,
    MAP_H, MAP_W, MAX_HEAT, MAX_POWER, MIN_COLS, MIN_ROWS, ROOMS, STORY,
    TABLE, TITLE_WORD, WALL,
)
from .world import GRID

RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(1, 8)
CREW_COLORS = [RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN]
HAS_COLOR = False

HUD_ROWS = 3
MAP_TOP = HUD_ROWS
MAP_LEFT = 2
LOG_TOP = MAP_TOP + MAP_H
HELP_ROW = LOG_TOP + 2


def init_colors():
    global HAS_COLOR
    HAS_COLOR = curses.has_colors()
    if not HAS_COLOR:
        return
    curses.start_color()
    try:
        curses.use_default_colors()
        bg = -1
    except curses.error:
        bg = curses.COLOR_BLACK
    for i, col in enumerate(
        (curses.COLOR_RED, curses.COLOR_GREEN, curses.COLOR_YELLOW, curses.COLOR_BLUE,
         curses.COLOR_MAGENTA, curses.COLOR_CYAN, curses.COLOR_WHITE), 1):
        curses.init_pair(i, col, bg)


def cp(n, extra=0):
    return (curses.color_pair(n) if HAS_COLOR else 0) | extra


def put(win, y, x, s, attr=0):
    try:
        win.addstr(y, x, s, attr)
    except curses.error:
        pass


def bar(value, maximum, width):
    filled = int(round(width * max(0.0, min(1.0, value / maximum))))
    return "█" * filled + "░" * (width - filled)


def too_small(win):
    rows, cols = win.getmaxyx()
    if rows >= MIN_ROWS and cols >= MIN_COLS:
        return False
    win.erase()
    put(win, 0, 0, "COLD WATCH NEEDS A %dx%d TERMINAL." % (MIN_COLS, MIN_ROWS), cp(YELLOW, curses.A_BOLD))
    put(win, 1, 0, "THIS ONE IS %dx%d. MAKE IT BIGGER." % (cols, rows))
    win.refresh()
    return True


# ------------------------------------------------------------------ title
def title_art():
    rows = [""] * 5
    for ch in TITLE_WORD:
        glyph = FONT[ch]
        for i in range(5):
            rows[i] += glyph[i].replace("#", "█") + " "
    return rows


def draw_title(win, frame, level, high, diff_name):
    win.erase()
    rows, cols = win.getmaxyx()
    art = title_art()
    col = max(0, (cols - len(art[0])) // 2)
    color = [RED, YELLOW, WHITE, CYAN, BLUE, MAGENTA][(frame // 4) % 6]
    for i, line in enumerate(art):
        put(win, 1 + i, col, line, cp(color, curses.A_BOLD))
    y = 7
    for line in STORY:
        put(win, y, max(0, (cols - len(line)) // 2), line, cp(WHITE))
        y += 1
    y += 1
    sel = "GAME SELECT:   1 EASY    2 NORMAL    3 HARD"
    put(win, y, (cols - len(sel)) // 2, sel, cp(YELLOW))
    chosen = "> %s <" % diff_name
    put(win, y + 1, (cols - len(chosen)) // 2, chosen, cp(GREEN, curses.A_BOLD))
    hint = "PRESS SPACE TO START      H  CONTROLS      Q  QUIT"
    attr = cp(WHITE, curses.A_BOLD) if (frame // 6) % 2 else cp(WHITE)
    put(win, y + 3, (cols - len(hint)) // 2, hint, attr)
    hs = "HI SCORE %06d" % high
    put(win, y + 5, (cols - len(hs)) // 2, hs, cp(CYAN))
    win.refresh()


# -------------------------------------------------------------------- map
def tile_glyph(tile, frame, w):
    if tile == WALL:
        return "██", cp(RED if w.flash_frames > 0 else YELLOW, curses.A_DIM)
    if tile == FLOOR:
        return "  ", 0
    if tile == DOOR:
        return "░░", cp(CYAN, curses.A_DIM)
    if tile == HEATER:
        if w.power > 0:
            return "▓▓", cp(RED if (frame // 2) % 2 else YELLOW, curses.A_BOLD)
        return "▓▓", cp(RED, curses.A_DIM)
    if tile == BUNK:
        return "▄▄", cp(BLUE, curses.A_BOLD)
    if tile == BENCH:
        return "▀▀", cp(GREEN)
    if tile == CONSOLE:
        return "▀▀", cp(CYAN, curses.A_BOLD)
    if tile == TABLE:
        return "▀▀", cp(MAGENTA)
    if tile == CRATE:
        return "▓▓", cp(YELLOW, curses.A_BOLD if w.fuel_crate > 0 else curses.A_DIM)
    if tile == GEN:
        if w.power > 0:
            return "▓▓", cp(GREEN, curses.A_BOLD if (frame // 3) % 2 else 0)
        return "▓▓", cp(GREEN, curses.A_DIM)
    return "??", 0


def sprite_glyph(c, frame):
    if c.revealed:
        return ("XX" if frame % 2 else "X "), cp(RED, curses.A_REVERSE | curses.A_BOLD)
    letter = c.name[0].lower() if c.cleared else c.name[0]
    return letter + " ", cp(CREW_COLORS[c.idx], curses.A_REVERSE)


def draw_map(win, w, frame):
    for y in range(MAP_H):
        for x in range(MAP_W):
            glyph, attr = tile_glyph(GRID[y][x], frame, w)
            put(win, MAP_TOP + y, MAP_LEFT + x * CELL_W, glyph, attr)
    for name, (x0, y0, x1, y1) in ROOMS.items():
        label = name[: (x1 - x0 + 1) * CELL_W]
        put(win, MAP_TOP + y0, MAP_LEFT + x0 * CELL_W, label, cp(WHITE, curses.A_DIM))
    # Sprites. When several share a cell they take turns, 2600 style.
    cells = {}
    for c in w.crew:
        if c.alive:
            cells.setdefault(c.pos, []).append(sprite_glyph(c, frame))
    cells.setdefault(w.player, []).append(("ME", cp(WHITE, curses.A_REVERSE | curses.A_BOLD)))
    for (x, y), sprites in cells.items():
        glyph, attr = sprites[frame % len(sprites)]
        put(win, MAP_TOP + y, MAP_LEFT + x * CELL_W, glyph, attr)


# -------------------------------------------------------------------- hud
def draw_hud(win, w, frame, high, bell_on):
    rows, cols = win.getmaxyx()
    put(win, 0, 1, "COLD WATCH", cp(CYAN, curses.A_BOLD))
    put(win, 0, 14, w.diff["name"], cp(WHITE, curses.A_DIM))
    put(win, 0, 28, "SCORE %06d" % w.score, cp(WHITE, curses.A_BOLD))
    put(win, 0, 46, "HI %06d" % max(high, w.score), cp(WHITE))
    put(win, 0, 60, "BELL %s" % ("ON " if bell_on else "OFF"), cp(WHITE, curses.A_DIM))

    low_power = w.power < 25 and (frame // 3) % 2
    put(win, 1, 1, "POWER", cp(RED if low_power else WHITE, curses.A_BOLD if low_power else 0))
    put(win, 1, 7, bar(w.power, MAX_POWER, 12), cp(GREEN if w.power >= 40 else YELLOW if w.power >= 20 else RED))
    put(win, 1, 20, "%3d" % int(w.power), cp(WHITE))
    low_heat = w.heat < 30 and (frame // 3) % 2
    put(win, 1, 26, "HEAT", cp(RED if low_heat else WHITE, curses.A_BOLD if low_heat else 0))
    put(win, 1, 31, bar(w.heat, MAX_HEAT, 10), cp(RED if w.heat >= 45 else YELLOW if w.heat >= 25 else BLUE, curses.A_BOLD))
    put(win, 1, 42, "%3d" % int(w.heat), cp(WHITE))
    put(win, 1, 48, "SCAN", cp(WHITE))
    put(win, 1, 53, "▮" * w.scans + "▯" * max(0, w.diff["scans"] - w.scans), cp(CYAN, curses.A_BOLD))
    put(win, 1, 60, "CRATE %2d" % w.fuel_crate, cp(YELLOW))
    if w.carrying:
        put(win, 1, 70, "[FUEL]", cp(YELLOW, curses.A_REVERSE if (frame // 4) % 2 else curses.A_BOLD))

    mins, secs = divmod(int(max(0, w.shift_left)), 60)
    shift_attr = cp(YELLOW if w.shift == "WORK" else BLUE, curses.A_BOLD)
    put(win, 2, 1, "DAY %d" % w.day, cp(WHITE))
    put(win, 2, 9, "%s SHIFT %d:%02d" % (w.shift, mins, secs), shift_attr)
    put(win, 2, 28, "CREW %d" % len(w.crew_alive()), cp(WHITE))
    near = w.near_crew()
    if near:
        names = " ".join(c.name for c in near[:3])
        put(win, 2, 38, "NEAR: " + names, cp(GREEN, curses.A_BOLD))


def draw_log(win, w):
    rows, cols = win.getmaxyx()
    recent = w.log[-2:]
    for i in range(2):
        put(win, LOG_TOP + i, 0, " " * (cols - 1))
    for i, (text, kind) in enumerate(recent):
        attr = {"alert": cp(RED, curses.A_BOLD), "warn": cp(YELLOW), "info": cp(WHITE)}[kind]
        put(win, LOG_TOP + i, 1, text[: cols - 2], attr)
    help_line = "ARROWS/WASD MOVE   SPACE SCAN   E EJECT   F FUEL   N ROSTER   P PAUSE   H HELP"
    put(win, HELP_ROW, 1, help_line[: cols - 2], cp(WHITE, curses.A_DIM))


def draw_game(win, w, frame, high, bell_on):
    win.erase()
    draw_hud(win, w, frame, high, bell_on)
    draw_map(win, w, frame)
    draw_log(win, w)


# ---------------------------------------------------------------- overlays
def draw_box(win, lines, color=WHITE, title=None):
    rows, cols = win.getmaxyx()
    width = min(cols - 4, max(len(l) for l in lines) + 4)
    height = len(lines) + 2
    top = max(0, (rows - height) // 2)
    left = max(0, (cols - width) // 2)
    border = cp(color, curses.A_BOLD)
    put(win, top, left, "█" * width, border)
    for i, line in enumerate(lines):
        put(win, top + 1 + i, left, "█", border)
        put(win, top + 1 + i, left + 1, " " * (width - 2))
        put(win, top + 1 + i, left + 2, line[: width - 4])
        put(win, top + 1 + i, left + width - 1, "█", border)
    put(win, top + height - 1, left, "█" * width, border)
    if title:
        put(win, top, left + 2, " %s " % title, cp(color, curses.A_REVERSE | curses.A_BOLD))


def draw_help(win):
    draw_box(win, HELP + ["", "PRESS ANY KEY TO GO BACK"], CYAN, "HOW TO PLAY")


def draw_pause(win):
    draw_box(win, ["GAME PAUSED", "", "P  RESUME", "Q  QUIT TO TITLE"], YELLOW)


def draw_roster(win, w):
    lines = ["LETTER  NAME  DUTY        STATUS", ""]
    for c in w.crew:
        lines.append("  %s     %-4s  %-10s  %s" % (c.name[0], c.name, c.role, c.status()))
    lines += ["", "SCANNER %d/%d   POWER %d   HEAT %d" % (w.scans, w.diff["scans"], int(w.power), int(w.heat)),
              "", "PRESS N OR ANY KEY TO CLOSE"]
    draw_box(win, lines, GREEN, "CREW ROSTER")


def draw_end(win, w, frame, high, new_high):
    won = w.state == "WIN"
    head = "STATION SECURE" if won else "STATION LOST"
    lines = [head, "", w.end_reason, ""]
    lines += w.reveal_lines()
    lines += ["", "SURVIVED %d DAY%s.  %d OF %d CREW REMAIN." % (
        w.day, "" if w.day == 1 else "S", len(w.humans_alive()), len(w.crew) - 1)]
    lines += ["SCORE %06d%s" % (w.score, "   NEW HIGH SCORE!" if new_high else "   HI %06d" % high), ""]
    lines += ["SPACE  PLAY AGAIN      T  TITLE      Q  QUIT"]
    color = GREEN if won else RED
    if (frame // 5) % 2 == 0:
        color = WHITE
    draw_box(win, lines, color, "GAME OVER")
