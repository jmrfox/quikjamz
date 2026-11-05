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
| MIDI preview | not started |
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

## Tests

```bash
uv run pytest
```

## License

MIT
