import os
from flask import Flask, request, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------------------------------------------------------------
# APP SETUP
# ---------------------------------------------------------------------
app = Flask(__name__, static_folder=".", static_url_path="")

# Fix old-style postgres:// URLs from Render
raw_db_url = os.getenv("DATABASE_URL")
if raw_db_url and raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = raw_db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")

# If front-end is same origin on Render, CORS is mostly harmless;
# if you later move front-end to another domain, this is ready.
CORS(app, supports_credentials=True)

db = SQLAlchemy(app)

# ---------------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------------
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    days = db.relationship("Day", backref="user", cascade="all, delete-orphan")


class Day(db.Model):
    __tablename__ = "days"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(50), nullable=False)  # "YYYY-MM-DD"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    notes = db.Column(db.Text, default="")
    tracker = db.Column(db.Text, default="")

    tasks = db.relationship("Task", backref="day", cascade="all, delete-orphan")
    appointments = db.relationship("Appointment", backref="day", cascade="all, delete-orphan")


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey("days.id"), nullable=False)
    priority = db.Column(db.String(2), default="A")  # A/B/C
    description = db.Column(db.Text, default="")
    checked = db.Column(db.Boolean, default=False)


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey("days.id"), nullable=False)
    time = db.Column(db.String(20), nullable=False)  # "7", "8", "9", etc.
    text = db.Column(db.Text, default="")

# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------
def current_user():
    """Return the logged-in User object or None."""
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)

# ---------------------------------------------------------------------
# AUTH ROUTES
# ---------------------------------------------------------------------
@app.post("/api/signup")
def api_signup():
    data = request.json or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "Email already exists"}), 400

    user = User(
        email=email,
        password_hash=generate_password_hash(password)
    )
    db.session.add(user)
    db.session.commit()

    session["user_id"] = user.id

    return jsonify({"status": "ok", "user_id": user.id})


@app.post("/api/login")
def api_login():
    data = request.json or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid credentials"}), 401

    session["user_id"] = user.id
    return jsonify({"status": "ok", "user_id": user.id})


@app.get("/api/logout")
def api_logout():
    session.clear()
    return jsonify({"status": "ok"})

# ---------------------------------------------------------------------
# DAY LOAD / SAVE – PER USER
# ---------------------------------------------------------------------
@app.get("/api/day/<date_str>")
def api_get_day(date_str):
    """
    Read planner data for the given date ("YYYY-MM-DD") for the current user.
    """
    user = current_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401

    day = Day.query.filter_by(user_id=user.id, date=date_str).first()
    if not day:
        # Return an empty shell so the front-end can render defaults
        return jsonify({
            "date": date_str,
            "tasks": [],
            "appointments": [],
            "tracker": "",
            "notes": ""
        })

    tasks = Task.query.filter_by(day_id=day.id).all()
    appts = Appointment.query.filter_by(day_id=day.id).all()

    return jsonify({
        "date": day.date,
        "tracker": day.tracker or "",
        "notes": day.notes or "",
        "tasks": [
            {
                "checked": t.checked,
                "priority": t.priority,
                "description": t.description,
            }
            for t in tasks
        ],
        "appointments": [
            {"time": a.time, "text": a.text}
            for a in appts
        ]
    })


@app.post("/api/day/<date_str>")
def api_save_day(date_str):
    """
    Overwrite planner data for the given date ("YYYY-MM-DD") for the current user.
    """
    user = current_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401

    payload = request.json or {}

    # Find or create the day row
    day = Day.query.filter_by(user_id=user.id, date=date_str).first()
    if not day:
        day = Day(date=date_str, user_id=user.id)
        db.session.add(day)
        db.session.commit()

    # Update notes & tracker
    day.notes = payload.get("notes", "") or ""
    day.tracker = payload.get("tracker", "") or ""
    db.session.commit()

    # Reset tasks & appointments for a clean overwrite
    Task.query.filter_by(day_id=day.id).delete()
    Appointment.query.filter_by(day_id=day.id).delete()
    db.session.commit()

    # Save tasks
    for t in payload.get("tasks", []):
        task = Task(
            day_id=day.id,
            priority=t.get("priority", "A"),
            description=t.get("description", "") or "",
            checked=bool(t.get("checked", False)),
        )
        db.session.add(task)

    # Save appointments
    for a in payload.get("appointments", []):
        appt = Appointment(
            day_id=day.id,
            time=a.get("time", "") or "",
            text=a.get("text", "") or "",
        )
        db.session.add(appt)

    db.session.commit()

    return jsonify({"status": "saved"})

# ---------------------------------------------------------------------
# STATIC ROUTES
# ---------------------------------------------------------------------
@app.get("/")
def index():
    return send_from_directory(".", "index.html")


@app.get("/planner.js")
def planner_js():
    return send_from_directory(".", "planner.js")


@app.get("/<path:path>")
def static_proxy(path):
    # This handles CSS or other assets if you add them later
    return send_from_directory(".", path)

# ---------------------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------------------
@app.get("/health")
def health():
    return "OK", 200

# ---------------------------------------------------------------------
# INIT & ENTRYPOINT
# ---------------------------------------------------------------------
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    # Local dev. On Render, gunicorn will run `app:app`
    app.run(host="0.0.0.0", port=5000)
