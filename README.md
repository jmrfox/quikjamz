# QuikJamz 🎵

**QuikJamz** is a procedural music jam guide generator that creates structured improvisation guides for multi-instrument jam sessions. Instead of traditional sheet music with specific notes, QuikJamz generates dynamic suggestions for vibe, rhythm, chords, dynamics, and playing style based on a latent variable system.

## Features

- **Latent Variable System**: Uses a 5-dimensional latent state (energy, tension, complexity, brightness, density) that evolves over time to generate coherent musical suggestions
- **Multi-Instrument Support**: Generates specific guidance for drums, bass, guitar, keys, synth, and vocals
- **Music Theory Foundation**: Built on proper music theory with support for various scales, chord qualities, and progressions
- **PDF Export**: Creates professional-looking jam guide documents similar to lead sheets
- **Highly Configurable**: Control tempo, time signature, key, mood, complexity, and progression characteristics

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from src.jam_guide import JamGuide, JamGuideConfig
from src.music_theory import Note, ScaleType, TimeSignature, Mood
from src.instrument_suggestions import InstrumentType

config = JamGuideConfig(
    title="My Jam Session",
    tempo=120,
    time_signature=TimeSignature(4, 4),
    key=Note.C,
    scale_type=ScaleType.MINOR,
    mood=Mood.ENERGETIC,
    total_measures=32,
    instruments=[
        InstrumentType.DRUMS,
        InstrumentType.BASS,
        InstrumentType.GUITAR
    ],
    chord_complexity=0.5,
    progression_complexity=0.5,
    output_filename="my_jam.pdf"
)

guide = JamGuide(config)
guide.generate()
guide.export_to_pdf()
```

## Running the Example

```bash
python example.py
```

This will generate a 32-measure funky jazz jam guide with drums, bass, guitar, and keys.

## How It Works

### Latent State System

QuikJamz uses a latent variable approach where each measure is generated from a 5-dimensional state vector:

- **Energy** (0-1): Controls dynamics and playing intensity
- **Tension** (0-1): Influences chord selection and harmonic tension
- **Complexity** (0-1): Determines chord voicing complexity (power chords → extended chords)
- **Brightness** (0-1): Affects timbre, register, and major/minor tendencies
- **Density** (0-1): Controls rhythm density and note activity

The latent state evolves measure-by-measure using a random walk with configurable drift and volatility, creating natural musical progression and variation.

### Measure Generation

For each measure, the system:

1. Generates/evolves the latent state
2. Derives musical attributes from the latent dimensions:
   - Chord suggestions based on complexity, tension, and brightness
   - Dynamics from energy levels
   - Rhythm density from the density parameter
   - Vibe descriptions from combined latent factors
3. Creates instrument-specific suggestions for each active instrument

### Instrument Suggestions

Each instrument receives tailored guidance:

- **Drums**: Groove patterns, fill density, technique (brushes, sticks, aggression)
- **Bass**: Note choices (root, chord tones), rhythm patterns, playing style
- **Guitar**: Chord voicings, strumming patterns, tone suggestions
- **Keys**: Voicing choices, register, comping vs. soloing
- **Synth**: Waveform/timbre, filter settings, rhythmic patterns
- **Vocals**: Delivery style, phrasing density, melodic guidance

## Configuration Options

### JamGuideConfig Parameters

- `title`: Name of your jam session
- `tempo`: BPM (beats per minute)
- `time_signature`: TimeSignature object (e.g., 4/4, 3/4, 7/8)
- `key`: Root note (Note.C, Note.D_SHARP, etc.)
- `scale_type`: ScaleType enum (MAJOR, MINOR, DORIAN, BLUES, etc.)
- `mood`: Overall mood (ENERGETIC, CALM, DARK, etc.)
- `total_measures`: Number of measures to generate
- `instruments`: List of InstrumentType enums
- `chord_complexity`: 0-1, preference for simple vs. complex chords
- `progression_complexity`: 0-1, affects density parameter initialization
- `initial_energy`: Starting energy level (0-1)
- `initial_tension`: Starting tension level (0-1)
- `initial_brightness`: Starting brightness level (0-1)
- `drift`: How much the latent state drifts per measure (default: 0.05)
- `volatility`: Random variation in latent state evolution (default: 0.15)
- `output_filename`: PDF output path

## Project Structure

```
quikjamz/
├── src/
│   ├── __init__.py
│   ├── music_theory.py          # Core music theory classes
│   ├── latent_state.py          # Latent variable system
│   ├── measure_generator.py     # Measure-level suggestion generation
│   ├── instrument_suggestions.py # Instrument-specific logic
│   ├── document_generator.py    # PDF generation
│   └── jam_guide.py            # Main orchestration class
├── example.py                   # Example usage
├── requirements.txt
└── README.md
```

## Future Enhancements

- Interactive web UI for configuration
- MIDI export for reference playback
- More sophisticated chord progression algorithms
- Style templates (jazz, rock, funk, etc.)
- Section structure (intro, verse, chorus, bridge)
- Real-time generation for live jamming
- Integration with DAWs

## License

MIT License - feel free to use and modify for your jam sessions!

---

**Happy Jamming! 🎸🥁🎹**
