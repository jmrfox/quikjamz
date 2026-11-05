"""Knobs, mood presets and arcs (spec section 2)."""

from __future__ import annotations

import math
import random
from dataclasses import asdict, dataclass, fields, replace
from functools import cache
from importlib import resources

import yaml


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


@dataclass(frozen=True)
class Knobs:
    energy: float = 0.5
    tension: float = 0.5
    complexity: float = 0.5
    brightness: float = 0.5
    density: float = 0.5
    harm_adv: float = 0.3
    rhythm_adv: float = 0.3
    stability: float = 0.6

    def __post_init__(self):
        for f in fields(self):
            object.__setattr__(self, f.name, round(clamp(float(getattr(self, f.name))), 3))

    def with_(self, **changes) -> "Knobs":
        return replace(self, **changes)

    def as_dict(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def names(cls) -> list[str]:
        return [f.name for f in fields(cls)]


# ------------------------------------------------------------------ moods


@cache
def moods() -> dict[str, Knobs]:
    text = (resources.files("quikjamz") / "data" / "moods.yaml").read_text(encoding="utf-8")
    return {name: Knobs(**values) for name, values in yaml.safe_load(text).items()}


def resolve_knobs(
    mood: str | None, overrides: dict[str, float], rng: random.Random
) -> tuple[str, Knobs]:
    """Start from a mood (random if not given) and apply explicit knob values on top."""
    presets = moods()
    if mood is None:
        mood = rng.choice(sorted(presets))
    if mood not in presets:
        raise ValueError(f"Unknown mood {mood!r}; known: {sorted(presets)}")
    unknown = set(overrides) - set(Knobs.names())
    if unknown:
        raise ValueError(f"Unknown knobs: {sorted(unknown)}")
    return mood, presets[mood].with_(**{k: v for k, v in overrides.items() if v is not None})


# ------------------------------------------------------------------- arcs


def _smoothstep(x: float) -> float:
    x = clamp(x)
    return x * x * (3 - 2 * x)


def _plateau(t: float) -> float:
    if t < 0.25:
        return _smoothstep(t / 0.25)
    if t > 0.75:
        return _smoothstep((1 - t) / 0.25)
    return 1.0


ARCS = {
    "flat": lambda t: 0.5,
    "build": lambda t: t,
    "slow_burn": lambda t: t * t,
    "arch": lambda t: math.sin(math.pi * t),
    "collapse": lambda t: 1 - t,
    "wave": lambda t: 0.5 + 0.5 * math.sin(2 * math.pi * 2 * t - math.pi / 2),
    "plateau": _plateau,
}
ARC_NAMES = sorted([*ARCS, "wander"])
DEFAULT_ARC = "arch"


class Arc:
    """An arc shape, evaluated at t in [0, 1]. 'wander' is a seeded, smoothed random walk."""

    def __init__(self, name: str, rng: random.Random):
        if name not in ARC_NAMES:
            raise ValueError(f"Unknown arc {name!r}; known: {ARC_NAMES}")
        self.name = name
        self._points: list[float] | None = None
        if name == "wander":
            walk = [0.0]
            for _ in range(32):
                walk.append(walk[-1] + rng.gauss(0, 1))
            smooth = [sum(walk[max(0, i - 2): i + 3]) / len(walk[max(0, i - 2): i + 3]) for i in range(len(walk))]
            lo, hi = min(smooth), max(smooth)
            self._points = [(v - lo) / (hi - lo or 1) for v in smooth]

    def __call__(self, t: float) -> float:
        t = clamp(t)
        if self._points is None:
            return clamp(ARCS[self.name](t))
        x = t * (len(self._points) - 1)
        i = min(int(x), len(self._points) - 2)
        frac = x - i
        return self._points[i] * (1 - frac) + self._points[i + 1] * frac


# How strongly each knob follows the arc. Tunable.
ARC_DEPTH = {"energy": 0.6, "density": 0.5, "tension": 0.4}
TENSION_LEAD = 0.15  # tension samples the arc a little early, so it rises before a peak
SECTION_NOISE = 0.12
GLOBAL_KNOBS = ("brightness", "harm_adv", "rhythm_adv")  # one identity across the jam


def section_knobs(global_knobs: Knobs, arc: Arc, t: float, rng: random.Random) -> Knobs:
    """Knob values for a section at position t (spec 2.3)."""
    stability = global_knobs.stability
    values = {}
    for name in Knobs.names():
        base = getattr(global_knobs, name)
        if name == "stability":
            values[name] = base
            continue
        shape = arc(t + TENSION_LEAD) if name == "tension" else arc(t)
        noise = rng.gauss(0, SECTION_NOISE)
        if name in GLOBAL_KNOBS:
            noise *= (1 - stability) ** 2  # these only wander when stability is low
        else:
            noise *= 1 - stability
        values[name] = base + ARC_DEPTH.get(name, 0.0) * (shape - 0.5) + noise
    return Knobs(**values)


# ------------------------------------------------------------------- vibe


_VIBE_WORDS = {
    "energy": ("laid-back", "driving"),
    "tension": ("settled", "tense"),
    "brightness": ("dark", "bright"),
    "density": ("spacious", "busy"),
    "complexity": ("plain", "intricate"),
}


def vibe_words(knobs: Knobs, limit: int = 3, threshold: float = 0.15) -> list[str]:
    """Words for the knobs that sit furthest from the middle, strongest first."""
    scored = []
    for name, (low, high) in _VIBE_WORDS.items():
        v = getattr(knobs, name)
        if abs(v - 0.5) > threshold:
            scored.append((abs(v - 0.5), high if v > 0.5 else low))
    return [w for _, w in sorted(scored, reverse=True)[:limit]] or ["even"]
