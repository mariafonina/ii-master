#!/usr/bin/env python3
"""Собирает ~/.claude/ii-master-card.html: берёт шаблон карточки, добавляет в данные поля подвала
(контракт 5) и инлайнит JSON между маркерами DATA.

Запуск:  python3 inline_data.py [путь к result.json] [путь к выходному html]
Без аргументов: вход ~/.claude/ii-master-result.json, выход ~/.claude/ii-master-card.html.

Путь к шаблону не зависит от окружения: CLAUDE_PLUGIN_ROOT берётся из env, если есть,
иначе корень плагина вычисляется от расположения этого файла (…/skills/share-card/scripts/).
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def plugin_root():
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env and os.path.isdir(env):
        return env
    return os.path.dirname(os.path.dirname(os.path.dirname(HERE)))  # scripts → share-card → skills → корень


def find_template(root):
    for cand in (
        os.path.join(root, "skills", "share-card", "assets", "share-card-template.html"),
        os.path.join(HERE, "..", "assets", "share-card-template.html"),  # страховка от самого файла
    ):
        if os.path.exists(cand):
            return cand
    raise SystemExit("шаблон share-card-template.html не найден рядом со скриптом")


def footer_fields(root):
    """handle / test_url / test_name из config.md ядра; без config подвал останется коротким."""
    cfg = os.path.join(root, "skills", "ii-master", "config.md")
    try:
        text = open(cfg, encoding="utf-8").read()
    except OSError:
        return {}

    def take(key):
        m = re.search(rf"^{key}:\s*(.+?)\s*$", text, re.M)
        return m.group(1).strip().strip('"') if m else None

    pairs = {"footer_handle": take("handle"), "footer_link": take("test_url"), "footer_test": take("test_name")}
    return {k: v for k, v in pairs.items() if v}


def main():
    home = os.path.expanduser("~")
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(home, ".claude", "ii-master-result.json")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(home, ".claude", "ii-master-card.html")
    root = plugin_root()
    data = json.load(open(src, encoding="utf-8"))
    for k, v in footer_fields(root).items():
        data.setdefault(k, v)
    html = open(find_template(root), encoding="utf-8").read()
    marker = "/*DATA*/"
    a = html.index(marker)
    b = html.index(marker, a + len(marker))
    html = html[:a] + marker + json.dumps(data, ensure_ascii=False) + html[b:]
    open(out, "w", encoding="utf-8").write(html)
    print(out)


if __name__ == "__main__":
    main()
