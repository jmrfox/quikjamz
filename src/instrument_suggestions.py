from dataclasses import dataclass
from typing import List
from enum import Enum

from .measure_generator import MeasureSuggestion
from .latent_state import LatentState
from .music_theory import RhythmDensity


class InstrumentType(Enum):
    DRUMS = "drums"
    BASS = "bass"
    GUITAR = "guitar"
    KEYS = "keys"
    SYNTH = "synth"
    VOCALS = "vocals"


@dataclass
class InstrumentSuggestion:
    instrument: InstrumentType
    measure_number: int
    technique: str
    notes_guidance: str
    rhythm_guidance: str

    def __str__(self):
        return f"{self.instrument.value.upper()}: {self.technique} | {self.notes_guidance} | {self.rhythm_guidance}"


class InstrumentSuggestionGenerator:
    @staticmethod
    def generate_for_instrument(
        instrument: InstrumentType,
        measure_suggestion: MeasureSuggestion,
        latent: LatentState,
    ) -> InstrumentSuggestion:
        if instrument == InstrumentType.DRUMS:
            return InstrumentSuggestionGenerator._generate_drums(
                measure_suggestion, latent
            )
        elif instrument == InstrumentType.BASS:
            return InstrumentSuggestionGenerator._generate_bass(
                measure_suggestion, latent
            )
        elif instrument == InstrumentType.GUITAR:
            return InstrumentSuggestionGenerator._generate_guitar(
                measure_suggestion, latent
            )
        elif instrument == InstrumentType.KEYS:
            return InstrumentSuggestionGenerator._generate_keys(
                measure_suggestion, latent
            )
        elif instrument == InstrumentType.SYNTH:
            return InstrumentSuggestionGenerator._generate_synth(
                measure_suggestion, latent
            )
        elif instrument == InstrumentType.VOCALS:
            return InstrumentSuggestionGenerator._generate_vocals(
                measure_suggestion, latent
            )
        else:
            raise ValueError(f"Unknown instrument: {instrument}")

    @staticmethod
    def _generate_drums(
        measure: MeasureSuggestion, latent: LatentState
    ) -> InstrumentSuggestion:
        if latent.energy > 0.7:
            technique = "Aggressive, accented hits"
        elif latent.energy < 0.3:
            technique = "Soft, brushes or light sticks"
        else:
            technique = "Standard groove"

        if measure.rhythm_density == RhythmDensity.SPARSE:
            rhythm = "Simple kick/snare pattern, minimal fills"
        elif measure.rhythm_density == RhythmDensity.MODERATE:
            rhythm = "Standard beat with hi-hat variations"
        elif measure.rhythm_density == RhythmDensity.DENSE:
            rhythm = "Complex patterns, ghost notes, syncopation"
        else:
            rhythm = "Busy fills, double bass, rapid hi-hat"

        if latent.tension > 0.7:
            notes = "Build tension with cymbal swells or tom rolls"
        else:
            notes = "Maintain steady groove"

        return InstrumentSuggestion(
            instrument=InstrumentType.DRUMS,
            measure_number=measure.measure_number,
            technique=technique,
            notes_guidance=notes,
            rhythm_guidance=rhythm,
        )

    @staticmethod
    def _generate_bass(
        measure: MeasureSuggestion, latent: LatentState
    ) -> InstrumentSuggestion:
        if latent.energy > 0.7:
            technique = "Aggressive attack, pick or slap"
        elif latent.energy < 0.3:
            technique = "Gentle fingerstyle"
        else:
            technique = "Standard fingerstyle or pick"

        if measure.chord:
            notes = f"Root: {measure.chord.root}, emphasize chord tones of {measure.chord.quality.value}"
        else:
            notes = f"Follow {measure.scale} scale, root on {measure.scale.root}"

        if measure.rhythm_density == RhythmDensity.SPARSE:
            rhythm = "Whole notes or half notes, sustained"
        elif measure.rhythm_density == RhythmDensity.MODERATE:
            rhythm = "Quarter note walking or steady groove"
        elif measure.rhythm_density == RhythmDensity.DENSE:
            rhythm = "Eighth note runs, syncopated patterns"
        else:
            rhythm = "Sixteenth note fills, complex rhythms"

        return InstrumentSuggestion(
            instrument=InstrumentType.BASS,
            measure_number=measure.measure_number,
            technique=technique,
            notes_guidance=notes,
            rhythm_guidance=rhythm,
        )

    @staticmethod
    def _generate_guitar(
        measure: MeasureSuggestion, latent: LatentState
    ) -> InstrumentSuggestion:
        if latent.energy > 0.7:
            technique = "Distorted, power chords or aggressive strumming"
        elif latent.energy < 0.3:
            technique = "Clean tone, fingerpicking or soft strums"
        else:
            technique = "Clean/light overdrive, standard strumming"

        if measure.chord:
            notes = f"Play {measure.chord} or arpeggiate, use {measure.scale} for fills"
        else:
            notes = f"Improvise in {measure.scale}"

        if measure.rhythm_density == RhythmDensity.SPARSE:
            rhythm = "Whole chords, let ring, minimal strumming"
        elif measure.rhythm_density == RhythmDensity.MODERATE:
            rhythm = "Standard strumming pattern or picking"
        elif measure.rhythm_density == RhythmDensity.DENSE:
            rhythm = "Fast strumming, palm muting, or rapid arpeggios"
        else:
            rhythm = "Shredding, tremolo picking, complex patterns"

        return InstrumentSuggestion(
            instrument=InstrumentType.GUITAR,
            measure_number=measure.measure_number,
            technique=technique,
            notes_guidance=notes,
            rhythm_guidance=rhythm,
        )

    @staticmethod
    def _generate_keys(
        measure: MeasureSuggestion, latent: LatentState
    ) -> InstrumentSuggestion:
        if latent.brightness > 0.7:
            technique = "Bright voicings, upper register"
        elif latent.brightness < 0.3:
            technique = "Dark voicings, lower register"
        else:
            technique = "Balanced voicings, mid register"

        if measure.chord:
            notes = f"Voice {measure.chord} with extensions, comp or solo in {measure.scale}"
        else:
            notes = f"Improvise in {measure.scale}, explore chord voicings"

        if measure.rhythm_density == RhythmDensity.SPARSE:
            rhythm = "Sustained chords, pads, minimal movement"
        elif measure.rhythm_density == RhythmDensity.MODERATE:
            rhythm = "Comping rhythm, standard voicings"
        elif measure.rhythm_density == RhythmDensity.DENSE:
            rhythm = "Active comping, runs, arpeggios"
        else:
            rhythm = "Fast runs, complex rhythms, fills"

        return InstrumentSuggestion(
            instrument=InstrumentType.KEYS,
            measure_number=measure.measure_number,
            technique=technique,
            notes_guidance=notes,
            rhythm_guidance=rhythm,
        )

    @staticmethod
    def _generate_synth(
        measure: MeasureSuggestion, latent: LatentState
    ) -> InstrumentSuggestion:
        if latent.brightness > 0.7:
            technique = "Bright, sharp waveforms (saw, square)"
        elif latent.brightness < 0.3:
            technique = "Dark, warm waveforms (sine, triangle)"
        else:
            technique = "Balanced timbres"

        if latent.tension > 0.7:
            notes = f"Dissonant intervals, filter sweeps, tension in {measure.scale}"
        elif measure.chord:
            notes = f"Pad or lead on {measure.chord}, use {measure.scale} for melody"
        else:
            notes = f"Ambient textures or leads in {measure.scale}"

        if measure.rhythm_density == RhythmDensity.SPARSE:
            rhythm = "Long pads, atmospheric swells"
        elif measure.rhythm_density == RhythmDensity.MODERATE:
            rhythm = "Arpeggiated patterns or pulsing rhythm"
        elif measure.rhythm_density == RhythmDensity.DENSE:
            rhythm = "Fast arpeggios, sequenced patterns"
        else:
            rhythm = "Rapid sequences, glitchy rhythms"

        return InstrumentSuggestion(
            instrument=InstrumentType.SYNTH,
            measure_number=measure.measure_number,
            technique=technique,
            notes_guidance=notes,
            rhythm_guidance=rhythm,
        )

    @staticmethod
    def _generate_vocals(
        measure: MeasureSuggestion, latent: LatentState
    ) -> InstrumentSuggestion:
        if latent.energy > 0.7:
            technique = "Powerful, belting, high energy"
        elif latent.energy < 0.3:
            technique = "Soft, breathy, intimate"
        else:
            technique = "Moderate projection, conversational"

        notes = (
            f"Melodic phrases in {measure.scale}, target chord tones if {measure.chord}"
        )

        if measure.rhythm_density == RhythmDensity.SPARSE:
            rhythm = "Long sustained notes, minimal phrasing"
        elif measure.rhythm_density == RhythmDensity.MODERATE:
            rhythm = "Standard phrasing, natural speech rhythm"
        elif measure.rhythm_density == RhythmDensity.DENSE:
            rhythm = "Rapid delivery, melismatic runs"
        else:
            rhythm = "Very fast phrasing, rap-style or scat"

        return InstrumentSuggestion(
            instrument=InstrumentType.VOCALS,
            measure_number=measure.measure_number,
            technique=technique,
            notes_guidance=notes,
            rhythm_guidance=rhythm,
        )
