# app.py - FULL WORKING VERSION WITH USERS + LOGIN
# -------------------------------------------------------------

from flask import Flask, request, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__, static_folder=".", static_url_path="")

# --------------------------------------------------------------------
# CONFIG
# --------------------------------------------------------------------
app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")

# Render provides DATABASE_URL; local dev uses SQLite
db_url = os.environ.get("DATABASE_URL", "sqlite:///local.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://")

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
CORS(app, supports_credentials=True)


# --------------------------------------------------------------------
# DATABASE MODELS
# --------------------------------------------------------------------

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password_hash = db.Column(db.String(255))


class Day(db.Model):
    __tablename__ = "days"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    notes = db.Column(db.Text)
    tracker = db.Column(db.Text)


class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey("days.id"))
    priority = db.Column(db.String(2))
    description = db.Column(db.Text)
    checked = db.Column(db.Boolean, default=False)


class Appointment(db.Model):
    __tablename__ = "appointments"
    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey("days.id"))
    time = db.Column(db.String(20))
    text = db.Column(db.Text)


# --------------------------------------------------------------------
# HELPER – REQUIRE LOGIN
# --------------------------------------------------------------------
def require_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)


# --------------------------------------------------------------------
# AUTH ROUTES
# --------------------------------------------------------------------

@app.post("/api/signup")
def signup():
    data = request.json
    email = data.get("email")
    pw = data.get("password")

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 400

    user = User(
        email=email,
        password_hash=generate_password_hash(pw)
    )
    db.session.add(user)
    db.session.commit()

    session["user_id"] = user.id

    return jsonify({"status": "ok", "user_id": user.id})


@app.post("/api/login")
def login():
    data = request.json
    email = data.get("email")
    pw = data.get("password")

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, pw):
        return jsonify({"error": "Invalid login"}), 401

    session["user_id"] = user.id
    return jsonify({"status": "ok", "user_id": user.id})


@app.post("/api/logout")
def logout():
    session.pop("user_id", None)
    return jsonify({"status": "ok"})


# --------------------------------------------------------------------
# LOAD DAY ENTRY
# --------------------------------------------------------------------
@app.get("/api/day/<date>")
def get_day(date):
    user = require_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401

    # Does this day exist?
    day = Day.query.filter_by(date=date, user_id=user.id).first()
    if not day:
        # Empty response
        return jsonify({
            "date": date,
            "tasks": [],
            "appointments": [],
            "tracker": "",
            "notes": ""
        })

    # Load tasks & appointments
    tasks = Task.query.filter_by(day_id=day.id).all()
    appts = Appointment.query.filter_by(day_id=day.id).all()

    return jsonify({
        "date": day.date,
        "notes": day.notes or "",
        "tracker": day.tracker or "",
        "tasks": [
            {
                "id": t.id,
                "priority": t.priority,
                "description": t.description,
                "checked": t.checked,
            }
            for t in tasks
        ],
        "appointments": [
            {"time": a.time, "text": a.text}
            for a in appts
        ]
    })


# --------------------------------------------------------------------
# SAVE DAY ENTRY
# --------------------------------------------------------------------
@app.post("/api/day/<date>")
def save_day(date):
    user = require_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401

    data = request.json

    # Find or create the day row
    day = Day.query.filter_by(date=date, user_id=user.id).first()
    if not day:
        day = Day(date=date, user_id=user.id)
        db.session.add(day)
        db.session.commit()

    # Update top-level fields
    day.notes = data.get("notes", "")
    day.tracker = data.get("tracker", "")
    db.session.commit()

    # Clear tasks/appointments for clean overwrite
    Task.query.filter_by(day_id=day.id).delete()
    Appointment.query.filter_by(day_id=day.id).delete()
    db.session.commit()

    # Rewrite tasks
    for t in data.get("tasks", []):
        task = Task(
            day_id=day.id,
            priority=t.get("priority", "A"),
            description=t.get("description", ""),
            checked=t.get("checked", False)
        )
        db.session.add(task)

    # Rewrite appointments
    for a in data.get("appointments", []):
        appt = Appointment(
            day_id=day.id,
            time=a.get("time", ""),
            text=a.get("text", "")
        )
        db.session.add(appt)

    db.session.commit()

    return jsonify({"status": "ok"})


# --------------------------------------------------------------------
# STATIC ROUTE (SERVE FRONTEND)
# --------------------------------------------------------------------

@app.get("/")
def index():
    return send_from_directory(".", "index.html")


@app.get("/planner.js")
def jsfile():
    return send_from_directory(".", "planner.js")


# --------------------------------------------------------------------

@app.get("/health")
def health():
    return "OK", 200


# --------------------------------------------------------------------
# INIT
# --------------------------------------------------------------------
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
