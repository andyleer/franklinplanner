import os
import datetime as dt

from flask import (
    Flask,
    request,
    jsonify,
    send_from_directory,
    session,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# ------------------------------------------------------------------------------
# App + DB setup
# ------------------------------------------------------------------------------

app = Flask(__name__, static_folder=".", static_url_path="")

# Secret key for sessions (set a strong one in Render)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-prod")

# Render / Heroku style DATABASE_URL handling
db_url = os.environ.get("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ------------------------------------------------------------------------------
# Models
# ------------------------------------------------------------------------------

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=dt.datetime.utcnow)


class Day(db.Model):
    __tablename__ = "days"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    date = db.Column(db.Date, nullable=False)
    tracker = db.Column(db.Text, default="")
    notes = db.Column(db.Text, default="")

    tasks = db.relationship(
        "Task",
        backref="day",
        cascade="all, delete-orphan",
        lazy=True,
    )
    appointments = db.relationship(
        "Appointment",
        backref="day",
        cascade="all, delete-orphan",
        lazy=True,
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "date", name="uq_days_user_date"),
    )


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(
        db.Integer,
        db.ForeignKey("days.id", ondelete="CASCADE"),
        nullable=False,
    )
    checked = db.Column(db.Boolean, default=False)
    priority = db.Column(db.String(1), default="A")
    description = db.Column(db.Text, default="")


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    day_id = db.Column(
        db.Integer,
        db.ForeignKey("days.id", ondelete="CASCADE"),
        nullable=False,
    )
    time_label = db.Column(db.String(20), nullable=False)  # e.g. "7", "8", "9"
    text = db.Column(db.Text, default="")


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def get_current_user():
    """Return the logged-in user object or None."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def require_user():
    """Return (user, error_response) so we can early-out if not logged in."""
    user = get_current_user()
    if not user:
        return None, (jsonify({"error": "Not logged in"}), 401)
    return user, None


# ------------------------------------------------------------------------------
# Auth routes (JSON-based)
# ------------------------------------------------------------------------------

@app.post("/api/register")
def register():
    """
    JSON: { "email": "...", "password": "..." }
    Creates a user and logs them in.
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "Email already registered"}), 400

    pw_hash = generate_password_hash(password)
    user = User(email=email, password_hash=pw_hash)
    db.session.add(user)
    db.session.commit()

    session["user_id"] = user.id

    return jsonify(
        {
            "status": "ok",
            "user": {"id": user.id, "email": user.email},
        }
    )


@app.post("/api/login")
def login():
    """
    JSON: { "email": "...", "password": "..." }
    Logs the user in by setting session["user_id"].
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password"}), 401

    session["user_id"] = user.id

    return jsonify(
        {
            "status": "ok",
            "user": {"id": user.id, "email": user.email},
        }
    )


@app.post("/api/logout")
def logout():
    session.pop("user_id", None)
    return jsonify({"status": "ok"})


@app.get("/api/me")
def me():
    user = get_current_user()
    if not user:
        return jsonify({"user": None})
    return jsonify({"user": {"id": user.id, "email": user.email}})


# ------------------------------------------------------------------------------
# Planner API – per-user via session
# ------------------------------------------------------------------------------

@app.route("/api/day/<date_str>", methods=["GET", "POST"])
def day_endpoint(date_str):
    """
    GET  /api/day/YYYY-MM-DD  -> load planner state for that user + date
    POST /api/day/YYYY-MM-DD  -> save planner state for that user + date

    Planner JSON schema (what your planner.js already uses):

    {
      "date": "YYYY-MM-DD",
      "tasks": [
        {"checked": bool, "priority": "A"/"B"/"C", "description": "..."},
        ...
      ],
      "tracker": "text",
      "appointments": [
        {"time": "7", "text": "..."},
        ...
      ],
      "notes": "text"
    }
    """
    user, err = require_user()
    if err:
        return err

    # Parse date string
    try:
        date_obj = dt.date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

    if request.method == "GET":
        day = Day.query.filter_by(user_id=user.id, date=date_obj).first()
        if not day:
            # No saved entry yet; let front-end fall back to blanks
            return jsonify(
                {
                    "date": date_str,
                    "tasks": [],
                    "tracker": "",
                    "appointments": [],
                    "notes": "",
                }
            ), 200

        tasks_data = [
            {
                "checked": t.checked,
                "priority": t.priority or "A",
                "description": t.description or "",
            }
            for t in day.tasks
        ]

        appt_data = [
            {
                "time": a.time_label,
                "text": a.text or "",
            }
            for a in day.appointments
        ]

        return jsonify(
            {
                "date": date_str,
                "tasks": tasks_data,
                "tracker": day.tracker or "",
                "appointments": appt_data,
                "notes": day.notes or "",
            }
        )

    # POST – save/update
    payload = request.get_json(silent=True) or {}

    tracker = payload.get("tracker") or ""
    notes = payload.get("notes") or ""
    tasks_payload = payload.get("tasks") or []
    appts_payload = payload.get("appointments") or []

    # Get or create Day row
    day = Day.query.filter_by(user_id=user.id, date=date_obj).first()
    if not day:
        day = Day(user_id=user.id, date=date_obj)
        db.session.add(day)

    day.tracker = tracker
    day.notes = notes

    # Clear existing tasks & appointments
    Task.query.filter_by(day_id=day.id).delete()
    Appointment.query.filter_by(day_id=day.id).delete()

    # Recreate tasks
    for t in tasks_payload:
        priority = (t.get("priority") or "A").upper()
        if priority not in ("A", "B", "C"):
            priority = "A"
        checked = bool(t.get("checked"))
        desc = t.get("description") or ""
        db.session.add(
            Task(
                day=day,
                checked=checked,
                priority=priority,
                description=desc,
            )
        )

    # Recreate appointments
    for a in appts_payload:
        time_label = (a.get("time") or "").strip()
        text = a.get("text") or ""
        if not time_label:
            continue
        db.session.add(
            Appointment(
                day=day,
                time_label=time_label,
                text=text,
            )
        )

    db.session.commit()

    return jsonify({"status": "ok", "date": date_str})


# ------------------------------------------------------------------------------
# Health & static
# ------------------------------------------------------------------------------

@app.get("/health")
def health():
    return jsonify({"status": "ok"})


# (Optional) serve index.html if you're hitting this via / in the browser
@app.get("/")
def index():
    # If your index.html is at project root with this app.py
    return send_from_directory(".", "index.html")


# ------------------------------------------------------------------------------
# Main entry for local dev
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    # For local testing only; Render uses gunicorn
    app.run(host="0.0.0.0", port=5000, debug=True)
