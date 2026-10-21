"""Linux & DevOps Learning Platform — backend (Flask + SQLite).

Запуск (за nginx, unix-сокет):
    gunicorn -w 2 -b unix:/tmp/platform.sock main:app
или для разработки:
    python main.py
"""

from datetime import date, datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, render_template, request

import database as dbm

BASE_DIR = Path(__file__).resolve().parent
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)
app.config["JSON_AS_ASCII"] = False


# ---------------------------------------------------------------- helpers

def current_user():
    """Сейчас всегда гость. Здесь появится авторизация (login/регистрация),
    и функция вернёт id пользователя из сессии."""
    return {"id": dbm.GUEST_USER_ID, "username": "guest", "is_guest": True}


# ---------------------------------------------------------------- pages

@app.route("/")
def index():
    with dbm.get_db() as db:
        tracks = dbm.list_tracks(db)
        stats = dbm.overall_stats(db)
    return render_template("index.html", user=current_user(),
                           tracks=tracks, stats=stats, page="home")


@app.route("/tracks/<key>")
def track_page(key):
    with dbm.get_db() as db:
        tr = db.execute("SELECT * FROM tracks WHERE key=?", (key,)).fetchone()
        if not tr:
            return render_template("404.html", user=current_user()), 404
        lessons = dbm.list_lessons(db, key)
    return render_template("track.html", user=current_user(),
                           track=dict(tr), lessons=[dict(l) for l in lessons],
                           page="tracks")


@app.route("/lesson/<slug>")
def lesson_page(slug):
    with dbm.get_db() as db:
        row = db.execute(
            """SELECT l.*, t.key track_key, t.name track_name, t.color track_color
               FROM lessons l JOIN tracks t ON t.id = l.track_id
               WHERE l.slug=?""", (slug,)).fetchone()
        if not row:
            return render_template("404.html", user=current_user()), 404
        lesson = dict(row)
    # Контента нет — урок-заглушка. Команды пользователь запускает локально в своей ОС.
    return render_template("lesson.html", user=current_user(), lesson=lesson,
                           page="tracks")


@app.route("/guides")
def guides_page():
    with dbm.get_db() as db:
        guides = [dict(r) for r in db.execute(
            "SELECT * FROM guides ORDER BY category, title")]
    cats = sorted({g["category"] for g in guides})
    return render_template("guides.html", user=current_user(),
                           guides=guides, cats=cats, page="guides")


@app.route("/guide/<slug>")
def guide_page(slug):
    with dbm.get_db() as db:
        g = db.execute("SELECT * FROM guides WHERE slug=?", (slug,)).fetchone()
        if not g:
            return render_template("404.html", user=current_user()), 404
    return render_template("guide.html", user=current_user(), guide=dict(g),
                           page="guides")


@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html", user=current_user(), page="dashboard")


@app.route("/search")
def search_page():
    q = request.args.get("q", "").strip()
    results = {"lessons": [], "guides": [], "tracks": []}
    if q:
        like = f"%{q}%"
        with dbm.get_db() as db:
            results["lessons"] = [dict(r) for r in db.execute(
                """SELECT l.slug, l.title, t.key track_key, t.name track_name
                   FROM lessons l JOIN tracks t ON t.id=l.track_id
                   WHERE l.title LIKE ? LIMIT 20""", (like,))]
            results["tracks"] = [dict(r) for r in db.execute(
                "SELECT key, name, icon FROM tracks WHERE name LIKE ? LIMIT 10",
                (like,))]
            results["guides"] = [dict(r) for r in db.execute(
                """SELECT slug, title, icon, summary FROM guides
                   WHERE title LIKE ? OR summary LIKE ? LIMIT 20""", (like, like))]
    return render_template("search.html", user=current_user(),
                           query=q, results=results, page="search")


@app.route("/auth/<mode>")
def auth_page(mode):
    if mode not in ("login", "register"):
        return render_template("404.html", user=current_user()), 404
    return render_template("auth.html", user=current_user(), mode=mode, page="auth")


# ---------------------------------------------------------------- API

