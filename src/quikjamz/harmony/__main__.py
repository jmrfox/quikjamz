"""Print some generated loops, for listening/reading while tuning the harmony engine.

    uv run python -m quikjamz.harmony --key D --mode dorian --harm-adv 0.4 --count 6
    uv run python -m quikjamz.harmony --mode dorian --count 4 --midi out/loops.mid
"""

from __future__ import annotations

import argparse
import random
import sys

from ..theory.scales import choose_mode, get_scale, make_key
from .progression import Loop, generate_loop


def format_bars(loop: Loop, style: str) -> str:
    """'| Dm7 . | G7 . |' style chart, one cell per bar, '/' where a chord is held."""
    bpb = loop.beats_per_bar
    bars: list[list[str]] = [[] for _ in range(loop.bars)]
    beat = 0
    for event in loop.events:
        bars[beat // bpb].append(event.chord.symbol(loop.key, style))
        beat += event.beats
    cells = [" ".join(chords) if chords else "/" for chords in bars]
    width = max(len(c) for c in cells)
    return "| " + " | ".join(c.ljust(width) for c in cells) + " |"


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m quikjamz.harmony", description=__doc__.splitlines()[0])
    p.add_argument("--key", default="C", help="tonic, e.g. D, Eb, F#")
    p.add_argument("--mode", default=None, help="ionian, dorian, ... (default: picked from brightness)")
    p.add_argument("--harm-adv", type=float, default=0.3)
    p.add_argument("--complexity", type=float, default=0.5)
    p.add_argument("--tension", type=float, default=0.5)
    p.add_argument("--brightness", type=float, default=0.5)
    p.add_argument("--beats", type=int, default=4, help="beats per bar")
    p.add_argument("--count", type=int, default=6)
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--style", choices=["plain", "jazz"], default="plain")
    p.add_argument("--verbose", "-v", action="store_true", help="show Roman numerals and tiers")
    p.add_argument("--midi", metavar="PATH", help="also write all loops, in order, to one .mid file")
    p.add_argument("--tempo", type=float, default=100, help="MIDI tempo in beats per minute")
    p.add_argument("--beat-unit", type=int, default=4, choices=[2, 4, 8], help="4 = quarter, 8 = eighth")
    p.add_argument("--passes", type=int, default=2, help="times each loop repeats in the MIDI")
    p.add_argument("--no-click", action="store_true", help="leave out the click track")
    args = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252

    seed = args.seed if args.seed is not None else random.randrange(10**6)
    rng = random.Random(seed)
    scale = get_scale(args.mode) if args.mode else choose_mode(args.brightness, rng)
    key = make_key(args.key, scale)

    print(f"{key}   harm_adv={args.harm_adv} complexity={args.complexity} "
          f"tension={args.tension} brightness={args.brightness}   seed={seed}\n")
    loops = []
    for _ in range(args.count):
        loop = generate_loop(
            key, rng,
            harm_adv=args.harm_adv, complexity=args.complexity, tension=args.tension,
            brightness=args.brightness, beats_per_bar=args.beats,
        )
        end = "→ home" if loop.ending == "resolve" else f"→ hang on {loop.final.symbol(key, args.style)}"
        print(f"{format_bars(loop, args.style)}   {end}")
        if args.verbose:
            romans = "  ".join(f"{c.roman()}[{c.tier}{c.fn}]" for c in loop.chords)
            print(f"    {romans}    surprise {loop.surprise:.2f} (target {loop.target:.2f})")
        loops.append(loop)
    print()

    if args.midi:
        from ..render.midi import MidiSection, write_midi

        path = write_midi(
            args.midi,
            [MidiSection(loop, passes=args.passes, beat_unit=args.beat_unit) for loop in loops],
            quarter_bpm=args.tempo * 4 / args.beat_unit,
            click=not args.no_click,
        )
        print(f"MIDI written to {path}  ({len(loops)} loops x {args.passes} passes, "
              f"1 bar rest between loops)")


if __name__ == "__main__":
    main()
