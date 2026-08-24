---
name: share-card
description: Собирает красивую карточку с результатом теста «ИИ-мастер» — PNG 1080×1920 для сторис и 1080×1080 для чатов. Используй, когда пользователь просит «карточку», «сделай картинку с баллами», «поделиться результатом», «карточку для сторис/инстаграма», а также когда скилл ii-master или квиз после записи результата предлагает карточку и пользователь соглашается. Требует готовый ~/.claude/ii-master-result.json; если файла нет — предложи сначала пройти тест «ИИ-мастер».
---

# Карточка результата «ИИ-мастер»

Вход: `~/.claude/ii-master-result.json` (пишут авто-замер и квиз). Выход: `~/.claude/ii-master-story.png` (1080×1920) и `~/.claude/ii-master-square.png` (1080×1080) плюс копии на рабочий стол. Всё локально, никакой сети: шаблон самодостаточный, шрифты и QR зашиты внутрь.

Если `~/.claude/ii-master-result.json` отсутствует — карточку не собирать; ответь простыми словами, что сначала нужен замер, и предложи пройти тест «ИИ-мастер».

## Шаг 0 — эмодзи-полоса (всегда, до любой картинки)

Прочитай result.json и сразу покажи текстовую версию результата — она остаётся даже там, где нет ни одного браузера:

```
🟩🟩⬜🟩⬜🟩🟩🟩⬜⬜🟩 7/11 · тест «ИИ-мастер» · labsme.ru/ai
```

Порядок сегментов фиксирован (контракт 1): `iter, goal, examples, format, mode, tone, context, audience, reason, approach, fact`. 🟩 — `habits[слаг] == 1`, ⬜ — 0. Число — `score11`. Ссылка в конце — `test_url` из `${CLAUDE_PLUGIN_ROOT}/skills/ii-master/config.md`, без `https://` (файла нет — не выдумывай, оставь строку без ссылки). Скажи, что эту строку уже можно скопировать куда угодно, а сейчас соберёшь картинку.

## Шаг 1 — собрать HTML карточки

Готовый скрипт делает всё сам (берёт шаблон рядом с собой, добавляет в JSON поля подвала `footer_handle`/`footer_link`/`footer_test` из `config.md` ядра — контракт 5 — и пишет результат):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/share-card/scripts/inline_data.py"
# выведет путь: ~/.claude/ii-master-card.html
```

На Windows команда может называться `python`. Если строка выше не сработала как есть (например, путь не подставился) — скрипт лежит рядом с этим SKILL.md: `scripts/inline_data.py`, запусти его по этому расположению; переменные окружения ему не нужны.

Если питона нет вовсе — сделай то же самое файловыми инструментами: открой `assets/share-card-template.html` (рядом с этим SKILL.md), найди два маркера-комментария `DATA` (слово DATA в `/*…*/`), замени всё между ними вместе с маркерами на `маркер + JSON + маркер`, где JSON = содержимое `~/.claude/ii-master-result.json` плюс поля `"footer_handle"` (ключ `handle` из `config.md` ядра), `"footer_link"` (ключ `test_url`), `"footer_test"` (ключ `test_name`). Сохрани как `~/.claude/ii-master-card.html`.

## Шаг 2 — PNG через headless-браузер (основной путь)

Найди первый существующий Chromium-браузер по абсолютным путям, сверху вниз.

**macOS** (проверь и `/Applications`, и `~/Applications`):
1. `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
2. `/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge`
3. `/Applications/Yandex.app/Contents/MacOS/Yandex` (Яндекс.Браузер; сборки на macOS часто не умеют headless-скриншот — если файла нет, не бейся, иди дальше по списку)
4. `/Applications/Brave Browser.app/Contents/MacOS/Brave Browser`
5. `/Applications/Chromium.app/Contents/MacOS/Chromium`
6. `/Applications/Chromium-Gost.app/Contents/MacOS/Chromium-Gost`

**Windows** (подставь реальные значения переменных окружения):
1. `%ProgramFiles%\Google\Chrome\Application\chrome.exe`
2. `%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe`
3. `%LocalAppData%\Google\Chrome\Application\chrome.exe`
4. `%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe`
5. `%ProgramFiles%\Microsoft\Edge\Application\msedge.exe`
6. `%LocalAppData%\Yandex\YandexBrowser\Application\browser.exe`
7. `%ProgramFiles%\Yandex\YandexBrowser\Application\browser.exe`
8. `%ProgramFiles%\BraveSoftware\Brave-Browser\Application\brave.exe`
9. `%LocalAppData%\BraveSoftware\Brave-Browser\Application\brave.exe`

