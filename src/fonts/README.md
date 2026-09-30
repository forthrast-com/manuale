# Bundled fonts

## IM FELL English

IM FELL English by Igino Marini, distributed under the SIL Open Font License 1.1.
The unmodified regular and italic faces from Google Fonts are kept, unshipped,
in `tools/fonts/`:
https://github.com/google/fonts/tree/main/ofl/imfellenglish

- Regular Git blob: `275d754ed6be5d26e37c6ccdb4934a0930dcbe3f`.
- Italic Git blob: `d9afa7e097d525cefa294f2575efc4bef66e1dda`.
- Licence: `IM_FELL_OFL.txt`.

FELL has no ǽ, Ǽ or combining acute, yet the corpus writes *sǽcula* and
*obœ́diens* thousands of times, and those letters fell back to a system serif
mid-word. `tools/patch_fonts.py` adds them as composites of FELL's own æ, œ
and acute, with a `ccmp` ligature so œ́ becomes one glyph. The licence
reserves the name, so the bundled result is **Manuale Fell**
(`manuale_fell.ttf`, `manuale_fell_italic.ttf`). The new glyphs kern as their
bases do, eased where FELL eases the same pair for its own accented vowels.
Run `make fonts` after changing the script; every table of the output is
reproducible (the bytes only with the same fontTools), and the script
refuses a source that is not the upstream blob above. Nothing else modifies
the outlines.

Both faces are bundled and precached for offline use. Uncommon liturgical
symbols (℣, ℟, ✠) can fall back to the system's serif fonts.

## Fraunces

Fraunces by Undercase Type, distributed under the SIL Open Font License 1.1.
The unmodified variable font is bundled locally; reading never requests Google Fonts.

Source: https://github.com/google/fonts/tree/main/ofl/fraunces
Upstream font Git blob: `8210f9488d3c732359a9292dd09aca3f2bae830e`.

The display face uses its optical size, softness and wonk axes. Prayer text
uses Manuale Fell, with its true italic for rubrics.
