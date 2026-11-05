import random
from collections import Counter

import mido
import pytest

from quikjamz.harmony import generate_loop
from quikjamz.harmony.rhythm import place_changes, strong_points
from quikjamz.jam import JamConfig, generate_jam
from quikjamz.render.midi import MidiSection, write_midi
from quikjamz.render.sheet import sheet_data
from quikjamz.render.text import bar_cells, beat_name
from quikjamz.theory.meter import Meter
from quikjamz.theory.scales import make_key

KEY = make_key("C", "ionian")


def landing_spots(meter: str, rhythm_adv: float, n=300, seed=0) -> Counter:
    m = Meter.parse(meter)
    strong = set(strong_points(m))
    rng = random.Random(seed)
    spots = Counter()
    for _ in range(n):
        loop = generate_loop(KEY, rng, complexity=0.6, meter=m, rhythm_adv=rhythm_adv)
        for event, start in list(zip(loop.events, loop.starts()))[1:]:
            pos = start % m.beats
            spots["push" if event.push else "bar" if pos == 0 else "strong" if pos in strong else "weak"] += 1
    return spots


def test_strong_points():
    assert strong_points(Meter.parse("4/4")) == [2]
    assert strong_points(Meter.parse("3/4")) == []
    assert strong_points(Meter.parse("7/8")) == [2, 4]
    assert strong_points(Meter.parse("6/8")) == [3]
    assert strong_points(Meter.parse("5/4")) == [3]


@pytest.mark.parametrize("meter", ["4/4", "7/8"])
def test_low_rhythm_adv_keeps_changes_on_strong_spots(meter):
    spots = landing_spots(meter, 0.0)
    assert spots["weak"] == 0 and spots["push"] == 0
    assert spots["bar"] > 0.8 * sum(spots.values())


@pytest.mark.parametrize("meter", ["4/4", "7/8"])
def test_high_rhythm_adv_moves_changes_and_pushes(meter):
    spots = landing_spots(meter, 0.9)
    total = sum(spots.values())
    assert spots["bar"] < 0.5 * total
    assert spots["push"] > 0.1 * total and spots["weak"] > 0


def test_placement_keeps_loop_length_and_min_durations():
    rng = random.Random(3)
    for meter in ("4/4", "3/4", "7/8", "12/8", "5/4"):
        m = Meter.parse(meter)
        min_d = 1.0 if m.unit == 4 else 2.0
        for _ in range(200):
            durations = [m.beats] * rng.randint(2, 5)
            placed, pushed = place_changes(durations, m, rng.random(), rng)
            assert sum(placed) == sum(durations)
            assert all(d >= min_d for d in placed)
            assert not pushed[0]


def test_first_chord_always_on_the_downbeat():
    rng = random.Random(1)
    for _ in range(100):
        loop = generate_loop(KEY, rng, complexity=0.8, meter=Meter(4), rhythm_adv=1.0)
        assert loop.starts()[0] == 0 and not loop.events[0].push


def test_beat_names_and_text_cells():
    assert [beat_name(p) for p in (0, 1, 2.5, 3.5)] == ["1", "2", "3&", "4&"]
    rng = random.Random(5)
    for _ in range(50):
        loop = generate_loop(KEY, rng, complexity=0.6, meter=Meter(4), rhythm_adv=0.9)
        cells = bar_cells(loop, KEY)
        assert len(cells) == loop.bars
        assert sum(c.count("›") for c in cells) == sum(e.push for e in loop.events)


def test_sheet_slots_are_one_per_beat():
    for seed in range(15):
        jam = generate_jam(JamConfig(seed=seed, knobs={"rhythm_adv": 0.85}, meter="4/4"))
        for sec_data, sec in zip(sheet_data(jam)["sections"], jam.sections):
            for bar in sec_data["bars"]:
                if bar["slots"] is not None:
                    chords = sum(s["chord"] is not None for s in bar["slots"])
                    assert len(bar["slots"]) - chords + chords >= sec.meter.beats
                    assert sec_data["bars_per_row"] == 4


def test_midi_lengths_follow_fractional_beats(tmp_path):
    rng = random.Random(2)
    loops = [generate_loop(KEY, rng, complexity=0.6, meter=Meter(4), rhythm_adv=1.0) for _ in range(3)]
    assert any(e.beats % 1 for l in loops for e in l.events)
    path = write_midi(tmp_path / "x.mid", [MidiSection(l, passes=1, play_ending=False) for l in loops],
                      quarter_bpm=120, gap_bars=0, click=False)
    beats = sum(l.bars * 4 for l in loops)
    assert mido.MidiFile(path).length == pytest.approx(beats * 0.5, rel=0.01)
