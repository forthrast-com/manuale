# verification

Local checks, 5 September 2026. Browser checks use agent-browser with Chrome;
this is not a claim of physical-device or liturgical certification.

## Automated

- Python import/calendar tests and Node's browser-state utility tests pass.
- All 730 generated dates for 2026–2027 have valid SHA-256 hashes, every
  supported rite and non-empty section lists. Special multi-Mass days are
  included. The build refuses an index that doesn't match its day packs.
- Regression checks cover the Mass sequence, consecration, people's Communion,
  Passion Sunday omissions, Sunday readings, Rosary Gospel reference, votives,
  Christmas Masses, private/choral Office and hostile source markup.
- State checks cover UTC+10 local dates, invalid routes/preferences,
  scrolling by default, migration from the initial implicit pagination
  preference and decorative liturgical colours.
- JS module syntax checks pass. Font files match their documented upstream
  Git blobs; both licences are bundled and included in the build.

## Browser

- Continuous reading scrolls the document, not a fixed inner panel. The
  masthead leaves the viewport; a narrow running footer keeps the index handy.
- Reload restores the same passage. Index → Canon jumps to its heading;
  the running footer returns to the top. Optional pagination still turns.
- Mobile 390 × 844 checked at normal and maximum reading size, without
  horizontal overflow. The desktop Office layout was also inspected.
- IM FELL English regular and italic are loaded locally. Fraunces supplies
  display headings. No Google Fonts request is needed at runtime.
- OLED mode computes to rgb(0, 0, 0), including the browser theme colour.
  Rubrics, response marks and crosses have identical computed accent colours.
- The calendar colours only each day's number and weekday, with neutral feast
  names. Mixed green/white days were checked individually in the rendered DOM.
- The Manuale name fits a 320px phone layout without horizontal overflow.
- Reading sizes now run from 80% to 140%. The 80% setting was checked at
  16px on mobile and persisted unchanged through a reload.
- A saved week was downloaded, the browser taken offline, and a different
  saved Sunday reopened and reloaded successfully, including both font faces.
- Sunday Mass uses green; the Requiem override uses graphite; switching from
  the Requiem to the Office restores the calendar's colour and text.
- No uncaught app errors were observed in these checks.

Screenshots and DOM probes remain in the ignored project-local scratch/
directory. The first attempted off-screen index click needed an explicit
scroll-into-view in the automation tool; the visible control worked correctly.

## Audit round, 5 September 2026

- The precache manifest no longer contains incidental dotfiles. `cache.addAll`
  is all-or-nothing, so a stray `.DS_Store` that vanished between build and
  deploy would have cost the entire offline shell silently.
- `dist/` is rebuilt rather than appended to, and day packs dropped from the
  index are removed instead of lingering as unreachable files.
- Downloading a week saves seven packs; clearing removes exactly those and
  leaves the app shell cached, so the app still opens offline afterwards.
- A planted pack under a superseded `?v=` hash and one for a date outside the
  calendar were both reclaimed on the next load; the current day's pack and
  its reading position survived. Reading-position keys are pruned against the
  published calendar window rather than accumulating for the life of the origin.
- Requesting a download from a date outside the calendar reports that plainly
  instead of printing `NaN`, and re-enables both buttons.
- With the local server stopped, a deep link to a saved day's Vespers rendered
  from cache: 6 sections, 138 blocks, both Fell faces and Fraunces loaded.

## Reading and calendar round, 5 September 2026

- Source-location notes ({ex Proprio de Tempore} and its kin, 208 in a sample)
  now carry their own kind rather than passing as rubrics, and stay out of the
  reading. A section left with nothing visible is hidden with them, so a vigil's
  "Gloria — omit." no longer shows a heading standing over silence.
- The propers filter matches the sections a printed propers sheet carries:
  introit, collect, epistle, gradual, gospel, offertory, secret, preface,
  communion, postcommunion. Checked against all 55 distinct Mass section titles
  in the corpus. Communio is proper where Communio fidelium and Communio Populi
  are not, and Evangelium where Ultimum Evangelium is not.
- Sollemnis, Lecta and Propria share one menu; the solemn or low Mass chosen
  underneath is remembered, and a place saved in the propers is keyed apart
  from a place in the whole Mass.
- The calendar keeps its list of nearby days and gains a full month behind a
  button. Both colour the day by its rite and set Sundays and first-class
  feasts in bold. Typed dates commit only on submit; a partial value navigates
  nowhere.
- Weekday heads read Sol, Lun, Mar, Mer, Iov, Ven, Sat. The planetary symbols
  were measured against both bundled fonts and are in neither, so they would
  have borrowed glyphs from the system and risked colour emoji on Apple devices.
- Liturgical colour was checked across all 730 days: 348 white, 140 violet,
  126 green, 112 red, 4 black. Red reaching only 15% of days is why a nine-day
  window can show none; the month view makes the distribution visible.

## Palette, 5 September 2026

- Every value was measured rather than chosen by eye. On cream #f8f5ed: green
  #175f42 at 7.00:1, red #a82715 at 6.50:1, violet #5f1c5e at 10.62:1, black
  #3b332a at 11.39:1, gold #7f5e0c at 5.49:1, lapis #1f4b8f at 7.83:1.
- The chrome sits on #e6e1d4, which is a lower surface than the paper, so both
  --muted and gold were darkened until they clear 4.5:1 there too: 3.88 -> 4.87
  and 3.80 -> 4.58. Nothing in the interface sits below AA on either surface.
- Ink moved to #1c1a17. The old #28251f was hue 40° at 22% saturation, which is
  why the wordmark read brown rather than black.
- Bright gold #c8971b measures 2.44:1 and fails even the 3:1 ornament floor. It
  is not used as a text colour anywhere; gold that is read is #7f5e0c.
- Dark mode keeps a true #000000 reading surface. Only the masthead and footer
  lift to #0e0d0c, so the OLED benefit over the large area is unchanged. The
  dark accents run 7.08:1 to 12.04:1 on black.
- Vellum was tried and rejected: at 12% saturation it read as beige, and it
  also cost contrast. Bright vermilion clears the text floor on cream (4.91:1)
  and does not on vellum (4.47:1), so the lighter ground is the more vivid one.

## Calendar dialog, 5 September 2026

- Aiming and choosing are now separate. Hodie and Ad diem move the list to a
  day and put the focus on it; only pressing a day in the list opens it and
  closes the dialog. Checked: submitting 2027-03-14 leaves the dialog open,
  moves the list to 12-20 March, focuses the 14th, and leaves the reading view
  untouched. Pressing that entry then navigates and closes.
- The date field keeps its caret. Editing mid-value holds position, deleting
  into a separator does not fling to the end, and typing forward steps
  2027 at 4 to 2027-0 at 6, stepping over the separator it just inserted.
- One status line carries either the available range or the complaint, so
  nothing below it moves when an entry is refused.
- Today is marked apart from the day being aimed at and the day being read.

## Boundaries

- Actual iOS/Android installation, physical swipe behaviour and wake-lock
  battery behaviour have not been tested on hardware.
- Rebuilding with a changed importer changes every pack hash, so the next
  online load now deletes previously downloaded days rather than orphaning
  them. They were already unusable; the deletion is visible where the leak
  was not.
- No GitHub repository or Pages deployment has been created. The static
  build and Pages workflow are ready for the user's repository.
- General-calendar and supported-votive coverage does not imply complete
  local propers or every rubrical combination.
- Renaming the app keeps its original internal browser-storage namespaces,
  so existing downloads and reading positions survive at the same origin/path.
  Moving a hosted site to another URL does not transfer browser storage.
