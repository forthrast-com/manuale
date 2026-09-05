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
