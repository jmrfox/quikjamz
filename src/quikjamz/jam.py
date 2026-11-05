"""Putting it together: config -> knobs -> form -> per-section knobs -> harmony -> cues -> Jam.

The Jam is the single source of truth (spec section 7). Renderers (text, MIDI,
later the Typst sheet) only read it.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .form import Cue, Slot, choose_form, make_cue, make_labels, make_start_cue
from .harmony.modulation import maybe_modulate
from .harmony.progression import Loop, generate_loop, reend_loop, vary_loop
from .prompts import pick_idea, pick_prompts
from .knobs import DEFAULT_ARC, Arc, Knobs, resolve_knobs, section_knobs, vibe_words
from .theory.meter import Meter, changes_meter_between_sections, choose_meter
from .theory.scales import Key, choose_mode, get_scale, make_key
from .theory.pitch import SpelledNote


@dataclass
class JamConfig:
    title: str = "Untitled Jam"
    seed: int | None = None
    mood: str | None = None
    knobs: dict[str, float] = field(default_factory=dict)  # overrides on top of the mood
    arc: str = DEFAULT_ARC
    key: str | None = None  # tonic, e.g. "D" or "Eb"
    mode: str | None = None
    tempo: int | None = None  # quarter-note BPM
    meter: str | None = None  # e.g. "4/4", "7/8"
    sections: int | None = None
    form: str | None = None  # through, return, ring, mirror, strophic, drift
    labels: str = "letters"


@dataclass
class Section:
    index: int
    label: str
    slot: Slot
    knobs: Knobs
    key: Key
    meter: Meter
    loop: Loop
    cue: Cue
    start_cue: str | None = None
    key_change: str | None = None  # how the key moved into this section, if it did
    start_bar: int = 1  # bar number where the section starts (counting each loop pass once)
    prompts: list[str] = field(default_factory=list)
    idea: dict | None = None  # {"type": "rhythm" | "melody", "text": ...}

    @property
    def vibe(self) -> list[str]:
        return vibe_words(self.knobs)

    @property
    def return_of(self) -> int | None:
        return self.slot.source if self.slot.kind == "return" else None

    @property
    def drift_of(self) -> int | None:
        return self.slot.source if self.slot.kind == "drift" else None


@dataclass
class Jam:
    title: str
    seed: int
    mood: str
    arc: str
    form: str
    label_style: str
    tempo: int  # quarter-note BPM
    meter: Meter
    home_key: Key
    knobs: Knobs
    sections: list[Section]

    def to_dict(self, style: str = "plain") -> dict:
        def chord_dict(chord, key, beats=None):
            d = {
                "symbol": chord.symbol(key, style),
                "roman": chord.roman(),
                "fn": chord.fn,
                "tier": chord.tier,
                "source": chord.source,
            }
            if beats is not None:
                d["beats"] = beats
            return d

        return {
            "title": self.title,
            "seed": self.seed,
            "mood": self.mood,
            "arc": self.arc,
            "form": self.form,
            "tempo": self.tempo,
            "meter": str(self.meter),
            "home_key": {"tonic": str(self.home_key.tonic), "mode": self.home_key.scale.name},
            "knobs": self.knobs.as_dict(),
            "sections": [
                {
                    "label": s.label,
                    "label_style": self.label_style,
                    "kind": s.slot.kind,
                    "return_of": s.return_of,
                    "drift_of": s.drift_of,
                    "start_bar": s.start_bar,
                    "key": {"tonic": str(s.key.tonic), "mode": s.key.scale.name},
                    "key_change": s.key_change,
                    "meter": str(s.meter),
                    "knobs": s.knobs.as_dict(),
                    "vibe": s.vibe,
                    "loop": {
                        "bars": s.loop.bars,
                        "chords": [chord_dict(e.chord, s.key, e.beats) for e in s.loop.events],
                        "ending": s.loop.ending,
                        "final": chord_dict(s.loop.final, s.key),
                    },
                    "cue": s.cue.to_dict(),
                    "start_cue": s.start_cue,
                    "prompts": s.prompts,
                    "idea": s.idea,
                }
                for s in self.sections
            ],
        }


def _tempo_from_energy(energy: float, rng: random.Random) -> int:
    bpm = 68 + energy * (152 - 68) + rng.gauss(0, 6)
    return int(round(max(50, min(200, bpm)) / 2) * 2)


def _home_key(config: JamConfig, knobs: Knobs, rng: random.Random) -> Key:
    scale = get_scale(config.mode) if config.mode else choose_mode(knobs.brightness, rng)
    if config.key:
        return make_key(SpelledNote.parse(config.key), scale)
    return make_key(rng.randrange(12), scale)


def generate_jam(config: JamConfig) -> Jam:
    seed = config.seed if config.seed is not None else random.randrange(10**6)
    rng = random.Random(seed)

    mood, knobs = resolve_knobs(config.mood, config.knobs, rng)
    arc = Arc(config.arc, rng)
    home_key = _home_key(config, knobs, rng)
    meter = Meter.parse(config.meter) if config.meter else choose_meter(knobs.rhythm_adv, rng)
    tempo = config.tempo or _tempo_from_energy(knobs.energy, rng)
    if not config.tempo and meter.unit == 8:
        tempo = int(round(tempo * 0.75 / 2) * 2)  # eighth-note meters: keep the counted pulse sane

    n = config.sections or rng.randint(4, 6)
    form_name, slots = choose_form(n, knobs.stability, rng, config.form)
    positions = [i / (n - 1) if n > 1 else 0.5 for i in range(n)]
    per_section = [section_knobs(knobs, arc, t, rng) for t in positions]
    labels = make_labels(slots, per_section, config.labels, rng)

    sections: list[Section] = []
    key, sec_meter = home_key, meter
    bar = 1
    used_prompts: set[str] = set()
    for i, (slot, sk) in enumerate(zip(slots, per_section)):
        key_change = None
        is_last = i == n - 1
        if slot.kind == "return":
            src = sections[slot.source]
            key, sec_meter = src.key, src.meter
            loop = reend_loop(src.loop, sk.tension, rng)
        elif slot.kind == "drift":
            src = sections[slot.source]
            key, sec_meter = src.key, src.meter
            loop = vary_loop(
                src.loop, rng, harm_adv=sk.harm_adv, complexity=sk.complexity,
                tension=sk.tension, brightness=sk.brightness,
            )
        else:
            if i > 0:
                key, key_change = maybe_modulate(key, sk.harm_adv, rng)
                if not config.meter and changes_meter_between_sections(sk.rhythm_adv, rng):
                    sec_meter = choose_meter(sk.rhythm_adv, rng)
            loop = generate_loop(
                key, rng, harm_adv=sk.harm_adv, complexity=sk.complexity, tension=sk.tension,
                brightness=sk.brightness, meter=sec_meter, rhythm_adv=sk.rhythm_adv,
            )
        cue = make_cue(sk, loop.bars, is_last, loop.ending, rng)
        start_cue = make_start_cue(sk, rng) if i == 0 else None
        prompts = pick_prompts(sk, rng, used_prompts)
        if slot.kind == "return":
            idea = sections[slot.source].idea  # returns keep the idea, so they're recognisable
        else:
            idea = pick_idea(key, sec_meter, sk, rng)
        sections.append(
            Section(
                index=i, label=labels[i], slot=slot, knobs=sk, key=key, meter=sec_meter,
                loop=loop, cue=cue, start_cue=start_cue, key_change=key_change, start_bar=bar,
                prompts=prompts, idea=idea,
            )
        )
        bar += loop.bars

    return Jam(
        title=config.title, seed=seed, mood=mood, arc=config.arc, form=form_name,
        label_style=config.labels, tempo=tempo, meter=meter, home_key=home_key,
        knobs=knobs, sections=sections,
    )
