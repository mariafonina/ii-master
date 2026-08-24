# ИИ-мастер — настройки

Всё сменное живёт только здесь: ссылка на оплату, метки, цена, короткая ссылка теста, хэндл.
Скиллы и скрипт `measure/render.py` читают блок ниже построчно (`ключ: значение`), поэтому
формат строк менять нельзя, значения — можно.

```yaml
test_name: ИИ-мастер
handle: "@mariafonina"
test_url: https://labsme.ru/ai
checkout_url: https://pay.labsme.ru/labs-6-kurs
utm_source: fluency-test
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
```

## Как собирается ссылка на оплату

`{checkout_url}?utm_source={utm_source}&utm_medium={utm_medium}&utm_campaign={utm_campaign}&utm_content=<слаг>`

- `<слаг>` — первая зона роста из `result.json` (`growth[0]`): `iter`, `goal`, `examples`, `format`,
  `mode`, `tone`, `context`, `audience`, `reason`, `approach`, `fact`.
- Сильный профиль (КОНТРАКТ 5: `score11 ≥ 8`, единое правило для авто и квиза) —
  `utm_content=first-money`.
- Профиль не сильный и `growth` пуст (все привычки на уровне базы) — питч собирается по
  неиспользуемым фишкам, `utm_content=tools`.

Пример: `https://pay.labsme.ru/labs-6-kurs?utm_source=fluency-test&utm_medium=plugin&utm_campaign=labs6&utm_content=examples`

## Что где используется

| Ключ | Где |
|---|---|
| `test_name`, `handle`, `test_url` | подвал страницы результата и карточки; эмодзи-полоса в чате |
| `checkout_url` + `utm_*` | кнопка на странице результата и ссылка в финале теста |
| `price`, `course_name` | питч; цена называется один раз, без давления |
| `cta_label`, `cta_label_strong` | текст кнопки: обычный профиль и сильный профиль |
| `share_utm_source` | метка для ссылки с карточки (редирект `test_url` заводится отдельно) |
| `footer_handle`, `footer_link`, `imya_testa` | подвал карточки: вызывающий скилл кладёт их в блок `/*DATA*/` шаблона (КОНТРАКТ 5) |

QR-код карточки печётся при сборке: смена `test_url`/`share_utm_source` требует перезапуска
`skills/share-card/scripts/build_assets.py` (иначе QR останется со старой ссылкой).

Короткая ссылка `labsme.ru/ai` — пока заглушка: редирект на страницу теста заводится отдельной задачей.
