import os
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# -------------------------
# DATABASE CONFIG
# -------------------------
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -------------------------
# MODELS
# -------------------------

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)

class Day(db.Model):
    __tablename__ = "days"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    notes = db.Column(db.Text, default="")
    tracker = db.Column(db.Text, default="")

class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey("days.id"), nullable=False)
    priority = db.Column(db.String, default="C")
    description = db.Column(db.Text, default="")
    checked = db.Column(db.Boolean, default=False)

class Appointment(db.Model):
    __tablename__ = "appointments"
    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey("days.id"), nullable=False)
    time = db.Column(db.String, nullable=False)
    text = db.Column(db.Text, default="")

# -------------------------
# HELPERS
# -------------------------

def get_or_create_user():
    """Gets user from header or creates one."""
    email = request.headers.get("X-User-Email")

    if not email:
        return None, ("Missing X-User-Email header", 400)

    existing = User.query.filter_by(email=email).first()
    if existing:
        return existing, None

    new_user = User(email=email)
    db.session.add(new_user)
    db.session.commit()
    return new_user, None

def get_or_create_day(user, date_str):
    """Gets or creates a day entry for a user"""
    day = Day.query.filter_by(user_id=user.id, date=date_str).first()
    if day:
        return day

    day = Day(date=date_str, user_id=user.id)
    db.session.add(day)
    db.session.commit()
    return day

# -------------------------
# API ROUTES
# -------------------------

@app.route("/api/day/<date_str>", methods=["GET"])
def api_get_day(date_str):
    user, err = get_or_create_user()
    if err:
        return err

    day = Day.query.filter_by(user_id=user.id, date=date_str).first()

    if not day:
        return jsonify({
            "tasks": [],
            "appointments": [],
            "notes": "",
            "tracker": ""
        })

    tasks = Task.query.filter_by(day_id=day.id).all()
    appointments = Appointment.query.filter_by(day_id=day.id).all()

    return jsonify({
        "tasks": [{
            "checked": t.checked,
            "priority": t.priority,
            "description": t.description
        } for t in tasks],
        "appointments": [{
            "time": a.time,
            "text": a.text
        } for a in appointments],
        "notes": day.notes,
        "tracker": day.tracker
    })

@app.route("/api/day/<date_str>", methods=["POST"])
def api_save_day(date_str):
    user, err = get_or_create_user()
    if err:
        return err

    payload = request.get_json()
    day = get_or_create_day(user, date_str)

    # Save notes & tracker
    day.notes = payload.get("notes", "")
    day.tracker = payload.get("tracker", "")

    # Replace tasks
    Task.query.filter_by(day_id=day.id).delete()
    for t in payload.get("tasks", []):
        task = Task(
            day_id=day.id,
            priority=t.get("priority", "C"),
            description=t.get("description", ""),
            checked=t.get("checked", False)
        )
        db.session.add(task)

    # Replace appointments
    Appointment.query.filter_by(day_id=day.id).delete()
    for a in payload.get("appointments", []):
        appt = Appointment(
            day_id=day.id,
            time=a.get("time", ""),
            text=a.get("text", "")
        )
        db.session.add(appt)

    db.session.commit()

    return jsonify({"status": "saved"})

# -------------------------
# STATIC FILE SERVE
# -------------------------

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/<path:path>")
def static_proxy(path):
    return send_from_directory(".", path)

@app.route("/health")
def health():
    return "OK", 200

# -------------------------
# MAIN
# -------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=8000)
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
