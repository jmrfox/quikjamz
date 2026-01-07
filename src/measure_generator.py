import numpy as np
from typing import List, Optional
from dataclasses import dataclass

from .music_theory import (
    Chord,
    ChordQuality,
    Note,
    Scale,
    ScaleType,
    Dynamics,
    RhythmDensity,
    Mood,
)
from .latent_state import LatentState


@dataclass
class MeasureSuggestion:
    measure_number: int
    chord: Optional[Chord]
    scale: Scale
    dynamics: Dynamics
    rhythm_density: RhythmDensity
    vibe_description: str
    emphasis: str

    def __str__(self):
        parts = [
            f"M{self.measure_number}",
            f"Chord: {self.chord}" if self.chord else "No specific chord",
            f"Scale: {self.scale}",
            f"Dynamics: {self.dynamics}",
            f"Rhythm: {self.rhythm_density.value}",
            f"Vibe: {self.vibe_description}",
            f"Emphasis: {self.emphasis}",
        ]
        return " | ".join(parts)


class MeasureGenerator:
    def __init__(self, root_key: Note, scale_type: ScaleType, mood: Mood):
        self.root_key = root_key
        self.scale_type = scale_type
        self.mood = mood
        self.base_scale = Scale(root_key, scale_type)

    def generate_from_latent(
        self,
        latent: LatentState,
        measure_number: int,
        chord_complexity_pref: float = 0.5,
    ) -> MeasureSuggestion:
        chord = self._derive_chord(latent, chord_complexity_pref)
        dynamics = self._derive_dynamics(latent)
        rhythm_density = self._derive_rhythm_density(latent)
        vibe = self._derive_vibe(latent)
        emphasis = self._derive_emphasis(latent)

        return MeasureSuggestion(
            measure_number=measure_number,
            chord=chord,
            scale=self.base_scale,
            dynamics=dynamics,
            rhythm_density=rhythm_density,
            vibe_description=vibe,
            emphasis=emphasis,
        )

    def _derive_chord(
        self, latent: LatentState, complexity_pref: float
    ) -> Optional[Chord]:
        scale_notes = self.base_scale.get_notes()

        complexity_score = (latent.complexity + complexity_pref) / 2

        if complexity_score < 0.2:
            quality = ChordQuality.POWER
        elif complexity_score < 0.35:
            if latent.brightness > 0.5:
                quality = ChordQuality.MAJOR
            else:
                quality = ChordQuality.MINOR
        elif complexity_score < 0.5:
            if latent.brightness > 0.5:
                quality = (
                    ChordQuality.SUS2 if np.random.random() > 0.5 else ChordQuality.SUS4
                )
            else:
                quality = ChordQuality.MINOR
        elif complexity_score < 0.65:
            if latent.brightness > 0.6:
                quality = ChordQuality.MAJOR_7
            elif latent.tension > 0.6:
                quality = ChordQuality.DOMINANT_7
            else:
                quality = ChordQuality.MINOR_7
        elif complexity_score < 0.8:
            if latent.brightness > 0.6:
                quality = ChordQuality.MAJOR_9
            elif latent.tension > 0.6:
                quality = ChordQuality.DOMINANT_9
            else:
                quality = ChordQuality.MINOR_9
        else:
            if latent.brightness > 0.6:
                quality = ChordQuality.MAJOR_13
            elif latent.tension > 0.6:
                quality = ChordQuality.AUGMENTED
            else:
                quality = ChordQuality.MINOR_13

        root_idx = int(latent.tension * len(scale_notes))
        root = scale_notes[root_idx % len(scale_notes)]

        return Chord(root, quality)

    def _derive_dynamics(self, latent: LatentState) -> Dynamics:
        energy = latent.energy

        if energy < 0.15:
            return Dynamics.PIANISSIMO
        elif energy < 0.35:
            return Dynamics.PIANO
        elif energy < 0.5:
            return Dynamics.MEZZO_PIANO
        elif energy < 0.65:
            return Dynamics.MEZZO_FORTE
        elif energy < 0.85:
            return Dynamics.FORTE
        else:
            return Dynamics.FORTISSIMO

    def _derive_rhythm_density(self, latent: LatentState) -> RhythmDensity:
        density = latent.density

        if density < 0.25:
            return RhythmDensity.SPARSE
        elif density < 0.5:
            return RhythmDensity.MODERATE
        elif density < 0.75:
            return RhythmDensity.DENSE
        else:
            return RhythmDensity.VERY_DENSE

    def _derive_vibe(self, latent: LatentState) -> str:
        vibes = []

        if latent.energy > 0.7:
            vibes.append("driving")
        elif latent.energy < 0.3:
            vibes.append("laid-back")

        if latent.tension > 0.7:
            vibes.append("tense")
        elif latent.tension < 0.3:
            vibes.append("resolved")

        if latent.brightness > 0.7:
            vibes.append("bright")
        elif latent.brightness < 0.3:
            vibes.append("dark")

        if latent.complexity > 0.7:
            vibes.append("intricate")
        elif latent.complexity < 0.3:
            vibes.append("simple")

        if not vibes:
            vibes.append("balanced")

        return ", ".join(vibes)

    def _derive_emphasis(self, latent: LatentState) -> str:
        if latent.density > 0.7:
            return "Fill space, active playing"
        elif latent.density < 0.3:
            return "Leave space, minimal notes"
        else:
            return "Moderate activity"
