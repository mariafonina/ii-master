#!/usr/bin/env python3
"""Шаг 4 замера «ИИ-мастер»: какие фишки Claude Code человек уже использует.

Смотрит только локально: ~/.claude/skills, agents, commands, settings.json (хуки),
plugins/installed_plugins.json, ~/.claude.json (MCP), .claude/ и .github/workflows в папках
проектов из логов, плюс следы в логах (слэш-команды, вызовы инструментов, ветки субагентов,
Bash-команды с `claude -p`). Тексты реплик в отчёт не попадают — только счётчики.

Пишет features.json: {"used": [...], "unused": [...], "unknown": [...], "evidence": {...}}.
unknown — то, что локально не проверить (нужен один вопрос пользователю).
"""
import argparse, collections, glob, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

HOME = os.path.expanduser("~")
CLAUDE = os.path.join(HOME, ".claude")
CMDNAME = re.compile(r"<command-name>\s*/?([^<\s]+)\s*</command-name>")
BUILTIN = set("""clear compact config cost doctor help init login logout mcp memory model permissions
pr-comments review status terminal-setup vim plugin plugins hooks agents skills resume exit quit bug
release-notes add-dir context export rewind usage stats upgrade keybindings schedule loop code-review
security-review simplify rename remote-control rc theme output-style ide install-github-app
privacy-settings passes todos tasks chrome sandbox branch fork diff copy desktop mobile share btw voice
statusline skill-doctor batch ultraplan ultrareview insights reload-plugins teleport effort fast color
fewer-permission-prompts extra-usage update-config keybindings-help run ii-master quiz ii-trener
share-card""".split())
VERIFY_RE = re.compile(r"докажи|прогони тест|запусти тест|покажи,? что работает|проверь,? что (всё |все )?работает|"
                       r"скриншот|скрин\b|e2e|smoke|тесты? (прош|зелен)|покажи лог|пруф", re.I)
HEADLESS_RE = re.compile(r"claude\s+(-p|--print)\b|--output-format\s+(json|stream-json)")


def has_files(pattern):
    return sorted(glob.glob(pattern))


