# app.py
import os
from datetime import datetime, date as date_cls

from flask import Flask, jsonify, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

# ------------------------------------------------------------------------------
# App / DB setup
# ------------------------------------------------------------------------------

app = Flask(__name__)

# Secret key for sessions
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# Database URL (Render gives DATABASE_URL)
raw_db_url = os.environ.get("DATABASE_URL", "sqlite:///planner.db")
# Render sometimes uses old postgres:// scheme
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = raw_db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# CORS – allow your frontend origin (or all in dev)
frontend_origin = os.environ.get("FRONTEND_ORIGIN", "*")
CORS(
    app,
    supports_credentials=True,
    resources={r"/api/*": {"origins": frontend_origin}},
)


# ------------------------------------------------------------------------------
# Models
# ------------------------------------------------------------------------------

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(120))
    password_hash = db.Column(db.String(255))  # optional (we'll allow passwordless)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)


class Day(db.Model):
    __tablename__ = "days"

    id = db.Column(db.Integer, primary_key=True)

    # date of the planner page
    date = db.Column(db.Date, nullable=False)

    # IMPORTANT: in your existing DB this column is TEXT.
    # We keep it as String here and always store str(user.id)
    # to avoid the Postgres "text = integer" error.
    user_id = db.Column(db.String, nullable=False, index=True)

    # Long notes text on the right side, etc.
    notes = db.Column(db.Text, default="")

    # JSON blob with tasks, appointments, trackers, etc.
    # Example structure (front-end can decide):
    # {
    #   "appointments": [...],
    #   "tasks": [...],
    #   "abc_list": [...],
    #   "daily_tracker": {...},
    #   ...
    # }
    tracker = db.Column(db.JSON, default=dict)


# Create tables if they don't exist
with app.app_context():
    db.create_all()


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def get_current_user() -> User | None:
    """Return the logged-in user based on the session, or None."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def require_user():
    """Helper to guard API routes."""
    user = get_current_user()
    if not user:
        return None, (jsonify({"error": "Unauthorized"}), 401)
    return user, None


def parse_date(date_str: str) -> date_cls:
    """Parse YYYY-MM-DD into a date object."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        # If parsing fails, raise 400
        return None


def default_tracker_payload():
    """Default empty structure for a new day – front-end can expand this as needed."""
    return {
        "appointments": [],   # your schedule/appointments
        "tasks": [],          # daily tasks list
        "abc_list": [],       # prioritized ABC list
        "daily_tracker": {},  # habit/checkbox tracker
    }


def day_to_dict(day: Day):
    """Serialize a Day model to JSON for the frontend."""
    return {
        "id": day.id,
        "date": day.date.isoformat(),
        "notes": day.notes or "",
        # Ensure tracker is always a dict with known keys
        "tracker": {
            **default_tracker_payload(),
            **(day.tracker or {}),
        },
    }


# ------------------------------------------------------------------------------
# Auth routes
# ------------------------------------------------------------------------------

@app.route("/api/login", methods=["POST"])
def login():
    """
    Simple login endpoint.

    Expected JSON:
    {
        "email": "you@example.com",
        "name": "Andy",              # optional
        "password": " optional "     # currently optional – you can enforce later
    }

    For now, if the user exists we log them in.
    If not, we create the user (password optional).
    """
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()
    name = data.get("name") or ""
    password = data.get("password")

    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = User.query.filter_by(email=email).first()
    if user is None:
        # Create a new user
        user = User(email=email, name=name)
        if password:
            user.set_password(password)
        db.session.add(user)
        db.session.commit()
    else:
        # If you decide to enforce password later, you can check it here.
        if user.password_hash and password:
            if not user.check_password(password):
                return jsonify({"error": "Invalid credentials"}), 401

    # Store user id in session
    session["user_id"] = user.id

    return jsonify(
        {
            "id": user.id,
            "email": user.email,
            "name": user.name,
        }
    )


@app.route("/api/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify({"ok": True})


@app.route("/api/me", methods=["GET"])
def me():
    """Return current user info (for the frontend to know who is logged in)."""
    user = get_current_user()
    if not user:
        return jsonify({"user": None}), 200
    return jsonify(
        {
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
            }
        }
    )


# ------------------------------------------------------------------------------
# Day routes (per-user, per-date)
# ------------------------------------------------------------------------------

@app.route("/api/day/<date_str>", methods=["GET"])
def get_day(date_str):
    """
    Get the planner data for the logged-in user on a given date.

    - Requires login (session-based)
    - date_str: YYYY-MM-DD
    - Returns a Day; if it doesn't exist, creates a blank day for that user+date
    """
    user, err = require_user()
    if err:
        return err

    parsed_date = parse_date(date_str)
    if not parsed_date:
        return jsonify({"error": "Invalid date format, expected YYYY-MM-DD"}), 400

    # IMPORTANT: user_id is stored as TEXT in DB, so compare with str(user.id)
    day = Day.query.filter_by(user_id=str(user.id), date=parsed_date).first()

    if day is None:
        day = Day(
            date=parsed_date,
            user_id=str(user.id),
            notes="",
            tracker=default_tracker_payload(),
        )
        db.session.add(day)
        db.session.commit()

    return jsonify(day_to_dict(day))


@app.route("/api/day/<date_str>", methods=["POST"])
def save_day(date_str):
    """
    Save planner data for a given date (for the logged-in user).

    Expected JSON body:
    {
        "notes": "string",
        "tracker": {
            "appointments": [...],
            "tasks": [...],
            "abc_list": [...],
            "daily_tracker": {...},
            ...
        }
    }

    Frontend: just send whatever structure you use for `tracker`.
    """
    user, err = require_user()
    if err:
        return err

    parsed_date = parse_date(date_str)
    if not parsed_date:
        return jsonify({"error": "Invalid date format, expected YYYY-MM-DD"}), 400

    payload = request.get_json(force=True) or {}
    notes = payload.get("notes") or ""
    tracker_from_client = payload.get("tracker") or {}

    # Ensure we have a day row for this user+date
    day = Day.query.filter_by(user_id=str(user.id), date=parsed_date).first()
    if day is None:
        day = Day(
            date=parsed_date,
            user_id=str(user.id),
        )
        db.session.add(day)

    day.notes = notes

    # Merge with default structure so keys like appointments/tasks always exist
    merged_tracker = {
        **default_tracker_payload(),
        **(day.tracker or {}),
        **tracker_from_client,
    }
    day.tracker = merged_tracker

    db.session.commit()

    return jsonify(day_to_dict(day))


# ------------------------------------------------------------------------------
# Health check / simple root
# ------------------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/")
def root():
    # This can serve an index.html or just a simple message.
    return "Franklin Planner backend is running."


# ------------------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    # For local dev; Render will use gunicorn / a Procfile
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