@app.post("/api/toggle-lesson")
def api_toggle_lesson():
    slug = (request.json or {}).get("slug", "")
    with dbm.get_db() as db:
        lesson = db.execute("SELECT id FROM lessons WHERE slug=?", (slug,)).fetchone()
        if not lesson:
            return jsonify(error="not found"), 404
        cur = db.execute(
            "SELECT completed FROM lesson_progress WHERE user_id=? AND lesson_id=?",
            (dbm.GUEST_USER_ID, lesson["id"])).fetchone()
        newval = 0 if (cur and cur["completed"]) else 1
        db.execute(
            """INSERT INTO lesson_progress (user_id, lesson_id, completed, updated_at)
               VALUES (?,?,?,datetime('now'))
               ON CONFLICT(user_id, lesson_id)
               DO UPDATE SET completed=excluded.completed, updated_at=datetime('now')""",
            (dbm.GUEST_USER_ID, lesson["id"], newval))
        # активность дня
        today = date.today().isoformat()
        day = db.execute("SELECT lessons FROM activity_days WHERE user_id=? AND day=?",
                         (dbm.GUEST_USER_ID, today)).fetchone()
        delta = 1 if newval else -1
        cur_l = (day["lessons"] if day else 0) + delta
        db.execute(
            """INSERT INTO activity_days (user_id, day, lessons, minutes)
               VALUES (?,?,?,0)
               ON CONFLICT(user_id, day) DO UPDATE SET lessons=?""",
            (dbm.GUEST_USER_ID, today, max(cur_l, 0), max(cur_l, 0)))
        stats = dbm.overall_stats(db)
    return jsonify(completed=bool(newval), stats=stats)


@app.post("/api/pomodoro/complete")
def api_pomodoro_complete():
    data = request.json or {}
    minutes = int(data.get("minutes", 25))
    mode = data.get("mode", "focus")
    label = (data.get("label") or "")[:120]
    now = datetime.now()
    with dbm.get_db() as db:
        db.execute(
            """INSERT INTO pomodoro_sessions
               (user_id, started_at, ended_at, minutes, mode, label)
               VALUES (?,?,?,?,?,?)""",
            (dbm.GUEST_USER_ID, (now - timedelta(minutes=minutes)).isoformat(sep=" ",
              timespec="seconds"), now.isoformat(sep=" ", timespec="seconds"),
             minutes, mode, label))
        if mode == "focus":
            today = date.today().isoformat()
            day = db.execute("SELECT minutes FROM activity_days WHERE user_id=? AND day=?",
                             (dbm.GUEST_USER_ID, today)).fetchone()
            newm = (day["minutes"] if day else 0) + minutes
            db.execute(
                """INSERT INTO activity_days (user_id, day, lessons, minutes)
                   VALUES (?,?,'0',?)
                   ON CONFLICT(user_id, day) DO UPDATE SET minutes=?""",
                (dbm.GUEST_USER_ID, today, newm, newm))
        stats = dbm.overall_stats(db)
    return jsonify(ok=True, stats=stats)


@app.get("/api/dashboard")
def api_dashboard():
    with dbm.get_db() as db:
        weeks = int(request.args.get("weeks", 53))
        return jsonify(
            stats=dbm.overall_stats(db),
            heatmap=dbm.heatmap_data(db, weeks),
            tracks=dbm.list_tracks(db),
            today=date.today().isoformat(),
        )


@app.get("/api/tasks")
def api_tasks_list():
    with dbm.get_db() as db:
        rows = db.execute(
            "SELECT id, title, done FROM tasks WHERE user_id=? ORDER BY done, id DESC",
            (dbm.GUEST_USER_ID,)).fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/tasks")
def api_tasks_add():
    title = ((request.json or {}).get("title") or "").strip()[:200]
    if not title:
        return jsonify(error="empty"), 400
    with dbm.get_db() as db:
        cur = db.execute("INSERT INTO tasks (user_id, title) VALUES (?,?)",
                         (dbm.GUEST_USER_ID, title))
        tid = cur.lastrowid
    return jsonify(id=tid, title=title, done=0)


@app.post("/api/tasks/<int:tid>/toggle")
def api_tasks_toggle(tid):
    with dbm.get_db() as db:
        cur = db.execute("SELECT done FROM tasks WHERE id=? AND user_id=?",
                         (tid, dbm.GUEST_USER_ID)).fetchone()
        if not cur:
            return jsonify(error="not found"), 404
        newval = 0 if cur["done"] else 1
        db.execute("UPDATE tasks SET done=? WHERE id=?", (newval, tid))
    return jsonify(id=tid, done=newval)


@app.delete("/api/tasks/<int:tid>")
def api_tasks_delete(tid):
    with dbm.get_db() as db:
        db.execute("DELETE FROM tasks WHERE id=? AND user_id=?",
                   (tid, dbm.GUEST_USER_ID))
    return jsonify(ok=True)


@app.get("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify(lessons=[], guides=[], tracks=[])
    like = f"%{q}%"
    with dbm.get_db() as db:
        lessons = [dict(r) for r in db.execute(
            """SELECT l.slug, l.title, t.key track_key, t.name track_name
               FROM lessons l JOIN tracks t ON t.id=l.track_id
               WHERE l.title LIKE ? LIMIT 8""", (like,))]
        guides = [dict(r) for r in db.execute(
            "SELECT slug, title, icon FROM guides WHERE title LIKE ? LIMIT 5",
            (like,))]
    return jsonify(lessons=lessons, guides=guides, tracks=[])


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html", user=current_user()), 404


dbm.init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
