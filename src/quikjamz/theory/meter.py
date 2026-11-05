"""Meters, and choosing one from rhythmic adventurousness (spec 2.2)."""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Meter:
    beats: int
    unit: int = 4
    grouping: tuple[int, ...] | None = None  # e.g. (2, 2, 3) for 7/8

    def __post_init__(self):
        if self.unit not in (2, 4, 8, 16):
            raise ValueError(f"Unsupported beat unit {self.unit}")
        if self.grouping and sum(self.grouping) != self.beats:
            raise ValueError(f"Grouping {self.grouping} doesn't add up to {self.beats}")

    def __str__(self) -> str:
        text = f"{self.beats}/{self.unit}"
        if self.grouping:
            text += " (" + "+".join(map(str, self.grouping)) + ")"
        return text

    @property
    def signature(self) -> str:
        return f"{self.beats}/{self.unit}"

    @classmethod
    def parse(cls, text: str) -> "Meter":
        """'4/4', '7/8', '7/8:2+2+3' or '7/8 (2+2+3)'."""
        text = text.strip().replace(" ", "")
        grouping = None
        for sep in (":", "("):
            if sep in text:
                text, group_text = text.split(sep, 1)
                grouping = tuple(int(g) for g in group_text.rstrip(")").split("+"))
                break
        beats, unit = text.split("/")
        meter = cls(int(beats), int(unit), grouping)
        if grouping is None and meter.signature in DEFAULT_GROUPINGS:
            meter = cls(meter.beats, meter.unit, DEFAULT_GROUPINGS[meter.signature])
        return meter


# Odd meters always print with a grouping.
DEFAULT_GROUPINGS = {
    "5/4": (3, 2),
    "5/8": (3, 2),
    "7/4": (4, 3),
    "7/8": (2, 2, 3),
    "9/8": (2, 2, 2, 3),
    "11/8": (3, 3, 3, 2),
}


def _m(text: str) -> Meter:
    return Meter.parse(text)


# (upper bound of rhythm_adv, [(meter, weight), ...]). Tunable.
METER_BANDS = (
    (0.30, [(_m("4/4"), 0.9), (_m("3/4"), 0.1)]),
    (0.55, [(_m("4/4"), 0.4), (_m("3/4"), 0.25), (_m("6/8"), 0.2), (_m("12/8"), 0.15)]),
    (0.80, [(_m("5/4"), 0.3), (_m("7/8"), 0.3), (_m("7/4"), 0.2), (_m("6/4"), 0.2)]),
    (1.01, [(_m("9/8"), 0.3), (_m("11/8"), 0.3), (_m("7/4"), 0.2), (_m("5/8"), 0.2)]),
)


def choose_meter(rhythm_adv: float, rng: random.Random) -> Meter:
    for upper, options in METER_BANDS:
        if rhythm_adv < upper:
            return rng.choices([m for m, _ in options], weights=[w for _, w in options])[0]
    raise AssertionError("unreachable")


def changes_meter_between_sections(rhythm_adv: float, rng: random.Random) -> bool:
    """Only the far end of rhythmic adventurousness changes meter mid-jam."""
    return rng.random() < max(0.0, min(1.0, (rhythm_adv - 0.8) * 5)) * 0.5
