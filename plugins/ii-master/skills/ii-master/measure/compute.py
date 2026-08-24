#!/usr/bin/env python3
"""Шаг 5 замера «ИИ-мастер»: профиль против базы Anthropic и result.json по контракту.

Вход: файлы ручной разметки flags*.json в рабочей папке. Схема файла:
  {"cols": ["iter","goal",...,"verify"], "S1": [1,0,...], "S2": [...]}   (12 нулей/единиц)
Необязательно: features.json (из features.py), dedup.json {"keep":[sid,...]}.

Выход: ~/.claude/ii-master-result.json (КОНТРАКТ 2), прежний результат сохраняется в
~/.claude/ii-master-result.prev.json, в консоль — таблица и дельта к прошлому замеру.

  python3 compute.py [--name "Имя"] [--mark-used research,headless] [--mark-unused managed-agents]
                     [--out PATH] [--work DIR]
"""
import argparse, datetime, glob, json, os, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from common import BASE, COLS, HABITS, NAMES


def load_flags(work):
    flags = {}
    for f in sorted(glob.glob(os.path.join(work, "flags*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        cols = d.get("cols", COLS)
        if cols[:11] != HABITS:
            sys.exit(f"{f}: порядок колонок не по контракту: {cols}")
        for k, v in d.items():
            if k == "cols":
                continue
            if not (isinstance(v, list) and len(v) >= 11 and all(x in (0, 1) for x in v)):
                sys.exit(f"{f}: {k}: нужен список из 11–12 нулей/единиц")
            flags[int(k.lstrip("Ss"))] = list(v) + [0] * (12 - len(v))
    return flags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=common.WORK)
    ap.add_argument("--name", default=None)
    ap.add_argument("--features", default=None)
    ap.add_argument("--mark-used", default="")
    ap.add_argument("--mark-unused", default="")
    ap.add_argument("--out", default=common.RESULT)
    ap.add_argument("--date", default=None)
    a = ap.parse_args()
    common.WORK = a.work

    flags = load_flags(a.work)
    if not flags:
        sys.exit("нет файлов разметки flags*.json в " + a.work)
    keep = set(flags)
    dd = os.path.join(a.work, "dedup.json")
    if os.path.exists(dd):
        keep &= set(json.load(open(dd))["keep"])
    sids = sorted(keep)
    N = len(sids)
    if N == 0:
        sys.exit("после dedup не осталось ни одной размеченной сессии — нечего считать")

    rates = {c: round(100 * sum(flags[s][i] for s in sids) / N, 1) for i, c in enumerate(HABITS)}
    verify_rate = round(100 * sum(flags[s][11] for s in sids) / N, 1)
    habits = {c: int(rates[c] >= BASE[c]) for c in HABITS}
    per = [sum(flags[s][:11]) for s in sids]
    mean_per = sum(per) / N
    score11 = int(mean_per + 0.5)      # арифметическое округление: 4.5 → 5, банковское занижало бы
    composite = round(sum(rates.values()) / 11, 1)
    delta = {c: rates[c] - BASE[c] for c in HABITS}
    strong = [c for c in sorted(HABITS, key=lambda c: -delta[c]) if delta[c] >= 0][:3]
    growth = [c for c in sorted(HABITS, key=lambda c: delta[c]) if delta[c] < 0][:2]
    # growth пуст, когда все привычки на уровне базы; питч тогда собирается по фишкам (utm_content=tools)

    # Фишки: features.json + ответы пользователя на «неизвестно».
    fpath = a.features or os.path.join(a.work, "features.json")
    used, unused, unknown = [], [], []
    features_checked = os.path.exists(fpath)
    if features_checked:
        fj = json.load(open(fpath, encoding="utf-8"))
        used, unused, unknown = list(fj.get("used", [])), list(fj.get("unused", [])), list(fj.get("unknown", []))
    else:
        print("ПРЕДУПРЕЖДЕНИЕ: features.json не найден — фишки не проверялись, списки останутся пустыми")
    if features_checked and verify_rate >= 15 and "verification" not in used:  # ручная колонка verify точнее регулярки
        used.append("verification")
        for lst in (unused, unknown):
            if "verification" in lst:
                lst.remove("verification")
    for s in filter(None, a.mark_used.split(",")):
        used.append(s.strip())
    for s in filter(None, a.mark_unused.split(",")):
        unused.append(s.strip())
    used = [s for s in common.FEATURES if s in used]
    if features_checked or used:
        unused = [s for s in common.FEATURES if s not in used and (s in unused or s in unknown)]
    # не отвеченные «неизвестно» считаем неиспользованными — об этом скилл говорит пользователю;
    # без features.json оба списка пустые → страница покажет «фишки не проверялись»

    result = {
        "version": 1, "mode": "auto",
        "date": a.date or datetime.date.today().isoformat(),
        "name": a.name or None,
        "dialogs_n": N, "score11": score11, "composite_pct": composite,
        "habits": habits, "habit_rates": rates,
        "strong": strong, "growth": growth,
        "features_unused": unused, "features_used": used,
        "extra": {"mean_per_dialog": round(mean_per, 2), "verify_rate": verify_rate,
                  "base_composite": common.BASE_COMPOSITE, "base_per_dialog": common.BASE_PER_DIALOG,
                  "strong_profile": score11 >= 8},      # КОНТРАКТ 5: единое правило для авто и квиза
    }

    prev = None
    prev_path = common.PREV if os.path.abspath(a.out) == os.path.abspath(common.RESULT) else a.out + ".prev"
    if os.path.exists(a.out):
        try:
            prev = json.load(open(a.out, encoding="utf-8"))
            shutil.copy(a.out, prev_path)
        except Exception:
            prev = None
    json.dump(result, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"диалогов в замере: {N}")
    for c in HABITS:
        flag = "+" if habits[c] else "-"
        line = f"{NAMES[c]:16s} {rates[c]:5.1f}%  база {BASE[c]:5.1f}%  {delta[c]:+6.1f} пп  {flag}"
        if prev and prev.get("habit_rates") and c in prev["habit_rates"] and prev["habit_rates"][c] is not None:
            line += f"   было {prev['habit_rates'][c]:5.1f}%  Δ {rates[c] - prev['habit_rates'][c]:+5.1f}"
        print(line)
    print(f"проверка «докажи» (вне индекса): {verify_rate:.1f}%")
    print(f"составной индекс: {composite:.1f}% против базы {common.BASE_COMPOSITE}%")
    print(f"привычек на диалог: {mean_per:.2f} → {score11} из 11 (база {common.BASE_PER_DIALOG})")
    print("сильное:", ", ".join(NAMES[c] for c in strong), "| зона роста:", ", ".join(NAMES[c] for c in growth))
    print("фишки используются:", ", ".join(used) or "—")
    print("фишки не используются:", ", ".join(unused) or "—")
    if prev:
        print(f"прошлый замер {prev.get('date')}: {prev.get('score11')} из 11, индекс {prev.get('composite_pct')}% → "
              f"сейчас {score11} из 11, индекс {composite}% (прежний файл: {prev_path})")
    print("записано:", a.out)


if __name__ == "__main__":
    main()
