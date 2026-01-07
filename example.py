from src.jam_guide import JamGuide, JamGuideConfig
from src.music_theory import Note, ScaleType, TimeSignature, Mood
from src.instrument_suggestions import InstrumentType


def main():
    config = JamGuideConfig(
        title="Funky Jazz Jam Session",
        tempo=110,
        time_signature=TimeSignature(4, 4),
        key=Note.C,
        scale_type=ScaleType.DORIAN,
        mood=Mood.ENERGETIC,
        total_measures=32,
        instruments=[
            InstrumentType.DRUMS,
            InstrumentType.BASS,
            InstrumentType.GUITAR,
            InstrumentType.KEYS,
        ],
        chord_complexity=0.6,
        progression_complexity=0.5,
        initial_energy=0.6,
        initial_tension=0.4,
        initial_brightness=0.7,
        drift=0.08,
        volatility=0.2,
        output_filename="funky_jazz_jam.pdf",
    )

    guide = JamGuide(config)

    print("Generating jam guide...")
    guide.generate()

    guide.print_summary()

    print("\nExporting to PDF...")
    output_file = guide.export_to_pdf()
    print(f"✓ PDF generated: {output_file}")


if __name__ == "__main__":
    main()
