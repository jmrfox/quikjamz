from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from typing import List, Dict

from .measure_generator import MeasureSuggestion
from .instrument_suggestions import InstrumentSuggestion, InstrumentType
from .music_theory import TimeSignature


class JamGuideDocument:
    def __init__(
        self,
        filename: str,
        title: str,
        tempo: int,
        time_signature: TimeSignature,
        key_info: str,
    ):
        self.filename = filename
        self.title = title
        self.tempo = tempo
        self.time_signature = time_signature
        self.key_info = key_info
        self.c = canvas.Canvas(filename, pagesize=letter)
        self.width, self.height = letter
        self.current_y = self.height - inch
        self.margin = 0.75 * inch
        self.measures_per_line = 4

    def add_header(self):
        self.c.setFont("Helvetica-Bold", 20)
        self.c.drawString(self.margin, self.current_y, self.title)
        self.current_y -= 0.4 * inch

        self.c.setFont("Helvetica", 12)
        info_text = f"Tempo: {self.tempo} BPM  |  Time: {self.time_signature}  |  Key: {self.key_info}"
        self.c.drawString(self.margin, self.current_y, info_text)
        self.current_y -= 0.5 * inch

        self.c.line(
            self.margin, self.current_y, self.width - self.margin, self.current_y
        )
        self.current_y -= 0.3 * inch

    def add_measure_block(
        self,
        measures: List[MeasureSuggestion],
        instrument_suggestions: Dict[InstrumentType, List[InstrumentSuggestion]],
    ):
        for i in range(0, len(measures), self.measures_per_line):
            measure_group = measures[i : i + self.measures_per_line]
            self._draw_measure_line(measure_group, instrument_suggestions)

            if self.current_y < 2 * inch:
                self.c.showPage()
                self.current_y = self.height - inch

    def _draw_measure_line(
        self,
        measures: List[MeasureSuggestion],
        instrument_suggestions: Dict[InstrumentType, List[InstrumentSuggestion]],
    ):
        measure_width = (self.width - 2 * self.margin) / self.measures_per_line
        start_y = self.current_y

        self.c.setFont("Helvetica-Bold", 10)
        for idx, measure in enumerate(measures):
            x_pos = self.margin + idx * measure_width

            self.c.rect(x_pos, start_y - 0.3 * inch, measure_width - 5, 0.3 * inch)

            self.c.drawString(
                x_pos + 5, start_y - 0.2 * inch, f"M{measure.measure_number}"
            )

        self.current_y = start_y - 0.4 * inch

        self.c.setFont("Helvetica-Bold", 9)
        self.c.drawString(self.margin, self.current_y, "General:")
        self.current_y -= 0.15 * inch

        self.c.setFont("Helvetica", 8)
        for idx, measure in enumerate(measures):
            x_pos = self.margin + idx * measure_width

            y_offset = self.current_y
            chord_text = str(measure.chord) if measure.chord else "Free"
            self.c.drawString(x_pos + 5, y_offset, chord_text)
            y_offset -= 0.12 * inch

            self.c.drawString(x_pos + 5, y_offset, str(measure.dynamics))
            y_offset -= 0.12 * inch

            rhythm_text = measure.rhythm_density.value[:8]
            self.c.drawString(x_pos + 5, y_offset, rhythm_text)

        self.current_y -= 0.3 * inch

        for instrument_type, suggestions in instrument_suggestions.items():
            relevant_suggestions = [
                s
                for s in suggestions
                if s.measure_number in [m.measure_number for m in measures]
            ]

            if relevant_suggestions:
                self._draw_instrument_line(
                    instrument_type, relevant_suggestions, measures, measure_width
                )

        self.current_y -= 0.2 * inch

    def _draw_instrument_line(
        self,
        instrument: InstrumentType,
        suggestions: List[InstrumentSuggestion],
        measures: List[MeasureSuggestion],
        measure_width: float,
    ):
        self.c.setFont("Helvetica-Bold", 9)
        self.c.drawString(self.margin, self.current_y, f"{instrument.value.upper()}:")
        self.current_y -= 0.15 * inch

        self.c.setFont("Helvetica", 7)

        measure_map = {s.measure_number: s for s in suggestions}

        for idx, measure in enumerate(measures):
            if measure.measure_number in measure_map:
                suggestion = measure_map[measure.measure_number]
                x_pos = self.margin + idx * measure_width
                y_offset = self.current_y

                tech_text = self._truncate_text(suggestion.technique, 20)
                self.c.drawString(x_pos + 5, y_offset, tech_text)
                y_offset -= 0.1 * inch

                rhythm_text = self._truncate_text(suggestion.rhythm_guidance, 20)
                self.c.drawString(x_pos + 5, y_offset, rhythm_text)

        self.current_y -= 0.25 * inch

    def _truncate_text(self, text: str, max_length: int) -> str:
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    def add_section_header(self, section_name: str):
        if self.current_y < 1.5 * inch:
            self.c.showPage()
            self.current_y = self.height - inch

        self.c.setFont("Helvetica-Bold", 14)
        self.c.drawString(self.margin, self.current_y, section_name)
        self.current_y -= 0.3 * inch

        self.c.line(
            self.margin, self.current_y, self.width - self.margin, self.current_y
        )
        self.current_y -= 0.2 * inch

    def add_vibe_notes(self, measures: List[MeasureSuggestion]):
        self.c.setFont("Helvetica-Bold", 10)
        self.c.drawString(self.margin, self.current_y, "Vibe Notes:")
        self.current_y -= 0.2 * inch

        self.c.setFont("Helvetica", 8)
        for measure in measures:
            if self.current_y < inch:
                self.c.showPage()
                self.current_y = self.height - inch

            text = f"M{measure.measure_number}: {measure.vibe_description} - {measure.emphasis}"
            self.c.drawString(self.margin + 0.2 * inch, self.current_y, text)
            self.current_y -= 0.15 * inch

        self.current_y -= 0.2 * inch

    def save(self):
        self.c.save()
        print(f"Jam guide saved to: {self.filename}")
