"""Chords as scale degrees, plus symbols and Roman numerals.

A chord's root is stored as (degree, alteration) measured against the major scale
on the tonic, so "bVI" is degree 6, alteration -1 in any key or mode. That is
also what makes spelling work: the letter comes from the degree.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .pitch import MAJOR_STEPS, wrap_signed
from .scales import Key

TRIAD_TONES = {
    "maj": (0, 4, 7),
    "min": (0, 3, 7),
    "dim": (0, 3, 6),
    "aug": (0, 4, 8),
    "sus2": (0, 2, 7),
    "sus4": (0, 5, 7),
    "5": (0, 7),
    "quartal": (0, 5, 10),
}
SEVENTH_TONE = {"maj7": 11, "7": 10, "dim7": 9, "6": 9}
EXTENSION_TONE = {"9": 14, "11": 17, "13": 21}
ALTERATION_TONE = {"b9": 13, "#9": 15, "#11": 18, "b13": 20}

ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII")

# (triad, seventh) -> symbol suffix, for the two symbol styles.
_SUFFIX = {
    ("maj", None): ("", ""),
    ("min", None): ("m", "m"),
    ("dim", None): ("dim", "°"),
    ("aug", None): ("+", "+"),
    ("sus2", None): ("sus2", "sus2"),
    ("sus4", None): ("sus4", "sus4"),
    ("5", None): ("5", "5"),
    ("quartal", None): ("(4ths)", "(4ths)"),
    ("maj", "7"): ("7", "7"),
    ("maj", "maj7"): ("maj7", "Δ7"),
    ("maj", "6"): ("6", "6"),
    ("min", "7"): ("m7", "m7"),
    ("min", "maj7"): ("m(maj7)", "mΔ7"),
    ("min", "6"): ("m6", "m6"),
    ("dim", "7"): ("m7b5", "ø7"),
    ("dim", "dim7"): ("dim7", "°7"),
    ("aug", "7"): ("7#5", "7#5"),
    ("aug", "maj7"): ("maj7#5", "Δ7#5"),
    ("sus4", "7"): ("7sus4", "7sus4"),
    ("sus2", "7"): ("7sus2", "7sus2"),
}


def triad_from_tones(third: int, fifth: int) -> str:
    """Classify a stacked triad from its third and fifth (semitones above the root)."""
    return {
        (4, 7): "maj",
        (3, 7): "min",
        (3, 6): "dim",
        (4, 8): "aug",
    }.get((third % 12, fifth % 12), "maj")


@dataclass(frozen=True)
class Chord:
    degree: int  # 1..7, letter position above the tonic
    alteration: int  # semitones vs. the major scale degree
    triad: str
    seventh: str | None = None
    extensions: tuple[str, ...] = ()
    alterations: tuple[str, ...] = ()
    bass: tuple[int, int] | None = None  # (degree, alteration) for slash chords

    # --- harmonic metadata (not part of what's played) ---
    fn: str = "A"  # H home, A away, P pull, N non-functional
    tier: int = 0
    source: str = "diatonic"
    resolves_to: int | None = None  # tonic-relative pc of the root this chord pulls to
    color: tuple[int, ...] = ()  # scale (semitones above the chord root) for extensions
    prior: float = 1.0  # extra weight in the chord pool
    label: str | None = None  # Roman numeral override, e.g. "V7/ii"
    fixed_seventh: bool = False  # always keeps its 7th (secondary dominants)

    # ---- pitch ----
    @property
    def rel_root(self) -> int:
        """Root as a pitch class relative to the tonic."""
        return (MAJOR_STEPS[self.degree - 1] + self.alteration) % 12

    @property
    def rel_bass(self) -> int | None:
        if self.bass is None:
            return None
        deg, alt = self.bass
        return (MAJOR_STEPS[deg - 1] + alt) % 12

    @property
    def ident(self) -> tuple:
        """What makes two chords 'the same chord' when walking a progression."""
        # Applied dominants (C7 as V7/IV) count as different from the plain chord (C).
        return (self.rel_root, self.triad, self.rel_bass, self.fixed_seventh)

    def tones(self, core_only: bool = False) -> tuple[int, ...]:
        """Semitones above the root, in stacking order."""
        out = list(TRIAD_TONES[self.triad])
        if self.seventh:
            out.append(SEVENTH_TONE[self.seventh])
        if not core_only:
            out += [EXTENSION_TONE[e] for e in self.extensions]
            out += [ALTERATION_TONE[a] for a in self.alterations]
        return tuple(out)

    def rel_pcs(self, core_only: bool = False) -> frozenset[int]:
        """Pitch classes relative to the tonic."""
        pcs = {(self.rel_root + t) % 12 for t in self.tones(core_only)}
        if self.rel_bass is not None:
            pcs.add(self.rel_bass)
        return frozenset(pcs)

    @property
    def is_dominant(self) -> bool:
        return self.triad == "maj" and self.seventh == "7"

    def with_(self, **changes) -> "Chord":
        return replace(self, **changes)

    # ---- display ----
    def symbol(self, key: Key, style: str = "plain") -> str:
        """Chord symbol in the key, e.g. 'Ebmaj7', 'F#m7b5', 'G7(b9)', 'Bb/C'."""
        root = str(key.note(self.degree, self.alteration))
        return root + self.suffix(style) + self._bass_text(key)

    def suffix(self, style: str = "plain") -> str:
        jazz = style == "jazz"
        base = _SUFFIX.get((self.triad, self.seventh))
        if base is None:
            base = _SUFFIX[(self.triad, None)]
        text = base[1] if jazz else base[0]

        if self.extensions:
            top = max(self.extensions, key=int)
            if self.seventh in ("7", "maj7"):
                # The highest extension replaces the 7: C7 -> C13, Cmaj7 -> Cmaj9, Cm7 -> Cm11
                text = text.replace("7", top, 1)
            elif self.seventh == "6" and "9" in self.extensions:
                text = text + "/9"
            else:
                text = text + f"add{top}"

        if self.alterations:
            text += "(" + ",".join(self.alterations) + ")"
        return text

    def _bass_text(self, key: Key) -> str:
        if self.bass is None:
            return ""
        return "/" + str(key.note(*self.bass))

    def roman(self) -> str:
        text = self.label or roman_numeral(self.degree, self.alteration, self.triad, self.seventh)
        if self.bass is not None:
            text += "/" + roman_numeral(self.bass[0], self.bass[1], "maj")
        return text


def roman_numeral(degree: int, alteration: int, triad: str, seventh: str | None = None) -> str:
    prefix = "b" * -alteration if alteration < 0 else "#" * alteration
    numeral = ROMAN[degree - 1]
    if triad in ("min", "dim"):
        numeral = numeral.lower()
    suffix = {"dim": "°", "aug": "+", "sus2": "sus2", "sus4": "sus4", "5": "5", "quartal": "q"}.get(
        triad, ""
    )
    if seventh == "7" and triad == "dim":
        suffix = "ø7"
    elif seventh:
        suffix += {"7": "7", "maj7": "maj7", "dim7": "7", "6": "6"}[seventh]
    return prefix + numeral + suffix


def degree_for(rel_root: int, letter_degree: int) -> tuple[int, int]:
    """(degree, alteration) for a tonic-relative root spelled on a given letter degree."""
    letter_degree = (letter_degree - 1) % 7 + 1
    return letter_degree, wrap_signed(rel_root - MAJOR_STEPS[letter_degree - 1])


def stacked_chord(scale_intervals: tuple[int, ...], step: int) -> tuple[str, tuple[int, ...]]:
    """Triad quality and colour scale built by stacking thirds on a 1-based scale step."""
    i = step - 1
    root = scale_intervals[i]
    third = scale_intervals[(i + 2) % 7] - root
    fifth = scale_intervals[(i + 4) % 7] - root
    color = tuple(sorted((x - root) % 12 for x in scale_intervals))
    return triad_from_tones(third, fifth), color
