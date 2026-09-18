# -*- coding: utf-8 -*-
"""Пересобирает faq/offer/privacy: настоящие шапка и подвал вокруг
обрезанного SVG-тела. Запускается один раз, исходник берётся из
docs/source/figma-export.html, чтобы скрипт был повторяемым."""
import re, pathlib

SRC = pathlib.Path('docs/source/figma-export.html').read_text(encoding='utf-8')
# координаты строк нарисованного оглавления (сняты из макета замером в браузере)
import json
TOC_ROWS = json.loads(pathlib.Path('docs/source/toc-rows.json').read_text(encoding='utf-8'))

FRAMES = {}
pat = re.compile(r'<div data-svg-wrapper data-layer="([^"]*)"[^>]*>')
ms = list(pat.finditer(SRC))
for i, m in enumerate(ms):
    key = m.group(1).split('— ', 1)[1].split(' /', 1)[0].strip()
    end = ms[i + 1].start() if i + 1 < len(ms) else len(SRC)
    FRAMES[key] = SRC[m.start():end].strip()

OFFER_TOC = [
    (671, 'Термины и определения'), (1684, 'Общие положения'),
    (2559, 'Предмет договора'), (3167, 'Учётная запись'),
    (3677, 'Тарифные планы и содержание услуг'), (4912, 'Баланс и порядок оплаты'),
    (5926, 'Активация, срок и продление подписки'),
    (6856, 'Быстрая покупка и подарочные подписки'), (7576, 'Реферальная программа'),
    (8687, 'Права и обязанности сторон'), (9813, 'Ограничения использования'),
    (10743, 'Отказ от договора и возврат денежных средств'),
    (11758, 'Приостановление и прекращение доступа'), (12421, 'Ответственность сторон'),
    (13420, 'Форс-мажор'), (14030, 'Персональные данные'),
    (14245, 'Изменение условий оферты'), (14615, 'Срок действия и расторжение договора'),
    (14930, 'Разрешение споров'), (15257, 'Заключительные положения'),
    (15544, 'Реквизиты исполнителя'),
]

PRIVACY_TOC = [
    (707, 'Общие положения'), (1231, 'Правовые основания обработки'),
    (1854, 'Какие данные обрабатываются'), (3143, 'Что оператор не собирает и не хранит'),
    (3835, 'Учёт объёма трафика'), (4359, 'Цели обработки'),
    (4926, 'Передача данных третьим лицам'), (6457, 'Трансграничная передача данных'),
    (6925, 'Место хранения данных'), (7168, 'Сроки хранения'),
    (8004, 'Права пользователя'), (8527, 'Удаление данных и учётной записи'),
    (9052, 'Рассылки'), (9545, 'Cookie-файлы и веб-аналитика'),
    (10100, 'Меры защиты'), (10722, 'Несовершеннолетние'),
    (11008, 'Изменение политики'), (11308, 'Реквизиты оператора'),
]

PAGES = {
    'faq': dict(frame='FAQ', file='faq.html', route='/faq', total=5833, footer_top=5455, hero_end=482,
                title='Ответы на вопросы — PawNet',
                desc='Частые вопросы о подписке, оплате, возврате средств, приватности и правилах использования PawNet.',
                toc=None, drop_faded=True,
                buttons=[dict(x=80, y=5269, w=253, h=56,
                              href='https://t.me/PawNet_sup',
                              label='Написать в поддержку')]),
    'offer': dict(frame='Оферта', file='offer.html', route='/offer', total=16278, footer_top=15900, hero_end=454,
                  title='Публичная оферта — PawNet',
                  desc='Публичная оферта на оказание услуг PawNet: тарифы, оплата, возврат средств, права и обязанности сторон.',
                  toc=OFFER_TOC, drop_faded=False, buttons=[]),
    'privacy': dict(frame='Политика', file='privacy.html', route='/privacy', total=12070, footer_top=11692, hero_end=517,
                    title='Политика конфиденциальности — PawNet',
                    desc='Какие данные PawNet обрабатывает, зачем, где хранит и как их удалить.',
                    toc=PRIVACY_TOC, drop_faded=False, buttons=[]),
}

NAV = [('/#why', 'Почему мы'), ('/#devices', 'Устройства'), ('/#plans', 'Тарифы'),
       ('/faq', 'Вопросы'), ('https://telegram.me/pawnet_vpn', 'Новости')]

