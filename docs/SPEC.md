# QuikJamz Spec (draft v0.1)

QuikJamz takes a few parameters and randomly generates a **jam guide**: a compact sheet that gives a group of improvisers a shared map, with form, harmony, meter and cues. It does not tell anyone exactly what to play.

This spec covers what the knobs mean, how harmony and form are generated, how parts work, and what the sheet looks like. Numbers marked *(tunable)* are starting values, to be adjusted by ear.

---

## 1. Glossary

| Term | Meaning |
|---|---|
| **Jam** | One generated piece: header info plus an ordered list of sections. |
| **Section** | A stretch of the jam with one harmonic loop, one set of knob values and one cue. Has a **label** (e.g. `A`, `△`, `Gather`). |
| **Loop** | The chord pattern a section repeats: 1, 2, 4 or 8 bars long. |
| **Pass** | One time through a loop. |
| **Cue** | How a section ends or moves on: a fixed count, or an open signal. |
| **Knob** | A 0–1 parameter (energy, tension, …). |
| **Arc** | A curve that moves knobs across the jam's sections. |
| **Role** | A musical job (pulse, low, harmony, melody, texture). Instruments map to roles. |
| **Part** | A sheet for one instrument. The generic part is written only in roles. |
| **Seed** | An integer that makes a jam fully reproducible. |

---

## 2. Knobs

All knobs are floats in **[0, 1]**. Each one has a **primary** job, the thing it mainly drives. Secondary effects are allowed but kept small, so turning one knob produces a change you can name.

