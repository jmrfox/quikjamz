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
    loop = section.loop
    bpb = loop.beats_per_bar
    cells = [{"n": section.start_bar + i, "chords": []} for i in range(loop.bars)]
    beat = 0
    for event in loop.events:
        cells[beat // bpb]["chords"].append(chord_display(event.chord, section.key, style))
        beat += event.beats
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


def sheet_data(jam: Jam, style: str = "plain") -> dict:
    tempo = f"♪ = {jam.tempo * 2}" if jam.meter.unit == 8 else f"♩ = {jam.tempo}"
    sections = []
    for s in jam.sections:
        sections.append(
            {
                "label": s.label,
                "cue": s.cue.text if s.cue.type == "count" else "",
                "notes": _notes(jam, s),
                "bars": _bars(s, style),
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
        "bars_per_row": BARS_PER_ROW,
        "footer": f"seed {jam.seed} · mood {jam.mood} · arc {jam.arc} · form {jam.form}",
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