def header(route):
    items = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == route else ''
        ext = ' target="_blank" rel="noopener"' if href.startswith('http') else ''
        items.append(f'      <a href="{href}"{cur}{ext}>{label}</a>')
    return f'''<header class="header">
  <div class="container header__inner">
    <a class="header__logo" href="/">
      <img src="/favicon.svg" width="44" height="44" alt="">
      PawNet
    </a>
    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="nav" aria-label="Меню">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
        <path d="M3 6h18M3 12h18M3 18h18"/>
      </svg>
    </button>
    <nav class="nav" id="nav">
{chr(10).join(items)}
    </nav>
    <a class="header__login" href="https://lk.pawnet.cloud">Войти</a>
  </div>
</header>'''

def footer(route):
    def cur(h): return ' aria-current="page"' if h == route else ''
    return f'''<footer class="footer">
  <div class="container">
    <div class="footer__cols">
      <div>
        <p class="footer__brand">PawNet</p>
        <div class="footer__meta">
          <a href="https://pawnet.ink">pawnet.ink</a> · <a href="https://lk.pawnet.cloud">lk.pawnet.cloud</a><br>
          Пержу Давыд Александрович<br>
          ИНН 745311160120 · режим НПД<br>
          <a href="mailto:guvchick@icloud.com">guvchick@icloud.com</a>
        </div>
      </div>
      <div>
        <p class="footer__head">Полезные ссылки</p>
        <div class="footer__list">
          <a href="/ip"{cur('/ip')}>Проверить свой IP</a>
          <a href="https://telegram.me/pawnet_vpn" target="_blank" rel="noopener">Новостной канал</a>
          <a href="https://t.me/PawNet_sup" target="_blank" rel="noopener">Служба поддержки</a>
          <a href="/offer"{cur('/offer')}>Публичная оферта</a>
          <a href="/privacy"{cur('/privacy')}>Политика конфиденциальности</a>
        </div>
      </div>
      <div>
        <p class="footer__head">Установить</p>
        <div class="footer__list">
          <a href="https://t.me/PawNet_robot" target="_blank" rel="noopener">Android</a>
          <a href="https://t.me/PawNet_robot" target="_blank" rel="noopener">iOS</a>
          <a href="https://t.me/PawNet_robot" target="_blank" rel="noopener">Windows</a>
          <a href="https://t.me/PawNet_robot" target="_blank" rel="noopener">macOS</a>
          <a href="https://t.me/PawNet_robot" target="_blank" rel="noopener">Linux</a>
          <a href="https://t.me/PawNet_robot" target="_blank" rel="noopener">Роутер</a>
        </div>
      </div>
      <div>
        <p class="footer__head">Принимаем</p>
        <div class="footer__pay">
          <span>Мир</span><span>СБП</span><span>Visa</span><span>Mastercard</span>
          <span>Telegram Stars</span><span>Heleket</span>
        </div>
      </div>
    </div>
    <div class="footer__bottom">
      <span>© 2026 PawNet</span>
      <span>Цены без НДС — применяется режим НПД</span>
    </div>
  </div>
</footer>'''

def add_backplate(svg, hero_end):
    """Кладёт сплошную жёлтую подложку под геройскую зону.

    Группы в экспорте обрезаны clip-path, и край обрезки сглаживается:
    сквозь него просвечивает тёмный фон, и на стыке видна тонкая линия.
    Если позади лежит тот же жёлтый, сглаживание смешивает жёлтый с жёлтым
    и линия пропадает."""
    import re
    m = re.search(r'<rect width="1440" height="[\d.]+" fill="#131318"[^>]*/>', svg)
    if not m:
        raise SystemExit('не найден фоновый прямоугольник')
    plate = (f'<rect x="0" y="90" width="1440" height="{hero_end - 90}" '
             f'fill="#F7D44F" stroke="#F7D44F" stroke-width="1"/>')
    return svg[:m.end()] + '\n  ' + plate + svg[m.end():]

def seal_seams(svg):
    """Закрывает волосяные швы между соседними полосами.

    Фигуры в экспорте стыкуются впритык. При дробном масштабе (а он дробный
    на любой ширине окна кроме 1440) на стыке остаётся полупрозрачная строка
    пикселей — видна как тонкая обводка. Обводка в цвет собственной заливки
    расширяет фигуру на полпикселя в каждую сторону и стык перекрывается."""
    import re
    n = 0

    def add(m):
        nonlocal n
        tag, attrs, fill = m.group(1), m.group(2), m.group(3)
        if 'stroke=' in attrs:
            return m.group(0)
        n += 1
        return f'<{tag}{attrs}fill="{fill}" stroke="{fill}" stroke-width="1"/>'

    # полноширинные полосы-прямоугольники
    svg = re.sub(r'<(rect)( width="1440"[^>]*?)fill="(#F7D44F|#131318)"\s*/>', add, svg)
    # волна между жёлтым и тёмным
    svg = re.sub(r'<(path)( d="M0 [^"]*H0Z" )fill="(#131318)"\s*/>', add, svg)
    return svg, n

