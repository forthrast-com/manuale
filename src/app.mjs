import { hours, dateKey, validDate, dateLabel, weekday, addDays, parseRoute, validatePreferences, storageRead, storageWrite, storagePrune, escapeHtml, liturgicalAccent } from './core.mjs';
import { loadIndex, loadDay, savedDays, forgetDays, pruneDays, registerWorker } from './offline.mjs';
import { Reader } from './reader.mjs';

const $ = id => document.getElementById(id);
const preferences = validatePreferences(storageRead('preferences', {}));
history.scrollRestoration = 'manual';
let route = parseRoute(location.search);
let calendar;
let payload;
let request;
let currentKey;
let massNumber = '1';
let currentSaved = false;
let downloading = false;
let workerReady = false;
let installPrompt;
let wakeLock;
let toastTimer;
let saveTimer;

function notify(message) {
  $('toast').textContent = message;
  $('toast').hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $('toast').hidden = true; }, 4500);
}

function applyPreferences() {
  document.documentElement.dataset.theme = preferences.theme;
  document.documentElement.dataset.rubrics = String(preferences.rubrics);
  document.documentElement.style.setProperty('--font-scale', String(preferences.fontSize));
  $('theme').value = preferences.theme;
  $('layout').value = preferences.layout;
  $('font-size').value = String(preferences.fontSize);
  $('show-rubrics').checked = preferences.rubrics;
  $('keep-awake').checked = preferences.awake;
  $('mass-type').value = preferences.massType;
  $('office-type').value = preferences.officeType;
  const dark = preferences.theme === 'dark' || (preferences.theme === 'auto' && matchMedia('(prefers-color-scheme: dark)').matches);
  document.querySelector('meta[name="theme-color"]').content = dark ? '#000000' : '#f8f5ed';
}

applyPreferences();
const reader = new Reader($('reading'), $('flow'), state => {
  if (!state.section) return;
  $('current-section').textContent = state.section.title;
  $('page-count').textContent = state.mode === 'pages' ? `${state.page + 1} / ${state.total}` : 'Index';
  $('previous-page').disabled = state.mode === 'pages' ? state.page === 0 : window.scrollY < 1;
  $('next-page').disabled = state.mode === 'pages' ? state.page >= state.total - 1 : state.progress >= .999;
  $('progress-fill').style.width = `${state.progress * 100}%`;
  document.querySelectorAll('.toc-entry').forEach(button => button.setAttribute('aria-current', String(button.dataset.section === state.section.id)));
  clearTimeout(saveTimer);
  const key = currentKey;
  saveTimer = setTimeout(() => { if (key) storageWrite(`position:${key}`, state.position); }, 160);
});
reader.configure(preferences.layout);
document.fonts.ready.then(() => reader.scheduleLayout());

function flushPosition() {
  clearTimeout(saveTimer);
  if (currentKey && reader.sections.length) storageWrite(`position:${currentKey}`, reader.capture());
}

function openDialog(id) {
  const dialog = $(id);
  if (!dialog.open) dialog.showModal();
}

function riteKey() {
  if (route.office === 'Missa') return `${preferences.massType === 'lecta' ? 'MissaLecta' : 'Missa'}${route.votive ? `-${route.votive}` : massNumber === '1' ? '' : massNumber}`;
  return `${route.office}${preferences.officeType === 'choro' ? 'Choro' : ''}`;
}

function renderRite() {
  const rite = payload?.rites[riteKey()];
  if (!rite) { showError('Hic ritus non invenitur.'); return; }
  const mass = route.office === 'Missa';
  const name = mass ? 'Ordo Missæ' : route.office === 'Vespera' ? 'Ad Vesperas' : route.office;
  document.documentElement.dataset.liturgicalColour = liturgicalAccent(rite.title, mass ? route.votive : '');
  $('day-title').textContent = mass && route.votive ? calendar.votives[route.votive] : rite.title;
  $('day-rank').textContent = `${mass && route.votive ? 'Missa votiva' : rite.rank || 'Calendarium Romanum'} · ${mass ? 'MISSALE' : 'BREVIARIUM'} · 1962`;
  $('index-name').textContent = name;
  $('toc-title').textContent = name;
  $('mass-button').setAttribute('aria-pressed', String(mass));
  $('office-button').setAttribute('aria-pressed', String(!mass));
  $('hour-select').hidden = mass;
  $('mass-type').hidden = !mass;
  $('office-type').hidden = mass;
  $('votive-select').hidden = !mass;
  $('votive-select').innerHTML = '<option value="">De die</option>' + Object.entries(calendar.votives ?? {}).map(([code, title]) => `<option value="${code}">${escapeHtml(title)}</option>`).join('');
  $('votive-select').value = route.votive;
  $('mass-number').hidden = !mass || Boolean(route.votive) || !payload.rites.Missa2;
  $('mass-number').value = massNumber;
  if (!mass) $('hour-select').value = route.office;
  currentKey = `${route.day}:${riteKey()}`;
  const entries = rite.sections.map((section, index) => `<button class="toc-entry" data-section="${section.id}" aria-current="false"><span aria-hidden="true">${String(index + 1).padStart(2, '0')}</span><span>${escapeHtml(section.title)}</span></button>`).join('');
  $('desktop-toc').innerHTML = entries;
  $('mobile-toc').innerHTML = entries;
  document.title = `${name} · ${dateLabel(route.day)} · Manuale`;
  $('reading-message').hidden = true;
  $('flow').hidden = false;
  $('reading').setAttribute('aria-busy', 'false');
  reader.render(rite, storageRead(`position:${currentKey}`, null));
}

