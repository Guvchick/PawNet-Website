/* Страница /ip: данные приходят из Worker'а (/api/ip). */
(() => {
  'use strict';

  const value = document.getElementById('ip-value');
  const copy = document.getElementById('ip-copy');
  const facts = document.querySelectorAll('[data-fact]');

  const fail = (msg) => {
    value.textContent = msg;
    value.dataset.state = 'error';
    facts.forEach((el) => { el.textContent = '—'; delete el.dataset.state; });
  };

  fetch('/api/ip', { headers: { accept: 'application/json' } })
    .then((r) => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then((data) => {
      if (!data.ip) return fail('Адрес определить не удалось');

      value.textContent = data.ip;
      delete value.dataset.state;
      copy.disabled = false;

      facts.forEach((el) => {
        const v = data[el.dataset.fact];
        el.textContent = v || 'Неизвестно';
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
    })
    .catch(() => fail('Адрес определить не удалось'));

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
