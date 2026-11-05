"""The chord pool for a key, organised into adventurousness tiers (spec 4.3).

Tier 0  main chords of the mode
Tier 1  the rest of the diatonic chords (+ scale 'extras' like V in Aeolian)
Tier 2  borrowed from neighbouring modes on the same tonic
Tier 3  secondary dominants
Tier 4  tritone substitutions, chromatic mediants
Tier 5  non-functional: quartal stacks, chords over a tonic pedal
        (parallel 'planing' moves are added during the walk; see progression.py)
"""

from __future__ import annotations

import math

from ..theory.chords import Chord, degree_for, roman_numeral, stacked_chord
from ..theory.scales import Key, ScaleDef, modes_by_brightness

MIXOLYDIAN = (0, 2, 4, 5, 7, 9, 10)
PHRYGIAN_DOMINANT = (0, 1, 4, 5, 7, 8, 10)
LYDIAN_DOMINANT = (0, 2, 4, 6, 7, 9, 10)
IONIAN = (0, 2, 4, 5, 7, 9, 11)
DORIAN = (0, 2, 3, 5, 7, 9, 10)


class Pool:
    """Chords keyed by identity; the first (lowest-tier) entry for an identity wins."""

    def __init__(self):
        self._chords: dict[tuple, Chord] = {}

    def add(self, chord: Chord) -> None:
        existing = self._chords.get(chord.ident)
        if existing is None:
            self._chords[chord.ident] = chord
        elif existing.tier == chord.tier and chord.prior > existing.prior:
            self._chords[chord.ident] = chord

    def __contains__(self, ident: tuple) -> bool:
        return ident in self._chords

    def chords(self) -> list[Chord]:
        return list(self._chords.values())


def diatonic_chords(scale: ScaleDef) -> list[Chord]:
    out = []
    for step in range(1, 8):
        triad, color = stacked_chord(scale.intervals, step)
        degree, alt = scale.degree_of_step(step)
        out.append(
            Chord(
                degree=degree,
                alteration=alt,
                triad=triad,
                fn=scale.functions[step],
                tier=0 if step in scale.tier0 else 1,
                source="diatonic",
                color=color,
                prior=0.3 if triad in ("dim", "aug") and step != 1 else 1.0,  # rarely used in practice
            )
        )
    return out


def _borrow_weights(home: ScaleDef, brightness: float) -> dict[str, float]:
    """How likely each neighbouring mode is as a source of borrowed chords."""
    modes = modes_by_brightness()
    names = [m.name for m in modes]
    if home.name not in names:
        return {}
    home_pos = names.index(home.name)
    direction = brightness - home.brightness  # >0: lean brighter
    weights = {}
    for pos, mode in enumerate(modes):
        dist = pos - home_pos  # >0 means darker (list is brightest first)
        if dist == 0 or abs(dist) > 3:
            continue
        w = math.exp(-0.7 * (abs(dist) - 1))
        if {home.name, mode.name} == {"ionian", "aeolian"}:
            w = max(w, 1.0)  # parallel major/minor is the classic source
        if abs(direction) >= 0.05:
            leans_darker = direction < 0
            w *= 1.5 if (dist > 0) == leans_darker else 0.6
        weights[mode.name] = w
    return weights


def build_pool(key: Key, brightness: float | None = None) -> list[Chord]:
    scale = key.scale
    if brightness is None:
        brightness = scale.brightness if scale.brightness is not None else 0.5
    pool = Pool()

    # Tiers 0-1: diatonic chords, then the scale's own extras.
    diatonic = diatonic_chords(scale)
    for chord in diatonic:
        pool.add(chord)
    for e in scale.extras:
        pool.add(
            Chord(
                degree=e.degree, alteration=e.alteration, triad=e.triad,
                fn=e.fn, tier=e.tier, source="extra", color=e.color,
            )
        )

    # Tier 2: borrowed chords from neighbouring modes on the same tonic.
    for mode_name, weight in _borrow_weights(scale, brightness).items():
        mode = next(m for m in modes_by_brightness() if m.name == mode_name)
        for chord in diatonic_chords(mode):
            if chord.triad == "dim" or chord.degree == 1:
                continue
            pool.add(chord.with_(tier=2, source=f"borrowed:{mode_name}", prior=weight))

    # Tier 3: secondary dominants, one for each major or minor diatonic chord.
    targets = [c for c in diatonic if c.triad in ("maj", "min")]
    secondaries = []
    for target in targets:
        root = (target.rel_root + 7) % 12
        degree, alt = degree_for(root, target.degree + 4)
        target_rn = roman_numeral(target.degree, target.alteration, target.triad)
        dom = Chord(
            degree=degree, alteration=alt, triad="maj", seventh="7",
            fn="P", tier=3, source="secondary", resolves_to=target.rel_root,
            color=PHRYGIAN_DOMINANT if target.triad == "min" else MIXOLYDIAN,
            label="V7" if target.degree == 1 else f"V7/{target_rn}",
            fixed_seventh=True,
        )
        secondaries.append((dom, target, target_rn))
        if target.degree == 1 and (root, "maj", None, False) in pool:
            continue  # the key already has a major V; V7 is just its coloured form
        pool.add(dom)

    # Tier 4: tritone substitutes for those dominants, and chromatic mediants.
    for dom, target, target_rn in secondaries:
        root = (target.rel_root + 1) % 12
        degree, alt = degree_for(root, target.degree + 1)
        pool.add(
            Chord(
                degree=degree, alteration=alt, triad="maj", seventh="7",
                fn="P", tier=4, source="tritone_sub", resolves_to=target.rel_root,
                color=LYDIAN_DOMINANT,
                label="subV7" if target.degree == 1 else f"subV7/{target_rn}",
                fixed_seventh=True,
            )
        )
    tonic = diatonic[0]
    mediant_triad = tonic.triad if tonic.triad in ("maj", "min") else "maj"
    for rel_root, letter in ((4, 3), (3, 3), (9, 6), (8, 6)):
        degree, alt = degree_for(rel_root, letter)
        pool.add(
            Chord(
                degree=degree, alteration=alt, triad=mediant_triad,
                fn="A", tier=4, source="mediant",
                color=IONIAN if mediant_triad == "maj" else DORIAN,
            )
        )

    # Tier 5: quartal stacks on the scale, and diatonic chords over a tonic pedal.
    pcs = scale.pcs
    for chord in diatonic:
        root = chord.rel_root
        if (root + 5) % 12 in pcs and (root + 10) % 12 in pcs:
            pool.add(
                chord.with_(triad="quartal", fn="N", tier=5, source="quartal", prior=0.5)
            )
    for chord in diatonic[1:]:
        if chord.triad in ("maj", "min"):
            pool.add(chord.with_(bass=(1, 0), fn="N", tier=5, source="pedal", prior=0.5))

    return pool.chords()
