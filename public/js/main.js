/* PawNet — поведение страниц: меню, аккордеон, переключатель срока. */
(() => {
  'use strict';

  /* ── Мобильное меню ─────────────────────────────────────────────── */
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.getElementById('nav');

  if (toggle && nav) {
    const mq = window.matchMedia('(max-width: 720px)');

    const sync = () => {
      // На десктопе меню всегда видно и не должно быть скрыто атрибутом
      if (mq.matches) {
        nav.hidden = toggle.getAttribute('aria-expanded') !== 'true';
      } else {
        nav.hidden = false;
        toggle.setAttribute('aria-expanded', 'false');
      }
    };

    toggle.addEventListener('click', () => {
      toggle.setAttribute('aria-expanded',
        toggle.getAttribute('aria-expanded') === 'true' ? 'false' : 'true');
      sync();
    });

    // Клик по пункту меню закрывает его
    nav.addEventListener('click', (e) => {
      if (e.target.closest('a') && mq.matches) {
        toggle.setAttribute('aria-expanded', 'false');
        sync();
      }
    });

    mq.addEventListener('change', sync);
    sync();
  }

  /* ── Аккордеон ──────────────────────────────────────────────────── */
  document.querySelectorAll('[data-accordion]').forEach((acc) => {
    acc.addEventListener('click', (e) => {
      const btn = e.target.closest('.acc-q');
      if (!btn) return;

      const open = btn.getAttribute('aria-expanded') === 'true';

      // Одновременно открыт только один вопрос — как в макете
      acc.querySelectorAll('.acc-q[aria-expanded="true"]').forEach((other) => {
        other.setAttribute('aria-expanded', 'false');
        document.getElementById(other.getAttribute('aria-controls')).hidden = true;
      });

      if (!open) {
        btn.setAttribute('aria-expanded', 'true');
        document.getElementById(btn.getAttribute('aria-controls')).hidden = false;
      }
    });
  });

  /* ── Срок подписки ──────────────────────────────────────────────── */
  const periods = document.querySelectorAll('.period');

  if (periods.length) {
    const apply = (btn) => {
      periods.forEach((b) => b.setAttribute('aria-pressed', String(b === btn)));

      const key = 'p' + btn.dataset.period;
      document.querySelectorAll('.plan__amount').forEach((el) => {
        const price = el.dataset[key];
        // неразрывный пробел перед знаком рубля, чтобы не переносилось
        if (price) el.textContent = price.replace(' ', '\u00a0');
      });
      document.querySelectorAll('.plan__per').forEach((el) => {
        el.textContent = btn.dataset.per;
      });
    };

    periods.forEach((btn) => btn.addEventListener('click', () => apply(btn)));
  }
})();
