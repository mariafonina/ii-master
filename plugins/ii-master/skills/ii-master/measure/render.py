#!/usr/bin/env python3
"""Шаг 6: собрать страницу результата из scorecard.html и result.json.

Подставляет плейсхолдеры {{...}} (список — в MEASURE.md), пишет ~/.claude/ii-master-result.html
и по флагу --open открывает её в браузере по умолчанию. Сеть не нужна.

  python3 render.py [--pitch pitch.html] [--utm-content examples] [--open]
                    [--template ../scorecard.html] [--result ~/.claude/ii-master-result.json]
                    [--config ../config.md] [--out ~/.claude/ii-master-result.html]
"""
import argparse, datetime, html, json, os, re, sys, urllib.parse, webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import BASE, HABITS, NAMES, HINTS, FEATURES, FEATURE_NAMES

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)

# Разметка фрагментов — ровно та, которую ждёт scorecard.html (шаблоны и подписи
# продублированы в HTML-комментариях самого шаблона; менять здесь и там вместе).
ROW = ('<div class="row{down}"><span class="lab">{lab}<span class="d">{defn}</span></span>'
       '<span class="track"><span class="fill" style="width:{width}%"></span>'
       '<span class="tickline" style="left:{base}%"></span></span>'
       '<span class="nums">{nums}</span></div>')
BAR_LABELS = {"iter": "Итерирует и уточняет", "goal": "Проясняет цель до просьбы",
              "examples": "Даёт образцы «как надо»", "format": "Задаёт формат и структуру",
              "mode": "Назначает роль и правила", "tone": "Проговаривает тон и стиль",
              "context": "Даёт контекст, которого у модели нет", "audience": "Называет адресата",
              "reason": "Оспаривает логику модели", "approach": "Советуется о подходе до старта",
              "fact": "Проверяет факты и цифры"}
# Строки-определения под названиями полос — те же, что в секции «Что мы меряли» scorecard.html
# (там ещё фразы-примеры); менять здесь и там вместе.
DEFS = {"iter": "первый ответ принимает как черновик и дожимает правками",
        "goal": "в запросе сказано, зачем нужен результат",
        "examples": "показывает пример или планку качества",
        "format": "называет, в каком виде нужен результат",
        "mode": "говорит модели, кем быть и как работать",
        "tone": "задаёт голос текста",
        "context": "прикладывает свои вводные: файлы, цифры, историю",
        "audience": "в запросе сказано, для кого результат",
        "reason": "спрашивает основания вывода",
        "approach": "до «сделай» спрашивает, как подойти",
        "fact": "сверяет руками цифры, даты и названия"}
FLI = '<li><span class="b">{nn}</span><span>{text}</span></li>'

# ── Блок «ЛАБС» ─────────────────────────────────────────────────────────────────
# Строки «пробел → чем закрывается в ЛАБС → цитата» render.py собирает из labs_map.md:
# у привычек и групп фишек читаются поля «**Куда ведёт в ЛАБС:**» и «**Кейс:**» (контракт полей).
GAP = ('<div class="gap"><p><b>{name}</b> <span class="miss">{miss}</span> — в ЛАБС: {lead}</p>'
      '<p class="q">{case}</p></div>')
GAP_F = ('<div class="gap"><p><b>Фишки без дела: {names}</b> — в ЛАБС: {lead}</p>'
         '<p class="q">{case}</p></div>')
GAP_S = ('<div class="gap"><p><b>Трек «первые деньги»</b> — в ЛАБС: {lead} Материалы трека: каталог '
         '«Способы зарабатывать на ИИ» с вилками цен с эфиров и PDF «Как участницы находили клиентов» '
         '— девять каналов первых заказов.</p></div>')
