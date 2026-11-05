import random

import pytest

from quikjamz.theory.chords import Chord
from quikjamz.theory.pitch import SpelledNote
from quikjamz.theory.scales import all_scales, choose_mode, make_key
from quikjamz.harmony.vocabulary import diatonic_chords


def names(notes):
    return [str(n) for n in notes]


def test_parse_and_print_notes():
    assert str(SpelledNote.parse("eb")) == "Eb"
    assert str(SpelledNote.parse("F#")) == "F#"
    assert SpelledNote.parse("Cb").pc == 11
    with pytest.raises(ValueError):
        SpelledNote.parse("H")


def test_all_seven_modes_load():
    assert set(all_scales()) == {
        "ionian", "dorian", "phrygian", "lydian", "mixolydian", "aeolian", "locrian"
    }


@pytest.mark.parametrize(
    "tonic, mode, expected",
    [
        ("C", "ionian", "C D E F G A B"),
        ("D", "dorian", "D E F G A B C"),
        ("Eb", "mixolydian", "Eb F G Ab Bb C Db"),
        ("F#", "lydian", "Gb Ab Bb C Db Eb F"),  # F# Lydian needs 7 sharps -> Gb
        ("A", "aeolian", "A B C D E F G"),
        ("Bb", "phrygian", "Bb Cb Db Eb F Gb Ab"),
    ],
)
def test_scale_spelling(tonic, mode, expected):
    assert " ".join(names(make_key(tonic, mode).scale_notes())) == expected


def test_signatures_follow_parent_major():
    assert make_key("D", "dorian").signature == 0  # C major
    assert make_key("Eb", "mixolydian").signature == -4  # Ab major
    assert make_key("E", "phrygian").signature == 0


def test_keys_with_too_many_accidentals_are_respelled():
    assert str(make_key("D#", "ionian").tonic) == "Eb"
    assert str(make_key("A#", "aeolian").tonic) == "Bb"  # A# minor would need 7 sharps
    assert str(make_key("F#", "ionian").tonic) == "F#"  # 6 sharps is allowed
    assert make_key(6, "ionian").signature in (6, -6)


def test_borrowed_degrees_spell_from_letters():
    key = make_key("C", "ionian")
    assert str(key.note(6, -1)) == "Ab"
    assert str(key.note(2, -1)) == "Db"
    assert str(key.note(4, +1)) == "F#"


def test_diatonic_chord_qualities():
    ionian = [c.triad for c in diatonic_chords(make_key("C", "ionian").scale)]
    assert ionian == ["maj", "min", "min", "maj", "maj", "min", "dim"]
    dorian = [c.triad for c in diatonic_chords(make_key("D", "dorian").scale)]
    assert dorian == ["min", "min", "maj", "maj", "min", "dim", "maj"]


@pytest.mark.parametrize(
    "chord, plain, jazz",
    [
        (Chord(1, 0, "maj", "maj7"), "Cmaj7", "CΔ7"),
        (Chord(7, 0, "dim", "7"), "Bm7b5", "Bø7"),
        (Chord(5, 0, "maj", "7", extensions=("9", "13")), "G13", "G13"),
        (Chord(2, 0, "min", "7", extensions=("9", "11")), "Dm11", "Dm11"),
        (Chord(5, 0, "maj", "7", alterations=("b9", "#11")), "G7(b9,#11)", "G7(b9,#11)"),
        (Chord(1, 0, "maj", "6", extensions=("9",)), "C6/9", "C6/9"),
        (Chord(7, -1, "maj", bass=(1, 0)), "Bb/C", "Bb/C"),
        (Chord(6, -1, "maj"), "Ab", "Ab"),
    ],
)
def test_chord_symbols(chord, plain, jazz):
    key = make_key("C", "ionian")
    assert chord.symbol(key) == plain
    assert chord.symbol(key, "jazz") == jazz


def test_roman_numerals():
    assert Chord(6, -1, "maj", "maj7").roman() == "bVImaj7"
    assert Chord(7, 0, "dim", "7").roman() == "viiø7"
    assert Chord(2, 0, "min").roman() == "ii"
    assert Chord(7, -1, "maj", bass=(1, 0)).roman() == "bVII/I"


def test_choose_mode_follows_brightness():
    rng = random.Random(0)
    bright = [choose_mode(0.95, rng).name for _ in range(200)]
    dark = [choose_mode(0.1, rng).name for _ in range(200)]
    assert bright.count("lydian") > 100
    assert set(dark) <= {"phrygian", "locrian", "aeolian"}
