# source notes

## Calendar and texts

- [Divinum Officium repository](https://github.com/DivinumOfficium/divinum-officium)
  at `4fe208cf6ca959cdaa7840bddc97c86aea0cb820`; MIT licence included in the build.
- The standalone `EofficiumXhtml.pl` and `Emissa.pl` renderers assemble the
  text. Both languages are explicitly `Latin`, version `Rubrics 1960 - 1960`.
- Every date contains all eight hours, private and priest-led variants,
  solemn and low Mass, and both forms of the five supported votive Masses.
  These are generated ahead of time; no proxy or live liturgy API is needed.
- Imported HTML is reduced to text and a small set of inline tags. Navigation,
  executable markup and presentational attributes aren't carried into the app.

## Independent calendar check

Checked on 5 September 2026 against a published 1962-Missal calendar from an
unrelated church, chosen because it prints the traditional designation itself:

- [The London Oratory, regular Mass times](https://www.bromptonoratory.co.uk/regular-mass-service-times)
  lists Sunday `9.00am (Latin, 1962 Missal)` and an `11.00am Solemn Latin Mass`,
  so its calendar is the one these books use.
- [Newsletter, Sunday 30 August 2026](https://www.bromptonoratory.co.uk/blog/sunday-30th-august-2026)
  prints `14th Sunday after Pentecost` alongside the modern `22nd Sunday of the
  Year (A)`. Manuale generates `Dominica XIV Post Pentecosten` for that date
  from the general calendar. The agreement is independent: the numbering was
  not copied from this source, only compared with it.

A single agreeing date is a sanity check on the Sunday reckoning, not proof of
the whole calendar, and no propers were taken from it. The published newsletter
carries no usus antiquior propers, so none were inferred. This does not imply
that any particular church's observance matches the general calendar: local
propers, external solemnities and votive Masses routinely differ, which is why
the UI names the general calendar plainly and offers selectable votives rather
than asserting a local schedule.

## Explicit adaptations

1. `Emissa.pl` deliberately returns no text for `Communio_Populi`, which the
   interactive website opens in a popup. The importer inserts the remaining
   Communion rite from `web/www/missa/Latin/Ordo/Communio.txt` at its original
   position, before the ablutions. It starts at *Ecce Agnus Dei*, omitting the
   pre-1962 second Confiteor and absolution. The three *Domine, non sum dignus*
   responses and Communion formula are included in full.
2. A broken source reference on 7 October points to `Sancti/9-12`, while the
   file is named `Sancti/09-12`. `source_patches.json` records this one-character
   correction. The intended Gospel is Luke 1:26–38, preserved from the
   existing 12 September source, not generated or paraphrased.
3. Inline source formatting becomes reading styles: italic rubrics and
   upright response markers in the rite's accent colour, and smaller verse
   numbers. These are display colours, not a change to the rubrics. Source section
   boundaries and prayer text are retained. The inserted section headings
   *Sanctus*, *Communio fidelium*, *Ablutiones* and *Ultimum Evangelium* aid
   navigation; they don't change spoken text.

There are no generated prayers or machine translations in the corpus.

## Ordinary and proper

The propers view needs to know which blocks are the day's own and which belong
to the ordinary, and the two are mixed inside the same section: the deacon's
`Munda cor meum` and the blessing before the Gospel sit inside `Evangelium`,
and the offertory prayers fill `Offertorium` around a two-block antiphon.

Rather than keep a list of Latin incipits, the corpus is asked. A block that
recurs on more than half the days of the de die Mass is the ordinary; one that
varies is proper. Measured over a year the distribution is bimodal and the gap
is wide: 4622 blocks appear on under 10% of days, 221 on over 90%, and nine
fall in between. Those nine set the boundary, between the common preface at
39.5%, which a propers sheet prints, and the Gloria's rubrics at 68.8%, which
it does not.

Votive and numbered Masses are excluded from the count. Their propers repeat
every day by nature, so counting them would file them as ordinary and hide
exactly the text a votive exists to supply.

The resulting identifiers are stored in `data/index.json` and recomputed in the
browser with the same FNV-1a 64 over the same plain text, so the corpus travels
without the list being shipped twice. The two implementations are pinned
against each other by tests on both sides.

Two rites are not Masses with propers set into an ordinary, but forms of their
own: Good Friday and Holy Saturday. Lifting the proper-looking sections out of
them returns a fragment that reads as complete while omitting the solemn
orations and the adoration of the Cross, or the Exsultet, the prophecies, the
litanies and the blessing of the font. The propers view refuses them instead,
and uses the presence of an Introit to tell one case from the other: across
both published years exactly eight rites lack one, which are these two days in
each form. A test holds that count exact.

## Authorship

The code, tooling, tests and notes in this repository were written with AI
assistance: OpenAI GPT models and Anthropic Claude models, under human
direction and review. The liturgical corpus was not. It is imported verbatim
from Divinum Officium at the pinned revision, and the three adaptations above
are the complete list of changes made to it, each with an exact boundary that
fails loudly rather than degrading quietly.
