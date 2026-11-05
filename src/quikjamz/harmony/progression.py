"""Loop generation (spec 4.4-4.5).

A loop is walked as a Markov chain over chord *functions* (home, away, pull,
non-functional), with chords from higher tiers faded in by harmonic
adventurousness. Many candidate loops are generated and the one whose
'surprise' is closest to the target for that adventurousness wins, with a
penalty for jumpy voice leading.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from ..theory.chords import Chord, degree_for
from ..theory.scales import Key
from .color import colorize
from .vocabulary import build_pool

# Base weights for moving between functions (rows: from, columns: to). Tunable.
FN_WEIGHTS = {
    "H": {"H": 0.20, "A": 0.50, "P": 0.30, "N": 0.30},
    "A": {"H": 0.15, "A": 0.30, "P": 0.55, "N": 0.30},
    "P": {"H": 0.70, "A": 0.20, "P": 0.10, "N": 0.30},
    "N": {"H": 0.35, "A": 0.30, "P": 0.25, "N": 0.40},
}

# Target surprise (mean -log P under the plain diatonic model) at harm_adv = 0 and 1.
# Measured loops range from ~1.3 (most expected) to ~3.5 (wildest), depending on mode and
# loop size. Targets sit at the edges so harm_adv 0 picks the most expected candidate and
# harm_adv 1 the most surprising one. Tunable.
SURPRISE_MIN = 1.0
SURPRISE_MAX = 3.5
BASELINE_EPS = 0.03  # baseline probability of any move to a non-diatonic chord

VOICE_LEADING_WEIGHT = 0.08
TIER_WEIGHT = 0.3  # at low harm_adv, prefer loops built from lower tiers
UNRESOLVED_WEIGHT = 0.6  # per applied dominant that doesn't go to its target
CANDIDATES = 32


def tier_multiplier(tier: int, harm_adv: float) -> float:
    if tier == 0:
        return 1.0
    return 1.0 / (1.0 + math.exp(-6.0 * (5.0 * harm_adv - tier + 0.5)))


def target_surprise(harm_adv: float) -> float:
    return SURPRISE_MIN + harm_adv * (SURPRISE_MAX - SURPRISE_MIN)


@dataclass(frozen=True)
class ChordEvent:
    chord: Chord
    beats: int


@dataclass
class Loop:
    key: Key
    beats_per_bar: int
    events: list[ChordEvent]
    ending: str  # "resolve" (land on home on the last pass) or "hang"
    final: Chord  # the chord the section ends on
    surprise: float
    target: float
    stats: dict = field(default_factory=dict)

    @property
    def bars(self) -> int:
        return sum(e.beats for e in self.events) // self.beats_per_bar

    @property
    def chords(self) -> list[Chord]:
        return [e.chord for e in self.events]


# ---------------------------------------------------------------- transitions


def _planing_moves(chord: Chord) -> list[Chord]:
    """Same chord shape slid up or down a step: the non-functional 'planing' move."""
    if chord.triad not in ("maj", "min", "quartal") or chord.bass is not None:
        return []
    out = []
    for shift, letters in ((2, 1), (-2, -1), (1, 1), (-1, -1)):
        degree, alt = degree_for((chord.rel_root + shift) % 12, chord.degree + letters)
        out.append(
            Chord(
                degree=degree, alteration=alt, triad=chord.triad, fn="N", tier=5,
                source="planing", color=chord.color, prior=0.6,
            )
        )
    return out


def transition_weight(frm: Chord, to: Chord, harm_adv: float) -> float:
    if to.ident == frm.ident:
        return 0.0
    w = FN_WEIGHTS[frm.fn][to.fn] * tier_multiplier(to.tier, harm_adv) * to.prior
    if frm.resolves_to is not None:
        lands = to.rel_root == frm.resolves_to and to.triad in ("maj", "min") and to.bass is None
        w *= 8.0 if lands else 0.25
    return w


def _wrap_factor(last: Chord, first: Chord, tension: float) -> float:
    """How well the loop's last chord leads back into its first. Less important when tense."""
    base = FN_WEIGHTS[last.fn][first.fn] / 0.7
    if last.resolves_to is not None:
        base *= 3.0 if last.resolves_to == first.rel_root else 0.3
    return max(base, 1e-6) ** (1.0 - tension)


