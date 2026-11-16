# JavaScript & TypeScript: Zero to Mastery — study guides

Four Socratic study guides, one per Part of the 105-card course in
`backend/app/content/js_ts_course/`. Each guide teaches the Part's chapters, then
works every card (the card, how to solve it, the trap, the verified solution, the
relevant readings), and ends with an audit trail and an index of terms.

| Part | Guide | Cards |
| --- | --- | --- |
| 1 · JavaScript Fundamentals | `part1-javascript-fundamentals.pdf` / `.tex` | 64 |
| 2 · TypeScript Core | `part2-typescript-core.pdf` / `.tex` | 19 |
| 3 · Intermediate TypeScript | `part3-intermediate-typescript.pdf` / `.tex` | 17 |
| 4 · Hands-On Labs | `part4-hands-on-labs.pdf` / `.tex` | 5 |

`decks/` holds the same cards as JSON for `POST /api/import/json`: per subdeck a
plain array (`NN-name.json`) and a wrapped copy (`NN-name.wrapped.json`). The
preferred way to install the course is still `backend/scripts/rebuild_js_ts_deck.py`,
which builds the whole deck tree.

## Rebuilding

Needs `backend/.venv` (with the backend installed), Node, `frontend/node_modules`
(for `tsc`) and `pdflatex`. From the repo root:

```bash
backend/.venv/bin/python study-guides/js-ts/source/build.py 1 2 3 4
backend/.venv/bin/python study-guides/js-ts/source/export_decks.py
```

`build.py` refuses to build if any card or snippet doesn't verify: every code
card's answer must pass its tests in the app's runner (and its starter must fail),
every predicted output must match Node, every compile verdict must match `tsc`,
and every snippet's printed output must match what the guide shows.

Sources: `source/chapters/` (chapter text), `source/parts/` (per-Part card notes,
snippets and audit entries), `source/preamble.tex`.
