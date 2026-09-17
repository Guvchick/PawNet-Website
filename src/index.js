/**
 * PawNet — Worker поверх статики.
 *
 * Всё, кроме /api/ip, отдаёт ассет-биндинг. /api/ip возвращает данные,
 * которые Cloudflare уже знает о запросе: сам IP и геоданные из request.cf.
 */

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
  // cf есть только на настоящем эдже: в `wrangler dev` без --remote его нет
  const cf = request.cf || {};
  const ip = request.headers.get('CF-Connecting-IP') || null;

  return Response.json(
    {
      ip,
      family: ip ? (ip.includes(':') ? 'IPv6' : 'IPv4') : null,
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
      },
    },
  );
}

export default {
  async fetch(request, env) {
    const { pathname } = new URL(request.url);

    if (pathname === '/api/ip') {
      if (request.method !== 'GET' && request.method !== 'HEAD') {
        return new Response('Method Not Allowed', { status: 405, headers: { allow: 'GET, HEAD' } });
      }
      return ipInfo(request);
    }

    return env.ASSETS.fetch(request);
  },
};
