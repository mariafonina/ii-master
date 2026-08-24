#!/usr/bin/env python3
"""Шаг 3 (подготовка к разметке): показать реплики пользователя по сессиям.

  python3 show.py --list                 список сессий: sid, дата, проект, число реплик
  python3 show.py --batch 1 [--size 12]  пачка сессий для ручной разметки (1-я, 2-я, …)
  python3 show.py --sid 7 [--full]       одна сессия; --full без обрезки длинных реплик
  python3 show.py --batches [--size 12]  сколько всего пачек

Показываются только реплики пользователя (ответы модели в индексе не участвуют).
Длинные реплики обрезаются до --max-chars (по умолчанию 2500) символов.
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common


def label(s):
    cwd = s.get("cwd") or s.get("project") or ""
    return os.path.basename(cwd.rstrip("/")) or cwd


def show(s, max_chars):
    print(f"=== S{s['sid']} | {(s.get('start') or '')[:10]} | {label(s)} | реплик: {s['n_user']} ===")
    for i, m in enumerate(s["msgs"], 1):
        t = m["text"]
        if max_chars and len(t) > max_chars:
            t = t[:max_chars] + f"\n[… обрезано {len(t) - max_chars} симв.; полностью: show.py --sid {s['sid']} --full]"
        print(f"[{i}] {t}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=common.WORK)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--batches", action="store_true")
    ap.add_argument("--batch", type=int)
    ap.add_argument("--size", type=int, default=12)
    ap.add_argument("--sid", type=int)
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--max-chars", type=int, default=2500)
    a = ap.parse_args()
    common.WORK = a.work
    mt = json.load(open(common.wpath("clean_multiturn.json"), encoding="utf-8"))
    n_batches = (len(mt) + a.size - 1) // a.size
    if a.list:
        for s in mt:
            print(f"S{s['sid']:<4} {(s.get('start') or '')[:10]}  {s['n_user']:>3} реплик  {label(s)}")
        print(f"всего: {len(mt)} сессий, пачек по {a.size}: {n_batches}")
    elif a.batches:
        print(n_batches)
    elif a.sid:
        for s in mt:
            if s["sid"] == a.sid:
                show(s, 0 if a.full else a.max_chars)
                break
        else:
            print("нет такой сессии среди многоходовых")
    elif a.batch:
        chunk = mt[(a.batch - 1) * a.size: a.batch * a.size]
        print(f"# пачка {a.batch} из {n_batches}: сессии " + ", ".join(f"S{s['sid']}" for s in chunk) + "\n")
        for s in chunk:
            show(s, a.max_chars)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
