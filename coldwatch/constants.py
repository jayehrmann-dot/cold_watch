"""Static data for Cold Watch: the station map, crew, difficulty and text."""

TICK = 0.08                # seconds per simulation tick (12.5 fps)
MAP_W, MAP_H = 36, 17
CELL_W = 2                 # terminal columns per map cell: fat Atari pixels
MIN_COLS, MIN_ROWS = 80, 24

# ------------------------------------------------------------------ tiles
WALL, FLOOR, DOOR = "#", ".", "+"
HEATER, BUNK, BENCH, CONSOLE, TABLE, CRATE, GEN = "H", "B", "L", "C", "T", "F", "G"
PASSABLE = {FLOOR, DOOR, BUNK}

# Rooms as inclusive floor rectangles (x0, y0, x1, y1).
ROOMS = {
    "HEATER": (1, 1, 8, 5),
    "BUNKS": (10, 1, 20, 5),
    "LAB": (22, 1, 30, 5),
    "COMMS": (32, 1, 34, 5),
    "HALL": (1, 7, 34, 9),
    "MESS": (1, 11, 11, 15),
    "STORAGE": (13, 11, 23, 15),
    "GENERATOR": (25, 11, 34, 15),
}
DOORS = [(4, 6), (15, 6), (26, 6), (33, 6), (6, 10), (18, 10), (29, 10)]

HEATER_TILES = [(4, 3), (5, 3), (4, 4), (5, 4)]
GEN_TILES = [(29, 12), (30, 12), (29, 13), (30, 13)]
BENCH_TILES = [(x, 2) for x in range(23, 30)]
CONSOLE_TILES = [(33, 2)]
TABLE_TILES = [(4, 13), (5, 13), (6, 13), (7, 13)]
CRATE_TILES = [(16, 13), (17, 13), (18, 13)]
BUNK_TILES = [(10, 3), (12, 3), (14, 3), (16, 3), (18, 3), (20, 3)]

# Where crew stand to warm up, and where the heater-shy alien goes instead.
HEATER_SPOTS = [(3, 3), (3, 4), (6, 3), (6, 4), (4, 2), (5, 2), (4, 5), (5, 5)]
MESS_SPOTS = [(4, 14), (5, 14), (6, 14), (7, 14), (4, 12), (5, 12), (6, 12), (7, 12)]
HEATER_DOOR_WAIT = (4, 7)            # hall tile just outside the heater room
HUMAN_WANDER_ROOMS = ["MESS", "HALL", "STORAGE"]
NIGHT_WANDER_ROOMS = ["LAB", "MESS", "STORAGE", "HALL", "GENERATOR", "COMMS"]

PLAYER_START = (18, 8)

# name, duty room, duty spot. Bunk i belongs to crew i.
CREW_DEFS = [
    ("ADA", "LAB", (24, 3)),
    ("BO", "LAB", (28, 3)),
    ("CY", "COMMS", (33, 3)),
    ("DEE", "GENERATOR", (28, 13)),
    ("ELI", "STORAGE", (19, 13)),
    ("FAY", "MESS", (5, 12)),
]

# ------------------------------------------------------------------ rules
TELL_HEATER = "RARELY WARMS UP AT THE HEATER"
TELL_FOLLOW = "KEEPS TURNING UP NEAR ONE CREWMATE"
TELL_NOBUNK = "KEEPS LEAVING ITS BUNK AT NIGHT"
ALL_TELLS = [TELL_HEATER, TELL_FOLLOW, TELL_NOBUNK]

# slip: chance per opportunity that the alien ignores its tell and acts human.
# quirk: chance per opportunity that a human does something tell-like anyway.
# shadow: how close the shadowing alien keeps to its mark (in tiles).
DIFFICULTY = {
    1: dict(name="EASY", tells=3, scans=4, drain=0.6, fuel=12, hunt=9.0, cooldown=70.0,
            slip=0.15, quirk=0.06, shadow=2),
    2: dict(name="NORMAL", tells=2, scans=3, drain=0.8, fuel=10, hunt=7.0, cooldown=50.0,
            slip=0.30, quirk=0.12, shadow=3),
    3: dict(name="HARD", tells=1, scans=2, drain=1.0, fuel=8, hunt=5.5, cooldown=40.0,
            slip=0.45, quirk=0.18, shadow=3),
}

