"""SQLite layer — локальная БД.

Схема изначально спроектирована "на вырост": почти все таблицы имеют
колонку user_id. Сейчас используется пользователь по умолчанию (id = 1,
guest). Когда появится система логина, достаточно будет подставлять id
зарегистрированного пользователя вместо guest.
"""

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "platform.db"

GUEST_USER_ID = 1


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def get_db():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    email         TEXT UNIQUE,
    password_hash TEXT,                -- заполнится при реализации логина
    created_at    TEXT DEFAULT (datetime('now')),
    is_guest      INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tracks (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    key    TEXT UNIQUE NOT NULL,       -- linux-basics / networking / devops ...
    name   TEXT NOT NULL,
    icon   TEXT DEFAULT '🐧',
    color  TEXT DEFAULT '#58a6ff'
);

CREATE TABLE IF NOT EXISTS lessons (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id  INTEGER NOT NULL REFERENCES tracks(id),
    slug      TEXT UNIQUE NOT NULL,
    title     TEXT NOT NULL,
    position  INTEGER DEFAULT 0,
    est_min   INTEGER DEFAULT 20,
    status    TEXT DEFAULT 'stub',     -- stub | draft | published
    content   TEXT                     -- markdown-контент урока (пока NULL)
);

CREATE TABLE IF NOT EXISTS guides (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    slug     TEXT UNIQUE NOT NULL,
    title    TEXT NOT NULL,
    category TEXT DEFAULT 'setup',
    icon     TEXT DEFAULT '📘',
    summary  TEXT,
    content  TEXT                      -- заглушка, потом наполним
);

-- Прогресс: на будущее — по одному набору строк на пользователя
CREATE TABLE IF NOT EXISTS lesson_progress (
    user_id    INTEGER NOT NULL REFERENCES users(id),
    lesson_id  INTEGER NOT NULL REFERENCES lessons(id),
    completed  INTEGER DEFAULT 0,
    updated_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, lesson_id)
);

CREATE TABLE IF NOT EXISTS pomodoro_sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    started_at  TEXT NOT NULL,
    ended_at    TEXT,
    minutes     INTEGER NOT NULL,
    mode        TEXT DEFAULT 'focus',   -- focus | short | long
    lesson_slug TEXT,
    label       TEXT
);

CREATE TABLE IF NOT EXISTS activity_days (
    user_id   INTEGER NOT NULL REFERENCES users(id),
    day       TEXT NOT NULL,            -- YYYY-MM-DD
    lessons   INTEGER DEFAULT 0,
    minutes   INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, day)
);

