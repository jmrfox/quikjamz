"""Prompts and seed ideas for sections (spec section 6)."""

from __future__ import annotations

import random
from dataclasses import dataclass
from functools import cache
from importlib import resources

import yaml

from .knobs import Knobs
from .theory.meter import Meter
from .theory.scales import Key


@dataclass(frozen=True)
class Prompt:
    text: str
    when: dict[str, tuple[float, float]]
    weight: float = 1.0

    def fits(self, knobs: Knobs) -> bool:
        return all(lo <= getattr(knobs, k) <= hi for k, (lo, hi) in self.when.items())


@cache
def prompt_deck() -> tuple[Prompt, ...]:
    text = (resources.files("quikjamz") / "data" / "prompts.yaml").read_text(encoding="utf-8")
    deck = []
    for raw in yaml.safe_load(text):
        when = {k: tuple(v) for k, v in (raw.get("when") or {}).items()}
        unknown = set(when) - set(Knobs.names())
        if unknown:
            raise ValueError(f"Prompt {raw['text']!r} uses unknown knobs {sorted(unknown)}")
        deck.append(Prompt(raw["text"], when, raw.get("weight", 1.0)))
    return tuple(deck)


def pick_prompts(knobs: Knobs, rng: random.Random, used: set[str]) -> list[str]:
    """0-2 prompts that fit the section's knobs. More complexity means more prompts."""
    c = knobs.complexity
    count = rng.choices([0, 1, 2], weights=[0.35 - 0.25 * c, 0.5, 0.15 + 0.35 * c])[0]
    options = [p for p in prompt_deck() if p.fits(knobs) and p.text not in used]
    picked = []
    for _ in range(count):
        if not options:
            break
        p = rng.choices(options, weights=[o.weight for o in options])[0]
        options.remove(p)
        picked.append(p.text)
        used.add(p.text)
    return picked


# --------------------------------------------------------------- seed ideas


def rhythm_idea(meter: Meter, knobs: Knobs, rng: random.Random) -> str:
    """One bar of hits ('x') and rests ('.'), grouped by beat (or by the meter's grouping).

    /4 meters get eighth-note steps, /8 meters one step per beat. Density sets how many
    hits there are; rhythmic adventurousness sets how many land off the beat.
    """
    if meter.unit == 8:
        groups = list(meter.grouping or ([3] * (meter.beats // 3) if meter.beats % 3 == 0 else [meter.beats]))
        steps_per_group = groups
    else:
        groups = [2] * meter.beats
        steps_per_group = groups

    base = 0.2 + 0.55 * knobs.density
    offbeat = 0.25 + 0.9 * knobs.rhythm_adv
    for _ in range(20):
        cells = []
        for size in steps_per_group:
            group = []
            for j in range(size):
                p = base if j == 0 else base * offbeat
                group.append("x" if rng.random() < min(p, 0.95) else ".")
            cells.append(group)
        if rng.random() > knobs.rhythm_adv * 0.7:
            cells[0][0] = "x"  # usually start on one
        hits = sum(c.count("x") for c in cells)
        if 2 <= hits < sum(steps_per_group):
            break
    return " ".join("".join(c) for c in cells)


def melody_idea(key: Key, knobs: Knobs, rng: random.Random) -> str:
    """3-5 notes from the section's scale, mostly stepwise, as note names."""
    length = 3 + round(knobs.complexity * 2)
    notes = key.scale_notes()
    leap_p = 0.15 + 0.35 * knobs.harm_adv
    pos = rng.choice([0, 2, 4])  # start on the 1st, 3rd or 5th of the scale
    line = [pos]
    for _ in range(length - 1):
        if rng.random() < leap_p:
            step = rng.choice([-4, -3, 3, 4])
        else:
            step = rng.choice([-1, 1, 1, -2, 2])
        pos = max(-3, min(9, pos + step))
        line.append(pos)
    return "–".join(str(notes[p % 7]) for p in line)


def pick_idea(section_key: Key, meter: Meter, knobs: Knobs, rng: random.Random) -> dict | None:
    """Maybe one seed idea for a section: a rhythm or a short melody."""
    if rng.random() > 0.6:
        return None
    if rng.random() < 0.5 + 0.3 * (knobs.rhythm_adv - knobs.harm_adv):
        return {"type": "rhythm", "text": rhythm_idea(meter, knobs, rng)}
    return {"type": "melody", "text": melody_idea(section_key, knobs, rng)}
