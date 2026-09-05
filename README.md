# manuale

A Latin-only pocket missal and breviary for the 1962 Roman books: the whole
sequence, with the day's propers in place. A static, installable web app for
GitHub Pages, with no runtime server, account, analytics, or third-party requests.

- Mass in solemn and low forms; all eight hours, for private recitation or
  celebration with a priest. First Vespers and commemorations follow the
  underlying calendar.
- Five selectable votive Masses: Our Lady, the dead, St Joseph, the Passion,
  and propagation of the faith. Selecting a votive doesn't change the Office.
- Continuous document scrolling, a section index, remembered place, larger
  type and true-black OLED dark mode. Screen-sized pages remain an optional
  reading mode.
- IM FELL English reading text, Fraunces headings and restrained liturgical
  accents. Both fonts are bundled locally, including the Fell italic.
- Installable on a phone. Opened days are saved automatically; download the
  next seven or thirty days, including every hour and supported Mass variant.

## Run locally

```sh
nix develop
make data       # downloads the pinned source and generates two calendar years
make serve      # http://127.0.0.1:4173
```

For a quicker first build:

```sh
nix develop
make source
python3 tools/generate.py --start 2026-09-01 --end 2026-09-30
make serve
```

The first full generation takes several minutes. Valid existing day packs
are reused. The default range is the current and following calendar year;
`--start` and `--end` select a different range. The calendar explicitly shows
which dates the current build contains. Generated files are kept in `data/`
and `dist/`, both ignored by Git. Development scripts and disposable work
stay visible in the project, in `tools/` and `scratch/`.

Nothing needs npm. The flake pins Python with Beautiful Soup, Perl with CGI,
Node for the small JS test suite, and the supporting utilities.

## GitHub Pages

Push this repository to GitHub, then choose **Settings → Pages → Source →
GitHub Actions**. The included workflow builds and publishes `dist/` on
pushes to `main`, manual dispatch, and monthly to roll the available years
forward. Calendar generation is cached. The upstream text revision only
changes when you update `sources.json` deliberately.

All URLs are relative: both `https://account.github.io/manuale/` and a custom
domain work. Query-string deep links reload without a SPA routing fallback.
The service worker and its caches are scoped to the repository's path.

## Offline and installation

On iOS, open the HTTPS site in Safari and choose **Share → Add to Home
Screen**. On Android, use the browser's **Install app** menu. The download
button shows exactly which dates are saved. Open or download the dates you
need before leaving the network; opening one date saves all its hours and
supported Masses. The app itself is cached separately.

HTTPS is required for installation and offline storage; `localhost` is the
development exception. A plain HTTP LAN address is useful for viewing but
cannot provide the same offline guarantees. Browser storage can be evicted;
downloads request persistent storage when supported. There is no claim that
installing the app downloads the entire calendar. A modern browser with
`DecompressionStream` support is required.

## Liturgical scope and provenance

Text and calendar: [Divinum Officium](https://github.com/DivinumOfficium/divinum-officium),
MIT-licensed, at the revision in `sources.json`. `Rubrics 1960 - 1960` is the
engine's name for the rubrics used by the 1962 books. English fallback files
are required by the engine; both output languages are fixed to Latin.

This uses the **general Roman calendar**, not a particular local calendar.
Research notes, source links and the exact text adaptations are recorded in
[docs/sources.md](docs/sources.md).

Votives use the engine's supported forms. The picker is a way to follow the
Mass being celebrated, not a ruling that every selection is permissible on
every date. It doesn't express every rank, external solemnity, local proper,
dedication, votive intention, or combination of additional collects.

The faint colour accents are decorative cues derived from the rite's title,
with overrides for the supported votives. They do not determine the texts
or assert a local vestment ruling. Marian feasts use a warm white/gold accent,
not blue. Rubrics, response markers and crosses share the same readable
accent; prayer text remains neutral.

The Mass export omits the Communion-of-the-faithful popup. The importer
expands it in place, using the source's Communion text from *Ecce Agnus Dei*
onwards (without the second Confiteor). Latin rubrics and references are
retained; turning rubrics off is a display preference. The ordinary ends at
the Last Gospel where prescribed. Low Mass exports also include the
Leonine prayers supplied by the source. Benediction is not yet included.

Special Holy Week rites come from the engine's own full-text forms.
Christmas and All Souls have their three Masses selectable. Sung mode shows
the solemn ritual, including the deacon and subdeacon; it is not a separate
rubrical reconstruction of every local missa cantata practice.

## How this was made

Manuale was built with AI assistance. Both **OpenAI GPT models** and
**Anthropic Claude models** were used to write the application code, the build
tooling, the tests and this documentation, under human direction and review.

That assistance stops at the liturgical text, and the design of this project
exists mostly to keep it stopped. Every prayer, rubric, antiphon and calendar
decision is taken verbatim from Divinum Officium at the revision pinned in
`sources.json`, rendered by that project's own Perl. **No prayer, rubric or
translation in this app was generated, paraphrased, completed or reordered by
a language model.** The importer's only job is to carry that text across
without altering it.

The safeguards are checkable rather than promised:

- The single deliberate correction to the source is recorded in
  `source_patches.json` with an exact before/after string, and the build
  aborts if it becomes ambiguous or stops applying.
- The importer refuses to turn an error page, a truncated render or an empty
  section into a prayer; those are tests, not comments.
- Generated day packs are hashed, and the hash covers the importer itself, so
  changing the importer invalidates every pack rather than silently reusing it.
- The corpus is redownloadable from upstream and diffable against it.

If you find text in this app that does not match Divinum Officium at the
pinned revision, that is a bug, and a serious one.

## Checks and maintenance

```sh
nix develop --command make test
nix develop --command make build
```

The tests check the data hashes and completeness, the actual Mass sequence,
consecration and Communion text, sample Sunday readings, seasonal omissions,
the corrected Rosary Gospel, Office variants, Christmas Masses and browser
state boundaries. Browser QA uses the `agent-browser` CLI; findings live in
[docs/verification.md](docs/verification.md).

To change the corpus, update the pinned revision in `sources.json`, review
`source_patches.json`, fetch into a fresh `vendor/divinum-officium` checkout,
then regenerate. Corrections have an exact before/after boundary and fail
loudly if they no longer apply. Changing the importer invalidates generated
packs. Do not turn a missing source text into an empty prayer.
