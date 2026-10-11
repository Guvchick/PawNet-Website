# -*- coding: utf-8 -*-
"""Собирает гео-базу для /api/ip в public/geo/.

Зачем. Сайт стоит за CDN VK Cloud, и request.cf описывает узел CDN, а не
посетителя. Адрес посетителя Worker знает из заголовков прокси, но страну,
город и провайдера Cloudflare для чужого адреса не считает. Поэтому
считаем сами по открытой базе, прямо в Worker'е: адрес никуда не уходит.

Источники (скачиваются сами в ~/.cache/pawnet-website/geo-src/):
  DB-IP Lite, город и провайдер — CC BY 4.0, https://db-ip.com
      Лицензия требует ссылку «IP Geolocation by DB-IP» там, где
      показываются данные; она стоит на странице /ip.
  GeoNames cities1000, часовые пояса — CC BY 4.0, https://www.geonames.org
      У DB-IP пояса нет, есть только координаты. Пояс места — это пояс
      ближайшего к нему города той же страны.

Только IPv4: у pawnet.cloud нет AAAA-записи, и через CDN посетитель
всегда приходит по IPv4.

Формат:
  geo/city/<a>.bin, geo/asn/<a>.bin — диапазоны внутри сети a.0.0.0/8.
      Запись — 6 байт: 3 байта начало диапазона (младшие 24 бита адреса)
      и 3 байта номер места или провайдера; FFFFFF — данных нет.
      Первая запись всегда начинается с нуля.
  geo/loc/<n>.json — места блоками по 1024: [страна, регион, город, пояс]
  geo/org/<n>.json — провайдеры блоками по 1024: [ASN, название]
  geo/meta.json    — месяц выпуска базы

База DB-IP выходит раз в месяц. Обновить:
  python3 scripts/build-geo.py            — свежий выпуск
  python3 scripts/build-geo.py --if-missing  — только если базы нет

База в git не лежит, поэтому её должен собирать каждый деплой. Сайт
выкатывают Workers Builds из GitHub при каждом push в main, а они не
запускают ни predeploy, ни [build] из wrangler.toml — только установку
зависимостей и `npx wrangler deploy`. Поэтому скрипт висит на
postinstall: npm install в сборке сам соберёт свежую базу. Если
скачать её не удалось, сборка падает и прод остаётся на прошлой версии,
а не выкатывается без гео.
"""
import argparse, array, bisect, csv, datetime, gzip, io, json, math
import pathlib, shutil, socket, sys, urllib.request, zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / 'public' / 'geo'
CACHE = pathlib.Path.home() / '.cache' / 'pawnet-website' / 'geo-src'

NONE = 0xFFFFFF   # «данных нет» в записи диапазона
BLOCK = 1024      # записей в одном loc/org-файле; то же число в src/index.js

DBIP = 'https://download.db-ip.com/free/dbip-{kind}-lite-{month}.csv.gz'
GEONAMES = 'https://download.geonames.org/export/dump/cities1000.zip'


def download(url, dest):
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f'  скачиваю {url}')
    req = urllib.request.Request(url, headers={'User-Agent': 'pawnet-website build-geo'})
    tmp = dest.with_suffix(dest.suffix + '.part')
    with urllib.request.urlopen(req, timeout=600) as r, open(tmp, 'wb') as f:
        shutil.copyfileobj(r, f)
    tmp.rename(dest)
    return dest


def latest_month(requested):
    """Выпуск DB-IP появляется в начале месяца: если текущего ещё нет,
    берём прошлый."""
    if requested:
        return requested
    today = datetime.date.today()
    prev = (today.replace(day=1) - datetime.timedelta(days=1))
    for d in (today, prev):
        month = d.strftime('%Y-%m')
        try:
            req = urllib.request.Request(DBIP.format(kind='asn', month=month), method='HEAD',
                                         headers={'User-Agent': 'pawnet-website build-geo'})
            urllib.request.urlopen(req, timeout=60).close()
            return month
        except Exception:
            continue
    raise SystemExit('не нашёл выпуск DB-IP за этот и прошлый месяц')


