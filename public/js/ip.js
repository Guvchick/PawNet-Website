/* Страница /ip: данные приходят из Worker'а (/api/ip). */
(() => {
  'use strict';

  const value = document.getElementById('ip-value');
  const copy = document.getElementById('ip-copy');
  const facts = document.querySelectorAll('[data-fact]');
  const note = document.getElementById('facts-note');

  // Если сайт отдаётся через сторонний CDN, до Worker'а доходит адрес
  // узла CDN, и гео-данные посчитать не из чего. Обойти это можно, дав
  // браузеру адрес, который идёт в Cloudflare напрямую, мимо CDN:
  // <body data-ip-endpoint="https://ip.pawnet.cloud/api/ip">
  const endpoints = [document.body.dataset.ipEndpoint, '/api/ip'].filter(Boolean);

  const fail = (msg) => {
    value.textContent = msg;
    value.dataset.state = 'error';
    facts.forEach((el) => { el.textContent = '—'; delete el.dataset.state; });
  };

  const fill = (data) => {
    value.textContent = data.ip;
    delete value.dataset.state;
    copy.disabled = false;

    facts.forEach((el) => {
      const v = data[el.dataset.fact];
      el.textContent = v || (data.geo ? 'Неизвестно' : '—');
      delete el.dataset.state;
    });

    // «Часовой пояс» показываем вместе со смещением: Europe/Moscow, UTC+3
    const tz = document.querySelector('[data-fact="timezone"]');
    if (tz && data.timezone) {
      try {
        const offset = new Intl.DateTimeFormat('ru', {
          timeZone: data.timezone, timeZoneName: 'shortOffset',
        }).formatToParts(new Date()).find((p) => p.type === 'timeZoneName');
        if (offset) tz.textContent = data.timezone + ', ' + offset.value;
      } catch { /* таймзона не распознана — оставляем как есть */ }
    }

    if (note) note.hidden = Boolean(data.geo);
  };

  const load = async () => {
    for (const url of endpoints) {
      try {
        const r = await fetch(url, { headers: { accept: 'application/json' } });
        if (!r.ok) continue;
        const data = await r.json();
        if (!data.ip) continue;
        fill(data);
        return;
      } catch { /* пробуем следующий адрес */ }
    }
    fail('Адрес определить не удалось');
  };

  load();

  copy.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(value.textContent.trim());
      const was = copy.textContent;
      copy.textContent = 'Скопировано';
      setTimeout(() => { copy.textContent = was; }, 1600);
    } catch {
      copy.textContent = 'Не вышло скопировать';
    }
  });
})();
