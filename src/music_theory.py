from enum import Enum
from typing import List, Tuple
from dataclasses import dataclass


class Note(Enum):
    C = 0
    C_SHARP = 1
    D = 2
    D_SHARP = 3
    E = 4
    F = 5
    F_SHARP = 6
    G = 7
    G_SHARP = 8
    A = 9
    A_SHARP = 10
    B = 11

    def __str__(self):
        return self.name.replace("_SHARP", "#")


class ChordQuality(Enum):
    MAJOR = "major"
    MINOR = "minor"
    DOMINANT_7 = "dom7"
    MAJOR_7 = "maj7"
    MINOR_7 = "min7"
    DIMINISHED = "dim"
    AUGMENTED = "aug"
    SUS2 = "sus2"
    SUS4 = "sus4"
    POWER = "power"
    MAJOR_9 = "maj9"
    MINOR_9 = "min9"
    DOMINANT_9 = "dom9"
    MAJOR_11 = "maj11"
    MINOR_11 = "min11"
    MAJOR_13 = "maj13"
    MINOR_13 = "min13"


class ScaleType(Enum):
    MAJOR = "major"
    MINOR = "minor"
    DORIAN = "dorian"
    PHRYGIAN = "phrygian"
    LYDIAN = "lydian"
    MIXOLYDIAN = "mixolydian"
    AEOLIAN = "aeolian"
    LOCRIAN = "locrian"
    HARMONIC_MINOR = "harmonic_minor"
    MELODIC_MINOR = "melodic_minor"
    PENTATONIC_MAJOR = "pentatonic_major"
    PENTATONIC_MINOR = "pentatonic_minor"
    BLUES = "blues"


SCALE_INTERVALS = {
    ScaleType.MAJOR: [0, 2, 4, 5, 7, 9, 11],
    ScaleType.MINOR: [0, 2, 3, 5, 7, 8, 10],
    ScaleType.DORIAN: [0, 2, 3, 5, 7, 9, 10],
    ScaleType.PHRYGIAN: [0, 1, 3, 5, 7, 8, 10],
    ScaleType.LYDIAN: [0, 2, 4, 6, 7, 9, 11],
    ScaleType.MIXOLYDIAN: [0, 2, 4, 5, 7, 9, 10],
    ScaleType.AEOLIAN: [0, 2, 3, 5, 7, 8, 10],
    ScaleType.LOCRIAN: [0, 1, 3, 5, 6, 8, 10],
    ScaleType.HARMONIC_MINOR: [0, 2, 3, 5, 7, 8, 11],
    ScaleType.MELODIC_MINOR: [0, 2, 3, 5, 7, 9, 11],
    ScaleType.PENTATONIC_MAJOR: [0, 2, 4, 7, 9],
    ScaleType.PENTATONIC_MINOR: [0, 3, 5, 7, 10],
    ScaleType.BLUES: [0, 3, 5, 6, 7, 10],
}


@dataclass
class Chord:
    root: Note
    quality: ChordQuality

    def __str__(self):
        return f"{self.root}{self.quality.value}"


@dataclass
class Scale:
    root: Note
    scale_type: ScaleType

    def get_notes(self) -> List[Note]:
        intervals = SCALE_INTERVALS[self.scale_type]
        notes = []
        for interval in intervals:
            note_value = (self.root.value + interval) % 12
            notes.append(Note(note_value))
        return notes

    def __str__(self):
        return f"{self.root} {self.scale_type.value}"


@dataclass
class TimeSignature:
    beats_per_measure: int
    beat_unit: int

    def __str__(self):
        return f"{self.beats_per_measure}/{self.beat_unit}"


class Dynamics(Enum):
    PIANISSIMO = "pp"
    PIANO = "p"
    MEZZO_PIANO = "mp"
    MEZZO_FORTE = "mf"
    FORTE = "f"
    FORTISSIMO = "ff"

    def __str__(self):
        return self.value


class RhythmDensity(Enum):
    SPARSE = "sparse"
    MODERATE = "moderate"
    DENSE = "dense"
    VERY_DENSE = "very_dense"


class Mood(Enum):
    HAPPY = "happy"
    SAD = "sad"
    ENERGETIC = "energetic"
    CALM = "calm"
    DARK = "dark"
    BRIGHT = "bright"
    TENSE = "tense"
    RELAXED = "relaxed"
    MYSTERIOUS = "mysterious"
    TRIUMPHANT = "triumphant"
