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
price_installment: 6 665 ₽/мес
defense_date: 20 сентября
course_name: ЛАБС 6
cta_label: Прокачать это в ЛАБС
cta_label_strong: Посмотреть трек «первые деньги» в ЛАБС
share_utm_source: share_card
footer_handle: "@mariafonina"
footer_link: labsme.ru/ai
imya_testa: ИИ-мастер
ask_label: Подать заявку в ЛАБС 6
manager_name: Катя
manager_phone: +7 900 319-21-55
manager_phone_raw: 79003192155
tg_username: kattvol
manager_telegram: https://t.me/kattvol
manager_prefill: Здравствуйте, Катя! Я {name}. Пишу с теста „ИИ-мастер“ — {score11} из 11 ({method}). Зона роста — {growth}. Хочу подать заявку на участие в ЛАБС
max_phone: +79610501100
max_hint: Пользуешься только MAX? Напиши Кате: +7 961 050-11-00 — текст заявки тот же.
max_username:
```

## Менеджер продаж (это и есть CTA)

CTA теста — заявка менеджеру по продажам: призыв `ask_label`, кнопки Telegram (первая) и
WhatsApp (вторая) на странице результата, те же ссылки в финале квиза; MAX — строкой под
кнопками, пока у менеджера нет ника. Чекаут-ссылка — резерв, в CTA не используется.

- `manager_prefill` — шаблон текста заявки, первичка для менеджера. Подстановки делает render.py
  (в чате при упавшем рендере — скилл квиза, по тем же правилам):
  - `{score11}` — балл из result.json;
  - `{method}` — «замер по реальной истории» или «экспресс-тест»;
  - `{growth}` — первая зона роста по-русски, со строчной буквы («тон», «спор с логикой»);
  - `{name}` — имя из result.json.
  Предложения с `{name}` и `{growth}` должны оставаться отдельными предложениями: когда данных
  нет (имя не назвали, зон роста нет), render.py выбрасывает такое предложение целиком.
  По этому тексту Катя видит балл, метод замера и зону роста — другой атрибуции у заявки нет.
- Ссылки render.py собирает из `manager_prefill` сам (URL-кодировка гарантирована):
  Telegram — `{manager_telegram}?text=<префилл>` (официальные клиенты подставляют текст
  черновиком в поле ввода), WhatsApp — `wa.me/{manager_phone_raw}?text=<префилл>`.
  `manager_telegram` = `https://t.me/<tg_username>`; меняешь ник — поменяй обе строки.
- MAX: прямой ссылки на чат по номеру телефона у MAX нет (архитектурно), поэтому кнопки MAX
  в ряду нет — под кнопками выходит строка `max_hint` с номером Кати в MAX. Это `max_phone`
  (+7 961 050-11-00); его не путать с `manager_phone`/`manager_phone_raw` — это номер для
  WhatsApp и подписи под кнопками. Меняешь `max_phone` — поменяй номер и в `max_hint`.
  Появится ник менеджера в MAX — заполни `max_username`, и render.py сам поставит в ряд
  третью кнопку-ссылку `https://max.ru/<ник>` (строка `max_hint` тогда не показывается).
- Рядом с кнопками страница просит приложить карточку результата — Катя сразу видит профиль;
  если карточки нет, шпаргалка Кати просит скрин страницы.

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
| `ask_label`, `manager_name`, `manager_phone` | блок заявки на странице результата и финал квиза; `ask_label` — ещё якорь после «Итога замера» и sticky-полоса внизу страницы |
| `manager_telegram`, `tg_username`, `manager_phone_raw` | кнопки Telegram (первая) и WhatsApp (вторая): render.py строит обе ссылки из `manager_prefill` с текстом заявки в параметре `?text=` |
| `manager_prefill` | шаблон текста заявки (балл, метод, зона роста, имя): в обеих ссылках и рядом с кнопками |
| `max_phone`, `max_hint`, `max_username` | MAX: пока ника нет — строка `max_hint` под кнопками с номером Кати в MAX (он свой, отличается от WhatsApp); с ником — третья кнопка `https://max.ru/<ник>` |
| `checkout_url` + `utm_*` | резерв: в CTA не используется, render.py печатает ссылку только в консоль |
| `price`, `price_installment`, `defense_date`, `course_name` | строка цены у кнопок заявки: «Стоимость: … или …/мес в рассрочку … Ближайшая защита проектов — …»; цена называется один раз, без давления |
| `cta_label`, `cta_label_strong` | резерв: подписи прежней кнопки чекаута, на странице этой кнопки больше нет |
| `share_utm_source` | метка для ссылки с карточки (редирект `test_url` заводится отдельно) |
| `footer_handle`, `footer_link`, `imya_testa` | подвал карточки: вызывающий скилл кладёт их в блок `/*DATA*/` шаблона (КОНТРАКТ 5) |

QR-код карточки печётся при сборке: смена `test_url`/`share_utm_source` требует перезапуска
`skills/share-card/scripts/build_assets.py` (иначе QR останется со старой ссылкой).

Короткая ссылка `labsme.ru/ai` — пока заглушка: редирект на страницу теста заводится отдельной задачей.
