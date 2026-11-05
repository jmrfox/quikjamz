import json
import random

import mido
import pytest

from quikjamz.cli import main
from quikjamz.form import TEMPLATES, build_form, choose_form, make_labels
from quikjamz.jam import JamConfig, generate_jam
from quikjamz.knobs import ARC_NAMES, Arc, Knobs, moods, resolve_knobs, section_knobs, vibe_words
from quikjamz.render.midi import jam_to_midi
from quikjamz.render.text import render_text
from quikjamz.theory.meter import Meter, choose_meter


# ------------------------------------------------------------------- knobs


def test_moods_load_with_all_knobs():
    presets = moods()
    assert len(presets) == 10
    assert presets["hypnotic"].stability == 0.95


def test_overrides_beat_the_mood():
    _, knobs = resolve_knobs("calm", {"energy": 0.9}, random.Random(0))
    assert knobs.energy == 0.9 and knobs.tension == moods()["calm"].tension


def test_unknown_mood_or_knob_is_an_error():
    with pytest.raises(ValueError):
        resolve_knobs("grumpy", {}, random.Random(0))
    with pytest.raises(ValueError):
        resolve_knobs("calm", {"loudness": 1}, random.Random(0))


@pytest.mark.parametrize("name", ARC_NAMES)
def test_arcs_stay_in_range(name):
    arc = Arc(name, random.Random(1))
    assert all(0 <= arc(t / 20) <= 1 for t in range(21))


def test_arch_peaks_in_the_middle():
    arc = Arc("arch", random.Random(0))
    assert arc(0.5) > arc(0.0) + 0.9


def test_section_knobs_follow_the_arc_and_keep_global_identity():
    rng = random.Random(0)
    base = Knobs(stability=1.0)
    arc = Arc("build", rng)
    start, end = section_knobs(base, arc, 0, rng), section_knobs(base, arc, 1, rng)
    assert end.energy > start.energy + 0.5
    assert start.brightness == end.brightness == base.brightness  # no noise at stability 1


def test_vibe_words():
    assert vibe_words(Knobs(energy=0.95, brightness=0.1)) == ["driving", "dark"]
    assert vibe_words(Knobs()) == ["even"]


# ------------------------------------------------------------------- meter


def test_meter_parsing_and_groupings():
    assert str(Meter.parse("7/8")) == "7/8 (2+2+3)"
    assert str(Meter.parse("7/8:3+2+2")) == "7/8 (3+2+2)"
    assert str(Meter.parse("4/4")) == "4/4"
    with pytest.raises(ValueError):
        Meter.parse("7/8:3+3")


def test_meter_follows_rhythmic_adventurousness():
    rng = random.Random(0)
    tame = {choose_meter(0.1, rng).signature for _ in range(100)}
    wild = {choose_meter(0.9, rng).signature for _ in range(100)}
    assert tame <= {"4/4", "3/4"}
    assert "4/4" not in wild


# -------------------------------------------------------------------- form


@pytest.mark.parametrize("template", sorted(TEMPLATES))
@pytest.mark.parametrize("n", [4, 5, 6])
def test_forms_are_consistent(template, n):
    slots = build_form(template, n)
    assert len(slots) == n and slots[0].kind == "new"
    for i, slot in enumerate(slots):
        if slot.kind in ("return", "drift"):
            assert 0 <= slot.source < i


def test_specific_forms():
    assert [s.kind for s in build_form("ring", 5)] == ["new", "new", "return", "new", "return"]
    assert [s.kind for s in build_form("mirror", 5)] == ["new", "new", "new", "return", "return"]


def test_stability_favours_returns():
    rng = random.Random(0)
    def returns(stability):
        total = 0
        for _ in range(200):
            _, slots = choose_form(5, stability, rng)
            total += sum(s.kind == "return" for s in slots)
        return total
    assert returns(0.95) > 2 * returns(0.05)


@pytest.mark.parametrize("style", ["letters", "glyphs", "colors", "motion", "image"])
def test_labels_mark_returns_with_primes(style):
    slots = build_form("ring", 5)
    knobs = [Knobs(energy=e) for e in (0.2, 0.5, 0.8, 0.5, 0.2)]
    labels = make_labels(slots, knobs, style, random.Random(0))
    assert labels[2] == labels[0] + "′" and labels[4] == labels[0] + "″"
    new = [l for l, s in zip(labels, slots) if s.kind == "new"]
    assert len(set(new)) == len(new)