CRS = '<li><span class="b">{nn}</span><span><b>{title}</b> · {n}{yours}{tag}</span></li>'
CRS_REST = '<li><span class="b">—</span><span>и ещё {n_word}: {names}.</span></li>'
CRS_TAG = ' <em class="tag">под твой пробел</em>'
CRS_YOURS = ' <em class="tag">прямо про твой инструмент</em>'
# База мини-курсов платформы — реальные категории и числа уроков из снимка Потока 5 от
# 24.08.2026 (агент-API платформы; см. раздел «База платформы» в program.md — менять вместе).
# Первые три категории — про Claude Code, инструмент аудитории теста: флаг yours=True даёт
# пометку «прямо про твой инструмент». Четвёртый столбец — program-слаги КОНТРАКТА 6:
# пересечение с пробелами человека даёт пометку «под твой пробел» (маппинг — из program.md);
# "strong" — служебный маркер, подсветка только у сильного профиля (score11 >= 8).
# Пятый столбец — короткое имя для свёрнутой строки «и ещё N разделов: …»: строками на страницу
# идут только разделы с пометками, остальные перечисляются одной строкой (одинаковые короткие
# имена соседних разделов схлопываются в одно упоминание, счётчик N при этом честный).
# Последние две строки — вне 11 категорий: эфиры потока (research/packaging) и платёжные
# системы (payments) — новинка 6 потока, в снимке Потока 5 своей категории ещё нет.
CATS = [
    ("Claude Code", "3 урока", True, set(), "Claude Code"),
    ("Claude Cowork", "8 уроков", True, set(), "Claude Cowork"),
    ("АГЕНТ НА CLAUDE для продвинутых, терминал", "12 уроков, включая MCP-интеграции", True, {"mcp-bot"},
     "агент на Claude для продвинутых"),
    ("АГЕНТ НА CLAUDE для новичков", "16 уроков", False, {"agent"}, "агенты на Claude и GPT для новичков"),
    ("АГЕНТ НА GPT для новичков", "16 уроков", False, {"agent"}, "агенты на Claude и GPT для новичков"),
    ("Агенты. Openclaw & Hermes", "15 уроков", False, {"agent"}, "Openclaw & Hermes"),
    ("Предобучение", "14 уроков", False, set(), "предобучение"),
    ("ИИ Дизайн", "10 уроков", False, {"design"}, "ИИ-дизайн"),
    ("ИИ-верстка и дизайн-макеты Claude Design", "7 уроков", False, {"typography"}, "вёрстка в Claude Design"),
    ("Мини-апп в Telegram", "5 уроков", False, {"miniapp"}, "мини-аппы в Telegram"),
    ("Дополнительные уроки", "4 урока: GetCourse, лендинги, Оберег", False, {"site"}, "дополнительные уроки"),
    ("Эфиры потока", "14 эфиров: архитектура проекта, лендинг, воронка продаж, работа с клиентами, разборы трудностей",
     False, {"research", "packaging"}, "эфиры потока"),
    ("Платёжные системы", "новинка 6 потока", False, {"payments", "strong"}, "платёжные системы"),
]


def _clean(t):
    return re.sub(r"\s+", " ", t or "").strip()


def _strip_msgid(t):
    """msg #id — внутренняя ссылка для проверки цитат, на страницу не выводится."""
    return _clean(re.sub(r"\s*\(#[^)]*\)", "", t))


def parse_labs_map(path):
    """Куда-ведёт и кейсы по слагам привычек, группам фишек и program-слагам (+ лид сильного профиля)."""
    out = {"habits": {}, "groups": [], "program": {}, "strong_lead": ""}
    try:
        txt = open(path, encoding="utf-8").read()
    except Exception:
        return out
    for m in re.finditer(r"^### +([^\n]+)\n(.*?)(?=^### |^## |\Z)", txt, re.M | re.S):
        head, body = m.group(1).strip(), m.group(2)
        lead = re.search(r"\*\*Куда ведёт в ЛАБС:\*\*\s*(.*?)\n[ \t]*\n", body, re.S)
        case = re.search(r"\*\*Кейс:\*\*\s*(.*?)\n[ \t]*\n", body, re.S)
        entry = {"lead": _clean(lead.group(1)) if lead else "",
                 "case": _strip_msgid(case.group(1)) if case else ""}
        hm = re.match(r"([a-z][a-z-]*) — ", head)
        gm = re.match(r"Группа «(.+?)»:\s*(.+)$", head)
        if hm and hm.group(1) in HABITS:
            out["habits"][hm.group(1)] = entry
        elif hm:
            out["program"][hm.group(1)] = entry   # program-слаги (КОНТРАКТ 6), раздел «Программа ЛАБС-6»
        elif gm:
            out["groups"].append({"slugs": [s.strip() for s in gm.group(2).split(",")], **entry})
    sm = re.search(r"^## Сильный профиль.*?\*\*Куда ведёт в ЛАБС:\*\*\s*(.*?)\n[ \t]*\n", txt, re.M | re.S)
    if sm:
        out["strong_lead"] = _clean(sm.group(1))
    return out


