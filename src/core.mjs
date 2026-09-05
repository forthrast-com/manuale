export const hours = ['Matutinum', 'Laudes', 'Prima', 'Tertia', 'Sexta', 'Nona', 'Vespera', 'Completorium'];
export const votives = ['C11', 'C9', 'V4', 'V6', 'Propaganda'];
const months = ['Ianuarii', 'Februarii', 'Martii', 'Aprilis', 'Maii', 'Iunii', 'Iulii', 'Augusti', 'Septembris', 'Octobris', 'Novembris', 'Decembris'];
const weekdays = ['Dom.', 'Fer. II', 'Fer. III', 'Fer. IV', 'Fer. V', 'Fer. VI', 'Sabb.'];

export function dateKey(date = new Date()) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

export function validDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value ?? '')) return false;
  const day = new Date(`${value}T12:00:00`);
  return Number.isFinite(day.getTime()) && dateKey(day) === value;
}

export function addDays(value, offset) {
  const day = new Date(`${value}T12:00:00`);
  day.setDate(day.getDate() + offset);
  return dateKey(day);
}

export function dateLabel(value, year = true) {
  const day = new Date(`${value}T12:00:00`);
  return `${day.getDate()} ${months[day.getMonth()]}${year ? ` ${day.getFullYear()}` : ''}`;
}

export function weekday(value) { return weekdays[new Date(`${value}T12:00:00`).getDay()]; }
export function clamp(value, min, max) { return Math.max(min, Math.min(max, value)); }
export function escapeHtml(value) { return String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]); }

export function parseRoute(search) {
  const params = new URLSearchParams(search);
  return { day: validDate(params.get('dies')) ? params.get('dies') : dateKey(),
    office: hours.includes(params.get('hora')) ? params.get('hora') : 'Missa',
    votive: votives.includes(params.get('votiva')) ? params.get('votiva') : '' };
}

export function validatePreferences(value = {}) {
  return {
    theme: ['auto', 'light', 'dark'].includes(value.theme) ? value.theme : 'auto',
    // The first edition saved pagination even when it was never chosen.
    layout: value.layoutVersion === 2 && value.layout === 'pages' ? 'pages' : 'scroll',
    layoutVersion: 2,
    fontSize: [.8, .9, 1, 1.2, 1.4].includes(Number(value.fontSize)) ? Number(value.fontSize) : 1,
    rubrics: value.rubrics !== false,
    massType: value.massType === 'lecta' ? 'lecta' : 'cantata',
    officeType: value.officeType === 'choro' ? 'choro' : 'privatim',
    awake: value.awake === true,
  };
}

export function storageRead(key, fallback) {
  // Keep the first edition's namespace when rebranding: bookmarks survive.
  try { return JSON.parse(localStorage.getItem(`preces:${key}`)) ?? fallback; }
  catch (error) {
    if (error instanceof SyntaxError || error.name === 'SecurityError') return fallback;
    throw error;
  }
}

export function liturgicalAccent(title, votive = '') {
  // A decorative cue, adapted from Divinum Officium's title colouring.
  // It does not determine texts or claim to settle local vestment rubrics.
  const votiveColours = { C11: 'white', C9: 'black', V4: 'white', V6: 'red', Propaganda: 'violet' };
  if (votiveColours[votive]) return votiveColours[votive];
  const name = String(title).normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/æ/g, 'ae').toLowerCase();
  if (/(?:defunctor|parasceve|morte)/.test(name)) return 'black';
  if (/(?:beat|sanct)(?:ae|a) mari|b\.\s*m\.\s*v\./.test(name) && !/vigil/.test(name)) return 'white';
  if (/vigilia pentecostes|quattuor temporum pentecostes|decollatione|martyr|reliquia/.test(name)) return 'red';
  if (/^in vigilia (?:ascensionis|epiphaniae)/.test(name)) return 'white';
  if (/vigilia|quattuor|rogatio|passion|palmis|gesim|hebdomadae (?:majoris|sanctae)|sabbato sancto|ciner|adventus/.test(name) && !/commemoratione|votivum/.test(name)) return 'violet';
  if (/conversione|dedicatione|cathedra|joann|ioann|pasch|confessor|ascensio|cena/.test(name)) return 'white';
  if (/pentecosten(?!.*infra octavam)|epiphaniam|post octavam/.test(name)) return 'green';
  if (/pentecostes|evangel|innocentium|sanguinis|cruc|apostol/.test(name)) return 'red';
  return 'white';
}

export function storagePrune(prefix, keep) {
  // Reading positions outlive the calendar window they belong to; one key per
  // day and rite would otherwise accumulate for as long as the origin lives.
  const scoped = `preces:${prefix}`;
  try {
    const doomed = [];
    for (let index = 0; index < localStorage.length; index += 1) {
      const key = localStorage.key(index);
      if (key?.startsWith(scoped) && !keep(key.slice(scoped.length))) doomed.push(key);
    }
    for (const key of doomed) localStorage.removeItem(key);
    return doomed.length;
  } catch (error) {
    if (error.name === 'SecurityError') return 0;
    throw error;
  }
}

export function storageWrite(key, value) {
  try { localStorage.setItem(`preces:${key}`, JSON.stringify(value)); return true; }
  catch (error) {
    if (['SecurityError', 'QuotaExceededError'].includes(error.name)) return false;
    throw error;
  }
}
