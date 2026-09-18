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
 * проставляет прокси, а гео-данные в таком случае честно помечаем
 * недоступными: посчитать их для чужого адреса Worker не может.
 */

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

function ipInfo(request) {
  const client = resolveClient(request);

  // cf описывает того, кто соединился с Cloudflare. Если это узел CDN,
  // его страна и провайдер к посетителю отношения не имеют.
  const cf = client.proxied ? {} : request.cf || {};

  return Response.json(
    {
      ip: client.ip,
      family: client.ip ? (client.ip.includes(':') ? 'IPv6' : 'IPv4') : null,
      // откуда взят адрес и стоял ли перед нами прокси
      via: client.via,
      proxied: client.proxied,
      // гео есть только при прямом соединении с Cloudflare
      geo: !client.proxied,
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
        'access-control-allow-origin': 'same-origin',
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

    if (pathname === '/api/ip') {
      if (request.method !== 'GET' && request.method !== 'HEAD') {
        return new Response('Method Not Allowed', { status: 405, headers: { allow: 'GET, HEAD' } });
      }
      return ipInfo(request);
    }

    return env.ASSETS.fetch(request);
  },
};
