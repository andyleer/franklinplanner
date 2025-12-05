import os
from flask import Flask, request, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------------------------------------------------
# APP INIT
# ---------------------------------------------------------
app = Flask(__name__, static_folder=".", static_url_path="")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")

CORS(app, supports_credentials=True)
db = SQLAlchemy(app)

# ---------------------------------------------------------
# MODELS
# ---------------------------------------------------------
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True)
    password_hash = db.Column(db.String)


class Day(db.Model):
    __tablename__ = "days"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    notes = db.Column(db.Text, default="")
    tracker = db.Column(db.Text, default="")


class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey("days.id"))
    priority = db.Column(db.String)
    description = db.Column(db.String)
    checked = db.Column(db.Boolean, default=False)


class Appointment(db.Model):
    __tablename__ = "appointments"
    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey("days.id"))
    time = db.Column(db.String)
    text = db.Column(db.String)

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def get_current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)

# ---------------------------------------------------------
# AUTH ROUTES
# ---------------------------------------------------------
@app.post("/api/signup")
def signup():
    data = request.json
    email = data.get("email", "").strip().lower()
    pw = data.get("password", "")

    if not email or not pw:
        return jsonify({"error": "Email and password required"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 400

    user = User(email=email, password_hash=generate_password_hash(pw))
    db.session.add(user)
    db.session.commit()

    session["user_id"] = user.id
    return jsonify({"status": "ok", "user_id": user.id})


@app.post("/api/login")
def login():
    data = request.json
    email = data.get("email", "").strip().lower()
    pw = data.get("password", "")

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, pw):
        return jsonify({"error": "Invalid login"}), 401

    session["user_id"] = user.id
    return jsonify({"status": "ok", "user_id": user.id})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"status": "ok"})

# ---------------------------------------------------------
# LOAD DAY
# ---------------------------------------------------------
@app.get("/api/day/<date>")
def load_day(date):
    user = get_current_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401

    day = Day.query.filter_by(date=date, user_id=user.id).first()
    if not day:
        return jsonify({
            "date": date,
            "tasks": [],
            "appointments": [],
            "tracker": "",
            "notes": ""
        })

    tasks = Task.query.filter_by(day_id=day.id).all()
    appts = Appointment.query.filter_by(day_id=day.id).all()

    return jsonify({
        "date": day.date,
        "notes": day.notes,
        "tracker": day.tracker,
        "tasks": [
            {
                "priority": t.priority,
                "description": t.description,
                "checked": t.checked
            } for t in tasks
        ],
        "appointments": [
            {"time": a.time, "text": a.text} for a in appts
        ]
    })

# ---------------------------------------------------------
# SAVE DAY
# ---------------------------------------------------------
@app.post("/api/day/<date>")
def save_day(date):
    user = get_current_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401

    data = request.json

    day = Day.query.filter_by(date=date, user_id=user.id).first()
    if not day:
        day = Day(date=date, user_id=user.id)
        db.session.add(day)
        db.session.commit()

    # Update top-level fields
    day.notes = data.get("notes", "")
    day.tracker = data.get("tracker", "")
    db.session.commit()

    # Replace tasks
    Task.query.filter_by(day_id=day.id).delete()
    for t in data.get("tasks", []):
        db.session.add(Task(
            day_id=day.id,
            priority=t.get("priority", "A"),
            description=t.get("description", ""),
            checked=t.get("checked", False)
        ))

    # Replace appointments
    Appointment.query.filter_by(day_id=day.id).delete()
    for a in data.get("appointments", []):
        db.session.add(Appointment(
            day_id=day.id,
            time=a.get("time", ""),
            text=a.get("text", "")
        ))

    db.session.commit()
    return jsonify({"status": "ok"})

# ---------------------------------------------------------
# STATIC FRONTEND
# ---------------------------------------------------------
@app.get("/")
def root():
    return send_from_directory(".", "index.html")

@app.get("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)

@app.get("/health")
def health():
    return "OK", 200

# ---------------------------------------------------------
# INIT
# ---------------------------------------------------------
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    db.session.add(user)
    db.session.commit()

    session["user_id"] = user.id
    return jsonify({"status": "ok", "user_id": user.id, "email": user.email})


@app.post("/api/login")
def login():
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    pw = data.get("password", "")

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, pw):
        return jsonify({"error": "Invalid email or password"}), 401

    session["user_id"] = user.id
    return jsonify({"status": "ok", "user_id": user.id, "email": user.email})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"status": "ok"})


@app.get("/api/session")
def get_session():
    user = require_user()
    if not user:
        return jsonify({"logged_in": False})
    return jsonify({"logged_in": True, "email": user.email})


# ---------------------------------------------------------
# DAY ROUTES
# ---------------------------------------------------------
@app.get("/api/day/<date>")
def api_get_day(date):
    """Return the planner data for the given date for the logged-in user."""
    user = require_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401

    day = Day.query.filter_by(user_id=user.id, date=date).first()
    if not day:
        # no data yet for this date
        return jsonify({
            "date": date,
            "notes": "",
            "tracker": "",
            "tasks": [],
            "appointments": [],
        })

    tasks = Task.query.filter_by(day_id=day.id).all()
    appts = Appointment.query.filter_by(day_id=day.id).all()

    return jsonify({
        "date": date,
        "notes": day.notes,
        "tracker": day.tracker,
        "tasks": [
            {
                "priority": t.priority,
                "description": t.description,
                "checked": t.checked,
            }
            for t in tasks
        ],
        "appointments": [
            {
                "time": a.time,
                "text": a.text,
            }
            for a in appts
        ],
    })


@app.post("/api/day/<date>")
def api_save_day(date):
    """Save the planner data for the day for the logged-in user."""
    user = require_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401

    payload = request.json or {}

    day = Day.query.filter_by(user_id=user.id, date=date).first()
    if not day:
        day = Day(user_id=user.id, date=date)
        db.session.add(day)
        db.session.commit()

    day.notes = payload.get("notes", "")
    day.tracker = payload.get("tracker", "")
    db.session.commit()

    # Clear existing tasks & appointments for this day
    Task.query.filter_by(day_id=day.id).delete()
    Appointment.query.filter_by(day_id=day.id).delete()

    # Re-insert from payload
    for t in payload.get("tasks", []):
        db.session.add(Task(
            day_id=day.id,
            priority=t.get("priority", "A"),
            description=t.get("description", ""),
            checked=bool(t.get("checked", False)),
        ))

    for a in payload.get("appointments", []):
        db.session.add(Appointment(
            day_id=day.id,
            time=a.get("time", ""),
            text=a.get("text", ""),
        ))

    db.session.commit()
    return jsonify({"status": "ok"})


# ---------------------------------------------------------
# STATIC + HEALTH
# ---------------------------------------------------------
@app.get("/")
def index():
    return send_from_directory(".", "index.html")


@app.get("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)


@app.get("/health")
def health():
    return "OK", 200


# ---------------------------------------------------------
# INIT
# ---------------------------------------------------------
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