def ipv4_rows(path):
    """Строки CSV с IPv4-диапазонами: (начало, конец, остальные поля)."""
    with gzip.open(path, 'rt', encoding='utf-8', newline='') as f:
        for row in csv.reader(f):
            if ':' in row[0]:
                continue
            start = int.from_bytes(socket.inet_aton(row[0]), 'big')
            end = int.from_bytes(socket.inet_aton(row[1]), 'big')
            yield start, end, row[2:]


def segments(rows, value_of):
    """Сплошное покрытие 0.0.0.0–255.255.255.255: начала отрезков и их
    значения. Дыры между диапазонами заполняются NONE, соседние отрезки
    с одинаковым значением склеиваются."""
    starts, values = array.array('I'), array.array('I')
    prev_end = -1

    def put(start, value):
        if values and values[-1] == value:
            return
        starts.append(start)
        values.append(value)

    for start, end, fields in rows:
        if start <= prev_end:
            raise SystemExit(f'диапазоны пересекаются у {socket.inet_ntoa(start.to_bytes(4, "big"))}')
        if start > prev_end + 1:
            put(prev_end + 1, NONE)
        put(start, value_of(fields))
        prev_end = end
    if prev_end < 0xFFFFFFFF:
        put(prev_end + 1, NONE)
    return starts, values


def write_shards(folder, starts, values):
    folder.mkdir(parents=True)
    total = 0
    for a in range(256):
        base = a << 24
        i = bisect.bisect_right(starts, base) - 1     # отрезок, покрывающий a.0.0.0
        j = bisect.bisect_left(starts, base + (1 << 24))
        out = bytearray()
        out += (0).to_bytes(3, 'big') + values[i].to_bytes(3, 'big')
        for k in range(i + 1, j):
            out += (starts[k] - base).to_bytes(3, 'big') + values[k].to_bytes(3, 'big')
        (folder / f'{a}.bin').write_bytes(out)
        total += len(out)
    return total


def write_blocks(folder, items):
    folder.mkdir(parents=True)
    for n in range(0, len(items), BLOCK):
        text = json.dumps(items[n:n + BLOCK], ensure_ascii=False, separators=(',', ':'))
        (folder / f'{n // BLOCK}.json').write_text(text, encoding='utf-8')


