"""quikjamz: generate a jam guide.

    quikjamz --mood mysterious --harm-adv 0.7 --arc build --key D --mode dorian \\
             --sections 5 --labels motion --seed 42 --pdf out/jam.pdf --midi out/jam.mid
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .form import LABEL_STYLES, TEMPLATES
from .jam import JamConfig, generate_jam
from .knobs import ARC_NAMES, DEFAULT_ARC, Knobs, moods
from .render.text import render_text


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="quikjamz", description="Generate a jam guide for improvisers.")
    p.add_argument("--title", default="Untitled Jam")
    p.add_argument("--seed", type=int, help="same seed + same options = same jam")
    p.add_argument("--mood", choices=sorted(moods()), help="starting knob values (default: random)")
    p.add_argument("--arc", choices=ARC_NAMES, default=DEFAULT_ARC, help=f"default: {DEFAULT_ARC}")
    p.add_argument("--key", help="tonic, e.g. D, Eb, F# (default: random)")
    p.add_argument("--mode", help="ionian, dorian, ... (default: picked from brightness)")
    p.add_argument("--tempo", type=int, help="quarter-note BPM (default: from energy)")
    p.add_argument("--meter", help="e.g. 4/4, 6/8, 7/8, 7/8:3+2+2 (default: from rhythmic adventurousness)")
    p.add_argument("--sections", type=int, help="number of sections (default: 4-6)")
    p.add_argument("--form", choices=sorted(TEMPLATES), help="form template (default: from stability)")
    p.add_argument("--labels", choices=LABEL_STYLES, default="letters", help="section label style")
    p.add_argument("--style", choices=["plain", "jazz"], default="plain", help="chord symbol style")

    knobs = p.add_argument_group("knobs (0-1, override the mood)")
    for name in Knobs.names():
        knobs.add_argument(f"--{name.replace('_', '-')}", type=float, dest=f"knob_{name}")

    out = p.add_argument_group("output")
    out.add_argument("--midi", metavar="PATH", help="write the jam to one .mid file")
    out.add_argument("--no-click", action="store_true", help="leave the click track out of the MIDI")
    out.add_argument("--pdf", metavar="PATH", help="write the jam sheet as a PDF")
    out.add_argument("--paper", choices=["letter", "a4"], default="letter", help="PDF paper size")
    out.add_argument("--json", metavar="PATH", help="write the jam plan as JSON")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252

    overrides = {
        name: getattr(args, f"knob_{name}")
        for name in Knobs.names()
        if getattr(args, f"knob_{name}") is not None
    }
    config = JamConfig(
        title=args.title, seed=args.seed, mood=args.mood, knobs=overrides, arc=args.arc,
        key=args.key, mode=args.mode, tempo=args.tempo, meter=args.meter,
        sections=args.sections, form=args.form, labels=args.labels,
    )
    try:
        jam = generate_jam(config)
    except ValueError as err:
        print(f"quikjamz: {err}", file=sys.stderr)
        return 2

    print(render_text(jam, args.style))

    if args.json:
        path = Path(args.json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(jam.to_dict(args.style), indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nJSON written to {path}")
    if args.pdf:
        from .render.sheet import render_pdf

        path = render_pdf(jam, args.pdf, style=args.style, paper=args.paper)
        print(f"\nPDF written to {path}")
    if args.midi:
        from .render.midi import jam_to_midi

        path = jam_to_midi(jam, args.midi, click=not args.no_click)
        print(f"\nMIDI written to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