def test_no_pop_section_names_anywhere():
    banned = {"verse", "chorus", "bridge", "intro", "outro", "pre-chorus", "hook"}
    for seed in range(30):
        for style in ("motion", "image"):
            jam = generate_jam(JamConfig(seed=seed, labels=style))
            assert not {s.label.lower().rstrip("′″‴") for s in jam.sections} & banned


# --------------------------------------------------------------------- jam


def test_same_seed_same_jam():
    a = generate_jam(JamConfig(seed=11, mood="dreamy")).to_dict()
    b = generate_jam(JamConfig(seed=11, mood="dreamy")).to_dict()
    assert a == b


def test_config_is_respected():
    jam = generate_jam(JamConfig(seed=1, key="Eb", mode="mixolydian", tempo=88, meter="5/4",
                                 sections=6, form="ring", labels="glyphs"))
    assert str(jam.home_key) == "Eb Mixolydian"
    assert jam.tempo == 88 and str(jam.meter) == "5/4 (3+2)" and jam.form == "ring"
    assert len(jam.sections) == 6
    assert all(s.meter == jam.meter for s in jam.sections)


def test_returns_reuse_harmony_key_and_meter():
    for seed in range(20):
        jam = generate_jam(JamConfig(seed=seed, form="ring", sections=5, mood="chaotic"))
        for s in jam.sections:
            if s.return_of is not None:
                src = jam.sections[s.return_of]
                assert s.loop.chords == src.loop.chords
                assert s.key == src.key and s.meter == src.meter


def test_drift_changes_one_chord_or_grows_a_vamp():
    for seed in range(20):
        jam = generate_jam(JamConfig(seed=seed, form="drift", sections=4))
        for s in jam.sections[1:]:
            prev = jam.sections[s.drift_of].loop.chords
            now = s.loop.chords
            if len(prev) == 1:
                assert len(now) == 2 and now[0] == prev[0]
            else:
                assert len(now) == len(prev)
                assert sum(a.ident != b.ident for a, b in zip(prev, now)) <= 1


def test_last_section_has_an_ending_cue():
    for seed in range(20):
        assert generate_jam(JamConfig(seed=seed)).sections[-1].cue.type in ("fade", "hit")


def test_only_the_first_section_has_a_start_cue():
    jam = generate_jam(JamConfig(seed=4))
    assert jam.sections[0].start_cue and not any(s.start_cue for s in jam.sections[1:])


def test_bar_numbers_run_across_sections():
    jam = generate_jam(JamConfig(seed=5))
    for a, b in zip(jam.sections, jam.sections[1:]):
        assert b.start_bar == a.start_bar + a.loop.bars


def test_key_changes_only_when_adventurous():
    tame = [generate_jam(JamConfig(seed=s, knobs={"harm_adv": 0.2})) for s in range(15)]
    assert all(sec.key == j.home_key for j in tame for sec in j.sections)


def test_json_round_trips():
    data = generate_jam(JamConfig(seed=9, labels="motion")).to_dict()
    again = json.loads(json.dumps(data, ensure_ascii=False))
    assert again["sections"][0]["loop"]["chords"][0]["symbol"]


def test_text_chart_has_header_and_no_jam_guide_heading():
    jam = generate_jam(JamConfig(seed=2, title="Tuesday", tempo=96, key="D", mode="dorian", meter="4/4"))
    text = render_text(jam)
    first = text.splitlines()[0]
    assert first.startswith("Tuesday") and "♩ = 96" in first and "4/4" in first and "D Dorian" in first
    assert "jam guide" not in text.lower()


def test_jam_midi_has_one_bar_per_click_accent(tmp_path):
    jam = generate_jam(JamConfig(seed=8, mood="chaotic", sections=6))
    path = jam_to_midi(jam, tmp_path / "jam.mid")
    midi = mido.MidiFile(path)
    accents = [m for m in midi.tracks[3] if m.type == "note_on" and m.velocity == 100]
    expected = sum(s.loop.bars * s.cue.passes for s in jam.sections) + 1  # + ending bar
    assert len(accents) == expected
    signatures = [m for m in midi.tracks[0] if m.type == "time_signature"]
    assert len(signatures) >= 1


def test_cli_writes_outputs(tmp_path, capsys):
    code = main(["--seed", "3", "--title", "CLI", "--midi", str(tmp_path / "a.mid"),
                 "--json", str(tmp_path / "a.json")])
    assert code == 0
    assert (tmp_path / "a.mid").exists() and (tmp_path / "a.json").exists()
    assert capsys.readouterr().out.startswith("CLI")


def test_cli_reports_bad_input(capsys):
    assert main(["--mode", "klingon", "--seed", "1"]) == 2
