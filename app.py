import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# -----------------------------
# DATABASE CONFIG
# -----------------------------
db_url = os.getenv("DATABASE_URL")
if not db_url:
    raise Exception("DATABASE_URL missing — Render did not inject it.")

# Render gives: postgresql://...
# SQLAlchemy needs: postgresql+psycopg2://...
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://")
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://")

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -----------------------------
# DATABASE MODELS
# -----------------------------

class Day(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String, unique=True, nullable=False)
    notes = db.Column(db.Text, default="")
    tracker = db.Column(db.Text, default="")

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String, nullable=False)
    priority = db.Column(db.String(1))   # A/B/C
    text = db.Column(db.String)
    done = db.Column(db.Boolean, default=False)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String, nullable=False)
    time = db.Column(db.String)   # "7", "8", "9" etc
    text = db.Column(db.String)


# -----------------------------
# INITIALIZE TABLES
# -----------------------------
with app.app_context():
    db.create_all()


# -----------------------------
# ROUTES
# -----------------------------

@app.route("/")
def home():
    return "Planner backend is running."

# -----------------------------
# LOAD A DAY
# -----------------------------
@app.route("/api/day/<date>", methods=["GET"])
def load_day(date):
    day = Day.query.filter_by(date=date).first()
    tasks = Task.query.filter_by(date=date).all()
    appts = Appointment.query.filter_by(date=date).all()

    return jsonify({
        "date": date,
        "notes": day.notes if day else "",
        "tracker": day.tracker if day else "",
        "tasks": [
            {"id": t.id, "priority": t.priority, "text": t.text, "done": t.done}
            for t in tasks
        ],
        "appointments": [
            {"id": a.id, "time": a.time, "text": a.text}
            for a in appts
        ]
    })

# -----------------------------
# SAVE A DAY
# -----------------------------
@app.route("/api/day/<date>", methods=["POST"])
def save_day(date):
    data = request.json

    # Save notes + tracker
    day = Day.query.filter_by(date=date).first()
    if not day:
        day = Day(date=date)
        db.session.add(day)

    day.notes = data.get("notes", "")
    day.tracker = data.get("tracker", "")

    # Clear existing tasks + reinsert
    Task.query.filter_by(date=date).delete()
    for t in data.get("tasks", []):
        db.session.add(Task(
            date=date,
            priority=t.get("priority", "C"),
            text=t.get("text", ""),
            done=t.get("done", False)
        ))

    # Clear existing appointments + reinsert
    Appointment.query.filter_by(date=date).delete()
    for a in data.get("appointments", []):
        db.session.add(Appointment(
            date=date,
            time=a.get("time", ""),
            text=a.get("text", "")
        ))

    db.session.commit()

    return jsonify({"status": "saved", "date": date})

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