def drop_faded_group(svg):
    """Убирает <g opacity="0.16"> — полупрозрачного кота, у которого
    из-за волны торчат только уши."""
    m = re.search(r'<g opacity="0\.16"\s*>', svg)
    if not m:
        raise SystemExit('группа с opacity 0.16 не найдена')
    depth, i = 1, m.end()
    while depth:
        o, c = svg.find('<g', i), svg.find('</g>', i)
        if c == -1:
            raise SystemExit('не закрыта группа')
        if o != -1 and o < c:
            depth += 1; i = o + 2
        else:
            depth -= 1; i = c + 4
    return svg[:m.start()] + svg[i:]

for key, cfg in PAGES.items():
    frame = FRAMES[cfg['frame']]
    svg = re.sub(r'^<div[^>]*>\s*', '', frame).rsplit('</div>', 1)[0].strip()

    if cfg['drop_faded']:
        svg = drop_faded_group(svg)

    svg = add_backplate(svg, cfg['hero_end'])
    svg, sealed = seal_seams(svg)

    crop_h = cfg['footer_top'] - 90
    svg, n = re.subn(
        rf'<svg width="1440" height="{cfg["total"]}" viewBox="0 0 1440 {cfg["total"]}"',
        f'<svg width="1440" height="{crop_h}" viewBox="0 90 1440 {crop_h}"', svg, count=1)
    assert n == 1, f'{key}: не заменён корневой svg'

    overlays = []

    for i, (y, label) in enumerate(cfg['toc'] or [], 1):
        pct = (y - 90 - 24) / crop_h * 100          # чуть выше заголовка
        overlays.append(f'      <div class="doc__anchor" id="s{i}" style="top:{pct:.4f}%"></div>')

    # накладки поверх оглавления, нарисованного в макете
    for i, ((ry, rh), (_, label)) in enumerate(zip(TOC_ROWS.get(key, []), cfg['toc'] or []), 1):
        overlays.append(
            f'      <a class="doc__row" href="#s{i}"'
            f' style="top:{ry / crop_h * 100:.4f}%;height:{rh / crop_h * 100:.4f}%"'
            f' aria-label="{label}"></a>')

    # накладки поверх нарисованных кнопок
    for btn in cfg['buttons']:
        ext = ' target="_blank" rel="noopener"' if btn['href'].startswith('http') else ''
        overlays.append(
            f'      <a class="doc__btn" href="{btn["href"]}"{ext}'
            f' style="left:{btn["x"] / 1440 * 100:.4f}%;top:{(btn["y"] - 90) / crop_h * 100:.4f}%;'
            f'width:{btn["w"] / 1440 * 100:.4f}%;height:{btn["h"] / crop_h * 100:.4f}%"'
            f' aria-label="{btn["label"]}"></a>')

    anchors = '\n'.join(overlays)

    html = f'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{cfg['title']}</title>
<meta name="description" content="{cfg['desc']}">
<link rel="canonical" href="https://pawnet.ink{cfg['route']}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<meta name="theme-color" content="#F7D44F">
<meta property="og:title" content="{cfg['title']}">
<meta property="og:type" content="article">
<meta property="og:url" content="https://pawnet.ink{cfg['route']}">
<link rel="stylesheet" href="/css/base.css">
<link rel="stylesheet" href="/css/doc.css">
</head>
<body>

{header(cfg['route'])}

<main>
  <div class="doc">
{anchors}
{svg}
  </div>
</main>

{footer(cfg['route'])}

<script src="/js/main.js" defer></script>
</body>
</html>
'''
    out = pathlib.Path('public') / cfg['file']
    before = out.stat().st_size
    out.write_text(html, encoding='utf-8')
    print(f"{cfg['file']:14} {before/1048576:6.2f} -> {out.stat().st_size/1048576:6.2f} МБ   "
          f"viewBox 0 90 1440 {crop_h}   якорей: {len(cfg['toc']) if cfg['toc'] else 0}   "
          f"швов закрыто: {sealed}   кнопок: {len(cfg['buttons'])}")
