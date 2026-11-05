"""Plain-text chart of a Jam, for the terminal. A preview of the sheet layout (spec section 8)."""

from __future__ import annotations

from ..jam import Jam, Section

SPARK = "▁▂▃▄▅▆▇█"


def _sparkline(values: list[float]) -> str:
    return "".join(SPARK[min(len(SPARK) - 1, int(v * len(SPARK)))] for v in values)


def _cue_short(section: Section) -> str:
    cue = section.cue
    if cue.type == "count":
        return f"{section.label} {cue.text}"
    if cue.type == "open":
        return f"{section.label} (open)"
    if cue.type in ("fade", "hit"):
        return f"{section.label} ({cue.type})"
    return f"{section.label} (cue)"


def _bars(section: Section, style: str) -> list[str]:
    loop = section.loop
    bpb = loop.beats_per_bar
    cells: list[list[str]] = [[] for _ in range(loop.bars)]
    beat = 0
    for event in loop.events:
        cells[beat // bpb].append(event.chord.symbol(section.key, style))
        beat += event.beats
    return [" ".join(c) if c else "/" for c in cells]


def render_text(jam: Jam, style: str = "plain", width: int = 72) -> str:
    tempo_text = f"♪ = {jam.tempo * 2}" if jam.meter.unit == 8 else f"♩ = {jam.tempo}"
    info = f"{tempo_text} · {jam.meter} · {jam.home_key}"
    lines = [jam.title.ljust(width - len(info)) + info]
    lines.append("energy " + _sparkline([s.knobs.energy for s in jam.sections]))
    lines.append(" → ".join(_cue_short(s) for s in jam.sections))
    lines.append("─" * width)

    for s in jam.sections:
        header = s.label
        if s.cue.type == "count":
            header += f"  {s.cue.text}"
        notes = []
        prev = jam.sections[s.index - 1] if s.index > 0 else None
        if prev is not None and s.key != prev.key:
            notes.append(f"key: {s.key}")
        if prev is not None and s.meter != prev.meter:
            notes.append(f"meter: {s.meter}")
        if s.return_of is not None:
            notes.append(f"returns to {jam.sections[s.return_of].label}")
        if s.drift_of is not None:
            notes.append(f"grows out of {jam.sections[s.drift_of].label}")
        right = " · ".join(notes)
        lines.append(header.ljust(width - len(right)) + right)

        cells = _bars(s, style)
        cell_w = max(len(c) for c in cells) + 1
        numbered = []
        for j, cell in enumerate(cells):
            numbered.append(f"{s.start_bar + j}".ljust(3) + cell.ljust(cell_w))
        lines.append("| " + "| ".join(numbered) + "|")

        ending = (
            "lands home" if s.loop.ending == "resolve"
            else f"hangs on {s.loop.final.symbol(s.key, style)}"
        )
        cue = s.cue.text if s.cue.type != "count" else ""
        parts = [", ".join(s.vibe)]
        if s.start_cue:
            parts.append(f"start: {s.start_cue}")
        if cue:
            parts.append(cue)
        parts.append(f"last pass {ending}")
        lines.append("  " + " · ".join(parts))
        lines.append("")

    lines.append(f"seed {jam.seed} · mood {jam.mood} · arc {jam.arc} · form {jam.form}".rjust(width))
    return "\n".join(lines)
