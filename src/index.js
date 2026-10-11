/**
 * PawNet — Worker поверх статики.
 *
 * Всё, кроме /api/ip, отдаёт ассет-биндинг.
 *
 * Про определение адреса. Если запрос приходит в Cloudflare напрямую,
 * настоящий адрес посетителя лежит в CF-Connecting-IP, а гео-данные —
 * в request.cf. Но перед нами стоит CDN VK Cloud, и тогда в
 * CF-Connecting-IP оказывается адрес узла CDN, а request.cf описывает
 * этот узел, а не посетителя. Поэтому адрес берём из заголовков, которые
 * проставляет прокси, а страну, город и провайдера ищем по своей базе
 * (public/geo/, см. geoLookup ниже).
 */

/** Сайт, с которого страница /ip может спрашивать /api/ip с другого хоста. */
const SITE_ORIGIN = 'https://pawnet.cloud';

/** Заголовки с адресом клиента, в порядке доверия. CF-Connecting-IP —
 *  последний: за сторонним CDN в нём лежит узел CDN. */
const FORWARDED_HEADERS = ['true-client-ip', 'x-real-ip', 'x-forwarded-for'];

const IPV4 = /^(\d{1,3}\.){3}\d{1,3}$/;

function isIp(value) {
  if (!value) return false;
  if (IPV4.test(value)) return value.split('.').every((o) => Number(o) <= 255);
  return value.includes(':') && /^[0-9a-f:.]+$/i.test(value); // IPv6
}

/**
 * Адрес посетителя и то, откуда он взят.
 * `via` показывает сработавший заголовок — по нему видно, дошёл ли
 * запрос напрямую или через CDN.
 */
function resolveClient(request) {
  const edge = request.headers.get('CF-Connecting-IP'); // кто соединился с Cloudflare

  for (const name of FORWARDED_HEADERS) {
    const raw = request.headers.get(name);
    if (!raw) continue;

    // X-Forwarded-For — цепочка «клиент, прокси1, прокси2»: нужен первый
    const candidate = raw.split(',')[0].trim();
    if (!isIp(candidate) || candidate === edge) continue;

    return { ip: candidate, via: name, proxied: true, edge };
  }

  return { ip: edge, via: 'cf-connecting-ip', proxied: false, edge };
}

/** Человеческое название страны по ISO-коду; при сбое ICU — сам код. */
function countryName(code) {
  if (!code) return null;
  try {
    return new Intl.DisplayNames(['ru'], { type: 'region' }).of(code) || code;
  } catch {
    return code;
  }
}

/* ── Гео по своей базе ─────────────────────────────────────────────
 * Cloudflare не считает гео для чужого адреса, поэтому за CDN ищем сами,
 * прямо здесь: адрес посетителя никуда не уходит. База лежит в
 * public/geo/ и собирается scripts/build-geo.py из DB-IP Lite и GeoNames,
 * формат описан там же. Только IPv4: у pawnet.cloud нет AAAA-записи,
 * и через CDN посетитель всегда приходит по IPv4. */

const GEO_NONE = 0xffffff; // «данных нет»
const GEO_BLOCK = 1024; // записей в loc/org-файле, как в build-geo.py
const GEO_CACHE_MAX = 64;

/** Прочитанные файлы базы — живут, пока жив изолят. Хранится промис,
 *  чтобы параллельные запросы не читали один файл дважды. */
const geoCache = new Map();

function geoFile(env, origin, path, json = false) {
  const hit = geoCache.get(path);
  if (hit) return hit;

  const load = env.ASSETS.fetch(new Request(`${origin}/geo/${path}`))
    .then(async (r) => {
      if (!r.ok) throw new Error(`geo/${path}: ${r.status}`);
      return json ? r.json() : new Uint8Array(await r.arrayBuffer());
    })
    .catch(() => {
      geoCache.delete(path); // неудачу не запоминаем
      return null;
    });

  geoCache.set(path, load);
  if (geoCache.size > GEO_CACHE_MAX) geoCache.delete(geoCache.keys().next().value);
  return load;
}

/** Значение диапазона, в который попадает key. Записи по 6 байт: 3 байта
 *  начало диапазона, 3 байта значение; идут по возрастанию начала. */
