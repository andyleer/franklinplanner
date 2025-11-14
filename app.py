import os
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# -----------------------------
# DATABASE CONFIG (Render)
# -----------------------------
db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise Exception("DATABASE_URL not found. Make sure it's set in Render.")

# Convert Render's URL to psycopg3-style URL for SQLAlchemy
# psycopg3 driver name is "psycopg"
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -----------------------------
# MODELS
# -----------------------------

class Day(db.Model):
    __tablename__ = "days"
    id = db.Column(db.Integer, primary_key=True)
    # YYYY-MM-DD
    date = db.Column(db.String(10), unique=True, nullable=False)
    notes = db.Column(db.Text, default="")
    tracker = db.Column(db.Text, default="")


class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), index=True, nullable=False)
    priority = db.Column(db.String(1))    # A / B / C
    text = db.Column(db.String(500))
    done = db.Column(db.Boolean, default=False)


class Appointment(db.Model):
    __tablename__ = "appointments"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(10), index=True, nullable=False)
    time = db.Column(db.String(10))       # "7", "8", "9", "13:30", etc
    text = db.Column(db.String(500))


# -----------------------------
# INITIALIZE TABLES
# -----------------------------
with app.app_context():
    db.create_all()


# -----------------------------
# FRONTEND ROUTES
# -----------------------------

@app.route("/")
def index():
    """
    Serve your planner UI from index.html in the repo root.
    """
    return send_from_directory(".", "index.html")


@app.route("/<path:path>")
def static_proxy(path):
    """
    Let you serve other static files (CSS/JS) from the repo root
    if/when you add them.
    """
    return send_from_directory(".", path)


# -----------------------------
# API: LOAD A DAY
# -----------------------------
@app.route("/api/day/<date_str>", methods=["GET"])
def load_day(date_str):
    """
    Load everything for a given date (YYYY-MM-DD):
    - notes (right page)
    - tracker (left page daily tracker)
    - tasks (ABC list)
    - appointments (schedule)
    """
    day = Day.query.filter_by(date=date_str).first()
    tasks = Task.query.filter_by(date=date_str).order_by(Task.id).all()
    appts = Appointment.query.filter_by(date=date_str).order_by(Appointment.time).all()

    return jsonify({
        "date": date_str,
        "notes": day.notes if day else "",
        "tracker": day.tracker if day else "",
        "tasks": [
            {
                "id": t.id,
                "priority": t.priority,
                "text": t.text,
                "done": t.done
            }
            for t in tasks
        ],
        "appointments": [
            {
                "id": a.id,
                "time": a.time,
                "text": a.text
            }
            for a in appts
        ]
    })


# -----------------------------
# API: SAVE A DAY
# -----------------------------
@app.route("/api/day/<date_str>", methods=["POST"])
def save_day(date_str):
    """
    Save all content for a given date.

    Expected JSON body:
    {
      "notes": "string",
      "tracker": "string",
      "tasks": [
        {"priority": "A", "text": "Task text", "done": true},
        ...
      ],
      "appointments": [
        {"time": "7", "text": "Breakfast"},
        ...
      ]
    }
    """
    data = request.get_json(force=True) or {}

    # --- Upsert Day row ---
    day = Day.query.filter_by(date=date_str).first()
    if not day:
        day = Day(date=date_str)
        db.session.add(day)

    day.notes = data.get("notes", "") or ""
    day.tracker = data.get("tracker", "") or ""

    # --- Replace tasks for that date ---
    Task.query.filter_by(date=date_str).delete()
    for t in data.get("tasks", []):
        db.session.add(Task(
            date=date_str,
            priority=(t.get("priority") or "C")[:1],
            text=(t.get("text") or "")[:500],
            done=bool(t.get("done"))
        ))

    # --- Replace appointments for that date ---
    Appointment.query.filter_by(date=date_str).delete()
    for a in data.get("appointments", []):
        db.session.add(Appointment(
            date=date_str,
            time=str(a.get("time") or "")[:10],
            text=(a.get("text") or "")[:500]
        ))

    db.session.commit()

    return jsonify({"status": "ok", "date": date_str})


# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.route("/health")
def health():
    return "ok", 200


# -----------------------------
# LOCAL DEV ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