# ------------------------------------------------------------------ surprise


def _baseline_prob(frm: Chord, to: Chord, diatonic: list[Chord]) -> float:
    if to.tier > 1 or to.source not in ("diatonic", "extra") or to.triad == "quartal":
        return BASELINE_EPS
    options = [c for c in diatonic if c.ident != frm.ident]
    total = sum(FN_WEIGHTS[frm.fn][c.fn] * c.prior for c in options)
    if to.ident == frm.ident or total == 0:
        return BASELINE_EPS
    return (1 - BASELINE_EPS) * FN_WEIGHTS[frm.fn][to.fn] * to.prior / total


def surprise(chords: list[Chord], pool: list[Chord]) -> float:
    """Mean -log P of each move (including the wrap back to the start) under a plain diatonic model."""
    if len(chords) < 2:
        return 0.0
    diatonic = [c for c in pool if c.tier <= 1]
    moves = zip(chords, chords[1:] + chords[:1])
    logs = [-math.log(_baseline_prob(a, b, diatonic)) for a, b in moves]
    return sum(logs) / len(logs)


def _move_cost(a: frozenset[int], b: frozenset[int]) -> float:
    def dist(x, y):
        d = abs(x - y) % 12
        return min(d, 12 - d)

    there = sum(min(dist(x, y) for y in b) for x in a) / len(a)
    back = sum(min(dist(x, y) for y in a) for x in b) / len(b)
    return (there + back) / 2


def voice_leading_cost(chords: list[Chord]) -> float:
    """Average semitone movement per voice between neighbouring chords (core tones only)."""
    if len(chords) < 2:
        return 0.0
    pairs = list(zip(chords, chords[1:] + chords[:1]))
    return sum(_move_cost(a.rel_pcs(True), b.rel_pcs(True)) for a, b in pairs) / len(pairs)


def unresolved_pulls(chords: list[Chord]) -> int:
    """Applied dominants (V7/x, subV7/x) not followed by their target, counting the wrap."""
    if len(chords) < 2:
        return 0
    pairs = zip(chords, chords[1:] + chords[:1])
    return sum(1 for a, b in pairs if a.resolves_to is not None and b.rel_root != a.resolves_to)


# ---------------------------------------------------------------------- walk


def _choose(rng: random.Random, options: list[Chord], weights: list[float]) -> Chord | None:
    if not options or sum(weights) <= 0:
        return None
    return rng.choices(options, weights=weights)[0]


def walk(
    pool: list[Chord], n: int, harm_adv: float, tension: float, rng: random.Random
) -> list[Chord]:
    tonic = next(c for c in pool if c.source == "diatonic" and c.degree == 1)
    if n == 1 or rng.random() < 0.9 - 0.4 * harm_adv:  # a one-chord vamp is always on home
        first = tonic
    else:
        first = _choose(rng, pool, [tier_multiplier(c.tier, harm_adv) * c.prior for c in pool])
    seq = [first]
    used = {first.ident}
    for i in range(1, n):
        prev = seq[-1]
        options = [c for c in pool + _planing_moves(prev) if c.ident not in used]
        weights = [transition_weight(prev, c, harm_adv) for c in options]
        last = i == n - 1
        if last:
            weights = [w * _wrap_factor(c, first, tension) for w, c in zip(weights, options)]
        # An applied dominant only makes sense if the chord it points at can follow it.
        open_roots = {c.rel_root for c in options if c.triad in ("maj", "min") and c.bass is None}
        for j, c in enumerate(options):
            if c.resolves_to is None:
                continue
            reachable = c.resolves_to == first.rel_root if last else c.resolves_to in open_roots
            if not reachable:
                weights[j] *= 0.05
        nxt = _choose(rng, options, weights)
        if nxt is None:
            break
        seq.append(nxt)
        used.add(nxt.ident)
    return seq