| Knob | Primary job | Secondary effects |
|---|---|---|
| **energy** | Dynamics, how many roles are playing, and tempo (when tempo is unset) | Attack words ("lean in", "barely there") |
| **tension** | How often the harmony resolves, and how much dissonance it allows | Altered extensions (b9, #11, b13), unresolved section endings |
| **complexity** | How many distinct chords, chord extensions, and how fast chords change | Longer loops, more prompts per section |
| **brightness** | Choice of mode (see 2.1); register | Direction of borrowed chords, voicing words ("open/high" vs "close/low") |
| **density** | How busy the rhythm is, and how much space is left | Density words, rhythmic seed ideas |
| **harmonic adventurousness** (`harm_adv`) | Distance from "expected" harmony (see 4.4) | Key changes between sections (at the high end only) |
| **rhythmic adventurousness** (`rhythm_adv`) | Meter choice and syncopation (see 2.2) | Rhythm prompts (displacement, polyrhythm, half-time), meter changes between sections |
| **stability** | How much sections change from one to the next | More returning sections (A … A′), less random variation per section |

**Feel is never printed.** The sheet never says swing, shuffle or straight; that is left to the players. Half-time and double-time can appear only as occasional prompts (section 6), never as a fixed property of a section.

### 2.2 Rhythmic adventurousness and meter

A meter the user sets always wins. If it's left unset, `rhythm_adv` picks one *(tunable)*:

| rhythm_adv | Meters it draws from |
|---|---|
| < 0.3 | 4/4 (3/4 about 10% of the time) |
| 0.3–0.55 | 4/4, 3/4, 6/8, 12/8 |
| 0.55–0.8 | 5/4, 7/8, 7/4, 6/4 |
| > 0.8 | 9/8, 11/8, combined loops (e.g. a bar of 4/4 then a bar of 3/4), and meter changes between sections |

Odd meters print with their grouping, e.g. `7/8 (2+2+3)`.

`rhythm_adv` also sets how syncopated the seed rhythms are (section 6), and how likely rhythm-bending prompts are.

### 2.1 Brightness and mode

Modes have a well-known order from bright to dark. Brightness picks a mode along it:

```
Lydian  Ionian  Mixolydian  Dorian  Aeolian  Phrygian  Locrian
 1.0     0.83     0.67       0.5     0.33     0.17      0.0
```

- If the user **does not fix the mode**, sample a mode near the brightness value. Weight by distance (σ ≈ 0.1) and down-weight Locrian ×0.3, since it has no stable tonic chord *(tunable)*.
- If the user **fixes the mode**, brightness only affects register and voicing words, plus the direction of borrowed chords: bright borrows from brighter modes (e.g. #IV°/II in major), dark from darker ones (bVI, bVII, iv, bII).
- Non-modal scales (harmonic/melodic minor, pentatonics, blues) can be fixed by the user, but brightness never picks them in v1.
- **Scales are data files.** Each one lists its intervals, its brightness position, and its home/away/pull chord table (section 4.2). That way scales from outside the seven modes, such as maqam-inspired ones or Hungarian minor, can be added later without changing code.

### 2.3 Global vs. per-section values

The user sets **global** knob values, directly or through a mood preset. Each section then gets its own values:

```
section_knob = clamp( global + depth · (arc(t) − 0.5) + noise · (1 − stability) )
```

- `t` is the section's position in the jam, 0 for the first section and 1 for the last.
- `depth` is how strongly the arc applies to that knob (default: energy 0.6, density 0.5, tension 0.4, others 0) *(tunable)*.
- `noise` ~ N(0, 0.12) *(tunable)*.
- **Tension leads energy:** tension samples the arc a little early, at `arc(t + 0.15)`, so tension rises before a peak and drops before energy falls.
- Brightness and both adventurousness knobs are **global by default**, so the jam keeps one harmonic and rhythmic identity. A section can still vary them if `stability` is low.

### 2.4 Mood presets

A mood is just a set of starting knob values. Users can override any knob. Values below are starting points *(tunable)*.

| Mood | energy | tension | complexity | brightness | density | harm_adv | rhythm_adv | stability |
|---|---|---|---|---|---|---|---|---|
| calm | 0.25 | 0.20 | 0.35 | 0.60 | 0.25 | 0.25 | 0.15 | 0.80 |
| happy | 0.65 | 0.25 | 0.40 | 0.85 | 0.55 | 0.25 | 0.30 | 0.70 |
| sad | 0.30 | 0.45 | 0.45 | 0.30 | 0.30 | 0.35 | 0.20 | 0.70 |
| energetic | 0.85 | 0.50 | 0.40 | 0.65 | 0.80 | 0.35 | 0.45 | 0.55 |
| dark | 0.50 | 0.65 | 0.45 | 0.15 | 0.45 | 0.50 | 0.40 | 0.60 |
| mysterious | 0.35 | 0.60 | 0.55 | 0.40 | 0.30 | 0.65 | 0.50 | 0.50 |
| triumphant | 0.85 | 0.35 | 0.45 | 0.80 | 0.65 | 0.30 | 0.25 | 0.65 |
| dreamy | 0.30 | 0.35 | 0.65 | 0.75 | 0.30 | 0.55 | 0.30 | 0.60 |
| chaotic | 0.80 | 0.80 | 0.70 | 0.45 | 0.85 | 0.90 | 0.90 | 0.15 |
| hypnotic | 0.50 | 0.30 | 0.15 | 0.50 | 0.55 | 0.15 | 0.35 | 0.95 |

Moods and presets are **data files**, not code.

### 2.5 Arcs

`arc(t)` returns a value in [0, 1].

| Arc | Shape | f(t) |
|---|---|---|
| flat | none | 0.5 |
| build | steady rise | t |
| slow burn | rises late | t² |
| arch | rise then fall | sin(πt) |
| collapse | falls | 1 − t |
| wave | two swells | 0.5 + 0.5·sin(2π·2t − π/2) |
| plateau | up, hold, down | smoothstep up over [0, 0.25], hold, down over [0.75, 1] |
| wander | random | smoothed random walk (seeded) |

Default arc: **arch**.

### 2.6 Seed

Every random choice draws from a single `random.Random` built from the seed, in a fixed order. The same seed with the same config always gives the same jam. The seed is printed on the sheet.

---

## 3. Form and sections

### 3.1 Choosing the form

The inputs are the **number of sections** (`--sections`, default: 4–6 chosen from the seed) and `stability`. Bar counts follow from the sections. Jam length is never given in minutes, because open cues make timing unpredictable anyway.

Forms are built from templates *(data)*:

| Template | Example |
|---|---|
| through | A B C D |
| return | A B A′ |
| ring | A B A C A |
| mirror | A B C B′ A′ |
| strophic | A A′ A″ B |
| drift | A B C … (each derived from the one before) |

- Higher `stability` favors templates with more **returns**.
- A **return** (`A′`) reuses the harmony of the earlier section, but its knob values are taken fresh from the arc at its own position, and it gets a new prompt. That way the band recognizes it, but it doesn't play out the same way.
- **Drift** sections take the previous loop and change one chord. Good for low-stability, ambient jams.

### 3.2 Section length and cues

Each section has a `loop_bars` (1, 2, 4, 8) and a **cue**:

| Cue | Sheet text | When it's likely |
|---|---|---|
| count | `×4` | High stability, short loops |
| open | `open – until cue` | Solos, spotlight sections, low stability |
| signal | `on drum fill` / `when bass drops out` / `on nod from the spotlight` | Medium stability |
| fade | `thin out to nothing` | Last section, low energy |
| hit | `end on a held chord` / `stop together on 1` | Last section, high energy |

The first section may have a `start` cue (`count in`, `drone first, others join`).

*As built (v0.2):*
- **Signal cues** are role-neutral ("after a fill", "at a nod from the spotlight", "when the low end drops out"), so they work for any band.
- **Count cues** aim for 8 or 16 bars of playing.
- **In the MIDI,** open and signal sections play 2 passes, and sections run straight into each other.
- **Returns** keep the original chords exactly, so the band recognises them. Only the ending (resolve or hang) is picked again, using the returning section's own tension.
- **Drift sections** get their own label and change one chord of the previous loop. A one-chord vamp gains a second chord instead.
- **Tempo:** when it comes from energy and the meter is in eighths, it's scaled by 0.75 so the counted pulse stays playable.
- **Spelling:** double sharps and flats are respelled for readability (Bbb → A).

### 3.3 Labels

The label style is chosen by the user and defaults to **letters**. Labels must never suggest pop form (no verse, chorus, bridge).

| Style | Example | Notes |
|---|---|---|
| letters | A B A′ C | Primes mark returns |
| glyphs | ○ △ ○′ □ | Glyphs need a font with these symbols |
| colors | Blue / Amber / Blue′ | A colored tab on the sheet |
| motion | Open · Gather · Surge · Thin · Return | Word picked from the arc slope and knob level at that section (see below) |
| image | Fog · Engine · Tide · Glass | Word picked from a word list tagged by knob ranges |

Motion words are chosen like this:
- rising and low → *Gather*
- rising and high → *Surge*
- at the peak → *Blaze*
- falling → *Thin*
- low and flat → *Drift*
- the first section → *Open*
- a return → the original word plus ′, or *Return*

Word lists live in data files.

---

## 4. Harmony

### 4.1 Representation

Chords are stored as **scale degree + quality + extensions**, relative to the section's key. They are converted to actual notes only when the sheet is drawn.

```
Chord { degree: 1..7, alteration: -1|0|+1, quality: maj|min|dim|aug|sus2|sus4|5,
        seventh: none|6|7|maj7, extensions: [9, 11, 13], alterations: [b9, #9, #11, b13],
        bass: optional degree }
```

Each chord also records the tier it came from (4.3) and its **function** (4.2), so harmony can be explained or tweaked later.

### 4.2 Functions

Each chord has a function:

- **H (home):** stable, at rest.
- **A (away):** moving off home.
- **P (pull):** strongly wants to go home.

| Mode | H | A | P (cadence chord) |
|---|---|---|---|
| Ionian | I, vi, iii | ii, IV | V, vii° |
| Aeolian | i, bIII | iv, ii°, bVI | v / V (borrowed), bVII |
| Dorian | i | ii, bIII, v | **IV** (characteristic), bVII |
| Mixolydian | I | ii, IV, vi | **bVII**, v |
| Lydian | I | iii, vi | **II** (characteristic), vii |
| Phrygian | i | bIII, iv | **bII** (characteristic), bvii |
| Locrian | i° (weak) | bIII, iv | bII, bV |

In the modes, the **pull** role goes to the chord that contains the mode's characteristic note, not to V. This avoids every mode sounding like major or minor in disguise.

### 4.3 Vocabulary tiers

These tiers are the ladder for `harm_adv`. A higher tier adds chords on top of the lower ones.

| Tier | Adds | Examples (C Ionian) |
|---|---|---|
| 0 | The three main chords, vamps, drones | C, F, G; C pedal; Dm–G vamp |
| 1 | The rest of the diatonic chords | Dm, Em, Am, B° |
| 2 | Borrowed chords (from the parallel mode, toward the brightness direction) | Fm, Ab, Bb, Eb |
| 3 | Secondary dominants, ii–V chains, deceptive resolutions | A7→Dm, D7→G, G→Am |
| 4 | Tritone substitutions, chromatic mediants, section key changes | Db7→C, C→E, C→Ab |
| 5 | Non-functional: chords sliding in parallel, quartal stacks, pedals under moving chords, slash chords | C–D–E (planing), quartal C–F–Bb, Bb/C |

Each tier has a **weight multiplier**, so tiers fade in gradually instead of switching on:

```
m_k(a) = sigmoid( 6 · (5a − k + 0.5) )      # a = harm_adv (tunable)
```

Tier 0 always gets weight 1.

### 4.4 Defining harmonic adventurousness

**Definition:** `harm_adv` (written `a` below) sets how *surprising* the progression is compared with a plain baseline: a model that uses only tiers 0–1, with standard home → away → pull → home moves.

```
surprise(progression) = mean over moves of  −log P_baseline(move)
target_surprise(a)    = s_min + a · (s_max − s_min)
```

This makes "adventurous" something we can measure and test, instead of just a feeling.

### 4.5 Generating a loop

1. **How many chords, and how long each lasts** (from complexity):
   - `distinct_chords` ≈ 1 + round(complexity · 4), giving 1–5 chords.
   - Harmonic rhythm: low complexity holds a chord for 2–4 bars; high complexity changes 2 times per bar.
   - `loop_bars` = the smallest of 1, 2, 4 or 8 that fits all the chords.
   - A one-chord result is a **vamp or drone**. That is a valid outcome, not a fallback.
2. **First chord:** home, with p = 0.9 − 0.4·a. Otherwise, any chord from an allowed tier.
3. **Walk:** a Markov chain over chords. The weight of moving to a chord is `base_function_weight(from.fn → to.fn) · m_tier(to) · fit(to)`, where `fit` favors chords whose quality matches the current scale unless the chord is deliberately borrowed. *(tunable)* Base function weights:

   | from \ to | H | A | P |
   |---|---|---|---|
   | H | 0.2 | 0.5 | 0.3 |
   | A | 0.15 | 0.3 | 0.55 |
   | P | 0.7 | 0.2 | 0.1 |

   **Where changes land (as built in v0.2):** complexity sets *how often* chords change. `rhythm_adv` sets *where* in the bar they land (`harmony/rhythm.py`):
   - **Strong points:** the meter's natural landing spots, which are its group boundaries. That's beat 3 of 4/4, beat 4 of 5/4 (3+2), eighths 3 and 5 of 7/8 (2+2+3), and the dotted-quarter pulses of 6/8 and 12/8.
   - **Moving a change:** each change point (never the loop's first chord) moves with probability 0.08 + 0.45·r. It moves to a nearby barline (weight 1), strong point (0.7) or other beat (0.6·r, ×0.4 in /8 meters), preferring spots within about half a bar.
   - **Pushes:** above r = 0.45, a change on a barline or strong point may be *pushed* an eighth early, with probability 0.8·(r − 0.45).
   - **Limits:** chords last at least a beat (two eighths in /8), and the loop length never changes.
   - **Measured spread (4/4, complexity 0.6):** at r = 0, 91% of changes are on barlines and the rest on strong points. At r = 0.9, about 33% are on barlines, 25% are pushes, and the rest land on other beats.

4. **Wrap-around:** the loop's last chord should lead back into its first chord, so it repeats naturally. At low tension, prefer **P → H** at the end.
5. **Resolution (tension):**
   - On the section's final pass, end on home with probability `1 − tension`.
   - If not, the sheet marks the ending as unresolved ("hang on the V").
6. **Choosing among candidates:** generate N = 32 candidate loops and score each:
   ```
   score = − |surprise − target_surprise(a)|
           − λ_vl  · voice_leading_cost
           − λ_tier · (1 − a) · mean_tier
           − λ_res · (1 − tension/2) · unresolved_applied_dominants
   ```
   Keep the best-scoring loop. Voice-leading cost is the average semitone movement per voice between neighbouring chords. A loop never repeats a chord, so no repetition term is needed.

   *As built (v0.2):*
   - `target_surprise` runs from 1.0 to 3.5, which are the edges of the measured range. So `a = 0` picks the most expected candidate and `a = 1` the most surprising one.
   - Diminished and augmented diatonic chords get a prior of 0.3, because they are rare in practice.
   - A one-chord vamp always sits on home.
   - An applied dominant (V7/x, subV7/x) is only picked if its target can follow it.

### 4.6 Extensions and colour

Complexity decides **how many notes** a chord has. Tension decides **which colour notes**.

| complexity | Chord size |
|---|---|
| < 0.2 | power chords / triads (genre permitting) |
| 0.2–0.45 | triads, sus chords |
| 0.45–0.7 | 7th and 6th chords |
| 0.7–0.9 | 9ths, 11ths on minor chords, 13ths on dominant chords |
| > 0.9 | full extensions |

Each extension is checked against the scale. Natural extensions are the default. At high tension they may be swapped for altered notes (b9, #9, #11, b13) on dominant (pull) chords.

### 4.7 Key changes between sections

These need tier 4 to be active. When a new section starts, it may change key by one of these moves (weights *tunable*):
- relative major/minor
- parallel major/minor
- up a whole step
- up a half step
- chromatic mediant (±3 or ±4 semitones)

A return section (A′) goes back to its original key.

### 4.8 Spelling

- Notes are spelled with the **key signature of the parent major scale**. For example, D Dorian uses C major's signature, and Eb Mixolydian uses Ab's.
- Altered degrees take their spelling from the scale-degree letter: bVI in C is **Ab**, not G#.
- Key choices are limited to keys whose parent signature has at most 6 accidentals. Otherwise use the enharmonic equivalent: D# Ionian (9 sharps) becomes Eb Ionian (3 flats). F# and Gb (6 each) are both allowed.
- Chord symbol style is a user choice: `Cmaj7` / `CΔ7` / `CM7`, and `Cm7b5` / `Cø7`.

---

## 5. Band, roles, parts

### 5.1 Roles

| Role | Job |
|---|---|
| **pulse** | Holds time and feel |
| **low** | Foundation: roots, pedals, bass motion |
| **harmony** | Plays the chords: comping, pads, strumming |
| **melody** | Lines, hooks, solos |
| **texture** | Colour, noise, atmosphere, effects, swells |

### 5.2 Instruments as data

```yaml
# instruments/bass.yaml
name: bass
roles: { low: 1.0, melody: 0.3, pulse: 0.4 }
range: [E1, G3]
vocab:
  low:
    sparse: ["roots on 1, let it ring", "pedal the tonic"]
    dense: ["walk between chord tones", "syncopated 8ths, lock with kick"]
```

The built-in instruments to start with:
- drums
- percussion
- bass
- guitar
- keys
- synth
- voice
- horn (generic)
- strings (generic)

### 5.3 The generic part

The **"any instrument"** part is always available and always printed when parts are requested. It says nothing specific to an instrument. For each section it lists the active roles and gives one sentence of advice per role:

> **Gather** · roles open: *texture*, *melody* · "If you join, add colour, not rhythm. Long tones, or answer the melody."

### 5.4 Band setup and who plays when

- **Band config:** a list of instruments, with no player names, so sheets work for any group. Duplicates are numbered on the sheet (`guitar 1`, `guitar 2`). If the list is empty, the jam is generic only.
- **Who plays per section:**
  - The number of active roles is `round(lerp(1, all, energy))`.
  - Each section gets one **spotlight** role, and an instrument for it if the band has one that fits. The spotlight rotates across the jam.
  - On the sheet, the active roles appear as **compact tags** on each section row (`pulse low harm`), with the spotlight highlighted. There is no separate grid.
  - At low energy, roles are allowed to drop out entirely. A drone with texture only is a valid section.
- **Instrument sheets:** for each section and role, pick from the instrument's vocab for that role, keyed on density, energy and brightness.

### 5.5 Output modes

| Mode | Output |
|---|---|
| `combined` | One sheet: chart, plus a short line per section for every instrument in the band and for the generic part. |
| `parts` | One sheet per instrument in the band, plus the generic part. Each sheet has the full chart and that instrument's lines. |
| `both` | All of the above. |

---

## 6. Prompts

- **Prompt deck** *(data)*: short improvisation prompts, each tagged with the knob ranges and roles it fits.

  ```yaml
  - text: "Only three notes. Make them count."
    when: { density: [0, 0.4] }
  - text: "Call and response with {other_role}."
    when: { complexity: [0.3, 1] }
  - text: "Drop into half-time for a pass."
    when: { energy: [0.3, 0.7], rhythm_adv: [0.3, 1] }
  - text: "Displace the groove by an eighth."
    when: { rhythm_adv: [0.6, 1] }
  ```
- Each section gets 0–2 prompts. More complexity means more likely to get one. No prompt repeats within a jam, and a returning section gets fresh prompts.
- Half-time and double-time exist **only** as prompts like these.
- **Seed ideas** (optional): one short rhythm (written in a text form like `x.x. ..x. x..x ....`) and/or a 3–5 note melodic idea in scale degrees. Both are given as starting ideas, not as material that must be played. Higher `rhythm_adv` makes the rhythm more syncopated. *As built:* about 60% of new sections get one idea, either a rhythm or a melody, chosen by `rhythm_adv` vs `harm_adv`. A returning section keeps its original's idea; a drift section gets a new one.

---

## 7. Pipeline and data model

```
Config ──► resolve knobs (mood + overrides) ──► form ──► per-section knobs (arc + noise)
       ──► harmony (loops, keys) ──► orchestration (roles, spotlight) ──► prompts
       ──► JamPlan (JSON) ──┬─► Typst renderer ──► PDF sheet(s)
                            └─► MIDI writer    ──► .mid preview
```

**JamPlan** is a plain, serializable object. It is the single source of truth: the renderers never make musical decisions. This also allows saving a jam, "lock and reroll," and more renderers (HTML, text) later.

**MIDI export (v1):** exactly **one `.mid` file** per run, made to be loaded into other software such as a DAW. It is written at the jam's tempo and meter and has separate tracks:
- **chords:** block chords held for each chord's length. The voicing is chosen from inversions and drop-2 shapes to move as little as possible, pulled toward E4.
- **bass:** chord roots, or the slash-chord bass.
- **click:** optional; on the GM drum channel, with an accent on beat 1.

Sections play in order, each repeated as its cue says (an open section plays 2 passes). It's for tuning the generator by ear and for hearing a jam before playing it. Library: `mido`. *Built in v0.2 for the harmony demo; it will take a JamPlan once sections exist.*

```jsonc
{
  "title": "…", "seed": 42, "tempo": 96, "meter": { "sig": "4/4", "grouping": null },
  "home_key": { "tonic": "D", "mode": "dorian" },
  "knobs": { "energy": 0.5, ... },          // resolved global values
  "band": [ "bass", "guitar", "guitar", "drums" ],
  "sections": [
    {
      "label": "A", "label_style": "letters", "return_of": null,
      "key": { "tonic": "D", "mode": "dorian" }, "meter": null,   // null = jam meter
      "knobs": { ... },
      "loop": { "bars": 4, "chords": [ { "symbol": "Dm7", "degree": "i", "fn": "H", "tier": 0, "beats": 8 }, ... ] },
      "cue": { "type": "count", "text": "×4" },
      "active_roles": ["pulse", "low", "harmony"], "spotlight": "harmony",
      "prompts": ["Leave the 1 empty."],
      "parts": { "bass": "Pedal D, open up on the IV", "guitar 1": "…", "guitar 2": "…", "generic": "…" }
    }
  ]
}
```

---

## 8. Sheet layout

The goal is **one page per sheet** for a normal-length jam (up to ~8 sections), readable from a music stand.

```
┌───────────────────────────────────────────────────────────────┐
│ Title                               ♩ = 96 · 4/4 · D Dorian    │  header
│ ▁▂▄▆█▆▄▂  (energy curve)                                       │  roadmap
│ A×4 → B (open) → A′×4 → C → A″ (fade)                          │
├───────────────────────────────────────────────────────────────┤
│ A  ×4                                         pulse low harm  │  section
│ ┌¹─────────┬²────────┬³────────┬⁴────────┐                    │  chart
│ │ Dm7      │          │ G7       │          │ :‖                │
│ └──────────┴──────────┴──────────┴──────────┘                    │
│ laid-back, dark · Leave the 1 empty.                          │  vibe + prompt
│ ...                                                           │
├───────────────────────────────────────────────────────────────┤
│                                                     seed 42   │  footer
└───────────────────────────────────────────────────────────────┘
```

- **Header:** title, tempo, time signature, key. No "Jam Guide" heading.
- **Roadmap:** a one-line form summary with a small energy curve above it. Returns are marked with primes.
- **Chart:** chords in thin-ruled boxes. Measure numbers are tiny (about 5 pt, top-left corner), numbered across the whole jam. Repeat signs or `×N` show repeats.
- **Each section** has at most two text lines: vibe words with the cue, and one prompt or part line.
- **Role tags** sit at the right edge of each section header (`pulse low harm`). The spotlight role is bold or inverted.
- **Part sheets** are the same, with that instrument's line in place of the general prompt line.
- **Typography:** a clean sans for text, and a chord font with good ♭/♯/Δ/ø glyphs.
- **Paper size:** Letter and A4.

*As built (v0.2):*
- **Section labels** sit in a left column, sized to fit the longest label, with the count cue (`×4`) under the label.
- **Bars** run 8 to a row at a fixed width, so a section's length on the page shows how long it is. Each bar has a tiny bar number in its top-left corner, and a held bar shows a faint `%`.
- **Mid-bar changes** use real-book slash notation, with one `/` per beat (per eighth in /8). Slashes are spaced by the meter's grouping, and a pushed chord gets an accent-coloured `›`. Example: `/ / / ›E♭m` puts E♭m on the "and" of 4. A section with any mid-bar change drops to 4 bars per row to make room. The footer explains `/` and `›` when they appear.
- **Text chart:** the same information as `G@3` and `›E♭m@4&`.
- **Text lines:** line 1 is the key or meter change, return or drift note (in the accent colour), then vibe words, the cue and the last-pass ending. Line 2 is the prompts plus any seed idea.
- **Seed ideas:** rhythm ideas print as ● (hit) and · (rest), grouped by beat or by the meter's grouping.
- **Accidentals** are real ♭ and ♯ throughout.
- **Fit:** 40 random six-section jams all fit on one Letter page.

**Rendering:** **Typst**, through the `typst` Python package, so no separate binary is needed. A Typst template reads the JamPlan JSON and lays out the sheet. Each part sheet is the same template with a different `part` input.

---

## 9. Configuration surface (v1)

```bash
quikjamz --title "Tuesday" --mood mysterious --harm-adv 0.7 --rhythm-adv 0.3 \
         --arc build --key D --mode dorian --tempo 96 --meter 4/4 --sections 5 \
         --labels motion --band bass,guitar,guitar,drums --out parts --midi --seed 42
```

Every knob can be set with `--energy 0.6` and so on, which overrides the mood. Anything left unset is chosen at random from the seed. For example, tempo is drawn from a range set by energy, and meter from `rhythm_adv`. `--band` also accepts a YAML file.

---

## 10. Decisions log

| # | Question | Decision (2026-11-04) |
|---|---|---|
| 1 | Meter and feel | Swing, shuffle and other feel words never go on the sheet. Adventurousness is split into `harm_adv` and `rhythm_adv`. Meter is user-set, or picked by `rhythm_adv` (2.2). Half-time and double-time appear only as prompts. |
| 2 | What drives harmonic rhythm | Complexity. Density stays purely rhythmic. |
| 3 | Scales outside the seven modes | Later. Scales are data files, so they can be added without code changes. |
| 4 | How jam length is set | By number of sections. |
| 5 | Who's-playing display | Compact role tags on each section row, with the spotlight highlighted. |
| 6 | Player names | Not used. The band is a list of instruments, and duplicates are numbered. |
| 7 | Renderer | Typst, through the `typst` Python package. |
| 8 | Tuning by ear | A simple MIDI export in v1: chords plus bass roots. |

## 11. Open questions

1. **Chord symbol default:** `Cmaj7` or `CΔ7`? (Both will be options. Which one should be the default?)
2. **Generic part and band parts together:** in `combined` mode, should the generic line always print, or only when the band config is empty?