# ── Программа ЛАБС-6 против истории (КОНТРАКТ 6) ────────────────────────────────
# Пункты — из program.md (снимок лендинга, обновляется вручную); отметки — из полей
# program_used / program_gaps result.json. Шаблоны согласованы с CSS scorecard.html
# (.prog / .pgrp / .pitem); плашки «уже делаешь» и «пробел» — классы .tag и .miss страницы.
P_GRP = '<div class="pgrp"><p class="pw">{week}</p>\n{items}</div>'
P_OK = ('<div class="pitem"><span class="pm">✓</span><span><b>{name}</b> — {does} '
        '<em class="tag">уже делаешь</em></span></div>')
P_GAP = ('<div class="pitem down"><span class="pm">—</span><span><b>{name}</b> — {does} '
         '<span class="miss">пробел</span></span></div>')
P_NC = '<div class="pitem"><span class="pm">·</span><span><b>{name}</b> — {does}</span></div>'


def parse_program(path):
    """program.md → дата снимка + пункты (слаг, имя, неделя, что делают) в порядке файла."""
    out = {"date": "", "items": []}
    try:
        txt = open(path, encoding="utf-8").read()
    except Exception:
        return out
    dm = re.search(r"\*\*Дата снимка:\*\*\s*([0-9.]+)", txt)
    if dm:
        out["date"] = dm.group(1).strip(".")
    for m in re.finditer(r"^### +([a-z][a-z-]*) — ([^\n]+)\n(.*?)(?=^### |^## |\Z)", txt, re.M | re.S):
        slug, name, body = m.group(1), m.group(2).strip(), m.group(3)
        wk = re.search(r"\*\*Неделя:\*\*\s*([^\n]+)", body)
        ds = re.search(r"\*\*Что делают:\*\*\s*(.*?)\n[ \t]*\n", body, re.S)
        out["items"].append({"slug": slug, "name": name,
                             "week": _clean(wk.group(1)) if wk else "",
                             "does": _clean(ds.group(1)).rstrip(".") if ds else ""})
    return out


def program_block(r, prog, quiz):
    """{{program_html}}, {{program_note}}, {{program_foot}}: пункты программы группами по неделям
    с отметками. program_used/program_gaps пустые или отсутствуют → блок сворачивается в одну
    строку (каталог без отметок — это прайс-лист, на страницу он не идёт): program_html и
    program_foot пустые, CSS страницы прячет пустые контейнеры."""
    used = set(r.get("program_used") or [])
    gaps = set(r.get("program_gaps") or [])
    if not (used or gaps):
        note = ("Чек-лист программы пропущен — пройди перемер, и раздел заполнится." if quiz else
                "Пункты программы в этот раз не проверяли — перемер заполнит раздел.")
        return "", note, ""
    groups = []
    for it in prog["items"]:
        if not groups or groups[-1][0] != it["week"]:
            groups.append((it["week"], []))
        groups[-1][1].append(it)
    parts = []
    for week, items in groups:
        lines = []
        for it in items:
            if it["slug"] in used:
                lines.append(P_OK.format(name=it["name"], does=it["does"]))
            elif it["slug"] in gaps:
                lines.append(P_GAP.format(name=it["name"], does=it["does"]))
            else:
                lines.append(P_NC.format(name=it["name"], does=it["does"]))
        parts.append(P_GRP.format(week=week, items="\n".join(lines)))
    if quiz:
        note = ("Отметки — по твоим ответам в чек-листе экспресс-теста. Галка — это ты уже "
                "делал; плашка «пробел» — этому в ЛАБС учат с нуля.")
    else:
        note = ("Отметки — по твоей реальной истории сессий. Галка — следы этого пункта уже "
                "есть в твоей работе; плашка «пробел» — этому в ЛАБС учат с нуля.")
    foot = (f"Программа — снимок лендинга от {prog['date'] or '24.08.2026'}; "
            "актуальная версия — на странице курса.")
    return "\n".join(parts), note, foot


