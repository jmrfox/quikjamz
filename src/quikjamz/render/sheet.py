"""PDF jam sheet via Typst (spec section 8).

Python turns a Jam into sheet-ready data (display strings, bar cells, road map);
the Typst template (sheet.typ) only lays it out.
"""

from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path

from ..jam import Jam, Section
from ..theory.chords import Chord
from ..theory.scales import Key

PAPERS = {"letter": "us-letter", "a4": "a4"}
BARS_PER_ROW = 8


def pretty(text: str) -> str:
    """Use real accidentals: Bb -> B♭, F# -> F♯, 7(b9,#11) -> 7(♭9,♯11)."""
    text = re.sub(r"(?<=[A-G])b", "♭", text)
    text = re.sub(r"(?<=[A-G])#", "♯", text)
    text = re.sub(r"b(?=\d)", "♭", text)
    return re.sub(r"#(?=\d)", "♯", text)


def chord_display(chord: Chord, key: Key, style: str) -> dict:
    root = pretty(str(key.note(chord.degree, chord.alteration)))
    bass = pretty(str(key.note(*chord.bass))) if chord.bass else None
    return {"root": root, "suffix": pretty(chord.suffix(style)), "bass": bass}


def key_display(key: Key) -> str:
    return f"{pretty(str(key.tonic))} {key.scale.display}"


def _cue_short(section: Section) -> str:
    cue = section.cue
    return {"count": cue.text, "open": "open", "signal": "on cue"}.get(cue.type, cue.type)


def _bars(section: Section, style: str) -> list[dict]:
    """Bar cells.

    A bar where every chord starts on beat 1 is just its chord (or '%' when held).
    A bar with a mid-bar change gets `slots`, one per beat in real-book slash
    notation: `C / / G` puts G on beat 4. A chord on an off-beat (a push) sits in
    the slot of the beat it follows and is marked `push`.
    """
    from ..harmony.rhythm import strong_points

    loop = section.loop
    bpb = loop.beats_per_bar
    groups = set(strong_points(section.meter))
    starts_by_bar: dict[int, list[tuple[float, dict]]] = {}
    for event, start in zip(loop.events, loop.starts()):
        bar, pos = int(start // bpb), start % bpb
        chord = chord_display(event.chord, section.key, style)
        chord["push"] = event.push or pos != int(pos)
        starts_by_bar.setdefault(bar, []).append((pos, chord))

    cells = []
    for i in range(loop.bars):
        entries = starts_by_bar.get(i, [])
        cell = {"n": section.start_bar + i, "chords": [c for _, c in entries], "slots": None}
        if any(pos for pos, _ in entries):
            slots = []
            for beat in range(bpb):
                here = [c for pos, c in entries if beat <= pos < beat + 1]
                group = beat in groups  # a wider gap before each beat group (2+2+3, ...)
                for j, c in enumerate(here or [None]):
                    slots.append({"chord": c, "group": group and j == 0})
            cell["slots"] = slots
        cells.append(cell)
    return cells


def _notes(jam: Jam, section: Section) -> list[str]:
    notes = []
    prev = jam.sections[section.index - 1] if section.index > 0 else None
    if prev is not None and section.key != prev.key:
        notes.append(f"key → {key_display(section.key)}")
    if prev is not None and section.meter != prev.meter:
        notes.append(f"meter → {section.meter}")
    if section.return_of is not None:
        notes.append(f"returns to {jam.sections[section.return_of].label}")
    if section.drift_of is not None:
        notes.append(f"grows out of {jam.sections[section.drift_of].label}")
    return notes


def _line(section: Section, style: str) -> str:
    parts = [", ".join(section.vibe)]
    if section.start_cue:
        parts.append(f"start: {section.start_cue}")
    if section.cue.type != "count":
        parts.append(section.cue.text)
    if section.loop.ending == "resolve":
        parts.append("last time: land home")
    else:
        final = chord_display(section.loop.final, section.key, style)
        parts.append(f"last time: hang on {final['root']}{final['suffix']}")
    return " · ".join(parts)


def _legend(jam: Jam) -> str:
    events = [(e, st) for s in jam.sections for e, st in zip(s.loop.events, s.loop.starts())]
    parts = []
    if any(st % s_bpb for s in jam.sections for st in s.loop.starts() for s_bpb in [s.loop.beats_per_bar]):
        eighths = any(s.meter.unit == 8 for s in jam.sections)
        parts.append("/ = one beat" + (", an eighth in /8" if eighths else "") + " (C / / G: G on beat 4)")
    if any(e.push for e, _ in events):
        parts.append("› pushed: arrives an eighth early")
    return " · ".join(parts)


def sheet_data(jam: Jam, style: str = "plain") -> dict:
    tempo = f"♪ = {jam.tempo * 2}" if jam.meter.unit == 8 else f"♩ = {jam.tempo}"
    sections = []
    for s in jam.sections:
        sections.append(
            {
                "label": s.label,
                "cue": s.cue.text if s.cue.type == "count" else "",
                "notes": _notes(jam, s),
                "bars": (bars := _bars(s, style)),
                # Bars with mid-bar changes need room for their slashes.
                "bars_per_row": 4 if any(b["slots"] for b in bars) else BARS_PER_ROW,
                "line": _line(s, style),
                "prompts": s.prompts,
                "idea": {**s.idea, "text": pretty(s.idea["text"])} if s.idea else None,
            }
        )
    roadmap = [
        {
            "label": s.label,
            "short": _cue_short(s),
            "energy": s.knobs.energy,
            "weight": s.loop.bars * s.cue.passes,
        }
        for s in jam.sections
    ]
    return {
        "title": jam.title,
        "tempo": tempo,
        "meter": str(jam.meter),
        "key": key_display(jam.home_key),
        "roadmap": roadmap,
        "sections": sections,
        "footer": f"seed {jam.seed} · mood {jam.mood} · arc {jam.arc} · form {jam.form}",
        "legend": _legend(jam),
    }


def render_pdf(jam: Jam, path: str | Path, *, style: str = "plain", paper: str = "letter") -> Path:
    import typst  # imported here so the rest of QuikJamz works without it

    if paper not in PAPERS:
        raise ValueError(f"Unknown paper {paper!r}; known: {sorted(PAPERS)}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    inputs = {"data": json.dumps(sheet_data(jam, style), ensure_ascii=False), "paper": PAPERS[paper]}
    template = resources.files("quikjamz") / "render" / "sheet.typ"
    with resources.as_file(template) as template_path:
        typst.compile(
            str(template_path), output=str(path), root=str(template_path.parent), sys_inputs=inputs
        )
    return path
