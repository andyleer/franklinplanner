from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
import os
import json

app = Flask(__name__, static_folder=".")

# ------------------------------------------------------
# DATABASE CONFIG
# ------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL not found. Make sure Render env var is set.")

# Render gives “postgresql://” sometimes — SQLAlchemy needs “postgresql+psycopg2://”
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ------------------------------------------------------
# DATABASE MODEL
# ------------------------------------------------------
class PlannerEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), unique=True, nullable=False)
    tasks_json = db.Column(db.Text, nullable=True)
    tracker_text = db.Column(db.Text, nullable=True)
    appts_json = db.Column(db.Text, nullable=True)
    notes_text = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "date": self.date,
            "tasks": json.loads(self.tasks_json) if self.tasks_json else [],
            "tracker": self.tracker_text or "",
            "appointments": json.loads(self.appts_json) if self.appts_json else [],
            "notes": self.notes_text or ""
        }

# Create the table if not exists
with app.app_context():
    db.create_all()

# ------------------------------------------------------
# API ROUTES
# ------------------------------------------------------

@app.route("/api/load")
def api_load():
    date = request.args.get("date")
    if not date:
        return jsonify({"error": "date required"}), 400

    entry = PlannerEntry.query.filter_by(date=date).first()
    if not entry:
        # Return a blank entry if none exists
        return jsonify({
            "date": date,
            "tasks": [],
            "tracker": "",
            "appointments": [],
            "notes": ""
        })

    return jsonify(entry.to_dict())


@app.route("/api/save", methods=["POST"])
def api_save():
    data = request.json
    date = data.get("date")

    entry = PlannerEntry.query.filter_by(date=date).first()

    if not entry:
        entry = PlannerEntry(date=date)

    entry.tasks_json = json.dumps(data.get("tasks", []))
    entry.tracker_text = data.get("tracker", "")
    entry.appts_json = json.dumps(data.get("appointments", []))
    entry.notes_text = data.get("notes", "")

    db.session.add(entry)
    db.session.commit()

    return jsonify({"status": "saved"})


# ------------------------------------------------------
# FRONTEND ROUTE
# ------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(".", "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
