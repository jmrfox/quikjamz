// QuikJamz sheet. Data comes in as JSON through sys.inputs (see sheet.py).

#let data = json(bytes(sys.inputs.at("data")))
#let paper = sys.inputs.at("paper", default: "us-letter")

#let ink = rgb("#1b1b1b")
#let soft = rgb("#666666")
#let faint = rgb("#bdbdbd")
#let accent = rgb("#2f5d8a")

#set page(
  paper: paper,
  margin: (x: 0.55in, top: 0.5in, bottom: 0.6in),
  footer: grid(
    columns: (1fr, auto),
    text(7pt, fill: soft, data.legend),
    text(7pt, fill: soft, data.footer),
  ),
)
#set text(
  font: ("Segoe UI", "Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans", "Libertinus Serif"),
  size: 9pt,
  fill: ink,
)
#set par(leading: 0.5em, spacing: 0.5em)

// ---------------------------------------------------------------- header

#grid(
  columns: (1fr, auto),
  align: (left + bottom, right + bottom),
  text(18pt, weight: "bold", data.title),
  text(11pt)[#data.tempo #h(0.5em)·#h(0.5em) #data.meter #h(0.5em)·#h(0.5em) #data.key],
)

#v(6pt)

// ------------------------------------------------- road map + energy curve

#let road = data.roadmap
#grid(
  columns: road.map(r => r.weight * 1fr),
  column-gutter: 3pt,
  row-gutter: 3pt,
  ..road.map(r => box(width: 100%, height: 14pt, place(
    bottom,
    rect(width: 100%, height: 2pt + r.energy * 12pt, fill: accent.lighten(60%), stroke: none),
  ))),
  ..road.map(r => text(8pt)[*#r.label* #text(fill: soft, r.short)]),
)

#v(2pt)
#line(length: 100%, stroke: 0.6pt + ink)
#v(4pt)

// --------------------------------------------------------------- sections

#let chord-text(c, small: false) = {
  let big = if small { 11.5pt } else { 13pt }
  let suffix-size = if c.suffix.clusters().len() > 6 or small { 8.5pt } else { 10pt }
  if c.at("push", default: false) { text(11pt, fill: accent, weight: "bold", "›") }
  text(big, weight: "semibold", c.root)
  text(suffix-size, c.suffix)
  if c.bass != none { text(big - 1pt, [/#c.bass]) }
}

#let slash = text(10pt, fill: soft, "/")

#let bar-cell(b, first, last) = box(
  width: 100%,
  height: 30pt,
  stroke: (
    left: if first { 1.4pt + ink } else { 0.6pt + ink },
    right: if last { 1.4pt + ink } else { none },
    bottom: 0.3pt + faint,
  ),
  inset: (left: 4pt, right: 2pt),
)[
  #place(top + left, dx: -2pt, dy: 1.5pt, text(5pt, fill: soft, str(b.n)))
  #align(horizon)[
    #if b.slots != none {
      for (i, s) in b.slots.enumerate() {
        if i > 0 { h(if s.group { 11pt } else { 4pt }) }
        if s.chord == none { slash } else { chord-text(s.chord, small: true) }
      }
    } else if b.chords.len() == 0 {
      text(11pt, fill: faint, "%")
    } else {
      b.chords.map(chord-text).join(h(6pt))
    }
  ]
]

#let idea-text(idea) = {
  if idea.type == "rhythm" {
    let shown = idea.text.replace("x", "●").replace(".", "·")
    [rhythm idea: #text(font: ("DejaVu Sans Mono", "Consolas"), size: 8pt, tracking: 1pt, shown)]
  } else {
    [melody idea: #idea.text]
  }
}

#let label-text(l) = text(14pt, weight: "bold", l)

#context {
  let label-w = calc.max(..data.sections.map(s => measure(label-text(s.label)).width)) + 4pt
  for s in data.sections {
    let n = s.bars.len()
    let body = {
      grid(
        columns: (1fr,) * s.bars_per_row,
        row-gutter: 4pt,
        ..s.bars.enumerate().map(((i, b)) => bar-cell(
          b,
          calc.rem(i, s.bars_per_row) == 0,
          i == n - 1 or calc.rem(i + 1, s.bars_per_row) == 0,
        )),
      )
      v(1pt)
      if s.notes.len() > 0 {
        text(8.5pt, fill: accent, weight: "semibold", s.notes.join(" · ") + " · ")
      }
      text(8.5pt, fill: soft, s.line)
      let extras = s.prompts.map(p => emph(p))
      if s.idea != none { extras.push(box(idea-text(s.idea))) }  // never wrap mid-idea
      if extras.len() > 0 {
        linebreak()
        text(8.5pt)[» #extras.join([ #h(0.3em)·#h(0.3em) ])]
      }
    }
    block(breakable: false, below: 12pt, grid(
      columns: (label-w, 1fr),
      column-gutter: 6pt,
      stack(
        spacing: 3pt,
        label-text(s.label),
        text(9pt, fill: accent, weight: "semibold", s.cue),
      ),
      body,
    ))
  }
}
