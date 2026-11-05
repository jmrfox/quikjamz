"""Spelled notes: letter names, accidentals, and key-signature arithmetic.

Everything in the harmony engine works in pitch classes *relative to the tonic*.
Spelling to real note names happens only here, at the edge.
"""

from __future__ import annotations

from dataclasses import dataclass

LETTERS = "CDEFGAB"
NATURAL_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
# Position of each natural letter's major key on the circle of fifths (C = 0).
LETTER_FIFTHS = {"F": -1, "C": 0, "G": 1, "D": 2, "A": 3, "E": 4, "B": 5}
# Semitones of each degree of the major scale; Roman numerals are measured against it.
MAJOR_STEPS = (0, 2, 4, 5, 7, 9, 11)

_ACCIDENTAL_CHARS = {"#": 1, "♯": 1, "b": -1, "♭": -1}


def wrap_signed(semitones: int) -> int:
    """Wrap an interval into -6..5, the smallest signed distance."""
    return (semitones + 6) % 12 - 6


@dataclass(frozen=True)
class SpelledNote:
    letter: str
    accidental: int = 0  # +1 sharp, -1 flat, +2 double sharp, ...

    @property
    def pc(self) -> int:
        return (NATURAL_PC[self.letter] + self.accidental) % 12

    @property
    def fifths(self) -> int:
        """Circle-of-fifths position of the major key on this note (C=0, G=1, F=-1)."""
        return LETTER_FIFTHS[self.letter] + 7 * self.accidental

    def __str__(self) -> str:
        if self.accidental >= 0:
            return self.letter + "#" * self.accidental
        return self.letter + "b" * -self.accidental

    @classmethod
    def parse(cls, text: str) -> "SpelledNote":
        text = text.strip()
        if not text or text[0].upper() not in LETTERS:
            raise ValueError(f"Not a note name: {text!r}")
        accidental = 0
        for ch in text[1:]:
            if ch not in _ACCIDENTAL_CHARS:
                raise ValueError(f"Not a note name: {text!r}")
            accidental += _ACCIDENTAL_CHARS[ch]
        return cls(text[0].upper(), accidental)

    def step(self, letter_steps: int, semitones: int) -> "SpelledNote":
        """The note `letter_steps` letters above this one, sounding `semitones` above it."""
        letter = LETTERS[(LETTERS.index(self.letter) + letter_steps) % 7]
        target_pc = (self.pc + semitones) % 12
        return SpelledNote(letter, wrap_signed(target_pc - NATURAL_PC[letter]))


def spellings_of(pc: int) -> list[SpelledNote]:
    """All spellings of a pitch class with at most one sharp or flat."""
    out = []
    for letter in LETTERS:
        acc = wrap_signed(pc - NATURAL_PC[letter])
        if abs(acc) <= 1:
            out.append(SpelledNote(letter, acc))
    return out
