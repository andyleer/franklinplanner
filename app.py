import streamlit as st
import datetime
import sqlite3
import json

st.set_page_config(page_title="Franklin Planner", page_icon="📘", layout="centered")

# --- DATABASE SETUP ---
conn = sqlite3.connect("planner.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS planner (
    date TEXT PRIMARY KEY,
    data TEXT
)
""")
conn.commit()

# --- HELPERS ---
def save_day(date, data):
    c.execute("REPLACE INTO planner (date, data) VALUES (?, ?)", (date, json.dumps(data)))
    conn.commit()

def load_day(date):
    c.execute("SELECT data FROM planner WHERE date = ?", (date,))
    row = c.fetchone()
    return json.loads(row[0]) if row else None

# --- PAGE HEADER ---
st.title("📘 Franklin Daily Planner")
today = datetime.date.today()
selected_date = st.date_input("Select date", today)

st.divider()

# --- LOAD EXISTING DATA ---
data = load_day(str(selected_date)) or {
    "quote": "",
    "tasks": [],
    "schedule": [],
    "notes": "",
    "goals": []
}

# --- QUOTE / INSPIRATION ---
st.subheader("🪞 Daily Quote or Affirmation")
data["quote"] = st.text_area("Enter or paste a quote", value=data["quote"])

# --- GOALS ---
st.subheader("🎯 Daily Goals")
goals = data.get("goals", [])
new_goal = st.text_input("Add a new goal")
if st.button("Add Goal"):
    if new_goal:
        goals.append(new_goal)
        data["goals"] = goals
        save_day(str(selected_date), data)
        st.rerun()

for i, g in enumerate(goals):
    cols = st.columns([0.9, 0.1])
    cols[0].write(f"- {g}")
    if cols[1].button("❌", key=f"goal_del_{i}"):
        goals.pop(i)
        data["goals"] = goals
        save_day(str(selected_date), data)
        st.rerun()

# --- TASKS ---
st.subheader("✅ Tasks (A/B/C priority)")
new_task = st.text_input("Add a task (prefix with A/B/C, e.g., 'A: Call vendor')")
if st.button("Add Task"):
    if new_task:
        data["tasks"].append({"task": new_task, "done": False})
        save_day(str(selected_date), data)
        st.rerun()

for i, t in enumerate(data["tasks"]):
    cols = st.columns([0.1, 0.8, 0.1])
    done = cols[0].checkbox("", value=t["done"], key=f"task_{i}")
    if done != t["done"]:
        t["done"] = done
        save_day(str(selected_date), data)
    cols[1].write(f"{t['task']}")
    if cols[2].button("❌", key=f"del_task_{i}"):
        data["tasks"].pop(i)
        save_day(str(selected_date), data)
        st.rerun()

# --- SCHEDULE ---
st.subheader("🕓 Appointments / Schedule")
times = [f"{h:02d}:00" for h in range(6, 23)]
schedule = data.get("schedule", [{"time": t, "desc": ""} for t in times])

for slot in schedule:
    slot["desc"] = st.text_input(f"{slot['time']}", value=slot["desc"], key=f"sched_{slot['time']}")

data["schedule"] = schedule

# --- NOTES ---
st.subheader("📝 Daily Notes / Journal")
data["notes"] = st.text_area("Write your thoughts, learnings, or reflections here:", value=data["notes"], height=200)

# --- SAVE BUTTON ---
if st.button("💾 Save Today"):
    save_day(str(selected_date), data)
    st.success("Saved successfully!")

st.caption("Built with ❤️ Streamlit + Franklin Planner principles")