def _habit_lower(slug):
    """Русское имя привычки со строчной буквы для текста заявки: «Спор с логикой» → «спор с логикой»."""
    if not slug:
        return ""
    name = NAMES.get(slug, slug)
    return name[0].lower() + name[1:] if re.match(r"^[А-ЯЁ]", name) else name


def _feature_short(slug):
    """Имя фишки без скобочной части и со строчной первой буквой для перечисления:
    «Хуки (…)» → «хуки»; латинские имена собственные (Claude, Managed Agents…) не трогаем."""
    name = re.sub(r"\s*\(.*\)$", "", FEATURE_NAMES.get(slug, slug))
    if re.match(r"^[А-ЯЁ][а-яё]", name):
        name = name[0].lower() + name[1:]
    return name


def labs_gaps_block(r, quiz, strong_profile, pitch_nonempty, bar_labels):
    """{{labs_gaps_html}}: привычки ниже базы и группы неиспользуемых фишек. Привычки из
    growth[:2] пропускаются, когда питч непустой (они уже разобраны в питче тем же кейсом) —
    кроме сильного профиля, где питч про «первые деньги» и пробелы в нём не разбираются.
    Пробелы программы ЛАБС-6 карточками сюда НЕ идут: они уже показаны плашками в блоке
    «Программа ЛАБС-6 против твоей истории» экраном выше, карточки их дублировали."""
    lm = parse_labs_map(os.path.join(SKILL, "labs_map.md"))
    habits = r.get("habits") or {}
    miss = "в заданиях не проявилась" if quiz else "ниже базы"
    skip = set((r.get("growth") or [])[:2]) if (pitch_nonempty and not strong_profile) else set()
    rows = []
    if strong_profile and lm["strong_lead"]:
        # имя трека уже стоит жирным в начале строки — из лида его убираем
        rows.append(GAP_S.format(lead=re.sub(r"^трек «первые деньги»:\s*", "", lm["strong_lead"])))
    for s in HABITS:
        if habits.get(s) or s in skip:
            continue
        e = lm["habits"].get(s)
        if e and e["lead"]:
            rows.append(GAP.format(name=bar_labels[s], miss=miss, lead=e["lead"],
                                   case=e["case"]))
    unused = set(r.get("features_unused") or [])
    for g in lm["groups"]:
        hit = [s for s in g["slugs"] if s in unused]
        if hit and g["lead"]:
            rows.append(GAP_F.format(names=", ".join(_feature_short(s) for s in hit),
                                     lead=g["lead"], case=g["case"]))
    if not rows:
        rows.append('<div class="gap"><p>Пробелов по шкале нет: привычки на уровне базы и выше, '
                    'пункты программы и проверенные фишки в работе. Смотри трек «первые деньги» '
                    'и мини-курсы ниже.</p></div>')
    return "\n".join(rows)


def labs_courses_block(gap_slugs):
    """{{labs_courses_html}}: категории базы платформы (CATS). Строками — только разделы
    с пометками («прямо про твой инструмент» / «под твой пробел»); остальные сворачиваются
    в одну строку «и ещё N разделов: …», чтобы каталог не превращался в простыню."""
    items, rest, rest_n = [], [], 0
    for title, n, yours, slugs, short in CATS:
        tagged = slugs & gap_slugs
        if yours or tagged:
            items.append(CRS.format(nn=f"{len(items) + 1:02d}", title=title, n=n,
                                    yours=CRS_YOURS if yours else "",
                                    tag=CRS_TAG if tagged else ""))
        else:
            rest_n += 1
            if short not in rest:
                rest.append(short)
    if rest:
        nw = (f"{rest_n} раздел" if rest_n % 10 == 1 and rest_n % 100 != 11 else
              f"{rest_n} раздела" if rest_n % 10 in (2, 3, 4) and rest_n % 100 not in (12, 13, 14) else
              f"{rest_n} разделов")
        items.append(CRS_REST.format(n_word=nw, names=", ".join(rest)))
    return "\n".join(items)
