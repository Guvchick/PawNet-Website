# -*- coding: utf-8 -*-
"""Проставляет версию в ссылки на стили: /css/base.css -> /css/base.css?v=<хэш>.

Зачем. Стили отдаются с долгим кэшем, а имя файла при правке не меняется.
Без версии и браузер, и CDN перед сайтом продолжают отдавать старый файл:
так после перевода заголовков на Dela Gothic One посетители ещё долго
видели прежнюю Geologica. Хэш берётся от содержимого, поэтому версия
меняется ровно тогда, когда меняется сам файл.

Запускается сам перед `npm run deploy`. Повторный запуск без правок
в стилях ничего не меняет."""
import hashlib, pathlib, re

PUBLIC = pathlib.Path(__file__).resolve().parent.parent / 'public'
LINK = re.compile(r'href="(/css/[\w.-]+\.css)(?:\?v=[0-9a-f]+)?"')

versions = {}

def version(path):
    if path not in versions:
        data = (PUBLIC / path.lstrip('/')).read_bytes()
        versions[path] = hashlib.sha256(data).hexdigest()[:10]
    return versions[path]

for page in sorted(PUBLIC.glob('*.html')):
    text = page.read_text(encoding='utf-8')
    stamped = LINK.sub(lambda m: f'href="{m.group(1)}?v={version(m.group(1))}"', text)
    if stamped != text:
        page.write_text(stamped, encoding='utf-8')
        print(f'{page.name:14} обновлён')

for path, v in sorted(versions.items()):
    print(f'{path:20} v={v}')
