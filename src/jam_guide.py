from typing import List, Optional
from dataclasses import dataclass

from .music_theory import Note, ScaleType, TimeSignature, Mood
from .latent_state import LatentState, LatentStateGenerator
from .measure_generator import MeasureGenerator, MeasureSuggestion
from .instrument_suggestions import (
    InstrumentType,
    InstrumentSuggestionGenerator,
    InstrumentSuggestion,
)
from .document_generator import JamGuideDocument


@dataclass
class JamGuideConfig:
    title: str
    tempo: int
    time_signature: TimeSignature
    key: Note
    scale_type: ScaleType
    mood: Mood
    total_measures: int
    instruments: List[InstrumentType]
    chord_complexity: float = 0.5
    progression_complexity: float = 0.5
    initial_energy: float = 0.5
    initial_tension: float = 0.5
    initial_brightness: float = 0.5
    drift: float = 0.05
    volatility: float = 0.15
    output_filename: str = "jam_guide.pdf"


class JamGuide:
    def __init__(self, config: JamGuideConfig):
        self.config = config
        self.measure_generator = MeasureGenerator(
            config.key, config.scale_type, config.mood
        )

        initial_state = LatentState.from_params(
            energy=config.initial_energy,
            tension=config.initial_tension,
            brightness=config.initial_brightness,
            complexity=config.chord_complexity,
            density=config.progression_complexity,
        )

        self.latent_generator = LatentStateGenerator(
            initial_state=initial_state,
            drift=config.drift,
            volatility=config.volatility,
        )

        self.measures: List[MeasureSuggestion] = []
        self.instrument_suggestions: dict[
            InstrumentType, List[InstrumentSuggestion]
        ] = {inst: [] for inst in config.instruments}

    def generate(self):
        latent_states = self.latent_generator.generate_sequence(
            self.config.total_measures
        )

        for i, latent in enumerate(latent_states):
            measure_num = i + 1
            measure = self.measure_generator.generate_from_latent(
                latent, measure_num, self.config.chord_complexity
            )
            self.measures.append(measure)

            for instrument in self.config.instruments:
                suggestion = InstrumentSuggestionGenerator.generate_for_instrument(
                    instrument, measure, latent
                )
                self.instrument_suggestions[instrument].append(suggestion)

    def export_to_pdf(self, filename: Optional[str] = None):
        if not self.measures:
            raise ValueError("No measures generated. Call generate() first.")

        output_file = filename or self.config.output_filename

        doc = JamGuideDocument(
            filename=output_file,
            title=self.config.title,
            tempo=self.config.tempo,
            time_signature=self.config.time_signature,
            key_info=f"{self.config.key} {self.config.scale_type.value}",
        )

        doc.add_header()

        doc.add_section_header("Jam Guide")
        doc.add_measure_block(self.measures, self.instrument_suggestions)

        doc.add_section_header("Detailed Vibe Notes")
        doc.add_vibe_notes(self.measures)

        doc.save()

        return output_file

    def print_summary(self):
        print(f"\n{'='*60}")
        print(f"JAM GUIDE: {self.config.title}")
        print(f"{'='*60}")
        print(f"Tempo: {self.config.tempo} BPM")
        print(f"Time Signature: {self.config.time_signature}")
        print(f"Key: {self.config.key} {self.config.scale_type.value}")
        print(f"Mood: {self.config.mood.value}")
        print(f"Total Measures: {self.config.total_measures}")
        print(f"Instruments: {', '.join([i.value for i in self.config.instruments])}")
        print(f"{'='*60}\n")

        for measure in self.measures[:10]:
            print(f"\n--- Measure {measure.measure_number} ---")
            print(f"Chord: {measure.chord}")
            print(f"Dynamics: {measure.dynamics}")
            print(f"Rhythm Density: {measure.rhythm_density.value}")
            print(f"Vibe: {measure.vibe_description}")
            print(f"Emphasis: {measure.emphasis}")

            for instrument in self.config.instruments:
                suggestions = [
                    s
                    for s in self.instrument_suggestions[instrument]
                    if s.measure_number == measure.measure_number
                ]
                if suggestions:
                    print(f"  {suggestions[0]}")

        if len(self.measures) > 10:
            print(f"\n... ({len(self.measures) - 10} more measures)")
