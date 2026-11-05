"""Key changes between sections (spec 4.7). Only happen once tier 4 is fading in."""

from __future__ import annotations

import random

from ..theory.scales import Key, get_scale
from .progression import tier_multiplier

MAJORISH = {"ionian", "lydian", "mixolydian"}

# (move, weight). Tunable.
MOVES = (
    ("relative", 0.25),
    ("parallel", 0.20),
    ("up_whole_step", 0.20),
    ("up_half_step", 0.15),
    ("chromatic_mediant", 0.20),
)


def modulate(key: Key, move: str, rng: random.Random) -> Key:
    major = key.scale.name in MAJORISH
    if move == "relative":
        return key.transposed(-3 if major else 3, get_scale("aeolian" if major else "ionian"))
    if move == "parallel":
        return key.transposed(0, get_scale("aeolian" if major else "ionian"))
    if move == "up_whole_step":
        return key.transposed(2)
    if move == "up_half_step":
        return key.transposed(1)
    if move == "chromatic_mediant":
        return key.transposed(rng.choice((3, 4, -3, -4)))
    raise ValueError(f"Unknown key-change move {move!r}")


def maybe_modulate(key: Key, harm_adv: float, rng: random.Random) -> tuple[Key, str | None]:
    """Possibly change key for the next section. Returns (key, move or None)."""
    if rng.random() >= 0.6 * tier_multiplier(4, harm_adv):
        return key, None
    move = rng.choices([m for m, _ in MOVES], weights=[w for _, w in MOVES])[0]
    return modulate(key, move, rng), move
