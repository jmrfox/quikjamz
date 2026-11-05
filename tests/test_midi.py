import random

import mido
import pytest

from quikjamz.harmony import generate_loop
from quikjamz.render.midi import CHORD_HIGH, CHORD_LOW, MidiSection, voice, write_midi
from quikjamz.theory.scales import make_key


def make_loops(n=3, seed=0, beats=4, **knobs):
    rng = random.Random(seed)
    key = make_key("D", "dorian")
    return [generate_loop(key, rng, beats_per_bar=beats, **knobs) for _ in range(n)]


def notes_by_start(track):
    tick, groups = 0, {}
    for msg in track:
        tick += msg.time
        if msg.type == "note_on" and msg.velocity > 0:
            groups.setdefault(tick, []).append(msg.note)
    return groups


def test_writes_one_file_with_named_tracks(tmp_path):
    path = write_midi(tmp_path / "jam.mid", [MidiSection(l) for l in make_loops()])
    midi = mido.MidiFile(path)
    assert [t.name for t in midi.tracks] == ["QuikJamz", "chords", "bass", "click"]
    assert list(tmp_path.iterdir()) == [path]


def test_no_click_track_when_disabled(tmp_path):
    path = write_midi(tmp_path / "jam.mid", [MidiSection(l) for l in make_loops()], click=False)
    assert [t.name for t in mido.MidiFile(path).tracks] == ["QuikJamz", "chords", "bass"]


@pytest.mark.parametrize("beats, unit, tempo", [(4, 4, 120), (7, 8, 210), (3, 4, 90)])
def test_tempo_meter_and_length(tmp_path, beats, unit, tempo):
    loops = make_loops(2, beats=beats)
    sections = [MidiSection(l, passes=2, beat_unit=unit) for l in loops]
    path = write_midi(tmp_path / "jam.mid", sections, quarter_bpm=tempo * 4 / unit, gap_bars=1)
    midi = mido.MidiFile(path)
    meta = {m.type: m for m in midi.tracks[0]}
    assert meta["time_signature"].numerator == beats
    assert meta["time_signature"].denominator == unit

    total_beats = sum(2 * sum(e.beats for e in l.events) + beats for l in loops) + beats  # + gap
    seconds_per_beat = 60 / tempo
    assert midi.length == pytest.approx(total_beats * seconds_per_beat, rel=0.01)


def test_bass_plays_each_chord_root(tmp_path):
    loop = make_loops(1, seed=4)[0]
    path = write_midi(tmp_path / "jam.mid", [MidiSection(loop, passes=1, play_ending=False)])
    bass = notes_by_start(mido.MidiFile(path).tracks[2])
    tonic = loop.key.tonic.pc
    expected = [(tonic + c.rel_root) % 12 for c in loop.chords]
    assert [notes[0] % 12 for _, notes in sorted(bass.items())] == expected


def test_chord_notes_match_chord_tones_and_range(tmp_path):
    loops = make_loops(4, seed=2, complexity=0.9)
    path = write_midi(tmp_path / "jam.mid", [MidiSection(l, passes=1, play_ending=False) for l in loops])
    played = [set(n % 12 for n in notes) for _, notes in sorted(notes_by_start(mido.MidiFile(path).tracks[1]).items())]
    chords = [c for l in loops for c in l.chords]
    assert len(played) == len(chords)
    for pcs, chord in zip(played, chords):
        tonic = loops[0].key.tonic.pc
        assert pcs <= {(tonic + p) % 12 for p in chord.rel_pcs()}
    for notes in notes_by_start(mido.MidiFile(path).tracks[1]).values():
        assert all(CHORD_LOW <= n <= CHORD_HIGH for n in notes)


def test_voicing_moves_smoothly():
    c, f = [0, 4, 7], [5, 9, 0]
    first = voice(c, None)
    nxt = voice(f, first)
    # C -> F keeps the common tone C and moves the others by a step or less.
    assert sum(min(abs(n - p) for p in first) for n in nxt) <= 4


def test_wide_chords_still_get_a_voicing():
    # Bb D Ab G Db: no close stack fits the range, so the fallback places each note.
    notes = voice([10, 2, 8, 7, 1], [55, 59, 62, 72, 76])
    assert sorted(n % 12 for n in notes) == sorted([10, 2, 8, 7, 1])
    assert all(CHORD_LOW <= n <= CHORD_HIGH for n in notes)