function rangeValue(bytes, key) {
  let lo = 0;
  let hi = bytes.length / 6 - 1;
  let value = GEO_NONE;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    const o = mid * 6;
    if (((bytes[o] << 16) | (bytes[o + 1] << 8) | bytes[o + 2]) <= key) {
      value = (bytes[o + 3] << 16) | (bytes[o + 4] << 8) | bytes[o + 5];
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  return value;
}

/**
 * Гео IPv4-адреса в тех же полях, что у request.cf: country, region, city,
 * timezone, asn, asOrganization. null — если адреса в базе нет или сама
 * база не собрана.
 */
async function geoLookup(env, origin, ip) {
  if (!isIp(ip) || ip.includes(':')) return null;
  const [a, b, c, d] = ip.split('.').map(Number);
  const key = (b << 16) | (c << 8) | d; // адрес внутри сети a.0.0.0/8

  const [cities, nets] = await Promise.all([
    geoFile(env, origin, `city/${a}.bin`),
    geoFile(env, origin, `asn/${a}.bin`),
  ]);
  const placeId = cities ? rangeValue(cities, key) : GEO_NONE;
  const orgId = nets ? rangeValue(nets, key) : GEO_NONE;

  const block = (dir, id) =>
    id === GEO_NONE ? null : geoFile(env, origin, `${dir}/${Math.floor(id / GEO_BLOCK)}.json`, true);
  const [places, orgs] = await Promise.all([block('loc', placeId), block('org', orgId)]);

  const place = places?.[placeId % GEO_BLOCK];
  const org = orgs?.[orgId % GEO_BLOCK];
  if (!place && !org) return null;

  const [country, region, city, timezone] = place || [];
  const [asn, asOrganization] = org || [];
  return { country, region, city, timezone, asn, asOrganization };
}

async function ipInfo(request, env) {
  const client = resolveClient(request);

  // cf описывает того, кто соединился с Cloudflare. Если это узел CDN,
  // его страна и провайдер к посетителю отношения не имеют — тогда
  // ищем по своей базе.
  const own = client.proxied ? await geoLookup(env, new URL(request.url).origin, client.ip) : null;
  const cf = client.proxied ? own || {} : request.cf || {};
  const source = client.proxied ? (own ? 'db-ip' : null) : 'cloudflare';

  return Response.json(
    {
      ip: client.ip,
      family: client.ip ? (client.ip.includes(':') ? 'IPv6' : 'IPv4') : null,
      // откуда взят адрес и стоял ли перед нами прокси
      via: client.via,
      proxied: client.proxied,
      // откуда гео: cloudflare — при прямом соединении, db-ip — своя база
      // за CDN, null — определить не удалось
      geo: source !== null,
      source,
      country: cf.country || null,
      countryName: countryName(cf.country),
      city: cf.city || null,
      region: cf.region || null,
      timezone: cf.timezone || null,
      org: cf.asOrganization || null,
      asn: cf.asn || null,
      colo: cf.colo || null,
      protocol: cf.httpProtocol || null,
      tls: cf.tlsVersion || null,
    },
    {
      headers: {
        'cache-control': 'no-store, no-cache, must-revalidate',
        // нужен, только если data-ip-endpoint на странице ведёт на другой хост
        'access-control-allow-origin': SITE_ORIGIN,
        // сторонний CDN не должен класть чужой ответ в кэш
        vary: 'CF-Connecting-IP, X-Forwarded-For, True-Client-IP, X-Real-IP',
      },
    },
  );
}

/**
 * Диагностика: показывает заголовки запроса как есть.
 *
 * По ним видно, что именно проставляет CDN перед нами — иначе это
 * приходится угадывать. Выключен, пока не задан секрет:
 *   npx wrangler secret put DEBUG_TOKEN
 * Вызов: /api/debug-headers?token=<секрет>. После настройки секрет
 * стоит удалить: wrangler secret delete DEBUG_TOKEN
 */
function debugHeaders(request, env) {
  const token = env.DEBUG_TOKEN;
  const given = new URL(request.url).searchParams.get('token');

  // без секрета эндпоинта как будто нет
  if (!token || given !== token) {
    return new Response('Not Found', { status: 404 });
  }

  const headers = {};
  for (const [name, value] of request.headers) headers[name] = value;

  return Response.json(
    { headers, resolved: resolveClient(request), cf: request.cf || null },
    { headers: { 'cache-control': 'no-store' } },
  );
}

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);

    if (pathname === '/api/debug-headers') {
      return debugHeaders(request, env);
    }

    // файлы гео-базы читает только сам Worker (run_worker_first в wrangler.toml)
    if (pathname.startsWith('/geo/')) {
      return new Response('Not Found', { status: 404 });
    }

    if (pathname === '/api/ip') {
      if (request.method !== 'GET' && request.method !== 'HEAD') {
        return new Response('Method Not Allowed', { status: 405, headers: { allow: 'GET, HEAD' } });
      }
      return ipInfo(request, env);
    }

    return env.ASSETS.fetch(request);
  },
};
