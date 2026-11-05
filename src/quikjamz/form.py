"""Form: which sections bring new material, which return, labels and cues (spec section 3)."""

from __future__ import annotations

import random
from dataclasses import dataclass
from functools import cache
from importlib import resources

import yaml

from .knobs import Knobs

PRIMES = ("", "′", "″", "‴")


@dataclass(frozen=True)
class Slot:
    """One section in the form, before any music is generated."""

    material: int  # index of the material (0 = first new idea, 1 = second, ...)
    kind: str  # "new", "return" (repeat earlier material) or "drift" (vary the previous section)
    source: int | None = None  # section index this one returns to or drifts from
    variant: int = 0  # how many times this material has come back (0 = first appearance)


# ---------------------------------------------------------------- patterns


def _from_letters(pattern: str) -> list[Slot]:
    """'ABA' -> slots. Repeated letters become returns of the first appearance."""
    slots: list[Slot] = []
    first_seen: dict[str, int] = {}
    counts: dict[str, int] = {}
    materials: dict[str, int] = {}
    for i, letter in enumerate(pattern):
        if letter in first_seen:
            counts[letter] += 1
            slots.append(Slot(materials[letter], "return", first_seen[letter], counts[letter]))
        else:
            first_seen[letter] = i
            counts[letter] = 0
            materials[letter] = len(materials)
            slots.append(Slot(materials[letter], "new"))
    return slots


_LETTERS = "ABCDEFGHIJKLMNOP"


def _through(n: int) -> str:
    return _LETTERS[:n]


def _return(n: int) -> str:  # A B C ... A
    return _LETTERS[: n - 1] + "A"


def _ring(n: int) -> str:  # A B A C A D ...
    out, nxt = [], 1
    for i in range(n):
        if i % 2 == 0:
            out.append("A")
        else:
            out.append(_LETTERS[nxt])
            nxt += 1
    return "".join(out)


def _mirror(n: int) -> str:  # A B C B A
    half = (n + 1) // 2
    first = _LETTERS[:half]
    return first + first[: n - half][::-1]


def _strophic(n: int) -> str:  # A A A ... B
    return "A" * (n - 1) + "B"


# name -> (builder, minimum sections, weight as a function of stability). Tunable.
TEMPLATES = {
    "through": (_through, 1, lambda s: 1.5 * (1 - s)),
    "return": (_return, 3, lambda s: 1.0),
    "ring": (_ring, 3, lambda s: 1.5 * s),
    "mirror": (_mirror, 4, lambda s: 1.0 * s),
    "strophic": (_strophic, 3, lambda s: 0.8 * s),
    "drift": (None, 2, lambda s: 1.0 * (1 - s)),
}


def build_form(template: str, n: int) -> list[Slot]:
    if template == "drift":
        slots = [Slot(0, "new")]
        slots += [Slot(i, "drift", i - 1) for i in range(1, n)]
        return slots
    builder = TEMPLATES[template][0]
    return _from_letters(builder(n))


def choose_form(n: int, stability: float, rng: random.Random, template: str | None = None):
    if template is None:
        options = [(name, w(stability)) for name, (_, low, w) in TEMPLATES.items() if n >= low]
        names = [o for o, _ in options]
        template = rng.choices(names, weights=[max(w, 0.01) for _, w in options])[0]
    elif template not in TEMPLATES:
        raise ValueError(f"Unknown form {template!r}; known: {sorted(TEMPLATES)}")
    return template, build_form(template, n)


# ------------------------------------------------------------------ labels


LABEL_STYLES = ("letters", "glyphs", "colors", "motion", "image")