FEATURE_ITEMS = {
    "schedule": "<b>Плановые задачи — /schedule</b>. Claude сам запускает рутину по расписанию: утренняя сводка, регулярная проверка, отчёт к понедельнику.",
    "slash-commands": "<b>Свои слэш-команды</b>. Запрос, который ты набираешь третий раз, превращается в команду из одного слова.",
    "hooks": "<b>Хуки</b>. Правило «каждый раз перед X делай Y» выполняется само — память так не умеет, хук умеет.",
    "verification": "<b>Проверка результата</b>. Слово «докажи» заставляет Claude прогнать тест, открыть страницу, показать лог или скрин.",
    "code-review": "<b>/code-review и /security-review</b>. Ревью изменений перед выкаткой одной командой.",
    "plugins": "<b>Плагины</b>. Свои скиллы и команды раздаются команде одной строкой установки.",
    "subagents": "<b>Субагенты</b>. Роль эксперта, которую ты описываешь второй раз, фиксируется файлом и вызывается по имени.",
    "mcp": "<b>MCP-серверы</b>. Claude подключается к твоей базе, CRM или API напрямую, без копирования данных в чат.",
    "headless": "<b>Headless-режим</b>. <code>claude -p</code> встраивает Claude в скрипты и пайплайны с JSON-выводом.",
    "remote-control": "<b>Remote Control</b>. Ушёл от компьютера — сессия продолжается, следить можно с телефона.",
    "github-actions": "<b>GitHub Actions</b>. @claude сам ревьюит пул-реквесты и отвечает в issues.",
    "research": "<b>Research-режим</b>. Большое исследование без кода — в claude.ai, с источниками.",
    "managed-agents": "<b>Managed Agents</b>. Прод-агент с памятью и событиями без самописной обвязки.",
}
# Старые списочные фрагменты (strong_html/growth_html) — для совместимости, шаблон их не использует.
LI = '<li data-slug="{slug}"><b>{name}</b> — {hint}</li>'


def read_config(path):
    cfg = {}
    try:
        txt = open(path, encoding="utf-8").read()
    except Exception:
        return cfg
    m = re.search(r"```yaml\n(.*?)```", txt, re.S)
    for line in (m.group(1) if m else txt).splitlines():
        if ":" in line and not line.strip().startswith("#"):
            k, v = line.split(":", 1)
            cfg[k.strip()] = v.strip().strip('"').strip("'")
    return cfg


def fmt_date(iso):
    try:
        return datetime.date.fromisoformat(iso).strftime("%d.%m.%Y")
    except Exception:
        return iso or ""


def plural_dialog(n):
    """Дательный падеж: по 1 диалогу, по 68 диалогам (для бейджа — родительный ниже)."""
    n = int(n or 0)
    return f"{n} диалогу" if (n % 10 == 1 and n % 100 != 11) else f"{n} диалогам"


def plural_dialog_gen(n):
    """Родительный: 1 диалог, 2 диалога, 68 диалогов."""
    n = int(n or 0)
    if n % 10 == 1 and n % 100 != 11:
        return f"{n} диалог"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return f"{n} диалога"
    return f"{n} диалогов"


def fmt_pct(x):
    return "—" if x is None else f"{x:.0f}%"