CREATE TABLE IF NOT EXISTS tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    title      TEXT NOT NULL,
    done       INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def init_db() -> None:
    with get_db() as db:
        db.executescript(SCHEMA)

        # --- пользователи -------------------------------------------------
        if not db.execute("SELECT id FROM users LIMIT 1").fetchone():
            db.execute(
                "INSERT INTO users (id, username, is_guest) VALUES (?, ?, 1)",
                (GUEST_USER_ID, "guest"),
            )

        # --- треки ----------------------------------------------------------
        tracks = [
            ("linux-basics", "Основы Linux", "🐧", "#8bc34a"),
            ("bash-scripting", "Bash и скриптинг", "💻", "#ffb454"),
            ("networking", "Сети", "🌐", "#4dd0e1"),
            ("git", "Git и GitHub", "🌱", "#7ee787"),
            ("docker", "Docker и контейнеры", "🐳", "#58a6ff"),
            ("ci-cd", "CI/CD", "⚙️", "#f778ba"),
            ("kubernetes", "Kubernetes", "☸️", "#a371f7"),
            ("monitoring", "Мониторинг и наблюдаемость", "📊", "#e3b341"),
        ]
        for key, name, icon, color in tracks:
            db.execute(
                "INSERT OR IGNORE INTO tracks (key, name, icon, color) VALUES (?,?,?,?)",
                (key, name, icon, color),
            )

        # --- уроки-заглушки ---------------------------------------------------
        existing = db.execute("SELECT COUNT(*) c FROM lessons").fetchone()["c"]
        if existing == 0:
            lesson_titles = {
                "linux-basics": [
                    "Что такое Linux и дистрибутивы",
                    "Файловая система и пути",
                    "Навигация: pwd, ls, cd",
                    "Работа с файлами: cp, mv, rm, cat",
                    "Права доступа: chmod, chown",
                    "Пользователи и группы",
                    "Текстовые редакторы nano и vim",
                    "Пакетные менеджеры apt и dnf",
                    "Системные процессы и top/htop",
                    "Службы и systemctl",
                ],
                "bash-scripting": [
                    "Анатомия команды: аргументы, опции",
                    "Перенаправление вывода и пайпы",
                    "Переменные и окружение",
                    "Условия if / case",
                    "Циклы for / while",
                    "Функции и аргументы",
                    "Первый полезный скрипт",
                    "Отладка: set -x, shellcheck",
                ],
                "networking": [
                    "Модель OSI простыми словами",
                    "IP-адреса, подсети, CIDR",
                    "DNS: как работает разрешение имён",
                    "Порты, TCP vs UDP",
                    "Полезные утилиты: ss, ping, curl, dig",
                    "SSH: вход, ключи, конфиг",
                    "iptables / nftables: основы",
                ],
                "git": [
                    "Инициализация репозитория и коммит",
                    "Ветки и слияние",
                    "Удалённые репозитории и pull request",
                    "Гитignore и распространённые ошибки",
                    "Rebase, stash, cherry-pick",
                    "Git flow в команде",
                ],
                "docker": [
                    "Контейнер vs виртуальная машина",
                    "Запуск первого контейнера",
                    "Образы и Dockerfile",
                    "Тома и привязка портов",
                    "docker compose",
                    "Оптимизация образов и multi-stage",
                    "Сеть в Docker",
                ],
                "ci-cd": [
                    "Что такое CI/CD и пайплайн",
                    "GitHub Actions: первый workflow",
                    "Кэширование и артефакты",
                    "Деплой по тегу",
                    "Секреты и переменные окружения",
                    "Quality gates и тесты в пайплайне",
                ],
                "kubernetes": [
                    "Архитектура кластера",
                    "minikube / k3s локально",
                    "Pod и Deployment",
                    "Service и Ingress",
                    "ConfigMap и Secret",
                    "kubectl: шпаргалка",
                ],
                "monitoring": [
                    "Зачем нужен мониторинг",
                    "Prometheus: сбор метрик",
                    "Grafana: дашборды",
                    "Логи: loki / journald",
                    "Алерты и дежурства",
                ],
            }
            tid = {r["id"]: r["key"] for r in db.execute("SELECT id, key FROM tracks")}
            key_id = {v: k for k, v in tid.items()}
            pos = 0
            for key, titles in lesson_titles.items():
                for i, t in enumerate(titles):
                    db.execute(
                        "INSERT INTO lessons (track_id, slug, title, position, est_min)"
                        " VALUES (?,?,?,?,?)",
                        (key_id[key], f"{key}-{i+1}", t, pos, 15 + (i % 4) * 10),
                    )
                    pos += 1

        # --- руководства -------------------------------------------------------
        guides = [
            ("wsl-install", "Установка WSL 2 (Windows Subsystem for Linux)", "windows",
             "🪟", "Как включить WSL, поставить Ubuntu, настроить терминал и интеграцию с VS Code."),
            ("ubuntu-install", "Установка Ubuntu Desktop", "linux",
             "🐧", "Разбивка диска, dual-boot с Windows, первые настройки после установки."),
            ("macos-homebrew", "Настройка macOS для разработки: Homebrew", "macos",
             "🍎", "Ставим пакетный менеджер, git, zsh, полезные утилиты одной командой."),
            ("terminal-setup", "Настройка терминала: zsh, oh-my-zsh, tmux", "tools",
             "⌨️", "Промпт, плагины,History, темы и многооконность в терминале."),
            ("ssh-keys", "SSH-ключи и безопасный доступ к серверам", "security",
             "🔐", "Генерация ключей ssh-keygen, agent, authorized_keys, запрет парольного входа."),
            ("vm-virtualbox", "Виртуальные машины: VirtualBox и Multipass", "virtualization",
             "🖥️", "Для тех случаев, когда захочется изолированный Linux (на платформе ВМ не запускаются)."),
            ("vscode-remote", "VS Code Remote — редактирование файлов на сервере", "tools",
             "🧩", "Подключение по SSH, проброс портов, синхронизация настроек."),
            ("nginx-local", "Nginx локально: конфигурация и reverse proxy", "servers",
             "🚦", "Установка nginx, location-блоки, proxy_pass, let's encrypt на локальном стенде."),
            ("docker-desktop", "Docker Desktop и docker engine на Linux", "containers",
             "🐳", "Установка, группа docker без sudo, first container, compose."),
            ("github-account", "Регистрация на GitHub и настройка git", "git",
             "🌱", "Аккаунт, ssh-ключ для GitHub, git config, первый push."),
        ]
        for slug, title, cat, icon, summary in guides:
            db.execute(
                "INSERT OR IGNORE INTO guides (slug, title, category, icon, summary, content)"
                " VALUES (?,?,?,?,?,?)",
                (slug, title, cat, icon, summary,
                 "<p>Это руководство — <strong>заглушка</strong>. Содержание появится позже.</p>"),
            )

        # --- демо-активность для графика вкладов (только если пусто) -------------
        days = db.execute("SELECT COUNT(*) c FROM activity_days WHERE user_id=?",
                          (GUEST_USER_ID,)).fetchone()["c"]
        if days == 0:
            today = date.today()
            rnd_seed = 7
            for back in range(0, 370):
                d = today - timedelta(days=back)
                rnd_seed = (rnd_seed * 1103515245 + 12345) & 0x7FFFFFFF
                r = rnd_seed % 100
                dow = d.weekday()
                chance = 55 if dow < 5 else 30
                if r < chance:
                    lessons_done = 1 + (rnd_seed >> 7) % 3
                    minutes = lessons_done * (15 + (rnd_seed >> 11) % 30)
                    db.execute(
                        "INSERT OR REPLACE INTO activity_days (user_id, day, lessons, minutes)"
                        " VALUES (?,?,?,?)",
                        (GUEST_USER_ID, d.isoformat(), lessons_done, minutes),
                    )