function showError(message) {
  $('day-title').textContent = calendar?.days[route.day]?.title ?? dateLabel(route.day);
  $('day-rank').textContent = 'CALENDARIUM ROMANUM · 1962';
  $('flow').hidden = true;
  $('reading-message').hidden = false;
  $('reading-message').replaceChildren();
  const text = document.createElement('p');
  text.textContent = message;
  const retry = document.createElement('button');
  retry.className = 'solid-button';
  retry.textContent = 'Iterum conare';
  retry.addEventListener('click', () => navigate(route.day, route.office, false));
  const dates = document.createElement('button');
  dates.className = 'outline-button';
  dates.textContent = 'Elige diem';
  dates.addEventListener('click', showCalendar);
  $('reading-message').append(text, retry, dates);
  $('reading').setAttribute('aria-busy', 'false');
  $('previous-page').disabled = true;
  $('next-page').disabled = true;
  $('saved-indicator').hidden = true;
  $('page-count').textContent = 'Index';
  $('desktop-toc').replaceChildren();
  $('mobile-toc').replaceChildren();
  reader.sections = [];
  currentKey = null;
}

async function navigate(day, office = route.office, push = true) {
  flushPosition();
  currentKey = null;
  reader.sections = [];
  $('previous-page').disabled = true;
  $('next-page').disabled = true;
  if (day !== route.day) massNumber = '1';
  route = { day, office, votive: route.votive };
  $('date-label').textContent = dateLabel(day, innerWidth > 520);
  if (push) history.pushState(null, '', `?dies=${day}&hora=${office}${route.votive ? `&votiva=${route.votive}` : ''}`);
  request?.abort();
  request = new AbortController();
  const activeRequest = request;
  $('flow').hidden = true;
  $('reading-message').hidden = false;
  $('reading-message').innerHTML = '<p>Textus parantur…</p>';
  $('reading').setAttribute('aria-busy', 'true');
  currentSaved = false;
  try {
    if (!calendar) {
      calendar = await loadIndex();
      reconcileStorage();
    }
    const result = await loadDay(day, calendar, { signal: activeRequest.signal });
    if (activeRequest !== request) return;
    payload = result.payload;
    currentSaved = result.saved;
    $('saved-indicator').hidden = !currentSaved;
    renderRite();
    $('announcement').textContent = `${payload.rites[riteKey()].title}. ${office}.`;
  } catch (error) {
    if (error.name === 'AbortError' || activeRequest !== request) return;
    payload = null;
    showError(error.message || 'Textus accipi non potuit.');
    console.error('Manuale:', error);
  }
}

function reconcileStorage() {
  // Days that have rolled out of the published calendar can keep neither a
  // downloaded pack nor a saved reading position.
  pruneDays(calendar).catch(error => console.warn('Manuale prune:', error));
  storagePrune('position:', key => Boolean(calendar.days[key.slice(0, 10)]));
}

function showCalendar() {
  $('date-input').value = route.day;
  const days = Object.keys(calendar?.days ?? {}).sort();
  $('date-input').min = days[0] ?? '';
  $('date-input').max = days.at(-1) ?? '';
  $('date-range').textContent = days.length ? `${dateLabel(days[0])} — ${dateLabel(days.at(-1))}` : 'Calendarium accipi non potuit.';
  const nearby = days.filter(day => day >= addDays(route.day, -2) && day <= addDays(route.day, 6));
  const shown = nearby.length ? nearby : days.slice(0, 7);
  $('calendar-days').innerHTML = shown.map(day => `<button class="calendar-day" data-day="${day}" aria-current="${day === route.day ? 'date' : 'false'}"><time datetime="${day}" data-liturgical-colour="${liturgicalAccent(calendar.days[day].title)}">${Number(day.slice(-2))}<small>${weekday(day)}</small></time><span>${escapeHtml(calendar.days[day].title)}<span class="small-note">${escapeHtml(calendar.days[day].rank)}</span></span></button>`).join('');
  $('previous-day').disabled = !calendar?.days[addDays(route.day, -1)];
  $('next-day').disabled = !calendar?.days[addDays(route.day, 1)];
  openDialog('calendar-dialog');
}

