# PawNet-Website

Сайт PawNet на Cloudflare Workers: статика плюс небольшой Worker для `/api/ip`.

## Структура

```
public/                 — то, что деплоится
├── index.html          — лендинг            → /
├── ip.html             — «Твой IP-адрес»    → /ip
├── faq.html            — FAQ               → /faq      ⚠ пока SVG-экспорт
├── offer.html          — Публичная оферта   → /offer    ⚠ пока SVG-экспорт
├── privacy.html        — Политика           → /privacy  ⚠ пока SVG-экспорт
├── 404.html
├── css/                — fonts / base / landing / ip
├── js/                 — main.js (меню, аккордеон, тарифы), ip.js
├── fonts/              — Geologica, локальные субсеты
├── img/                — коты, волна, флаги стран
├── favicon.svg         — логотип PawNet
├── robots.txt, sitemap.xml, _headers

src/index.js            — Worker: /api/ip + раздача ассетов
wrangler.toml           — конфиг
docs/source/            — исходный экспорт из Figma (все 5 страниц одним файлом)
```

## Разработка

```sh
npm install
npm run dev      # http://localhost:8787
```

⚠️ **Папка синхронизируется Nextcloud**, а он снимает бит выполнения с нативных
бинарников. Поэтому `node_modules` вынесен наружу симлинком:

```
node_modules -> ~/.cache/pawnet-website/node_modules
```

Если после `npm install` появились ошибки `EACCES … esbuild` или
`permission denied`, значит `node_modules` снова оказался внутри синхронизации —
повтори вынос:

```sh
mv node_modules ~/.cache/pawnet-website/node_modules
ln -s ~/.cache/pawnet-website/node_modules node_modules
```

По той же причине npm-скрипты зовут wrangler через `node`, а не через
`node_modules/.bin`.

## Деплой

```sh
npm run check    # проверка конфига без публикации
npm run deploy
```

Домен `pawnet.ink` привязывается в дашборде Cloudflare
(Workers → Settings → Domains & Routes) или через `routes` в `wrangler.toml`.

## Состояние страниц

| Страница | Состояние |
|---|---|
| `/` | пересобрана настоящей вёрсткой, 18 КБ |
| `/ip` | пересобрана, данные живые из Worker'а |
| `/faq` | SVG-экспорт, 3.9 МБ — ждёт пересборки |
| `/offer` | SVG-экспорт, 17.7 МБ — ждёт пересборки |
| `/privacy` | SVG-экспорт, 11.3 МБ — ждёт пересборки |

У страниц, помеченных SVG-экспортом, весь текст — векторные контуры: он не
выделяется, не ищется и не виден поисковикам, а ссылки внутри не работают
(Figma потеряла координаты у прозрачных хитбоксов).

## Что осталось сделать

- пересобрать `/faq`, `/offer`, `/privacy` — нужны блоки из Figma
  (copy as code) в `docs/blocks/`, иначе юридические тексты придётся
  переписывать с картинки на глаз
- цены для 3 / 6 / 12 месяцев: в макете отрисован только «Месяц»,
  переключатель срока их пока не меняет
- проверка утечки DNS на `/ip`: со стороны Worker'а не определяется,
  нужны поддомены-ловушки и свой DNS-резолвер
