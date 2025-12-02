import os
from flask import Flask, request, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder=".", static_url_path="")

# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")

CORS(app, supports_credentials=True)

db = SQLAlchemy(app)

# ---------------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------------
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
    tracker = db.Column(db.Text)
    notes = db.Column(db.Text)

    appointments = db.relationship("Appointment", cascade="all, delete-orphan")
    tasks = db.relationship("Task", cascade="all, delete-orphan")


class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey("days.id"))
    checked = db.Column(db.Boolean)
    priority = db.Column(db.String)
    description = db.Column(db.String)


class Appointment(db.Model):
    __tablename__ = "appointments"
    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(db.Integer, db.ForeignKey("days.id"))
    time = db.Column(db.String)
    text = db.Column(db.String)


# ---------------------------------------------------------------------
# AUTH HELPERS
# ---------------------------------------------------------------------
def require_login():
    if "user_id" not in session:
        return False
    return True


# ---------------------------------------------------------------------
# AUTH ENDPOINTS
# ---------------------------------------------------------------------
@app.post("/api/signup")
def signup():
    data = request.json
    email = data.get("email", "").lower().strip()
    password = data.get("password", "")
    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    # Check existing
    if User.query.filter_by(email=email).first():
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
def login():
    data = request.json
    email = data.get("email", "").lower().strip()
    password = data.get("password", "")

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid credentials"}), 401

    session["user_id"] = user.id
    return jsonify({"status": "ok", "user_id": user.id})


@app.get("/api/logout")
def logout():
    session.clear()
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------
# MAIN SAVE / LOAD ENDPOINTS (PER USER)
# ---------------------------------------------------------------------
@app.get("/api/day/<date>")
def load_day(date):
    if not require_login():
        return jsonify({"error": "Not logged in"}), 401

    user_id = session["user_id"]
    day = Day.query.filter_by(user_id=user_id, date=date).first()

    if not day:
        return jsonify({
            "date": date,
            "tasks": [],
            "appointments": [],
            "tracker": "",
            "notes": ""
        }), 200

    return jsonify({
        "date": date,
        "tasks": [
            {"checked": t.checked, "priority": t.priority, "description": t.description}
            for t in day.tasks
        ],
        "appointments": [
            {"time": a.time, "text": a.text}
            for a in day.appointments
        ],
        "tracker": day.tracker or "",
        "notes": day.notes or ""
    })


@app.post("/api/day/<date>")
def save_day(date):
    if not require_login():
        return jsonify({"error": "Not logged in"}), 401

    user_id = session["user_id"]
    data = request.json

    day = Day.query.filter_by(user_id=user_id, date=date).first()
    if not day:
        day = Day(date=date, user_id=user_id)
        db.session.add(day)
        db.session.commit()

    # Update fields
    day.tracker = data.get("tracker", "")
    day.notes = data.get("notes", "")

    # Clear old tasks/appointments
    Task.query.filter_by(day_id=day.id).delete()
    Appointment.query.filter_by(day_id=day.id).delete()

    # Insert new tasks
    for t in data.get("tasks", []):
        task = Task(
            day_id=day.id,
            checked=t.get("checked", False),
            priority=t.get("priority", "A"),
            description=t.get("description", "")
        )
        db.session.add(task)

    # Insert new appointments
    for a in data.get("appointments", []):
        appt = Appointment(
            day_id=day.id,
            time=a.get("time", ""),
            text=a.get("text", "")
        )
        db.session.add(appt)

    db.session.commit()

    return jsonify({"status": "saved"})


# ---------------------------------------------------------------------
# STATIC FILES
# ---------------------------------------------------------------------
@app.get("/")
def serve_index():
    return send_from_directory(".", "index.html")


@app.get("/<path:path>")
def static_proxy(path):
    return send_from_directory(".", path)


# ---------------------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------------------
@app.get("/health")
def health():
    return "ok"


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    tracker = db.Column(db.Text)
    notes = db.Column(db.Text)

    appointments_json = db.Column(db.JSON)

    user = db.relationship("User", backref=db.backref("days", lazy=True))


# ---------------------------------------------------------
# USER AUTH ROUTES
# ---------------------------------------------------------
@app.route("/api/signup", method=["POST"])
def signup():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    hashed = bcrypt.generate_password_hash(password).decode("utf8")
    user = User(email=email, password_hash=hashed)

    db.session.add(user)
    db.session.commit()

    return jsonify({"status": "ok"})


@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    if not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid credentials"}), 401

    # Minimal auth token (You can upgrade later)
    token = f"user-{user.id}-{os.urandom(8).hex()}"

    return jsonify({"token": token, "user_id": user.id})


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def get_user_id_from_request():
    token = request.headers.get("X-Auth")
    if not token:
        return None

    # crude parsing: user-<id>-...
    try:
        parts = token.split("-")
        if len(parts) < 2:
            return None
        return int(parts[1])
    except:
        return None


# ---------------------------------------------------------
# GET DAY (READ)
# ---------------------------------------------------------
@app.route("/api/day/<date>", methods=["GET"])
def get_day(date):
    user_id = get_user_id_from_request()
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    day = Day.query.filter_by(date=date, user_id=user_id).first()
    if not day:
        return jsonify({})  # blank new day

    return jsonify({
        "tasks": day.tasks_json or [],
        "tracker": day.tracker or "",
        "notes": day.notes or "",
        "appointments": day.appointments_json or []
    })


# ---------------------------------------------------------
# SAVE DAY (WRITE)
# ---------------------------------------------------------
@app.route("/api/day/<date>", methods=["POST"])
def save_day(date):
    user_id = get_user_id_from_request()
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    payload = request.json

    day = Day.query.filter_by(date=date, user_id=user_id).first()
    if not day:
        day = Day(date=date, user_id=user_id)
        db.session.add(day)

    day.tasks_json = payload.get("tasks", [])
    day.tracker = payload.get("tracker", "")
    day.notes = payload.get("notes", "")
    day.appointments_json = payload.get("appointments", [])

    db.session.commit()

    return jsonify({"status": "saved"})


# ---------------------------------------------------------
# STATIC FILE SERVE
# ---------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(".", "index.html")


# ---------------------------------------------------------
# Render health check
# ---------------------------------------------------------
@app.route("/health")
def health():
    return "ok"  


if __name__ == "__main__":
    app.run()
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