@cache
def _label_data() -> dict:
    text = (resources.files("quikjamz") / "data" / "labels.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text)


def _motion_category(i: int, energies: list[float], is_last: bool) -> str:
    e = energies[i]
    prev = energies[i - 1] if i > 0 else None
    nxt = energies[i + 1] if i + 1 < len(energies) else None
    if i == 0:
        return "open"
    if nxt is not None and e >= max(energies) - 1e-9 and e > prev and e >= nxt:
        return "blaze"
    if is_last and e < 0.45:
        return "close"
    slope = e - prev
    if slope > 0.05:
        return "surge" if e > 0.6 else "gather"
    if slope < -0.05:
        return "thin"
    return "hold" if e > 0.55 else "drift"


def _fits(entry: dict, knobs: Knobs) -> float:
    score = 1.0
    for name in Knobs.names():
        if name in entry:
            lo, hi = entry[name]
            v = getattr(knobs, name)
            if not lo <= v <= hi:
                score *= 0.05
    return score


def make_labels(
    slots: list[Slot], knobs: list[Knobs], style: str, rng: random.Random
) -> list[str]:
    if style not in LABEL_STYLES:
        raise ValueError(f"Unknown label style {style!r}; known: {LABEL_STYLES}")
    data = _label_data()
    labels: list[str] = []
    base_for_material: dict[int, str] = {}
    used: set[str] = set()
    energies = [k.energy for k in knobs]

    for i, slot in enumerate(slots):
        if slot.kind == "return":
            labels.append(base_for_material[slot.material] + PRIMES[min(slot.variant, 3)])
            continue

        if style == "letters":
            base = _LETTERS[slot.material]
        elif style == "glyphs":
            base = data["glyphs"][slot.material % len(data["glyphs"])]
        elif style == "colors":
            base = data["colors"][slot.material % len(data["colors"])]
        elif style == "motion":
            category = _motion_category(i, energies, i == len(slots) - 1)
            words = [w for w in data["motion"][category] if w not in used]
            base = words[0] if words else data["motion"][category][0] + PRIMES[1]
        else:  # image
            entries = [e for e in data["image"] if e["word"] not in used]
            weights = [_fits(e, knobs[i]) for e in entries]
            base = rng.choices(entries, weights=weights)[0]["word"]

        used.add(base)
        base_for_material[slot.material] = base
        labels.append(base)
    return labels


# -------------------------------------------------------------------- cues


@dataclass(frozen=True)
class Cue:
    type: str  # count, open, signal, fade, hit
    text: str
    passes: int  # how many times the loop is played in the MIDI / counted on the sheet

    def to_dict(self) -> dict:
        return {"type": self.type, "text": self.text, "passes": self.passes}


SIGNALS = (
    "move on after a fill",
    "move on at a nod from the spotlight",
    "move on when the low end drops out",
    "move on after everyone lands on one",
)
STARTS = ("count in", "one player starts, others join", "drone first, others join")


def make_cue(
    knobs: Knobs, loop_bars: int, is_last: bool, ending: str, rng: random.Random
) -> Cue:
    s = knobs.stability
    if is_last:
        if knobs.energy < 0.45:
            return Cue("fade", "thin out to nothing", 2)
        text = "end on a held chord" if ending == "resolve" and rng.random() < 0.6 else "stop together on 1"
        return Cue("hit", text, max(1, 8 // loop_bars))

    weights = {
        "count": 0.3 + s,
        "open": 0.2 + 0.8 * (1 - s),
        "signal": 0.2 + 0.6 * (1 - abs(s - 0.5) * 2),
    }
    kind = rng.choices(list(weights), weights=list(weights.values()))[0]
    if kind == "count":
        target_bars = rng.choice((8, 16) if s > 0.5 else (8, 8, 16))
        passes = max(1, target_bars // loop_bars)
        return Cue("count", f"×{passes}", passes)
    if kind == "open":
        return Cue("open", "open – until cue", 2)
    return Cue("signal", rng.choice(SIGNALS), 2)


def make_start_cue(knobs: Knobs, rng: random.Random) -> str:
    weights = (0.5 + knobs.energy, 0.5, 0.2 + (1 - knobs.density))
    return rng.choices(STARTS, weights=weights)[0]
