#!/usr/bin/env python3
"""Шаг 6: собрать страницу результата из scorecard.html и result.json.

Подставляет плейсхолдеры {{...}} (список — в MEASURE.md), пишет ~/.claude/ii-master-result.html
и по флагу --open открывает её в браузере по умолчанию. Сеть не нужна.

  python3 render.py [--pitch pitch.html] [--utm-content examples] [--open]
                    [--template ../scorecard.html] [--result ~/.claude/ii-master-result.json]
                    [--config ../config.md] [--out ~/.claude/ii-master-result.html]
"""
import argparse, datetime, html, json, os, re, sys, webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import BASE, HABITS, NAMES, HINTS, FEATURES, FEATURE_NAMES

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)

# Разметка фрагментов — ровно та, которую ждёт scorecard.html (шаблоны и подписи
# продублированы в HTML-комментариях самого шаблона; менять здесь и там вместе).
ROW = ('<div class="row{down}"><span class="lab">{lab}</span>'
       '<span class="track"><span class="fill" style="width:{width}%"></span>'
       '<span class="tickline" style="left:{base}%"></span></span>'
       '<span class="nums">{nums}</span></div>')
BAR_LABELS = {"iter": "Итерирует и уточняет", "goal": "Проясняет цель до просьбы",
              "examples": "Даёт образцы «как надо»", "format": "Задаёт формат и структуру",
              "mode": "Назначает роль и правила", "tone": "Проговаривает тон и стиль",
              "context": "Даёт контекст, которого у модели нет", "audience": "Называет адресата",
              "reason": "Оспаривает логику модели", "approach": "Советуется о подходе до старта",
              "fact": "Проверяет факты и цифры"}
FLI = '<li><span class="b">{nn}</span><span>{text}</span></li>'
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
    tpl = re.sub(r"^\ufeff?\s*<!--.*?-->\s*", "", tpl, count=1, flags=re.S)   # шапка-дока шаблона не для выдачи
    quiz = r.get("mode") == "quiz"
    rates = r.get("habit_rates") or {}
    habits = r.get("habits") or {}
    strong_profile = bool((r.get("extra") or {}).get("strong_profile")) or (r.get("score11") or 0) >= 8  # КОНТРАКТ 5

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
        bars.append(ROW.format(down="" if shown else " down", lab=BAR_LABELS[slug],
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
    if quiz:
        mode_badge = "экспресс-тест"
        caption = "в экспресс-тесте"
        score_note = "привычек показано в трёх заданиях"
    else:
        mode_badge = f"по реальной истории · {plural_dialog_gen(n)}"
        caption = "в среднем на диалог"
        score_note = f"привычек в среднем на диалог — по {plural_dialog(n)}"

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

    sub = {
        "name": html.escape(r.get("name") or ""),      # пустое имя — шаблон сам уберёт двоеточие
        "mode_badge": mode_badge,
        "date": fmt_date(r.get("date")),
        "score11": "" if score is None else str(score),
        "score_caption": caption,
        "score_note": score_note,
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
    print("ссылка оплаты:", cta_url)
    if missing:
        print("в шаблоне есть плейсхолдеры без данных:", ", ".join(sorted(missing)))
    if a.open:
        webbrowser.open("file://" + a.out)


if __name__ == "__main__":
    main()
