import random
import statistics

import pytest

from quikjamz.harmony import build_pool, generate_loop, maybe_modulate, modulate
from quikjamz.harmony.progression import plan_durations, tier_multiplier
from quikjamz.theory.scales import all_scales, make_key

C_MAJOR = make_key("C", "ionian")


def symbols(chords, key=C_MAJOR):
    return {c.symbol(key) for c in chords}


def by_source(pool, prefix):
    return [c for c in pool if c.source.startswith(prefix)]


# ---------------------------------------------------------------- vocabulary


def test_low_tiers_stay_in_the_scale():
    for name in all_scales():
        key = make_key("C", name)
        for chord in build_pool(key):
            if chord.tier <= 1 and chord.source == "diatonic":
                assert chord.rel_pcs() <= key.scale.pcs, (name, chord)


def test_tier0_is_the_main_three_chords():
    tier0 = [c for c in build_pool(C_MAJOR) if c.tier == 0]
    assert symbols(tier0) == {"C", "F", "G"}
    dorian = make_key("D", "dorian")
    assert symbols([c for c in build_pool(dorian) if c.tier == 0], dorian) == {"Dm", "G", "C"}


def test_borrowed_chords_in_major_include_modal_interchange():
    borrowed = symbols(by_source(build_pool(C_MAJOR, brightness=0.3), "borrowed"))
    assert {"Fm", "Ab", "Bb", "Eb"} <= borrowed


def test_secondary_dominants_and_tritone_subs():
    pool = build_pool(C_MAJOR)
    secondary = {c.symbol(C_MAJOR): c.roman() for c in by_source(pool, "secondary")}
    assert secondary["A7"] == "V7/ii"
    assert secondary["D7"] == "V7/V"
    assert secondary["E7"] == "V7/vi"
    assert secondary["C7"] == "V7/IV"
    assert "G7" not in secondary  # V already exists in major
    subs = {c.symbol(C_MAJOR) for c in by_source(pool, "tritone_sub")}
    assert {"Db7", "Ab7", "Eb7"} <= subs


def test_chromatic_mediants():
    pool = build_pool(C_MAJOR)
    # Eb and Ab already arrive as borrowed chords (a lower tier), so only E and A are new here.
    assert symbols(by_source(pool, "mediant")) == {"E", "A"}
    assert {"Eb", "Ab"} <= symbols(pool)


def test_tier_multiplier_fades_in():
    assert tier_multiplier(0, 0.0) == 1.0
    assert tier_multiplier(1, 0.0) < 0.1
    assert tier_multiplier(1, 0.3) > 0.9
    assert tier_multiplier(4, 0.5) < 0.01
    assert tier_multiplier(5, 1.0) > 0.9


# ----------------------------------------------------------------------- loops


def loops(n=150, seed=0, key=C_MAJOR, **knobs):
    rng = random.Random(seed)
    return [generate_loop(key, rng, **knobs) for _ in range(n)]


def test_same_seed_same_loop():
    a = [l.chords for l in loops(10, seed=42, harm_adv=0.6)]
    b = [l.chords for l in loops(10, seed=42, harm_adv=0.6)]
    assert a == b


@pytest.mark.parametrize("beats", [3, 4, 5, 7])
def test_loop_lengths_are_whole_bars(beats):
    for loop in loops(50, beats_per_bar=beats, complexity=0.8):
        total = sum(e.beats for e in loop.events)
        assert total % beats == 0
        assert loop.bars in (1, 2, 4, 8)


def test_durations_hold_chords_longer_at_low_complexity():
    rng = random.Random(1)
    slow = [statistics.mean(plan_durations(3, 0.1, 4, rng)) for _ in range(50)]
    fast = [statistics.mean(plan_durations(3, 0.9, 4, rng)) for _ in range(50)]
    assert statistics.mean(slow) > statistics.mean(fast)


def test_harm_adv_raises_tiers_and_surprise():
    def mean_tier(ls):
        return statistics.mean(c.tier for l in ls for c in l.chords)

    tame, wild = loops(harm_adv=0.0), loops(harm_adv=0.9)
    assert all(c.tier <= 1 for l in tame for c in l.chords)
    assert mean_tier(wild) > mean_tier(tame) + 1.0
    assert statistics.mean(l.surprise for l in wild) > statistics.mean(l.surprise for l in tame) + 1.0


def test_complexity_raises_chord_count_and_colour():
    simple, rich = loops(complexity=0.1), loops(complexity=0.9)
    assert statistics.mean(len(l.chords) for l in rich) > statistics.mean(len(l.chords) for l in simple) + 2
    assert all(c.seventh is None for l in simple for c in l.chords)
    assert statistics.mean(len(c.extensions) for l in rich for c in l.chords) > 0.5


def test_one_chord_vamps_sit_on_home():
    for loop in loops(40, complexity=0.0, harm_adv=0.8, n_chords=1):
        assert loop.chords[0].degree == 1 and loop.chords[0].source == "diatonic"


def test_tension_controls_resolution():
    calm = loops(tension=0.05)
    tense = loops(tension=0.95)
    assert sum(l.ending == "resolve" for l in calm) > 0.85 * len(calm)
    assert sum(l.ending == "hang" for l in tense) > 0.6 * len(tense)


def test_altered_dominants_only_when_tense():
    calm = loops(tension=0.2, complexity=0.8, harm_adv=0.6)
    tense = loops(tension=0.95, complexity=0.8, harm_adv=0.6)
    assert not any(c.alterations and c.fn == "P" and "#11" not in c.alterations
                   for l in calm for c in l.chords)
    assert any(c.alterations for l in tense for c in l.chords)


def test_secondary_dominants_resolve_to_their_target():
    hits = misses = 0
    for loop in loops(300, harm_adv=0.6, seed=3):
        chords = loop.chords
        for a, b in zip(chords, chords[1:] + chords[:1]):
            if a.source == "secondary":
                if b.rel_root == a.resolves_to:
                    hits += 1
                else:
                    misses += 1
    assert hits > 2 * misses


# ------------------------------------------------------------------ key changes


def test_modulation_moves():
    rng = random.Random(0)
    assert str(modulate(C_MAJOR, "relative", rng)) == "A Aeolian"
    assert str(modulate(C_MAJOR, "parallel", rng)) == "C Aeolian"
    assert str(modulate(C_MAJOR, "up_whole_step", rng)) == "D Ionian"
    assert str(modulate(make_key("A", "aeolian"), "relative", rng)) == "C Ionian"


def test_no_key_changes_at_low_adventurousness():
    rng = random.Random(0)
    assert all(maybe_modulate(C_MAJOR, 0.4, rng)[1] is None for _ in range(200))
    assert any(maybe_modulate(C_MAJOR, 0.9, rng)[1] for _ in range(50))
