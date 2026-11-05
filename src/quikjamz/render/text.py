"""Plain-text chart of a Jam, for the terminal. A preview of the sheet layout (spec section 8)."""

from __future__ import annotations

from ..harmony.progression import Loop
from ..jam import Jam, Section
from ..theory.scales import Key

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


def beat_name(pos_in_bar: float) -> str:
    """0 -> '1', 2 -> '3', 3.5 -> '4&'."""
    whole = int(pos_in_bar)
    return f"{whole + 1}" + ("&" if pos_in_bar - whole else "")


def bar_cells(loop: Loop, key: Key, style: str = "plain") -> list[str]:
    """One text cell per bar. Chords not on beat 1 show where they land ('G@3');
    pushed chords are marked '›' ('›G@4&' = G arrives on the and of 4)."""
    bpb = loop.beats_per_bar
    cells: list[list[str]] = [[] for _ in range(loop.bars)]
    for event, start in zip(loop.events, loop.starts()):
        bar, pos = int(start // bpb), start % bpb
        text = event.chord.symbol(key, style)
        if pos:
            text += "@" + beat_name(pos)
        if event.push:
            text = "›" + text
        cells[bar].append(text)
    return [" ".join(c) if c else "/" for c in cells]


def _bars(section: Section, style: str) -> list[str]:
    return bar_cells(section.loop, section.key, style)


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
        extras = list(s.prompts)
        if s.idea:
            extras.append(f"{s.idea['type']} idea: {s.idea['text']}")
        if extras:
            lines.append("  » " + " · ".join(extras))
        lines.append("")

    if any(e.push for s in jam.sections for e in s.loop.events):
        lines.append("@3 = chord lands on beat 3 · › = pushed, arrives an eighth early")
    lines.append(f"seed {jam.seed} · mood {jam.mood} · arc {jam.arc} · form {jam.form}".rjust(width))
    return "\n".join(lines)
