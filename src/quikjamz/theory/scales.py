"""Scale definitions (loaded from data files) and keys."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from functools import cache
from importlib import resources

import yaml

from .pitch import MAJOR_STEPS, SpelledNote, spellings_of

FUNCTIONS = ("H", "A", "P")  # home, away, pull


@dataclass(frozen=True)
class ExtraChord:
    """A chord outside the scale that the scale treats as its own (e.g. V in Aeolian)."""

    degree: int
    alteration: int
    triad: str
    fn: str
    tier: int
    color: tuple[int, ...]


@dataclass(frozen=True)
class ScaleDef:
    name: str
    display: str
    intervals: tuple[int, ...]
    functions: dict[int, str]  # scale step (1-based) -> H/A/P
    tier0: tuple[int, ...]
    brightness: float | None = None
    signature_offset: int | None = None
    choose_weight: float = 1.0
    extras: tuple[ExtraChord, ...] = field(default=())

    def __post_init__(self):
        if len(self.intervals) != 7:
            raise ValueError(f"{self.name}: only seven-note scales are supported so far")
        if set(self.functions) != set(range(1, 8)):
            raise ValueError(f"{self.name}: functions must cover steps 1-7")
        if any(f not in FUNCTIONS for f in self.functions.values()):
            raise ValueError(f"{self.name}: functions must be one of {FUNCTIONS}")

    @property
    def pcs(self) -> frozenset[int]:
        return frozenset(self.intervals)

    def degree_of_step(self, step: int) -> tuple[int, int]:
        """(degree, alteration vs. the major scale) for a 1-based scale step."""
        return step, self.intervals[step - 1] - MAJOR_STEPS[step - 1]

    def __hash__(self) -> int:
        return hash(self.name)


def _parse_scale(raw: dict) -> ScaleDef:
    extras = tuple(
        ExtraChord(
            degree=e["degree"],
            alteration=e.get("alteration", 0),
            triad=e["triad"],
            fn=e["fn"],
            tier=e.get("tier", 1),
            color=tuple(e["color"]),
        )
        for e in raw.get("extras", [])
    )
    return ScaleDef(
        name=raw["name"],
        display=raw.get("display", raw["name"].title()),
        intervals=tuple(raw["intervals"]),
        functions={int(k): v for k, v in raw["functions"].items()},
        tier0=tuple(raw["tier0"]),
        brightness=raw.get("brightness"),
        signature_offset=raw.get("signature_offset"),
        choose_weight=raw.get("choose_weight", 1.0),
        extras=extras,
    )


@cache
def all_scales() -> dict[str, ScaleDef]:
    folder = resources.files("quikjamz") / "data" / "scales"
    scales = {}
    for entry in folder.iterdir():
        if entry.name.endswith(".yaml"):
            scale = _parse_scale(yaml.safe_load(entry.read_text(encoding="utf-8")))
            scales[scale.name] = scale
    return scales


def get_scale(name: str) -> ScaleDef:
    try:
        return all_scales()[name.lower()]
    except KeyError:
        raise ValueError(f"Unknown scale {name!r}; known: {sorted(all_scales())}") from None


def modes_by_brightness() -> list[ScaleDef]:
    """Scales that sit on the brightness axis, brightest first."""
    modes = [s for s in all_scales().values() if s.brightness is not None]
    return sorted(modes, key=lambda s: -s.brightness)


def choose_mode(brightness: float, rng: random.Random, sigma: float = 0.1) -> ScaleDef:
    modes = modes_by_brightness()
    weights = [
        s.choose_weight * math.exp(-((brightness - s.brightness) ** 2) / (2 * sigma**2))
        for s in modes
    ]
    return rng.choices(modes, weights=weights)[0]


@dataclass(frozen=True)
class Key:
    tonic: SpelledNote
    scale: ScaleDef

    def __str__(self) -> str:
        return f"{self.tonic} {self.scale.display}"

    @property
    def signature(self) -> int | None:
        """Key-signature position: >0 sharps, <0 flats. None for non-modal scales."""
        if self.scale.signature_offset is None:
            return None
        return self.tonic.fifths - self.scale.signature_offset

    def note(self, degree: int, alteration: int = 0) -> SpelledNote:
        """Spell a scale degree (measured against the major scale on the tonic)."""
        return self.tonic.step(degree - 1, MAJOR_STEPS[degree - 1] + alteration)

    def scale_notes(self) -> list[SpelledNote]:
        return [self.note(*self.scale.degree_of_step(s)) for s in range(1, 8)]

    def transposed(self, semitones: int, scale: ScaleDef | None = None) -> "Key":
        return make_key((self.tonic.pc + semitones) % 12, scale or self.scale)


def _signature_cost(tonic: SpelledNote, scale: ScaleDef) -> tuple[int, int]:
    if scale.signature_offset is None:
        return (abs(tonic.accidental), 0)
    sig = tonic.fifths - scale.signature_offset
    # Fewest accidentals wins; on a tie (F# vs Gb) prefer flats.
    return (abs(sig), 0 if sig <= 0 else 1)


def make_key(tonic: int | str | SpelledNote, scale: ScaleDef | str) -> Key:
    """Build a key, respelling the tonic if its signature would need more than 6 accidentals."""
    if isinstance(scale, str):
        scale = get_scale(scale)
    if isinstance(tonic, str):
        tonic = SpelledNote.parse(tonic)
    if isinstance(tonic, SpelledNote):
        if _signature_cost(tonic, scale)[0] <= 6:
            return Key(tonic, scale)
        tonic = tonic.pc
    best = min(spellings_of(tonic), key=lambda n: _signature_cost(n, scale))
    return Key(best, scale)
