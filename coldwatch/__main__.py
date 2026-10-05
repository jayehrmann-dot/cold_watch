"""Entry point: python3 -m coldwatch [--sound] [--level N] [--seed N] [--selftest]"""
import curses
import locale
import os
import sys

USAGE = """usage: python3 -m coldwatch [--sound] [--level 1|2|3] [--seed N] [--selftest]

  --sound      ring the terminal bell on scans, alarms and disappearances
  --level N    start the title screen on EASY (1), NORMAL (2) or HARD (3)
  --seed N     fixed random seed, for a repeatable station
  --selftest   run the simulation headlessly and print what happened"""


def arg_value(argv, flag, default, cast=int):
    if flag in argv:
        i = argv.index(flag)
        try:
            return cast(argv[i + 1])
        except (IndexError, ValueError):
            print("bad value for %s" % flag)
            sys.exit(2)
    return default


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "-h" in argv or "--help" in argv:
        print(USAGE)
        return 0
    level = arg_value(argv, "--level", 2)
    if level not in (1, 2, 3):
        print("level must be 1, 2 or 3")
        return 2
    seed = arg_value(argv, "--seed", None)
    if "--selftest" in argv:
        from .selftest import run_selftest
        return run_selftest(seed)
    sound = "--sound" in argv or "-s" in argv

    locale.setlocale(locale.LC_ALL, "")
    os.environ.setdefault("ESCDELAY", "25")
    if not os.environ.get("TERM"):
        os.environ["TERM"] = "xterm-256color"
    from .app import App

    def run(stdscr):
        return App(stdscr, sound=sound, level=level, seed=seed).run()

    try:
        high = curses.wrapper(run)
    except KeyboardInterrupt:
        high = None
    if high:
        print("Watch ended. High score: %d. Stay warm." % high)
    else:
        print("Watch ended. Stay warm.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
