# QuikJamz

Randomly generated **jam guides** for groups of improvisers. You set a few knobs (energy, tension, complexity, brightness, harmonic and rhythmic adventurousness, …) and QuikJamz gives you a compact sheet with a form, chord loops, cues and prompts. It never tells anyone exactly what to play.

The design lives in [docs/SPEC.md](docs/SPEC.md).

## Status

Being rebuilt from scratch (v0.2).

| Part | State |
|---|---|
| Harmony engine (modes, chord vocabulary tiers, loop generation, colour, key changes) | ✅ working |
| Sections, form, labels, cues | not started |
| Band, roles, parts | not started |
| Prompts | not started |
| Typst sheet renderer | not started |
| MIDI export (one `.mid`: chords, bass, click tracks) | ✅ working |
| `quikjamz` CLI | not started |

## Try the harmony engine

```bash
uv sync
uv run python -m quikjamz.harmony --key D --mode dorian --harm-adv 0.4 --count 6 -v
```

Useful flags:
- `--harm-adv`, `--complexity`, `--tension`, `--brightness` (all 0–1)
- `--mode` (leave it out to pick the mode from brightness)
- `--beats` (beats per bar)
- `--style jazz` (Δ / ø chord symbols)
- `--seed`

`-v` shows each chord's Roman numeral, tier and function, plus the loop's surprise score.

### MIDI

Add `--midi PATH` to write every printed loop, one after another, into a single `.mid` file you can load into a DAW:

```bash
uv run python -m quikjamz.harmony --mode dorian --count 6 --tempo 96 --midi out/loops.mid
```

- **Tracks:** `chords` (block chords voiced to move smoothly, Electric Piano), `bass` (the roots, Finger Bass) and `click` (GM drums, accent on beat 1).
- **Layout:** each loop plays `--passes` times (default 2), then its ending chord for a bar, then a bar of rest.
- **Options:**
  - `--no-click` leaves out the click track.
  - `--beat-unit 8` together with `--beats 7` gives 7/8, with `--tempo` counted in eighth notes.

`out/` is git-ignored.

## Tests

```bash
uv run pytest
```

## License

MIT
