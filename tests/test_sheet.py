import random

import pytest

from quikjamz.jam import JamConfig, generate_jam
from quikjamz.knobs import Knobs
from quikjamz.prompts import melody_idea, pick_prompts, prompt_deck, rhythm_idea
from quikjamz.render.sheet import pretty, render_pdf, sheet_data
from quikjamz.theory.meter import Meter
from quikjamz.theory.scales import make_key


# ----------------------------------------------------------------- prompts


def test_deck_loads_and_has_no_pop_section_words():
    deck = prompt_deck()
    assert len(deck) >= 30
    banned = ("verse", "chorus", "bridge", "swing", "shuffle")
    assert not [p.text for p in deck if any(b in p.text.lower() for b in banned)]


def test_prompts_fit_the_knobs_and_dont_repeat():
    rng = random.Random(0)
    used: set[str] = set()
    calm = Knobs(energy=0.1, density=0.1, complexity=0.9)
    picked = []
    for _ in range(10):
        picked += pick_prompts(calm, rng, used)
    assert len(picked) == len(set(picked))
    by_text = {p.text: p for p in prompt_deck()}
    assert all(by_text[t].fits(calm) for t in picked)
    assert "This is the peak. Nothing held back." not in picked


def test_half_time_only_appears_as_a_prompt():
    for seed in range(40):
        jam = generate_jam(JamConfig(seed=seed))
        for s in jam.sections:
            assert "half-time" not in s.cue.text and "half-time" not in " ".join(s.vibe)


@pytest.mark.parametrize("meter", ["4/4", "3/4", "6/8", "7/8", "5/4", "12/8"])
def test_rhythm_ideas_fill_one_bar(meter):
    m = Meter.parse(meter)
    rng = random.Random(1)
    for _ in range(20):
        text = rhythm_idea(m, Knobs(density=0.5, rhythm_adv=0.5), rng)
        steps = text.replace(" ", "")
        assert set(steps) <= {"x", "."} and "x" in steps
        assert len(steps) == (m.beats * 2 if m.unit == 4 else m.beats)


def test_melody_ideas_use_the_scale():
    key = make_key("D", "dorian")
    names = {str(n) for n in key.scale_notes()}
    rng = random.Random(2)
    for _ in range(30):
        notes = melody_idea(key, Knobs(complexity=0.5), rng).split("–")
        assert 3 <= len(notes) <= 5 and set(notes) <= names


def test_returns_keep_their_idea_but_get_fresh_prompts():
    for seed in range(20):
        jam = generate_jam(JamConfig(seed=seed, form="ring", sections=5))
        for s in jam.sections:
            if s.return_of is not None:
                assert s.idea == jam.sections[s.return_of].idea
        all_prompts = [p for s in jam.sections for p in s.prompts]
        assert len(all_prompts) == len(set(all_prompts))


# ------------------------------------------------------------------- sheet


def test_pretty_accidentals():
    assert pretty("Bb") == "B♭"
    assert pretty("F#m7b5") == "F♯m7♭5"
    assert pretty("7(b9,#11)") == "7(♭9,♯11)"
    assert pretty("sus4") == "sus4" and pretty("dim7") == "dim7"


def test_sheet_data_matches_the_jam():
    jam = generate_jam(JamConfig(seed=5, title="Tue", key="Eb", mode="mixolydian", tempo=96, meter="4/4"))
    data = sheet_data(jam)
    assert (data["title"], data["tempo"], data["meter"], data["key"]) == ("Tue", "♩ = 96", "4/4", "E♭ Mixolydian")
    assert len(data["sections"]) == len(jam.sections) == len(data["roadmap"])
    for sec, s in zip(data["sections"], jam.sections):
        assert [b["n"] for b in sec["bars"]] == list(range(s.start_bar, s.start_bar + s.loop.bars))
        assert sum(len(b["chords"]) for b in sec["bars"]) == len(s.loop.events)
    assert "jam guide" not in str(data).lower()


def test_eighth_note_meters_show_eighth_tempo():
    jam = generate_jam(JamConfig(seed=1, meter="7/8", tempo=100))
    assert sheet_data(jam)["tempo"] == "♪ = 200"


@pytest.mark.parametrize("paper", ["letter", "a4"])
def test_render_pdf(tmp_path, paper):
    jam = generate_jam(JamConfig(seed=3, mood="chaotic", labels="image", sections=6))
    path = render_pdf(jam, tmp_path / "sheet.pdf", style="jazz", paper=paper)
    assert path.read_bytes().startswith(b"%PDF")


def test_unknown_paper_is_an_error(tmp_path):
    with pytest.raises(ValueError):
        render_pdf(generate_jam(JamConfig(seed=1)), tmp_path / "x.pdf", paper="legal")