class Timezones:
    """Пояс по координатам: пояс ближайшего города той же страны из GeoNames."""

    def __init__(self, zip_path):
        self.cells = {}      # (страна, широта°, долгота°) -> [(lat, lon, tz)]
        self.zones = {}      # страна -> множество поясов
        with zipfile.ZipFile(zip_path) as z, z.open('cities1000.txt') as raw:
            for line in io.TextIOWrapper(raw, encoding='utf-8'):
                f = line.rstrip('\n').split('\t')
                lat, lon, cc, tz = float(f[4]), float(f[5]), f[8], f[17]
                if not tz:
                    continue
                key = (cc, math.floor(lat), math.floor(lon) % 360)
                self.cells.setdefault(key, []).append((lat, lon, tz))
                self.zones.setdefault(cc, set()).add(tz)

    def only(self, cc):
        """Пояс страны, если он у неё один."""
        zones = self.zones.get(cc, ())
        return next(iter(zones)) if len(zones) == 1 else ''

    def nearest(self, cc, lat, lon):
        if cc not in self.zones:
            return ''
        if len(self.zones[cc]) == 1:
            return self.only(cc)
        cy, cx = math.floor(lat), math.floor(lon)
        k = math.cos(math.radians(lat))
        best, best_d, found_at = '', float('inf'), None
        # расходимся кольцами клеток 1°×1°; после первой находки смотрим
        # ещё одно кольцо — ближайший мог оказаться в соседней клетке
        for r in range(0, 40):
            if found_at is not None and r > found_at + 1:
                break
            for y in range(cy - r, cy + r + 1):
                for x in range(cx - r, cx + r + 1):
                    if max(abs(y - cy), abs(x - cx)) != r:
                        continue
                    for plat, plon, tz in self.cells.get((cc, y, x % 360), ()):
                        dlon = (plon - lon + 180) % 360 - 180
                        d = (plat - lat) ** 2 + (dlon * k) ** 2
                        if d < best_d:
                            best, best_d = tz, d
            if best and found_at is None:
                found_at = r
        return best


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--if-missing', action='store_true', help='ничего не делать, если база уже собрана')
    ap.add_argument('--month', help='выпуск DB-IP, например 2026-10')
    args = ap.parse_args()

    if args.if_missing and (OUT / 'meta.json').exists():
        meta = json.loads((OUT / 'meta.json').read_text(encoding='utf-8'))
        print(f'гео-база уже есть (DB-IP {meta["month"]}), пропускаю')
        return

    month = latest_month(args.month)
    print(f'DB-IP Lite {month}')
    city_src = download(DBIP.format(kind='city', month=month), CACHE / f'dbip-city-lite-{month}.csv.gz')
    asn_src = download(DBIP.format(kind='asn', month=month), CACHE / f'dbip-asn-lite-{month}.csv.gz')
    names_src = download(GEONAMES, CACHE / f'geonames-cities1000-{month}.zip')

    tmp = OUT.with_name('geo.tmp')
    if tmp.exists():
        shutil.rmtree(tmp)

    # города: [страна, регион, город] -> номер места
    places, coords = {}, []

    def place(fields):
        _continent, cc, region, city, lat, lon = fields
        if not cc or cc == 'ZZ':
            return NONE
        key = (cc, region, city)
        n = places.get(key)
        if n is None:
            n = places[key] = len(places)
            coords.append((float(lat), float(lon)))
        return n

    print('  города…')
    starts, values = segments(ipv4_rows(city_src), place)
    city_bytes = write_shards(tmp / 'city', starts, values)
    ranges_city = len(starts)
    del starts, values

    print('  часовые пояса…')
    zones = Timezones(names_src)
    locs = []
    for (cc, region, city), (lat, lon) in zip(places, coords):
        tz = zones.nearest(cc, lat, lon) if (city or region) else zones.only(cc)
        locs.append([cc, region, city, tz])
    write_blocks(tmp / 'loc', locs)

    # провайдеры: [ASN, название] -> номер
    orgs = {}

    def org(fields):
        asn, name = fields[0], fields[1]
        if not asn or asn == '0':
            return NONE
        key = (int(asn), name)
        n = orgs.get(key)
        if n is None:
            n = orgs[key] = len(orgs)
        return n

    print('  провайдеры…')
    starts, values = segments(ipv4_rows(asn_src), org)
    asn_bytes = write_shards(tmp / 'asn', starts, values)
    ranges_asn = len(starts)
    write_blocks(tmp / 'org', [list(k) for k in orgs])

    meta = {'month': month, 'built': datetime.date.today().isoformat(),
            'sources': ['IP Geolocation by DB-IP (CC BY 4.0) https://db-ip.com',
                        'GeoNames (CC BY 4.0) https://www.geonames.org']}
    (tmp / 'meta.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    if OUT.exists():
        shutil.rmtree(OUT)
    tmp.rename(OUT)

    no_tz = sum(1 for l in locs if not l[3])
    size = sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
    print(f'готово: {OUT.relative_to(ROOT)}  {size / 1048576:.1f} МБ')
    print(f'  городов {len(locs)} (без пояса {no_tz}), диапазонов {ranges_city}, {city_bytes / 1048576:.1f} МБ')
    print(f'  провайдеров {len(orgs)}, диапазонов {ranges_asn}, {asn_bytes / 1048576:.1f} МБ')


if __name__ == '__main__':
    main()
