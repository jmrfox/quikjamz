"""Write generated loops to a single MIDI file, for loading into a DAW.

The file has one track per part so each can be muted or reassigned:
  1. chords - block chords, smoothly voiced, held for each chord's length
  2. bass   - the root (or slash-chord bass) of each chord
  3. click  - optional metronome on the GM drum channel, accent on beat 1
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import mido

from ..harmony.progression import Loop
from ..theory.chords import Chord

TICKS_PER_QUARTER = 480

CHORD_LOW, CHORD_HIGH = 52, 79  # E3..G5
BASS_LOW = 36  # C2; bass notes land in C2..B2
MAX_CHORD_NOTES = 5

CHORD_CHANNEL, BASS_CHANNEL, CLICK_CHANNEL = 0, 1, 9
CHORD_PROGRAM = 4  # GM Electric Piano 1
BASS_PROGRAM = 33  # GM Electric Bass (finger)
CLICK_ACCENT, CLICK_BEAT = 37, 42  # side stick, closed hi-hat


@dataclass
class MidiSection:
    loop: Loop
    passes: int = 2
    play_ending: bool = True  # add one bar of the loop's final chord after the last pass
    beat_unit: int = 4  # 4 = quarter-note beats, 8 = eighth-note beats


# ------------------------------------------------------------------- voicing


def _chord_pcs(chord: Chord, tonic_pc: int) -> list[int]:
    """Absolute pitch classes, root first; thins out the 5th on big chords."""
    tones = list(chord.tones())
    if len(tones) > MAX_CHORD_NOTES and 7 in tones:
        tones.remove(7)
    tones = tones[:MAX_CHORD_NOTES]
    root = (tonic_pc + chord.rel_root) % 12
    pcs = []
    for t in tones:
        pc = (root + t) % 12
        if pc not in pcs:
            pcs.append(pc)
    return pcs


VOICING_CENTER = 64  # E4: voicings are pulled toward the middle of the range


def _candidate_voicings(pcs: list[int]) -> list[list[int]]:
    """Close-position inversions, plus drop-2 versions of each, that fit the chord range."""
    out = []
    for r in range(len(pcs)):
        order = pcs[r:] + pcs[:r]
        for bottom in range(CHORD_LOW, CHORD_LOW + 12):
            if bottom % 12 != order[0]:
                continue
            notes = [bottom]
            for pc in order[1:]:
                notes.append(notes[-1] + 1 + (pc - notes[-1] - 1) % 12)
            shapes = [notes]
            if len(notes) >= 4:
                drop2 = sorted(notes[:-2] + [notes[-2] - 12] + notes[-1:])
                shapes.append(drop2)
            for shape in shapes:
                for shift in (0, 12):
                    v = [n + shift for n in shape]
                    if v[0] >= CHORD_LOW and v[-1] <= CHORD_HIGH:
                        out.append(v)
    return out


def _voicing_cost(v: list[int], previous: list[int] | None) -> float:
    cost = 0.3 * abs(sum(v) / len(v) - VOICING_CENTER)
    cost += 2.0 * sum(1 for a, b in zip(v, v[1:]) if b - a == 1)  # semitone clusters
    if previous:
        cost += sum(min(abs(n - p) for p in previous) for n in v) / len(v)
        cost += sum(min(abs(p - n) for n in v) for p in previous) / len(previous)
    return cost


def voice(pcs: list[int], previous: list[int] | None) -> list[int]:
    """Pick the inversion that moves least from the previous chord and stays mid-register."""
    candidates = _candidate_voicings(pcs)
    return min(candidates, key=lambda v: (_voicing_cost(v, previous), v))


def bass_note(chord: Chord, tonic_pc: int) -> int:
    rel = chord.rel_bass if chord.rel_bass is not None else chord.rel_root
    return BASS_LOW + (tonic_pc + rel) % 12


# --------------------------------------------------------------------- write


def _ticks_per_beat(unit: int) -> int:
    return TICKS_PER_QUARTER * 4 // unit


def _timeline(sections: list[MidiSection], gap_bars: int):
    """Chord events and bar starts, in ticks.

    Returns (events, bars, total_ticks) where events are (on, off, chord, tonic_pc) and bars
    are (tick, beats_per_bar, beat_unit) for every bar, so meter changes can be written.
    """
    events, bars = [], []
    tick = 0
    for i, section in enumerate(sections):
        loop = section.loop
        tpb = _ticks_per_beat(section.beat_unit)
        bpb = loop.beats_per_bar
        tonic = loop.key.tonic.pc
        start = tick
        for _ in range(section.passes):
            for event in loop.events:
                events.append((tick, tick + event.beats * tpb, event.chord, tonic))
                tick += event.beats * tpb
        if section.play_ending:
            events.append((tick, tick + bpb * tpb, loop.final, tonic))
            tick += bpb * tpb
        if i < len(sections) - 1:
            tick += gap_bars * bpb * tpb
        bars += [(t, bpb, section.beat_unit) for t in range(start, tick, bpb * tpb)]
    return events, bars, tick


def _to_track(name: str, messages: list[tuple[int, mido.Message]]) -> mido.MidiTrack:
    """Absolute-tick messages -> a track with delta times. Note-offs sort before note-ons."""
    track = mido.MidiTrack([mido.MetaMessage("track_name", name=name, time=0)])
    ordered = sorted(messages, key=lambda m: (m[0], 0 if m[1].type == "note_off" else 1))
    now = 0
    for tick, msg in ordered:
        track.append(msg.copy(time=tick - now))
        now = tick
    return track


def write_midi(
    path: str | Path,
    sections: list[MidiSection],
    *,
    quarter_bpm: float = 100,
    click: bool = True,
    gap_bars: int = 1,
) -> Path:
    """Write all sections, one after another, to a single .mid file.

    Tempo is in quarter notes per minute; a section in 7/8 at quarter_bpm 105 has
    210 eighth-note beats a minute. Each section can have its own meter.
    """
    if not sections:
        raise ValueError("Nothing to write")
    path = Path(path)
    events, bars, total_ticks = _timeline(sections, gap_bars)

    meta_msgs = [(0, mido.MetaMessage("set_tempo", tempo=round(60_000_000 / quarter_bpm)))]
    current = None
    for tick, bpb, unit in bars:
        if (bpb, unit) != current:
            meta_msgs.append((tick, mido.MetaMessage("time_signature", numerator=bpb, denominator=unit)))
            current = (bpb, unit)
    meta = _to_track("QuikJamz", meta_msgs)
    meta.append(mido.MetaMessage("end_of_track", time=total_ticks - sum(m.time for m in meta)))

    chord_msgs = [(0, mido.Message("program_change", channel=CHORD_CHANNEL, program=CHORD_PROGRAM))]
    bass_msgs = [(0, mido.Message("program_change", channel=BASS_CHANNEL, program=BASS_PROGRAM))]
    previous = None
    for on, end, chord, tonic in events:
        off = end - 1
        notes = voice(_chord_pcs(chord, tonic), previous)
        previous = notes
        for n in notes:
            chord_msgs.append((on, mido.Message("note_on", channel=CHORD_CHANNEL, note=n, velocity=72)))
            chord_msgs.append((off, mido.Message("note_off", channel=CHORD_CHANNEL, note=n)))
        b = bass_note(chord, tonic)
        bass_msgs.append((on, mido.Message("note_on", channel=BASS_CHANNEL, note=b, velocity=90)))
        bass_msgs.append((off, mido.Message("note_off", channel=BASS_CHANNEL, note=b)))

    midi = mido.MidiFile(ticks_per_beat=TICKS_PER_QUARTER)
    midi.tracks += [meta, _to_track("chords", chord_msgs), _to_track("bass", bass_msgs)]

    if click:
        click_msgs = []
        for bar_tick, bpb, unit in bars:
            tpb = _ticks_per_beat(unit)
            for beat in range(bpb):
                accent = beat == 0
                note = CLICK_ACCENT if accent else CLICK_BEAT
                tick = bar_tick + beat * tpb
                vel = 100 if accent else 60
                click_msgs.append((tick, mido.Message("note_on", channel=CLICK_CHANNEL, note=note, velocity=vel)))
                click_msgs.append((tick + tpb // 4, mido.Message("note_off", channel=CLICK_CHANNEL, note=note)))
        midi.tracks.append(_to_track("click", click_msgs))

    path.parent.mkdir(parents=True, exist_ok=True)
    midi.save(path)
    return path


def jam_to_midi(jam, path: str | Path, *, click: bool = True) -> Path:
    """Write a whole Jam: sections back to back, each repeated as its cue says."""
    last = len(jam.sections) - 1
    sections = [
        MidiSection(s.loop, passes=s.cue.passes, play_ending=i == last, beat_unit=s.meter.unit)
        for i, s in enumerate(jam.sections)
    ]
    return write_midi(path, sections, quarter_bpm=jam.tempo, click=click, gap_bars=0)