async function refreshOffline() {
  if (!calendar) return;
  const saved = await savedDays(calendar);
  $('offline-status').textContent = `${saved.length} dies servati.${workerReady ? ' Manuale sine interrete aperiri potest.' : ' Applicatio ad usum sine interrete paratur…'}`;
  $('saved-days').innerHTML = saved.map(day => `<button class="saved-day" data-day="${day}">${dateLabel(day)} <span aria-hidden="true">↗</span></button>`).join('');
  $('saved-indicator').hidden = !saved.includes(route.day);
}

async function downloadDays(count) {
  if (downloading || !calendar) return;
  downloading = true;
  $('save-week').disabled = $('save-month').disabled = true;
  const days = Array.from({ length: count }, (_, i) => addDays(route.day, i)).filter(day => calendar.days[day]);
  if (!days.length) {
    $('download-status').textContent = 'Nulli dies ex hoc die in libro continentur.';
    downloading = false;
    $('save-week').disabled = $('save-month').disabled = false;
    return;
  }
  $('download-progress').hidden = false;
  $('download-progress').max = Math.max(1, days.length);
  $('download-progress').value = 0;
  let completed = 0;
  try {
    for (const day of days) {
      $('download-status').textContent = `${completed} / ${days.length} · ${dateLabel(day, false)}`;
      const result = await loadDay(day, calendar);
      if (!result.saved) throw new Error('Dies servari non potest. Spatium navigatoris inspice.');
      completed += 1;
      $('download-progress').value = completed;
    }
    $('download-status').textContent = `${completed} dies servati: ${dateLabel(days[0], false)} — ${dateLabel(days.at(-1))}.`;
    if (navigator.storage?.persist) await navigator.storage.persist();
  } catch (error) {
    $('download-status').textContent = `${completed} / ${days.length} dies servati. ${error.message}`;
  } finally {
    downloading = false;
    $('save-week').disabled = $('save-month').disabled = false;
    await refreshOffline();
  }
}

async function updateWakeLock() {
  if (!preferences.awake || document.visibilityState !== 'visible') {
    await wakeLock?.release();
    wakeLock = null;
    return;
  }
  if (!('wakeLock' in navigator)) {
    $('wake-status').hidden = false;
    $('wake-status').textContent = 'Hic navigator scrinium accensum retinere non potest.';
    return;
  }
  try {
    wakeLock = await navigator.wakeLock.request('screen');
    $('wake-status').hidden = true;
  } catch (error) {
    if (!['NotAllowedError', 'AbortError'].includes(error.name)) throw error;
    $('wake-status').hidden = false;
    $('wake-status').textContent = 'Scrinium accensum retineri non potuit; modum energiæ inspice.';
  }
}

document.querySelectorAll('dialog').forEach(dialog => {
  dialog.querySelector('[data-close]').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  });
});

$('date-button').addEventListener('click', showCalendar);
$('settings-button').addEventListener('click', () => openDialog('settings-dialog'));
$('sources-button').addEventListener('click', () => openDialog('settings-dialog'));
$('index-button').addEventListener('click', () => { if (payload) openDialog('index-dialog'); });
$('offline-button').addEventListener('click', () => { openDialog('offline-dialog'); refreshOffline(); });
$('previous-page').addEventListener('click', () => reader.turn(-1));
$('next-page').addEventListener('click', () => reader.turn(1));
$('top-button').addEventListener('click', () => {
  window.scrollTo({ top: 0, behavior: 'instant' });
  $('date-button').focus({ preventScroll: true });
});
$('mass-button').addEventListener('click', () => navigate(route.day, 'Missa'));
$('office-button').addEventListener('click', () => {
  const last = storageRead('lastHour', 'Vespera');
  navigate(route.day, hours.includes(last) ? last : 'Vespera');
});
$('hour-select').addEventListener('change', event => { storageWrite('lastHour', event.target.value); navigate(route.day, event.target.value); });
$('mass-number').addEventListener('change', event => { flushPosition(); massNumber = event.target.value; renderRite(); });
$('votive-select').addEventListener('change', event => { flushPosition(); route.votive = event.target.value; history.pushState(null, '', `?dies=${route.day}&hora=Missa${route.votive ? `&votiva=${route.votive}` : ''}`); renderRite(); });

