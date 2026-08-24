#!/usr/bin/env python3
"""Шаг 2 замера «ИИ-мастер»: оставить только то, что писал человек.

Режет служебное (хуки, уведомления задач, служебные вставки скиллов, продолжения сессий),
отбрасывает одноходовые тривиальные сессии и сессии самого теста, схлопывает дубли
(одинаковое первое сообщение в один день — остаётся самая длинная).

Пишет в рабочую папку: clean_sessions.json (все), clean_multiturn.json (2+ реплики —
их размечаем), и печатает строку SUMMARY {...} для роутера.

Параметры:
  --substantive N   порог «содержательной» сессии в репликах (по умолчанию 11) — только для
                    статистики и сравнения с другими людьми, в индексе участвуют все многоходовые
  --min-multiturn N сколько многоходовых нужно для авто-замера (по умолчанию 5)
  --max-sessions N  сколько самых свежих многоходовых размечать (по умолчанию 80)
"""
import argparse, collections, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

NOISE_PREFIX = ("<task-notification>", "<local-command-caveat>", "Base directory for this skill:",
                "This session is being continued from", "Continue from where you left off.",
                "[Request interrupted by user]", "<command-name>", "Caveat: The messages below",
                "<system-reminder>", "API Error", "[Image:", "<ide_selection>", "<ide_opened_file>")
AUTO_SESS = ("вызван хуком", "<<autonomous-loop", "Analyze this codebase and generate",
             "<task-notification>")
TRIV = {"тест", "test", "готово", "да", "ок", "ok", "?", "привет", "hi", "hello", "спасибо"}
# Сессии самого теста в замер не идут.
SELF_TEST = re.compile(r"ИИ-мастер|ии-мастер|AI Fluency|пройди тест|перемерь|оцени,? как я работаю с ИИ|"
                       r"замерь мои навыки|какие фишки Claude", re.I)


def authored(t):
    t = t.strip()
    if not t:
        return None
    if any(t.startswith(p) for p in NOISE_PREFIX):
        return None
    if t.startswith("<channel source="):      # сообщение, пришедшее через канал (например, Telegram)
        t = re.sub(r"^<channel[^>]*>", "", t)
        t = re.sub(r"</channel>\s*$", "", t).strip()
    if t.startswith("[Image"):
        return None
    return t or None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=common.WORK)
    ap.add_argument("--substantive", type=int, default=11)
    ap.add_argument("--min-multiturn", type=int, default=5)
    ap.add_argument("--max-sessions", type=int, default=80)
    a = ap.parse_args()
    common.WORK = a.work

    S = json.load(open(common.wpath("sessions.json"), encoding="utf-8"))
    out = []
    for s in S:
        if any(x in s["msgs"][0]["text"][:400] for x in AUTO_SESS):
            continue
        msgs = []
        for m in s["msgs"]:
            t = authored(m["text"])
            if t:
                msgs.append({"ts": m["ts"], "text": t})
        if not msgs:
            continue
        if len(msgs) == 1 and (len(msgs[0]["text"]) < 25 or msgs[0]["text"].strip().lower() in TRIV):
            continue
        if SELF_TEST.search(msgs[0]["text"][:300]):
            continue
        s2 = dict(s)
        s2["msgs"] = msgs
        s2["n_user"] = len(msgs)
        s2["chars"] = sum(len(m["text"]) for m in msgs)
        out.append(s2)

    # Дубли: одинаковое начало первого сообщения в тот же день — оставляем самую длинную.
    best = {}
    for s in out:
        key = (s["msgs"][0]["text"][:200], (s["start"] or "")[:10])
        if key not in best or s["n_user"] > best[key]["n_user"]:
            best[key] = s
    out = sorted(best.values(), key=lambda s: s["start"] or "")
    for i, s in enumerate(out, 1):
        s["sid"] = i

    json.dump(out, open(common.wpath("clean_sessions.json"), "w", encoding="utf-8"), ensure_ascii=False)
    n = [s["n_user"] for s in out]
    print("сессий после чистки:", len(out), "| реплик:", sum(n), "| символов:", sum(s["chars"] for s in out))
    print("распределение по длине: 1=%d 2-4=%d 5-9=%d 10-19=%d 20+=%d" % (
        sum(1 for x in n if x == 1), sum(1 for x in n if 2 <= x <= 4), sum(1 for x in n if 5 <= x <= 9),
        sum(1 for x in n if 10 <= x <= 19), sum(1 for x in n if x >= 20)))
    mt_all = [s for s in out if s["n_user"] >= 2]
    substantive = sum(1 for s in mt_all if s["n_user"] >= a.substantive)
    mt = mt_all[-a.max_sessions:] if len(mt_all) > a.max_sessions else mt_all
    json.dump(mt, open(common.wpath("clean_multiturn.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print("многоходовых (2+ реплики):", len(mt_all), "| из них содержательных (%d+ реплик): %d" % (a.substantive, substantive),
          "| в разметку идут самые свежие: %d" % len(mt))
    print("месяцы:", dict(sorted(collections.Counter((s["start"] or "?")[:7] for s in out).items())))
    route = "auto" if len(mt_all) >= a.min_multiturn else "quiz"
    print("SUMMARY", json.dumps({"sessions": len(out), "multiturn": len(mt_all), "to_mark": len(mt), "substantive": substantive,
                                 "threshold": a.min_multiturn, "route": route,
                                 "work": common.WORK}, ensure_ascii=False))


if __name__ == "__main__":
    main()