WORK_LEN, REST_LEN = 45.0, 25.0     # seconds per shift
MAX_POWER, MAX_HEAT = 100.0, 70.0
SCAN_COST = 20.0                    # power burned by one scan
FUEL_POWER = 30.0                   # power from one fuel cell
HEAT_RISE, HEAT_FALL = 2.0, 1.5     # heat per second with / without power
GRACE = 35.0                        # seconds before the alien may strike
MIN_CREW = 3                        # station fails below this many humans
CREW_MOVE_TICKS = 3                 # crew step every N ticks
FLEE_MOVE_TICKS = 2                 # a revealed alien steps every N ticks

WIN_BONUS = 3000
GUT_CALL_BONUS = 2000

# ------------------------------------------------------------------ text
TITLE_WORD = "COLD WATCH"

FONT = {
    "C": ["#####", "#    ", "#    ", "#    ", "#####"],
    "O": ["#####", "#   #", "#   #", "#   #", "#####"],
    "L": ["#    ", "#    ", "#    ", "#    ", "#####"],
    "D": ["#### ", "#   #", "#   #", "#   #", "#### "],
    "W": ["#   #", "#   #", "# # #", "# # #", " # # "],
    "A": [" ### ", "#   #", "#####", "#   #", "#   #"],
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  "],
    "H": ["#   #", "#   #", "#####", "#   #", "#   #"],
    " ": ["   ", "   ", "   ", "   ", "   "],
}

STORY = [
    "OUTPOST 9. SEVENTY-ONE DEGREES SOUTH. WINTER.",
    "SOMETHING CAME BACK WITH THE ICE CORES.",
    "IT LOOKS LIKE ONE OF YOUR CREW. IT ACTS ALMOST LIKE THEM.",
    "",
    "WATCH THEM OVER SEVERAL SHIFTS. WHO HARDLY EVER WARMS UP AT THE HEATER?",
    "WHO KEEPS TURNING UP NEAR THE SAME CREWMATE? WHO KEEPS LEAVING THEIR BUNK?",
    "EVERYONE HAS AN OFF DAY. THE ALIEN HAS A PATTERN.",
    "",
    "KEEP THE GENERATOR FED. EVERY SCAN BURNS POWER YOU NEED FOR HEAT.",
    "EJECT THE WRONG PERSON AND THE CREW TURNS ON YOU.",
]

HELP = [
    "CONTROLS",
    "  ARROWS / WASD   MOVE",
    "  SPACE           SCAN THE CREWMATE NEXT TO YOU (COSTS A CHARGE + 20 POWER)",
    "  E               EJECT THE CREWMATE NEXT TO YOU  (RIGHT: WIN.  WRONG: LOSE)",
    "  F               TAKE FUEL AT THE CRATE / LOAD IT AT THE GENERATOR",
    "  N               CREW ROSTER       P  PAUSE       B  TERMINAL BELL",
    "  H               THIS SCREEN       Q  QUIT (FROM PAUSE)",
    "",
    "LEGEND",
    "  YELLOW WALLS   RED/YELLOW HEATER   BLUE BUNKS   GREEN LAB BENCH",
    "  CYAN CONSOLE   MAGENTA MESS TABLES   YELLOW FUEL CRATE   GREEN GENERATOR",
    "  CREW ARE LETTERED BLOCKS. YOU ARE THE WHITE BLOCK MARKED ME.",
    "  A LOWERCASE LETTER MEANS THAT CREWMATE SCANNED HUMAN.",
    "",
    "THE STATION",
    "  POWER DRAINS ALL THE TIME. AT ZERO THE HEAT DROPS. AT ZERO HEAT YOU LOSE.",
    "  COLD CREW GO TO THE HEATER. AT REST SHIFT THEY GO TO THEIR BUNKS.",
    "  HUMANS SOMETIMES SKIP THE HEATER, VISIT A FRIEND, OR GET UP AT NIGHT.",
    "  THE ALIEN DOES ONE OR MORE OF THOSE FAR MORE OFTEN. COUNT, DO NOT GUESS.",
    "  THE ALIEN TAKES ANYONE IT CATCHES ALONE IN A ROOM. IT WILL NOT ACT",
    "  WHILE YOU ARE IN THE ROOM. LOSE THREE CREW AND THE STATION FAILS.",
]