# ---------------------------------------------------------------- queries

def list_tracks(db):
    rows = []
    for t in db.execute("SELECT * FROM tracks ORDER BY id"):
        stat = db.execute(
            """SELECT COUNT(l.id) total,
                      SUM(CASE WHEN p.completed=1 THEN 1 ELSE 0 END) done
               FROM lessons l
               LEFT JOIN lesson_progress p ON p.lesson_id = l.id AND p.user_id = ?
               WHERE l.track_id = ?""",
            (GUEST_USER_ID, t["id"]),
        ).fetchone()
        d = dict(t)
        d["total"] = stat["total"] or 0
        d["done"] = stat["done"] or 0
        rows.append(d)
    return rows


def list_lessons(db, track_key):
    return db.execute(
        """SELECT l.*, COALESCE(p.completed,0) completed
           FROM lessons l
           JOIN tracks t ON t.id = l.track_id
           LEFT JOIN lesson_progress p ON p.lesson_id = l.id AND p.user_id = ?
           WHERE t.key = ?
           ORDER BY l.position""",
        (GUEST_USER_ID, track_key),
    ).fetchall()


def overall_stats(db):
    prog = db.execute(
        "SELECT COUNT(*) done FROM lesson_progress WHERE user_id=? AND completed=1",
        (GUEST_USER_ID,),
    ).fetchone()["done"]
    total = db.execute("SELECT COUNT(*) c FROM lessons").fetchone()["c"]
    sess = db.execute(
        "SELECT COALESCE(SUM(minutes),0) m, COUNT(*) c FROM pomodoro_sessions WHERE user_id=?",
        (GUEST_USER_ID,),
    ).fetchone()
    streak = current_streak(db)
    return {
        "lessons_done": prog,
        "lessons_total": total,
        "minutes": sess["m"],
        "sessions": sess["c"],
        "streak": streak,
    }


def current_streak(db):
    rows = [r["day"] for r in db.execute(
        "SELECT day FROM activity_days WHERE user_id=? AND (lessons>0 OR minutes>0) ORDER BY day DESC",
        (GUEST_USER_ID,),
    )]
    ds = {date.fromisoformat(x) for x in rows}
    today = date.today()
    streak = 0
    cur = today if today in ds else today - timedelta(days=1)
    while cur in ds:
        streak += 1
        cur -= timedelta(days=1)
    return streak


def heatmap_data(db, weeks=53):
    start = date.today() - timedelta(days=weeks * 7)
    start -= timedelta(days=start.weekday())  # понедельник
    out = {}
    for r in db.execute(
        "SELECT day, lessons, minutes FROM activity_days WHERE user_id=? AND day>=?",
        (GUEST_USER_ID, start.isoformat()),
    ):
        out[r["day"]] = {"lessons": r["lessons"], "minutes": r["minutes"]}
    return out
