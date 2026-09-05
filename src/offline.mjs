const scope = new URL('./', import.meta.url);
// A display-name change must not discard previously downloaded days.
const cacheName = `preces-days-v1:${scope.pathname}`;

export class UnavailableDay extends Error {}

function packUrl(day, info) {
  return new URL(`data/days/${day}.json.gz?v=${info.sha256.slice(0, 16)}`, scope).href;
}

export async function loadIndex() {
  const response = await fetch(new URL('data/index.json', scope), { cache: 'no-cache' });
  if (!response.ok) throw new Error(`Calendarium: ${response.status}`);
  const index = await response.json();
  if (index.schema !== 1 || !index.days || !Object.keys(index.days).length) throw new Error('Calendarium invalidum');
  return index;
}

async function dayCache() {
  if (!('caches' in globalThis)) return null;
  try { return await caches.open(cacheName); }
  catch (error) {
    if (['SecurityError', 'QuotaExceededError', 'InvalidStateError', 'NotSupportedError'].includes(error.name)) return null;
    throw error;
  }
}

async function decode(response, day, info) {
  const bytes = await response.arrayBuffer();
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  const hash = Array.from(new Uint8Array(digest), value => value.toString(16).padStart(2, '0')).join('');
  if (hash !== info.sha256) throw new Error('Textus corruptus; iterum conare.');
  if (!('DecompressionStream' in globalThis)) throw new Error('Navigator recentior requiritur.');
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
  const payload = await new Response(stream).json();
  if (payload.schema !== 1 || payload.date !== day || !payload.rites?.Missa || !payload.rites?.Completorium) throw new Error('Textus incompletus.');
  return payload;
}

export async function loadDay(day, index, { signal } = {}) {
  const info = index.days[day];
  if (!info) throw new UnavailableDay('Hic dies nondum in libro continetur.');
  const url = packUrl(day, info);
  const cache = await dayCache();
  const saved = await cache?.match(url);
  if (saved) {
    try { return { payload: await decode(saved, day, info), saved: true }; }
    catch (error) {
      if (error.name === 'AbortError') throw error;
      // An invalid cached copy must not prevent a clean download.
      await cache.delete(url);
    }
  }
  let response;
  try { response = await fetch(url, { signal }); }
  catch (error) {
    if (error.name === 'AbortError') throw error;
    if (error instanceof TypeError) throw new UnavailableDay('Hic dies non est servatus. Coniunge ad interrete, vel elige diem servatum.');
    throw error;
  }
  if (!response.ok) throw new UnavailableDay('Textus huius diei accipi non potuit. Iterum conare.');
  const copy = response.clone();
  const payload = await decode(response, day, info);
  let stored = false;
  if (cache) {
    try { await cache.put(url, copy); stored = true; }
    catch (error) {
      if (!['QuotaExceededError', 'SecurityError', 'InvalidStateError'].includes(error.name)) throw error;
    }
  }
  return { payload, saved: stored };
}

export async function savedDays(index) {
  const cache = await dayCache();
  if (!cache) return [];
  const keys = new Set((await cache.keys()).map(request => request.url));
  return Object.keys(index.days).filter(day => keys.has(packUrl(day, index.days[day]))).sort();
}

export async function pruneDays(index) {
  // A regenerated pack gets a new ?v= hash, orphaning the previous copy under a
  // URL savedDays() no longer looks for. Reclaim it instead of leaking ~200 KiB.
  const cache = await dayCache();
  if (!cache) return 0;
  const current = new Set(Object.keys(index.days).map(day => packUrl(day, index.days[day])));
  const stale = (await cache.keys()).filter(request => !current.has(request.url));
  await Promise.all(stale.map(request => cache.delete(request)));
  return stale.length;
}

export async function forgetDays() {
  const cache = await dayCache();
  if (!cache) return 0;
  const keys = await cache.keys();
  await Promise.all(keys.map(request => cache.delete(request)));
  return keys.length;
}

export async function registerWorker() {
  if (!('serviceWorker' in navigator)) return false;
  await navigator.serviceWorker.register(new URL('sw.js', scope), { scope: scope.pathname });
  await navigator.serviceWorker.ready;
  return true;
}
