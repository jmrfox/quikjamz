"""Chord colour: sevenths and extensions from complexity, altered tones from tension (spec 4.6)."""

from __future__ import annotations

import random

from ..theory.chords import Chord

ALTERED = ("b9", "#9", "#11", "b13")


def _natural_seventh(chord: Chord) -> str | None:
    has = set(chord.color)
    if chord.triad == "maj":
        return "maj7" if 11 in has else "7" if 10 in has else None
    if chord.triad == "min":
        return "7" if 10 in has else "maj7" if 11 in has else None
    if chord.triad == "dim":
        return "7" if 10 in has else "dim7" if 9 in has else None
    if chord.triad == "aug":
        return "maj7" if 11 in has else "7" if 10 in has else None
    if chord.triad == "sus4":
        return "7" if 10 in has else None
    return None


def colorize(chord: Chord, complexity: float, tension: float, rng: random.Random) -> Chord:
    if chord.triad in ("quartal", "5"):
        return chord
    has = set(chord.color) if chord.color else set(range(12))

    triad = chord.triad
    seventh = "7" if chord.fixed_seventh else None
    extensions: list[str] = []

    if complexity < 0.2:
        if not chord.fixed_seventh and triad in ("maj", "min") and rng.random() < 0.15:
            triad = "5"
    elif complexity < 0.45:
        if not chord.fixed_seventh and triad in ("maj", "min") and chord.bass is None:
            if chord.fn == "P" and triad == "maj" and 5 in has and rng.random() < 0.25:
                triad = "sus4"
            elif 2 in has and rng.random() < 0.12:
                triad = "sus2"
    else:
        if seventh is None and rng.random() < 0.85:
            seventh = _natural_seventh(chord)
            if (
                chord.fn == "H" and triad in ("maj", "min") and 9 in has
                and complexity < 0.7 and rng.random() < 0.3
            ):
                seventh = "6"
        if complexity >= 0.7 and seventh is not None:
            if 2 in has:
                extensions.append("9")
            if triad == "min" and 5 in has and (complexity >= 0.9 or rng.random() < 0.5):
                extensions.append("11")
            dominant = triad == "maj" and seventh == "7"
            if dominant and 9 in has and (complexity >= 0.9 or rng.random() < 0.5):
                extensions.append("13")
            if triad == "maj" and seventh == "maj7" and 6 in has and complexity >= 0.9:
                extensions.append("11")  # #11 from Lydian colour; spelled as an alteration below

    alterations: list[str] = []
    if "11" in extensions and triad == "maj":
        extensions.remove("11")
        alterations.append("#11")

    # Tension bends dominant pull chords toward altered colours.
    if triad == "maj" and seventh == "7" and chord.fn == "P":
        p_alt = max(0.0, (tension - 0.5) * 1.6)
        if rng.random() < p_alt:
            count = 2 if tension > 0.85 else 1
            for alt in rng.sample(ALTERED, count):
                if alt not in alterations:
                    alterations.append(alt)
            if "b9" in alterations or "#9" in alterations:
                extensions = [e for e in extensions if e != "9"]
            if "b13" in alterations:
                extensions = [e for e in extensions if e != "13"]
            if "b9" in alterations and "#9" in alterations:
                alterations.remove("#9")

    order = {"b9": 0, "#9": 1, "#11": 2, "b13": 3}
    return chord.with_(
        triad=triad,
        seventh=seventh if triad not in ("5", "sus2") else None,
        extensions=tuple(extensions),
        alterations=tuple(sorted(alterations, key=order.get)),
    )