def features_block(r):
    """{{features_html}}: список неиспользуемых фишек; пустой список — честная строка вместо пустого блока."""
    unused = r.get("features_unused") or []
    used = r.get("features_used") or []
    if unused:
        return "\n".join(FLI.format(nn=f"{i:02d}", text=FEATURE_ITEMS.get(s, FEATURE_NAMES.get(s, s)))
                          for i, s in enumerate(unused, 1))
    if used:
        return FLI.format(nn="—", text="Всё из этого списка уже в работе — добавить нечего.")
    return FLI.format(nn="—", text="Фишки в этот раз не проверялись. Авто-замер посмотрит их по твоим настройкам и логам — скажи «перемерь», когда наберётся реальная история.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", default=os.path.join(SKILL, "scorecard.html"))
    ap.add_argument("--result", default=common.RESULT)
    ap.add_argument("--prev", default=common.PREV)
    ap.add_argument("--pitch", default=None)
    ap.add_argument("--config", default=os.path.join(SKILL, "config.md"))
    ap.add_argument("--utm-content", default=None)
    ap.add_argument("--out", default=os.path.expanduser("~/.claude/ii-master-result.html"))
    ap.add_argument("--open", action="store_true")
    a = ap.parse_args()

    r = json.load(open(a.result, encoding="utf-8"))
    cfg = read_config(a.config)
    tpl = open(a.template, encoding="utf-8").read()
    # Шапка-дока шаблона не для выдачи: срезать первый комментарий, сохранив <!doctype> перед ним.
    tpl = re.sub(r"^(\ufeff?\s*(?:<!doctype[^>]*>)?\s*)<!--.*?-->\s*", r"\1", tpl, count=1, flags=re.S | re.I)
    quiz = r.get("mode") == "quiz"
    rates = r.get("habit_rates") or {}
    habits = r.get("habits") or {}
    strong_profile = bool((r.get("extra") or {}).get("strong_profile")) or (r.get("score11") or 0) >= 8  # КОНТРАКТ 5

    # Чекаут-ссылка — РЕЗЕРВ: собирается и печатается в консоль, но в CTA страницы не идёт.
    utm = a.utm_content or ("first-money" if strong_profile else ((r.get("growth") or ["tools"])[0]))
    cta_url = (f"{cfg.get('checkout_url', '')}?utm_source={cfg.get('utm_source', '')}"
               f"&utm_medium={cfg.get('utm_medium', '')}&utm_campaign={cfg.get('utm_campaign', '')}&utm_content={utm}")

    bars, per = [], {}
    for slug in HABITS:
        rate = rates.get(slug)
        shown = bool(habits.get(slug))
        base = BASE[slug]
        if quiz or rate is None:
            pct = 100 if shown else 0
            nums = f"<b>есть</b> / {base:.0f}" if shown else f"нет / {base:.0f}"
            cls = "yes" if shown else "no"
        else:
            pct = max(0, min(100, rate))
            nums = f"<b>{rate:.0f}</b> / {base:.0f}"
            cls = "above" if shown else "below"
        bars.append(ROW.format(down="" if shown else " down", lab=BAR_LABELS[slug], defn=DEFS[slug],
                               width=f"{pct:.1f}".rstrip("0").rstrip("."), base=f"{base:.1f}".rstrip("0").rstrip("."),
                               nums=nums))
        per[f"rate_{slug}"] = fmt_pct(rate) if not quiz else ("есть" if shown else "нет")
        per[f"pct_{slug}"] = f"{pct:.0f}"
        per[f"base_{slug}"] = f"{base:.0f}"
        per[f"cls_{slug}"] = cls
        per[f"name_{slug}"] = NAMES[slug]
        per[f"flag_{slug}"] = "1" if shown else "0"

    emoji = "".join("🟩" if habits.get(s) else "⬜" for s in HABITS)
    score = r.get("score11")
    n = r.get("dialogs_n")
    above_base = sum(1 for s in HABITS if habits.get(s))   # привычек не ниже базы = зелёные полосы
    if quiz:
        mode_badge = "экспресс-тест"
        caption = "в экспресс-тесте"
        score_note = "привычек показано в трёх заданиях"
        score_tile_k = "Твой результат"
        # Тайл «Выше среднего пользователя» в квизе скрыт (класс off): балл квиза уже равен числу
        # показанных привычек, отдельный тайл дублировал бы главный.
        above_tile_cls = " off"
        profile_note = ("Полоса — показана привычка в трёх заданиях или нет; штрих — доля диалогов "
                        "с этой привычкой в исследовании Anthropic. Рыжим — привычки, которые "
                        "в заданиях не проявились.")
    else:
        mode_badge = f"по реальной истории · {plural_dialog_gen(n)}"
        caption = "в среднем за диалог"
        score_note = ("Привычка засчитывается диалогу, только если в нём проявилась. "
                      f"{'Балл' if score is None else score} — сколько привычек набирается в среднем "
                      f"за один твой диалог; посчитано по {plural_dialog(n)}.")
        score_tile_k = "В среднем за диалог"
        above_tile_cls = ""
        profile_note = ("Полоса — в какой доле твоих диалогов привычка встретилась; штрих — то же "
                        "по исследованию Anthropic. Зелёная полоса — по этой привычке ты выше среднего "
                        "пользователя. Это про частоту: привычка может быть зелёной и при этом "
                        "встречаться через диалог, поэтому зелёных полос обычно больше, чем привычек "
                        "в среднем за диалог. Рыжим — привычки реже базы.")

    delta_html = ""      # КОНТРАКТ 5: слот {{delta_html}} — пустая строка при первом замере
    if os.path.exists(a.prev):
        try:
            p = json.load(open(a.prev, encoding="utf-8"))
            parts = []
            for slug in HABITS:
                pr, cr = (p.get("habit_rates") or {}).get(slug), rates.get(slug)
                if pr is not None and cr is not None and abs(cr - pr) >= 5:
                    parts.append(f"{NAMES[slug]} {pr:.0f}% → {cr:.0f}%")
            was_quiz = " (экспресс-тест)" if p.get("mode") == "quiz" else ""
            # слот в scorecard.html — <section class="delta">: разметка с собственным h2, пустая
            # строка оставляет секцию пустой и CSS её прячет (section.delta:empty)
            delta_html = ("<h2>Перемер: было → стало</h2>"
                          f"<p class=\"fine\">Прошлый замер {fmt_date(p.get('date'))}{was_quiz}: "
                          f"{p.get('score11')} из 11 → сейчас {score} из 11." +
                          (" Заметнее всего изменилось: " + "; ".join(parts) + "." if parts else "") + "</p>")
        except Exception:
            pass

    pitch = ""
    if a.pitch and os.path.exists(a.pitch):
        pitch = open(a.pitch, encoding="utf-8").read()

    # Программа ЛАБС-6 против истории (КОНТРАКТ 6): пункты из program.md, отметки из result.json.
    prog = parse_program(os.path.join(SKILL, "program.md"))
    program_html, program_note, program_foot = program_block(r, prog, quiz)

    # Блок «ЛАБС»: строки по всем пробелам человека из labs_map.md + категории с подсветкой.
    # Подсветку категорий дают ТОЛЬКО пробелы программы (+ strong): слаг research есть и у фишек
    # Claude, и в программе — фишки в маппинге категорий не участвуют, иначе ложная подсветка.
    cat_slugs = set(r.get("program_gaps") or [])
    if strong_profile:
        cat_slugs.add("strong")
    labs_gaps_html = labs_gaps_block(r, quiz, strong_profile, bool(pitch.strip()), BAR_LABELS)
    labs_courses_html = labs_courses_block(cat_slugs)

    # CTA страницы — заявка менеджеру (блок «Менеджер продаж» в config.md).
    # Текст заявки — это первичка для менеджера: балл, метод замера, зона роста и имя;
    # render.py собирает его из шаблона manager_prefill и кладёт в обе ссылки (Telegram и
    # WhatsApp) сам — гарантия URL-кодировки и единственная атрибуция «пришёл с теста».
    # Предложение с {name} или {growth} выбрасывается целиком, если данных нет.
    x = "?" if score is None else str(score)
    ask_prefill = cfg.get("manager_prefill", "")
    for ph, val in (("name", (r.get("name") or "").strip()),
                    ("growth", _habit_lower((r.get("growth") or [None])[0]))):
        if val:
            ask_prefill = ask_prefill.replace("{" + ph + "}", val)
        else:
            ask_prefill = re.sub(r"[^.!?]*\{" + ph + r"\}[^.!?]*[.!?]", "", ask_prefill)
    ask_prefill = (ask_prefill.replace("{score11}", x)
                   .replace("{method}", "экспресс-тест" if quiz else "замер по реальной истории"))
    ask_prefill = re.sub(r"\s{2,}", " ", ask_prefill).strip()
    q_prefill = urllib.parse.quote(ask_prefill, safe="")
    ask_wa_url = f"https://wa.me/{cfg.get('manager_phone_raw', '')}?text={q_prefill}"
    # Telegram: t.me/<ник>?text=… — официальные клиенты подставляют текст черновиком в поле ввода.
    ask_tg_url = f"{cfg.get('manager_telegram', '').rstrip('/')}?text={q_prefill}"
    # MAX: прямой ссылки по номеру у MAX нет. Пока ника нет — кнопки нет вовсе, под кнопками
    # выходит строка max_hint (номер Кати в MAX). Появился ник — кнопка встаёт в ряд третьей.
    max_user = cfg.get("max_username", "")
    ask_max_btn = f'<a class="abtn" href="https://max.ru/{html.escape(max_user)}">MAX</a>' if max_user else ""
    max_note_html = "" if max_user else f'<p class="fine">{html.escape(cfg.get("max_hint", ""))}</p>'

    sub = {
        "name": html.escape(r.get("name") or ""),      # пустое имя — шаблон сам уберёт двоеточие
        "mode_badge": mode_badge,
        "date": fmt_date(r.get("date")),
        "score11": "" if score is None else str(score),
        "score_caption": caption,
        "score_note": score_note,
        "score_tile_k": score_tile_k,
        "above_base": str(above_base),
        "above_tile_cls": above_tile_cls,
        "profile_note": profile_note,
        "composite_pct": "—" if r.get("composite_pct") is None else f"{r['composite_pct']:.1f}".replace(".", ",") + "%",
        "dialogs_n": "—" if n is None else str(n),
        "base_per_dialog": "3–4",
        "emoji_bar": emoji,
        "bars_html": "\n".join(bars),
        "strong_html": "\n".join(LI.format(slug=s, name=NAMES[s], hint=html.escape(HINTS[s])) for s in r.get("strong") or []),
        "growth_html": "\n".join(LI.format(slug=s, name=NAMES[s], hint=html.escape(HINTS[s])) for s in r.get("growth") or []),
        "features_html": features_block(r),
        "features_used_html": "\n".join(FLI.format(nn=f"{i:02d}", text=FEATURE_ITEMS.get(s, FEATURE_NAMES.get(s, s)))
                                         for i, s in enumerate(r.get("features_used") or [], 1)),
        "pitch_html": pitch,
        "program_html": program_html,
        "program_note": program_note,
        "program_foot": program_foot,
        "program_date": prog["date"] or "24.08.2026",
        "labs_gaps_html": labs_gaps_html,
        "labs_courses_html": labs_courses_html,
        "price": cfg.get("price", ""),
        "price_installment": cfg.get("price_installment", "6 665 ₽/мес"),
        "defense_date": cfg.get("defense_date", "20 сентября"),
        "ask_label": cfg.get("ask_label", "Подать заявку в ЛАБС 6"),
        "ask_wa_url": ask_wa_url,
        "ask_tg_url": ask_tg_url,
        "ask_max_btn": ask_max_btn,
        "max_note_html": max_note_html,
        "ask_prefill": html.escape(ask_prefill),
        "manager_name": html.escape(cfg.get("manager_name", "")),
        "manager_phone": cfg.get("manager_phone", ""),
        # cta_url/cta_label — резерв (чекаут): шаблон их больше не использует
        "cta_url": cta_url,
        "cta_label": cfg.get("cta_label_strong" if strong_profile else "cta_label", "Посмотреть программу ЛАБС"),
        "test_url": cfg.get("test_url", ""),
        "handle": cfg.get("handle", ""),
        "test_name": cfg.get("test_name", "ИИ-мастер"),
        "delta_html": delta_html,
    }
    sub.update(per)

    # re.sub заменяет КАЖДЫЙ плейсхолдер во ВСЕХ вхождениях (mode_badge и score11 в шаблоне дважды).
    missing = set(re.findall(r"{{\s*([a-z0-9_]+)\s*}}", tpl)) - set(sub)
    out = re.sub(r"{{\s*([a-z0-9_]+)\s*}}", lambda m: sub.get(m.group(1), m.group(0)), tpl)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(out)
    print("страница:", a.out)
    print("полоса:", emoji, f"{'' if score is None else score} из 11")
    print("заявка Telegram:", ask_tg_url)
    print("заявка WhatsApp:", ask_wa_url)
    print("заявка MAX:", ("https://max.ru/" + max_user) if max_user else cfg.get("max_hint", ""))
    print("текст заявки:", ask_prefill)
    print("чекаут (резерв, в CTA не используется):", cta_url)
    if missing:
        print("в шаблоне есть плейсхолдеры без данных:", ", ".join(sorted(missing)))
    if a.open:
        webbrowser.open("file://" + a.out)


if __name__ == "__main__":
    main()
