import test from 'node:test';
import assert from 'node:assert/strict';
import { dateKey, validDate, addDays, weekday, weekdayFull, isSunday, roman, monthGrid, monthLabel, addMonths, isFirstClass, parseRoute, validatePreferences, liturgicalAccent, escapeHtml, storagePrune, isProperSection } from '../src/core.mjs';

test('local dates do not shift to yesterday east of UTC', () => {
  assert.equal(dateKey(new Date(2026, 8, 5, 0, 5)), '2026-09-05');
});
test('date validation rejects rollover and malformed deep links', () => {
  assert.equal(validDate('2026-02-29'), false);
  assert.equal(validDate('2028-02-29'), true);
  assert.equal(validDate('2026-13-01'), false);
  assert.equal(validDate('../index'), false);
});
test('day arithmetic crosses years and leap days', () => {
  assert.equal(addDays('2026-12-31', 1), '2027-01-01');
  assert.equal(addDays('2028-03-01', -1), '2028-02-29');
});
test('routes restore the selected votive and reject unknown rites', () => {
  assert.deepEqual(parseRoute('?dies=2026-09-05&hora=Missa&votiva=C9'), { day: '2026-09-05', office: 'Missa', votive: 'C9' });
  assert.deepEqual(parseRoute('?dies=2026-09-05&hora=Vespera'), { day: '2026-09-05', office: 'Vespera', votive: '' });
  assert.equal(parseRoute('?hora=bogus&votiva=../../bad').votive, '');
});
test('corrupt preferences cannot break the reader layout', () => {
  const prefs = validatePreferences({ layout: 'nonsense', fontSize: -20, theme: '<script>', massType: 'lecta' });
  assert.equal(prefs.fontSize, 1);
  assert.equal(prefs.layout, 'scroll');
  assert.equal(prefs.theme, 'auto');
  assert.equal(prefs.massType, 'lecta');
});
test('labels are escaped at the HTML boundary', () => {
  assert.equal(escapeHtml('<script>"&\''), '&lt;script&gt;&quot;&amp;&#39;');
});
test('continuous reading is the default, including old implicit page preferences', () => {
  assert.equal(validatePreferences().layout, 'scroll');
  assert.equal(validatePreferences({ layout: 'pages', theme: 'dark' }).layout, 'scroll');
  assert.equal(validatePreferences({ layout: 'pages', layoutVersion: 2 }).layout, 'pages');
});
test('the two smaller text sizes survive preference restoration', () => {
  assert.equal(validatePreferences({ fontSize: '0.8' }).fontSize, .8);
  assert.equal(validatePreferences({ fontSize: .9 }).fontSize, .9);
  assert.equal(validatePreferences({ fontSize: .2 }).fontSize, 1);
});
test('decorative accents follow the rite, with votive overrides', () => {
  const cases = [
    ['Dominica XV Post Pentecosten', 'green'],
    ['Dominica III post Epiphaniam', 'green'],
    ['Dominica I Adventus', 'violet'],
    ['Dominica Passionis', 'violet'],
    ['Dominica Resurrectionis', 'white'],
    ['Dominica Pentecostes', 'red'],
    ['S. Laurentii Martyris', 'red'],
    ['S. Laurentii Justiniani Episcopi et Confessoris', 'white'],
    ['Sanctæ Mariæ ad Nives', 'white'],
    ['In Commemoratione Omnium Fidelium Defunctorum', 'black'],
    ['Feria VI in Parasceve', 'black'],
  ];
  for (const [title, colour] of cases) assert.equal(liturgicalAccent(title), colour, title);
  assert.equal(liturgicalAccent('Dominica XV Post Pentecosten', 'C9'), 'black');
  assert.equal(liturgicalAccent('Dominica XV Post Pentecosten', 'C11'), 'white');
  assert.equal(liturgicalAccent('De Passione Domini', 'V6'), 'red');
});
test('reading positions outside the calendar window are pruned, nothing else', () => {
  const store = new Map([
    ['preces:position:2026-01-01:Missa', '{}'],
    ['preces:position:2026-01-01:Vespera', '{}'],
    ['preces:position:2027-06-30:Missa', '{}'],
    ['preces:preferences', '{}'],
    ['preces:lastHour', '"Vespera"'],
    ['unrelated-origin-key', '{}'],
  ]);
  globalThis.localStorage = {
    get length() { return store.size; },
    key: index => [...store.keys()][index],
    removeItem: key => { store.delete(key); },
  };
  try {
    const window = { '2027-06-30': true };
    assert.equal(storagePrune('position:', key => Boolean(window[key.slice(0, 10)])), 2);
    assert.deepEqual([...store.keys()].sort(), [
      'preces:lastHour', 'preces:position:2027-06-30:Missa', 'preces:preferences', 'unrelated-origin-key',
    ]);
  } finally {
    delete globalThis.localStorage;
  }
});
test('pruning survives a browser that forbids storage', () => {
  globalThis.localStorage = { get length() { throw Object.assign(new Error('no'), { name: 'SecurityError' }); } };
  try { assert.equal(storagePrune('position:', () => true), 0); }
  finally { delete globalThis.localStorage; }
});
test('the Mass proper is exactly what a propers sheet prints', () => {
  // Introit, collect, epistle, gradual, gospel, offertory, secret, preface,
  // communion, postcommunion — per extraordinaryform.org's propers sheets.
  for (const title of ['Introitus', 'Oratio', 'Lectio', 'Epistola', 'Graduale',
    'Allel\u00faia.', 'Tractus', 'Sequentia', 'Evangelium', 'Passio', 'Offertorium',
    'Secreta', 'Pr\u00e6fatio', 'Communio', 'Postcommunio']) {
    assert.equal(isProperSection(title), true, title);
  }
});
test('the ordinary, and the near-misses, stay out of the proper', () => {
  for (const title of ['Kyrie', 'Gloria', 'Credo', 'Sanctus', 'Canon', 'Incipit',
    'Asperges me', 'Vidi aquam', 'Incensatio', 'Conclusio', 'Ablutiones',
    'Preparatio Communionis', 'Orationes Leonis XIII',
    // These three would each be caught by a sloppier prefix or substring match.
    'Communio fidelium', 'Communio Populi', 'Ultimum Evangelium']) {
    assert.equal(isProperSection(title), false, title);
  }
});
test('the whole Mass is the default view, and an odd value cannot strand the reader', () => {
  assert.equal(validatePreferences().massView, 'tota');
  assert.equal(validatePreferences({ massView: 'propria' }).massView, 'propria');
  assert.equal(validatePreferences({ massView: 'nonsense' }).massView, 'tota');
});
test('the week is named for the planets, not numbered as ferias', () => {
  // 6 September 2026 is a Sunday.
  assert.equal(weekday('2026-09-06'), 'Sol');
  assert.equal(weekdayFull('2026-09-06'), 'dies Solis');
  assert.equal(weekday('2026-09-10'), 'Iov');
  assert.equal(weekdayFull('2026-09-12'), 'dies Saturni');
  assert.equal(isSunday('2026-09-06'), true);
  assert.equal(isSunday('2026-09-05'), false);
});
test('only the first class is set in bold', () => {
  assert.equal(isFirstClass('I. classis'), true);
  for (const rank of ['II. classis', 'III. classis', 'IV. classis', '', undefined]) {
    assert.equal(isFirstClass(rank), false, String(rank));
  }
});
test('roman numerals read as the edition sets them', () => {
  assert.equal(roman(1962), 'MCMLXII');
  assert.equal(roman(2026), 'MMXXVI');
  assert.equal(roman(4), 'IV');
  assert.equal(roman(0), '');
  assert.equal(monthLabel('2026-09'), 'Septembris MMXXVI');
});
test('a month grid puts the first day under its own weekday', () => {
  const september = monthGrid('2026-09');
  assert.equal(september.length % 7, 0);
  assert.equal(september.filter(Boolean).length, 30);
  // 1 September 2026 is a Tuesday, so Sunday and Monday lead as blanks.
  assert.equal(september.findIndex(Boolean), 2);
  assert.equal(monthGrid('2026-02').filter(Boolean).length, 28);
  assert.equal(monthGrid('2028-02').filter(Boolean).length, 29);
  assert.equal(addMonths('2026-12', 1), '2027-01');
  assert.equal(addMonths('2026-01', -1), '2025-12');
});