def settings_hooks(path):
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception:
        return False
    h = d.get("hooks")
    return bool(h) and any(v for v in h.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--projects", default=common.PROJECTS)
    ap.add_argument("--work", default=common.WORK)
    a = ap.parse_args()
    common.WORK = a.work

    ev = collections.defaultdict(list)      # slug -> список улик (без текстов пользователя)
    cwds = set()
    cmds = collections.Counter()
    tools = collections.Counter()
    sess_side = sess_agent = sess_verify = sess_headless = 0
    n_sessions = 0

    for f in glob.glob(os.path.join(a.projects, "*", "*.jsonl")):
        side = agent = verify = headless = False
        n_sessions += 1
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    if d.get("isSidechain"):
                        side = True
                        continue
                    if d.get("cwd"):
                        cwds.add(d["cwd"])
                    t = d.get("type")
                    m = d.get("message") or {}
                    c = m.get("content")
                    if t == "assistant" and isinstance(c, list):
                        for b in c:
                            if isinstance(b, dict) and b.get("type") == "tool_use":
                                name = str(b.get("name"))
                                tools[name] += 1
                                if name in ("Agent", "Task"):
                                    agent = True
                                inp = b.get("input") or {}
                                cmd = inp.get("command") if isinstance(inp, dict) else None
                                if isinstance(cmd, str) and HEADLESS_RE.search(cmd):
                                    headless = True
                    elif t == "user":
                        texts = []
                        if isinstance(c, str):
                            texts.append(c)
                        elif isinstance(c, list):
                            texts += [b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text"]
                        raw = "\n".join(texts)
                        for name in CMDNAME.findall(raw):
                            cmds[name.lower()] += 1
                        if not d.get("toolUseResult") and not d.get("isMeta") and not d.get("sourceToolUseID"):
                            if VERIFY_RE.search(raw):
                                verify = True
                            if HEADLESS_RE.search(raw):
                                headless = True
        except Exception:
            continue
        sess_side += side
        sess_agent += agent
        sess_verify += verify
        sess_headless += headless

    used, unused, unknown = [], [], []

    def mark(slug, ok, why, unknown_if_none=False):
        if ok:
            used.append(slug); ev[slug].append(why)
        elif unknown_if_none:
            unknown.append(slug); ev[slug].append(why)
        else:
            unused.append(slug); ev[slug].append(why)

    # schedule
    sched = cmds.get("schedule", 0) + cmds.get("loop", 0) + sum(v for k, v in tools.items() if "scheduled-tasks" in k or k.startswith("mcp__schedule"))
    mark("schedule", sched > 0, f"команды /schedule,/loop и задачи по расписанию: {sched}")

    # slash-commands
    own = has_files(os.path.join(CLAUDE, "commands", "*.md"))
    for cwd in cwds:
        own += has_files(os.path.join(cwd, ".claude", "commands", "*.md"))
    custom = {k: v for k, v in cmds.items() if k not in BUILTIN and ":" not in k}   # plugin:cmd — это плагин
    mark("slash-commands", bool(own) or bool(custom),
         f"файлов команд: {len(own)}; своих команд в логах: {sum(custom.values())}")

    # hooks
    hk = [p for p in [os.path.join(CLAUDE, "settings.json"), os.path.join(CLAUDE, "settings.local.json")]
          + [os.path.join(c, ".claude", n) for c in cwds for n in ("settings.json", "settings.local.json")]
          if os.path.exists(p) and settings_hooks(p)]
    mark("hooks", bool(hk), f"файлов настроек с хуками: {len(hk)}")

    # verification
    mark("verification", sess_verify >= 3, f"сессий с просьбой доказать/проверить: {sess_verify}")

    # code-review
    cr = cmds.get("code-review", 0) + cmds.get("security-review", 0) + cmds.get("simplify", 0) + cmds.get("review", 0)
    mark("code-review", cr > 0, f"вызовов /code-review,/security-review,/simplify: {cr}")

    # plugins
    plugs = []
    try:
        pj = json.load(open(os.path.join(CLAUDE, "plugins", "installed_plugins.json"), encoding="utf-8"))
        plugs = [k for k in (pj.get("plugins") or {}) if not k.startswith("ii-master@")]
    except Exception:
        pass
    mark("plugins", bool(plugs), f"установлено плагинов (кроме этого теста): {len(plugs)}")

    # subagents
    ag = has_files(os.path.join(CLAUDE, "agents", "*.md"))
    for cwd in cwds:
        ag += has_files(os.path.join(cwd, ".claude", "agents", "*.md"))
    mark("subagents", bool(ag) or sess_agent >= 2 or sess_side >= 2,
         f"файлов агентов: {len(ag)}; сессий с субагентами: {max(sess_agent, sess_side)}")

    # mcp
    mcp_cfg = 0
    try:
        cj = json.load(open(os.path.join(HOME, ".claude.json"), encoding="utf-8"))
        mcp_cfg += len(cj.get("mcpServers") or {})
        for p in (cj.get("projects") or {}).values():
            mcp_cfg += len((p or {}).get("mcpServers") or {})
    except Exception:
        pass
    mcp_cfg += sum(1 for c in cwds if os.path.exists(os.path.join(c, ".mcp.json")))
    mcp_tools = sum(v for k, v in tools.items() if k.startswith("mcp__"))
    mark("mcp", mcp_cfg > 0 or mcp_tools > 0, f"настроенных MCP-серверов: {mcp_cfg}; вызовов MCP-инструментов: {mcp_tools}")

    # headless
    mark("headless", sess_headless > 0, f"сессий с claude -p: {sess_headless}", unknown_if_none=True)

    # remote-control
    rcn = cmds.get("remote-control", 0) + cmds.get("rc", 0)
    mark("remote-control", rcn > 0, f"вызовов /remote-control: {rcn}", unknown_if_none=True)

    # github-actions
    gha = []
    for cwd in cwds:
        for wf in has_files(os.path.join(cwd, ".github", "workflows", "*.y*ml")):
            try:
                if "claude-code-action" in open(wf, encoding="utf-8", errors="replace").read():
                    gha.append(wf)
            except Exception:
                pass
    mark("github-actions", bool(gha) or cmds.get("install-github-app", 0) > 0,
         f"воркфлоу с claude-code-action: {len(gha)}", unknown_if_none=True)

    # research, managed-agents — локально не видно
    mark("research", False, "локально не проверить", unknown_if_none=True)
    mark("managed-agents", False, "локально не проверить", unknown_if_none=True)

    out = {"used": used, "unused": unused, "unknown": unknown,
           "evidence": {k: "; ".join(v) for k, v in ev.items()},
           "sessions_scanned": n_sessions}
    path = common.wpath("features.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for slug in common.FEATURES:
        st = "использует" if slug in used else ("не использует" if slug in unused else "неизвестно")
        print(f"{slug:16s} {st:14s} {out['evidence'].get(slug, '')}")
    print("записано:", path)


if __name__ == "__main__":
    main()
