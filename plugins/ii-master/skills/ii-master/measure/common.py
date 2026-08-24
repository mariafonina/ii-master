"""Общее для скриптов замера «ИИ-мастер». Всё работает локально, без сети."""
import os

# Где лежат логи Claude Code и куда класть промежуточные файлы замера.
# Переопределяются переменными окружения II_MASTER_PROJECTS / II_MASTER_WORK.
PROJECTS = os.path.expanduser(os.environ.get("II_MASTER_PROJECTS", "~/.claude/projects"))
WORK = os.path.expanduser(os.environ.get("II_MASTER_WORK", "~/.claude/ii-master-work"))
RESULT = os.path.expanduser("~/.claude/ii-master-result.json")
PREV = os.path.expanduser("~/.claude/ii-master-result.prev.json")

# КОНТРАКТ 1 — слаги привычек, порядок фиксирован. 12-я колонка verify — вне индекса.
COLS = ["iter", "goal", "examples", "format", "mode", "tone",
        "context", "audience", "reason", "approach", "fact", "verify"]
HABITS = COLS[:11]

# База из исследования Anthropic (AI Fluency Index, январь 2026), % диалогов с привычкой.
BASE = {"iter": 85.7, "goal": 51.1, "examples": 41.1, "format": 30.0, "mode": 30.0, "tone": 22.7,
        "context": 20.3, "audience": 17.6, "reason": 15.8, "approach": 10.1, "fact": 8.7}
BASE_COMPOSITE = 30.3     # составной индекс базы
BASE_PER_DIALOG = 3.33    # привычек на диалог у среднего пользователя

# Русские имена — из шпаргалки мастер-класса «11 привычек».
NAMES = {"iter": "Итерация", "goal": "Цель", "examples": "Образец", "format": "Формат",
         "mode": "Роль и правила", "tone": "Тон", "context": "Контекст", "audience": "Адресат",
         "reason": "Спор с логикой", "approach": "Совет до старта", "fact": "Проверка фактов"}
HINTS = {"iter": "минимум три сообщения вдогонку: уточни, оспорь, доведи",
         "goal": "«Мне это нужно, чтобы …»",
         "examples": "«Хорошо = … Такого быть не должно: … Приму по …»",
         "format": "«Формат: …» — таблица, слайды, письмо, пдф",
         "mode": "«Спорь со мной. Не хватает данных — спрашивай. Не уверен — скажи прямо»",
         "tone": "«Тон: …» — просто, по-деловому, как в примере",
         "context": "приложи то, чего модель не знает: файл, ссылку, вводные",
         "audience": "«Читать будет …»",
         "reason": "«Откуда ты это взял? Пересчитай»",
         "approach": "«Сначала предложи 2–3 подхода с минусами»",
         "fact": "проверь руками цифры, даты и названия"}

# Слаги фишек Claude (КОНТРАКТ 2), 13 штук.
FEATURES = ["schedule", "slash-commands", "hooks", "verification", "code-review", "plugins",
            "subagents", "mcp", "headless", "remote-control", "github-actions", "research",
            "managed-agents"]
FEATURE_NAMES = {
    "schedule": "Задачи по расписанию (/schedule, /loop)",
    "slash-commands": "Свои слэш-команды",
    "hooks": "Хуки (автоматические действия до и после шагов)",
    "verification": "Просьба доказать, что сделанное работает",
    "code-review": "Проверка кода командой (/code-review, /security-review)",
    "plugins": "Плагины",
    "subagents": "Субагенты (параллельные помощники)",
    "mcp": "Подключение внешних сервисов (MCP)",
    "headless": "Claude внутри скриптов (режим без чата, claude -p)",
    "remote-control": "Управление сессией с телефона (Remote Control)",
    "github-actions": "Claude в GitHub Actions (ревью пул-реквестов)",
    "research": "Режим исследования в claude.ai",
    "managed-agents": "Managed Agents (агенты на стороне Anthropic)",
}


def ensure_work():
    os.makedirs(WORK, exist_ok=True)
    return WORK


def wpath(name):
    return os.path.join(ensure_work(), name)
