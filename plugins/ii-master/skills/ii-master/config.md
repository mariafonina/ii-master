# ИИ-мастер — настройки

Всё сменное живёт только здесь: контакты менеджера продаж, ссылка на оплату (резерв), метки,
цена, короткая ссылка теста, хэндл. Скиллы и скрипт `measure/render.py` читают блок ниже
построчно (`ключ: значение`), поэтому формат строк менять нельзя, значения — можно.

```yaml
test_name: ИИ-мастер
handle: "@mariafonina"
test_url: https://labsme.ru/ai
# чекаут — резерв, в CTA не используется (CTA = заявка менеджеру, блок «Менеджер продаж» ниже)
checkout_url: https://pay.labsme.ru/labs-6-kurs
utm_source: ii-master
utm_medium: plugin
utm_campaign: labs6
price: 39 990 ₽
course_name: ЛАБС 6
cta_label: Прокачать это в ЛАБС
cta_label_strong: Посмотреть трек «первые деньги» в ЛАБС
share_utm_source: share_card
footer_handle: "@mariafonina"
footer_link: labsme.ru/ai
imya_testa: ИИ-мастер
ask_label: Подать заявку на участие
manager_name: Катя
manager_phone: +7 900 319-21-55
manager_phone_raw: 79003192155
tg_username: kattvol
manager_telegram: https://t.me/kattvol
manager_prefill: Здравствуйте, Катя! Пишу с теста „ИИ-мастер“, мой результат — {score11} из 11. Хочу подать заявку на участие в ЛАБС
manager_whatsapp: https://wa.me/79003192155?text=%D0%97%D0%B4%D1%80%D0%B0%D0%B2%D1%81%D1%82%D0%B2%D1%83%D0%B9%D1%82%D0%B5%2C%20%D0%9A%D0%B0%D1%82%D1%8F%21%20%D0%9F%D0%B8%D1%88%D1%83%20%D1%81%20%D1%82%D0%B5%D1%81%D1%82%D0%B0%20%E2%80%9E%D0%98%D0%98-%D0%BC%D0%B0%D1%81%D1%82%D0%B5%D1%80%E2%80%9C%2C%20%D0%BC%D0%BE%D0%B9%20%D1%80%D0%B5%D0%B7%D1%83%D0%BB%D1%8C%D1%82%D0%B0%D1%82%20%E2%80%94%20{score11}%20%D0%B8%D0%B7%2011.%20%D0%A5%D0%BE%D1%87%D1%83%20%D0%BF%D0%BE%D0%B4%D0%B0%D1%82%D1%8C%20%D0%B7%D0%B0%D1%8F%D0%B2%D0%BA%D1%83%20%D0%BD%D0%B0%20%D1%83%D1%87%D0%B0%D1%81%D1%82%D0%B8%D0%B5%20%D0%B2%20%D0%9B%D0%90%D0%91%D0%A1
max_phone: +79610501100
max_hint: MAX: +7 961 050-11-00 — найди по номеру
max_username:
```

## Менеджер продаж (это и есть CTA)

CTA теста — заявка менеджеру по продажам: призыв `ask_label` и кнопки WhatsApp · Telegram · MAX
на странице результата, те же ссылки в финале квиза. Чекаут-ссылка — резерв, в CTA не используется.

- `manager_prefill` — текст заявки. `{score11}` заменяется на балл из result.json: на странице
  это делает render.py, в чате — скилл квиза. По этому тексту менеджер видит, что человек пришёл
  с теста и с каким баллом, — другой атрибуции у заявки нет.
- `manager_whatsapp` — готовая ссылка: тот же префилл в URL-кодировке, `{score11}` внутри неё
  так же заменяется на балл. Меняешь `manager_prefill` — пересобери и эту ссылку
  (render.py строит ссылку из `manager_prefill` сам и предупреждает, если строки разошлись).
- `manager_telegram` = `https://t.me/<tg_username>` — ссылка по нику: работает надёжно,
  от настроек приватности номера не зависит. Меняешь ник — поменяй обе строки. Текст в ссылку
  Telegram не передаётся, человек вставляет его сам (он показан рядом с кнопками).
- MAX: прямой ссылки на чат по номеру телефона у MAX нет (архитектурно), поэтому кнопка MAX —
  пока текст `max_hint`. В MAX у Кати свой номер — `max_phone` (+7 961 050-11-00); его не путать
  с `manager_phone`/`manager_phone_raw` — это номер для WhatsApp и подписи под кнопками.
  Меняешь `max_phone` — поменяй номер и в `max_hint`. Появится ник менеджера в MAX — заполни
  `max_username`, и render.py сам сделает кнопку ссылкой `https://max.ru/<ник>`.

## Как собирается ссылка на оплату (резерв, в CTA не используется)

`{checkout_url}?utm_source={utm_source}&utm_medium={utm_medium}&utm_campaign={utm_campaign}&utm_content=<слаг>`

- `<слаг>` — первая зона роста из `result.json` (`growth[0]`): `iter`, `goal`, `examples`, `format`,
  `mode`, `tone`, `context`, `audience`, `reason`, `approach`, `fact`.
- Сильный профиль (КОНТРАКТ 5: `score11 ≥ 8`, единое правило для авто и квиза) —
  `utm_content=first-money`.
- Профиль не сильный и `growth` пуст (все привычки на уровне базы) — питч собирается по
  неиспользуемым фишкам, `utm_content=tools`.

Пример: `https://pay.labsme.ru/labs-6-kurs?utm_source=ii-master&utm_medium=plugin&utm_campaign=labs6&utm_content=examples`

render.py по-прежнему собирает эту ссылку и печатает её в консоль строкой «чекаут (резерв…)» —
на страницу и в чат она не идёт.

## Что где используется

| Ключ | Где |
|---|---|
| `test_name`, `handle`, `test_url` | подвал страницы результата и карточки; эмодзи-полоса в чате |
| `ask_label`, `manager_name`, `manager_phone` | блок заявки на странице результата и финал квиза |
| `manager_whatsapp`, `manager_telegram`, `tg_username`, `manager_phone_raw` | кнопки WhatsApp и Telegram (render.py строит WhatsApp из `manager_prefill` + `manager_phone_raw`) |
| `manager_prefill` | текст заявки: в ссылке WhatsApp и рядом с кнопками для пишущих в Telegram/MAX руками |
| `max_phone`, `max_hint`, `max_username` | кнопка MAX: пока ника нет — текст-подсказка с номером Кати в MAX (он свой, отличается от WhatsApp); с ником — ссылка `https://max.ru/<ник>` |
| `checkout_url` + `utm_*` | резерв: в CTA не используется, render.py печатает ссылку только в консоль |
| `price`, `course_name` | питч; цена называется один раз, без давления |
| `cta_label`, `cta_label_strong` | резерв: подписи прежней кнопки чекаута, на странице этой кнопки больше нет |
| `share_utm_source` | метка для ссылки с карточки (редирект `test_url` заводится отдельно) |
| `footer_handle`, `footer_link`, `imya_testa` | подвал карточки: вызывающий скилл кладёт их в блок `/*DATA*/` шаблона (КОНТРАКТ 5) |

QR-код карточки печётся при сборке: смена `test_url`/`share_utm_source` требует перезапуска
`skills/share-card/scripts/build_assets.py` (иначе QR останется со старой ссылкой).

Короткая ссылка `labsme.ru/ai` — пока заглушка: редирект на страницу теста заводится отдельной задачей.