# ----------------------------------------------------------------- durations


def plan_durations(n: int, complexity: float, beats_per_bar: int, rng: random.Random) -> list[int]:
    """Beats per chord. Low complexity holds chords for bars; high complexity changes mid-bar."""
    if complexity < 0.25:
        bars_per_chord = rng.choices([4, 2], weights=[0.6, 0.4])[0]
    elif complexity < 0.5:
        bars_per_chord = rng.choice([2, 1])
    elif complexity < 0.75:
        bars_per_chord = rng.choices([1, 2], weights=[0.8, 0.2])[0]
    else:
        halves_ok = beats_per_bar % 2 == 0
        bars_per_chord = rng.choices([1, 0.5], weights=[0.6, 0.4 if halves_ok else 0])[0]
    while n * bars_per_chord > 8 and bars_per_chord > 1:
        bars_per_chord /= 2

    unit = int(bars_per_chord * beats_per_bar)
    durations = [unit] * n
    used = sum(durations)
    loop_beats = next(b * beats_per_bar for b in (1, 2, 4, 8, 16) if b * beats_per_bar >= used)

    # Give leftover time to the first chord, then the last, then the inner ones.
    order = [0]
    if n > 1:
        order.append(n - 1)
    order += list(range(1, n - 1))
    left = loop_beats - used
    i = 0
    while left > 0:
        chunk = min(beats_per_bar if left >= beats_per_bar else left, left)
        durations[order[i % len(order)]] += chunk
        left -= chunk
        i += 1
    return durations


# ---------------------------------------------------------------------- loop


def generate_loop(
    key: Key,
    rng: random.Random,
    *,
    harm_adv: float = 0.3,
    complexity: float = 0.5,
    tension: float = 0.5,
    brightness: float | None = None,
    beats_per_bar: int = 4,
    n_chords: int | None = None,
    candidates: int = CANDIDATES,
) -> Loop:
    pool = build_pool(key, brightness)
    if n_chords is None:
        n_chords = round(1 + complexity * 4 + rng.gauss(0, 0.6))
    n = max(1, min(5, n_chords))
    target = target_surprise(harm_adv)

    best, best_score = None, -math.inf
    for _ in range(candidates):
        seq = walk(pool, n, harm_adv, tension, rng)
        s = surprise(seq, pool)
        vl = voice_leading_cost(seq)
        mean_tier = sum(c.tier for c in seq) / len(seq)
        score = (
            -abs(s - target)
            - VOICE_LEADING_WEIGHT * vl
            - TIER_WEIGHT * (1 - harm_adv) * mean_tier
            - UNRESOLVED_WEIGHT * (1 - 0.5 * tension) * unresolved_pulls(seq)
            - 1.0 * (n - len(seq))
        )
        if score > best_score:
            best, best_score, best_stats = seq, score, {"surprise": s, "voice_leading": vl}

    durations = plan_durations(len(best), complexity, beats_per_bar, rng)
    colored = [colorize(c, complexity, tension, rng) for c in best]
    events = [ChordEvent(c, d) for c, d in zip(colored, durations)]

    plain_tonic = next(c for c in pool if c.source == "diatonic" and c.degree == 1)
    in_loop = [c for c, raw in zip(colored, best) if raw.ident == plain_tonic.ident]
    tonic = in_loop[0] if in_loop else colorize(plain_tonic, complexity, tension, rng)
    # On the last pass, either land on home or hang on the last chord that isn't home.
    unresolved = [c for c in reversed(colored) if c.fn != "H"]
    if unresolved and rng.random() < tension:
        ending, final = "hang", unresolved[0]
    else:
        ending, final = "resolve", tonic

    return Loop(
        key=key,
        beats_per_bar=beats_per_bar,
        events=events,
        ending=ending,
        final=final,
        surprise=best_stats["surprise"],
        target=target,
        stats={**best_stats, "score": best_score, "n_target": n},
    )
