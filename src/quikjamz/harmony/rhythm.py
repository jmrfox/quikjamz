"""Where chord changes land inside the bar (harmonic rhythm placement).

Complexity decides *how often* chords change (see progression.plan_durations).
Rhythmic adventurousness decides *where*:

  low     on barlines, or on the meter's strong points (beat 3 of 4/4, the
          group boundaries of 7/8 = 2+2+3, ...)
  middle  any beat, so uneven splits like 3+1 appear
  high    pushes: the change arrives an eighth early, ahead of a strong point
"""

from __future__ import annotations

import math
import random

from ..theory.meter import Meter

# Tunable.
SHIFT_BASE = 0.08  # chance to move a change point at rhythm_adv 0 ...
SHIFT_SLOPE = 0.45  # ... plus this much more at rhythm_adv 1
WEAK_BEAT_WEIGHT = 0.6  # weight of a weak beat as a landing spot, times rhythm_adv
STRONG_WEIGHT = 0.7  # weight of a strong point (relative to a barline at 1.0)
PUSH_FROM = 0.45  # pushes start appearing above this rhythm_adv
PUSH_SLOPE = 0.8
SHIFT_REACH = 0.5  # how far (in bars) a change usually moves


def strong_points(meter: Meter) -> list[int]:
    """Beat positions inside a bar (not 0) where a change feels natural."""
    if meter.grouping:
        points, acc = [], 0
        for g in meter.grouping[:-1]:
            acc += g
            points.append(acc)
        return points
    if meter.unit == 8 and meter.beats % 3 == 0:
        return list(range(3, meter.beats, 3))  # 6/8, 9/8, 12/8: dotted-quarter pulses
    if meter.unit in (2, 4) and meter.beats % 2 == 0 and meter.beats > 2:
        return [meter.beats // 2]  # 4/4 -> beat 3, 6/4 -> beat 4
    return []


def subdivision(meter: Meter) -> float:
    """One eighth note, in beats."""
    return 0.5 if meter.unit in (2, 4) else 1.0


def min_chord_beats(meter: Meter) -> float:
    return 1.0 if meter.unit in (2, 4) else 2.0


def place_changes(
    durations: list[int], meter: Meter, rhythm_adv: float, rng: random.Random
) -> tuple[list[float], list[bool]]:
    """Move chord-change points according to rhythm_adv.

    Takes durations in beats (all changes on barlines/half-bars) and returns new
    durations plus a 'pushed' flag per chord. The first chord always starts on the
    downbeat of the loop, and the loop length never changes.
    """
    n = len(durations)
    if n < 2:
        return [float(d) for d in durations], [False] * n
    bpb = meter.beats
    total = sum(durations)
    starts = [0.0]
    for d in durations[:-1]:
        starts.append(starts[-1] + d)
    original = starts[:]
    strong = set(strong_points(meter))
    min_d = min_chord_beats(meter)
    sub = subdivision(meter)
    pushed = [False] * n

    p_shift = SHIFT_BASE + SHIFT_SLOPE * rhythm_adv
    p_push = PUSH_SLOPE * max(0.0, rhythm_adv - PUSH_FROM)

    def spot_weight(pos: float) -> float:
        in_bar = pos % bpb
        if in_bar == 0:
            return 1.0
        if in_bar in strong:
            return STRONG_WEIGHT
        weak = WEAK_BEAT_WEIGHT * rhythm_adv
        # In /8 meters a 'weak beat' is a lone eighth inside a group: rarer still.
        return weak * (0.4 if meter.unit == 8 else 1.0)

    for i in range(1, n):
        lo = starts[i - 1] + min_d
        hi = (original[i + 1] if i + 1 < n else total) - min_d
        here = original[i]
        if lo > hi:
            continue
        if rng.random() < p_shift:
            options = [float(b) for b in range(math.ceil(lo), math.floor(hi) + 1) if b != here]
            weights = [
                spot_weight(b) * math.exp(-abs(b - here) / (SHIFT_REACH * bpb)) for b in options
            ]
            if options and sum(weights) > 0:
                here = rng.choices(options, weights=weights)[0]
        here = min(max(here, lo), hi)
        # Pushes anticipate a barline or strong point by an eighth.
        if (here % bpb == 0 or here % bpb in strong) and rng.random() < p_push:
            if here - sub >= lo:
                here -= sub
                pushed[i] = True
        starts[i] = here

    new_durations = [b - a for a, b in zip(starts, starts[1:] + [float(total)])]
    return new_durations, pushed