**Linux**: первый найденный через `command -v` из списка `google-chrome, google-chrome-stable, chromium, chromium-browser, microsoft-edge, microsoft-edge-stable, yandex-browser, yandex-browser-stable, brave-browser`; затем `/snap/bin/chromium`; затем flatpak (`flatpak run org.chromium.Chromium` / `com.google.Chrome` / `com.brave.Browser`, если `flatpak list` их показывает).

Запусти два рендера (пути в кавычках; `$HOME` → `%USERPROFILE%` на Windows):

```bash
"<браузер>" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
  --window-size=540,960 --screenshot="$HOME/.claude/ii-master-story.png" \
  "file://$HOME/.claude/ii-master-card.html?variant=story&shot=1"

"<браузер>" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
  --window-size=540,540 --screenshot="$HOME/.claude/ii-master-square.png" \
  "file://$HOME/.claude/ii-master-card.html?variant=square&shot=1"
```

Правила запуска:
- **Таймаут 20 секунд** на каждый рендер. Некоторые сборки Chrome пишут PNG за 2–3 секунды, а процесс потом висит — по таймауту убей процесс и всё равно проверь файл: он часто уже готов. Если запускаешь через инструмент с параметром таймаута — просто поставь 20 секунд. В голом шелле учти: на macOS команды `timeout` нет, поэтому запускай в фоне и жди файл циклом:

```bash
"<браузер>" <флаги как выше> & BPID=$!
for i in $(seq 1 20); do [ -s "<выходной PNG>" ] && break; sleep 1; done
sleep 1   # дать файлу дописаться
kill -9 $BPID 2>/dev/null
```
- Не добавляй `--user-data-dir` без нужды (свежий профиль на macOS заставляет Chrome зависать на первичной настройке). Добавь `--user-data-dir=<временная папка>` только если без него браузер падает или жалуется на занятый профиль.
- Файл не появился или невалиден → повтори один раз со старым флагом `--headless` вместо `--headless=new` (старые сборки не знают `new`).
- Linux под root → добавь `--no-sandbox`.
- Браузер не справился после обоих заходов → возьми следующий из списка.

**Валидация каждого PNG**: файл существует, первые байты `89 50 4E 47`, размер больше 20 КБ (нормальная карточка — 60–160 КБ). Если есть питон, проверь и габариты (1080×1920 / 1080×1080):

```bash
python3 -c "import struct,sys; b=open(sys.argv[1],'rb').read(); assert b[:4]==b'\x89PNG' and len(b)>20480, 'битый PNG'; print(struct.unpack('>II', b[16:24]))" "$HOME/.claude/ii-master-story.png"
```

Оба PNG валидны → скопируй их на рабочий стол (`~/Desktop`, на Windows `%USERPROFILE%\Desktop`; папки нет — пропусти копирование и скажи, где лежат оригиналы) и переходи к итогу.

## Шаг 3 — запасной путь: браузер с кнопкой

Ни один headless-рендер не сработал → открой карточку в браузере по умолчанию:

- macOS: `open "$HOME/.claude/ii-master-card.html"`
- Windows: `start "" "%USERPROFILE%\.claude\ii-master-card.html"`
- Linux: `xdg-open "$HOME/.claude/ii-master-card.html"`
- не сработало → `python3 -c "import webbrowser, os; webbrowser.open('file://' + os.path.expanduser('~/.claude/ii-master-card.html'))"`

Скажи пользователю простыми словами: откроется страница с карточкой, под ней кнопка «Скачать PNG» — она сохранит сторис-версию; для квадратной рядом с кнопкой есть ссылка «открыть квадрат», там своя такая же кнопка. Работает в любом браузере, включая Safari.

Совсем не открылось (нет ни одного браузера, сервер без экрана) → остаётся эмодзи-полоса из шага 0; скажи об этом честно и напомни, что HTML-карточка лежит в `~/.claude/ii-master-card.html` — её можно открыть на любом другом компьютере.

## Итоговое сообщение

Простыми словами, без технических деталей. Пример для успешного пути:

> Готово. На рабочем столе две карточки: **ii-master-story.png** — вертикальная для сторис, **ii-master-square.png** — квадратная для чатов и постов. Текстовую полосу сверху можно вставить прямо в сообщение. Захочешь пересобрать после нового замера — просто скажи «карточка».

## Правила

- Никакой сети: не скачивай шрифты, библиотеки или браузеры; всё уже в шаблоне.
- В карточку попадают только поля result.json — никаких цитат диалогов, имён файлов или секретов.
- Данные не приукрашивать: балл и сегменты — ровно из result.json.
- Все ответы пользователю — на русском.
