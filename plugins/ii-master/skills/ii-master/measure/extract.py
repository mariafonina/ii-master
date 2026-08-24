#!/usr/bin/env python3
"""Шаг 1 замера «ИИ-мастер»: собрать реплики пользователя из логов Claude Code.

Читает ~/.claude/projects/*/*.jsonl (или II_MASTER_PROJECTS), отбрасывает побочные ветки
субагентов и результаты инструментов, пишет sessions.json в рабочую папку (II_MASTER_WORK,
по умолчанию ~/.claude/ii-master-work). Никуда ничего не отправляет.

Запуск: python3 extract.py [--projects DIR] [--work DIR]
"""
import argparse, collections, glob, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

SYSRE = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
CMD = re.compile(r"<command-(name|message|args)>.*?</command-\1>", re.S)
CMDNAME = re.compile(r"<command-name>\s*/?([^<\s]+)\s*</command-name>")
LOCAL = re.compile(r"<local-command-stdout>.*?</local-command-stdout>", re.S)


def clean(t):
    t = SYSRE.sub("", t)
    t = CMD.sub("", t)
    t = LOCAL.sub("", t)
    return t.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--projects", default=common.PROJECTS)
    ap.add_argument("--work", default=common.WORK)
    a = ap.parse_args()
    common.WORK = a.work

    sessions = []
    files = glob.glob(os.path.join(a.projects, "*", "*.jsonl"))
    for f in files:
        proj = os.path.basename(os.path.dirname(f))
        msgs, ts_first, ts_last = [], None, None
        n_assistant = n_tools = n_side = 0
        meta_cwd = None
        tools = collections.Counter()
        commands = []
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    if d.get("isSidechain"):
                        n_side += 1
                        continue
                    ts = d.get("timestamp")
                    if ts:
                        ts_first = ts_first or ts
                        ts_last = ts
                    meta_cwd = meta_cwd or d.get("cwd")
                    t = d.get("type")
                    if t == "assistant":
                        n_assistant += 1
                        c = (d.get("message") or {}).get("content")
                        if isinstance(c, list):
                            for b in c:
                                if isinstance(b, dict) and b.get("type") == "tool_use":
                                    n_tools += 1
                                    tools[str(b.get("name"))] += 1
                    elif t == "user":
                        if d.get("isMeta") or d.get("sourceToolUseID"):
                            continue          # вставки обвязки (payload скиллов и т.п.), не человек
                        m = d.get("message") or {}
                        c = m.get("content")
                        texts = []
                        if isinstance(c, str):
                            texts.append(c)
                        elif isinstance(c, list):
                            for b in c:
                                if isinstance(b, dict) and b.get("type") == "text":
                                    texts.append(b.get("text", ""))
                        raw = "\n".join(texts)
                        commands += CMDNAME.findall(raw)
                        txt = clean(raw)
                        if txt and not d.get("toolUseResult"):
                            msgs.append({"ts": ts, "text": txt})
        except Exception:
            continue
        if not msgs:
            continue
        sessions.append({
            "file": f, "project": proj, "cwd": meta_cwd,
            "start": ts_first, "end": ts_last,
            "n_user": len(msgs), "n_assistant": n_assistant, "n_tools": n_tools,
            "n_sidechain": n_side, "tools": dict(tools), "commands": commands,
            "chars": sum(len(m["text"]) for m in msgs),
            "msgs": msgs,
        })

    sessions.sort(key=lambda s: s["start"] or "")
    out = common.wpath("sessions.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(sessions, fh, ensure_ascii=False)

    print(f"файлов логов: {len(files)} | сессий с репликами пользователя: {len(sessions)}")
    print("реплик пользователя всего:", sum(s["n_user"] for s in sessions))
    byproj = collections.Counter(s["project"] for s in sessions)
    print("проектов:", len(byproj))
    dates = collections.Counter((s["start"] or "?")[:7] for s in sessions)
    print("по месяцам:", dict(sorted(dates.items())))
    print("многоходовых (2+ реплики, до чистки):", sum(1 for s in sessions if s["n_user"] >= 2))
    print("записано:", out)


if __name__ == "__main__":
    main()