for (const id of ['desktop-toc', 'mobile-toc']) {
  $(id).addEventListener('click', event => {
    const button = event.target.closest('[data-section]');
    if (!button) return;
    if ($('index-dialog').open) $('index-dialog').close();
    reader.goTo(button.dataset.section);
  });
}

for (const id of ['calendar-days', 'saved-days']) {
  $(id).addEventListener('click', event => {
    const day = event.target.closest('[data-day]')?.dataset.day;
    if (!day) return;
    document.querySelectorAll('dialog[open]').forEach(dialog => dialog.close());
    navigate(day);
  });
}
$('date-input').addEventListener('change', event => {
  if (!validDate(event.target.value)) return;
  $('calendar-dialog').close();
  navigate(event.target.value);
});
$('today-button').addEventListener('click', () => { $('calendar-dialog').close(); navigate(dateKey()); });
for (const [id, delta] of [['previous-day', -1], ['next-day', 1]]) {
  $(id).addEventListener('click', () => { navigate(addDays(route.day, delta)); showCalendar(); });
}

for (const [id, key] of [['theme', 'theme'], ['layout', 'layout'], ['font-size', 'fontSize'], ['show-rubrics', 'rubrics'], ['keep-awake', 'awake'], ['mass-type', 'massType'], ['office-type', 'officeType']]) {
  $(id).addEventListener('change', event => {
    flushPosition();
    reader.anchor = reader.capture();
    preferences[key] = event.target.type === 'checkbox' ? event.target.checked : key === 'fontSize' ? Number(event.target.value) : event.target.value;
    storageWrite('preferences', preferences);
    if (key === 'layout') reader.configure(preferences.layout);
    applyPreferences();
    if (['massType', 'officeType'].includes(key) && payload) renderRite();
    else reader.scheduleLayout();
    if (key === 'awake') updateWakeLock();
  });
}

$('forget-days').addEventListener('click', async () => {
  $('forget-days').disabled = true;
  try {
    const removed = await forgetDays();
    $('download-status').textContent = removed ? `${removed} dies deleti.` : 'Nulli dies servati erant.';
  } catch (error) {
    $('download-status').textContent = 'Dies deleri non potuerunt.';
    console.warn('Manuale forget:', error);
  } finally {
    $('forget-days').disabled = false;
    currentSaved = false;
    await refreshOffline();
  }
});
$('save-week').addEventListener('click', () => downloadDays(7));
$('save-month').addEventListener('click', () => downloadDays(30));
window.addEventListener('popstate', () => { const next = parseRoute(location.search); route.votive = next.votive; navigate(next.day, next.office, false); });
window.addEventListener('pagehide', flushPosition);
document.addEventListener('visibilitychange', () => { flushPosition(); updateWakeLock(); });
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyPreferences);
window.addEventListener('resize', () => { $('date-label').textContent = dateLabel(route.day, innerWidth > 520); });
window.addEventListener('keydown', event => {
  if (document.querySelector('dialog[open]') || event.altKey || event.metaKey || event.ctrlKey) return;
  if (event.target.matches('input, select, textarea, button, a, [contenteditable]')) return;
  const delta = ['ArrowRight', 'PageDown', ' '].includes(event.key) ? 1 : ['ArrowLeft', 'PageUp'].includes(event.key) ? -1 : 0;
  if (delta) { event.preventDefault(); reader.turn(event.shiftKey && event.key === ' ' ? -1 : delta); }
});
window.addEventListener('beforeinstallprompt', event => {
  event.preventDefault();
  installPrompt = event;
  $('install-button').hidden = false;
});
$('install-button').addEventListener('click', async () => {
  if (!installPrompt) return;
  await installPrompt.prompt();
  installPrompt = null;
  $('install-button').hidden = true;
});
window.addEventListener('offline', () => { notify(currentSaved ? 'Dies servatus · sine interrete.' : 'Sine interrete.'); });

registerWorker().then(ready => { workerReady = ready; if ($('offline-dialog').open) refreshOffline(); }).catch(error => {
  console.warn('Manuale offline:', error);
  $('offline-status').textContent = 'Applicatio servari non potuit. Reaperi Manuale cum interrete.';
});
if ('serviceWorker' in navigator) navigator.serviceWorker.addEventListener('controllerchange', async () => {
  try { calendar = await loadIndex(); }
  catch (error) { console.warn('Manuale calendar update:', error); }
});
updateWakeLock();
navigate(route.day, route.office, false);
