import streamlit as st
import datetime
import pandas as pd
import json
import sqlite3

st.set_page_config(page_title="Franklin Daily Planner", layout="wide")

# --- Colors & Styles ---
st.markdown("""
<style>
body {
    background-color: #f4f8f8;
    color: #0A6C6D;
    font-family: 'Georgia', serif;
}
h1, h2, h3 {
    color: #0A6C6D;
}
textarea, input {
    background-color: #ffffff !important;
    color: #0A6C6D !important;
}
.block-container {
    padding-top: 1rem;
}
</style>
""", unsafe_allow_html=True)

# --- Database ---
conn = sqlite3.connect("planner.db", check_same_thread=False)
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS planner (date TEXT PRIMARY KEY, data TEXT)""")
conn.commit()

def load_day(date):
    c.execute("SELECT data FROM planner WHERE date=?", (date,))
    row = c.fetchone()
    return json.loads(row[0]) if row else None

def save_day(date, data):
    c.execute("REPLACE INTO planner (date, data) VALUES (?, ?)", (date, json.dumps(data)))
    conn.commit()

# --- Date & Header ---
today = datetime.date.today()
selected_date = st.date_input("Select Date", today)

col1, col2 = st.columns([1.2, 1])

# --- Left Page ---
with col1:
    st.markdown(f"### {selected_date.strftime('%A, %B %d, %Y')}")
    data = load_day(str(selected_date)) or {
        "tasks": [],
        "notes": "",
        "quote": "",
        "tracker": {}
    }

    st.subheader("Prioritized Daily Task List (A/B/C)")
    new_task = st.text_input("Add task")
    if st.button("Add Task"):
        if new_task:
            data["tasks"].append({"task": new_task, "done": False})
            save_day(str(selected_date), data)
            st.rerun()

    for i, t in enumerate(data["tasks"]):
        cols = st.columns([0.1, 0.8, 0.1])
        done = cols[0].checkbox("", value=t["done"], key=f"t{i}")
        if done != t["done"]:
            t["done"] = done
            save_day(str(selected_date), data)
        cols[1].write(t["task"])
        if cols[2].button("❌", key=f"d{i}"):
            data["tasks"].pop(i)
            save_day(str(selected_date), data)
            st.rerun()

    st.divider()
    st.subheader("Appointment Schedule")
    times = [f"{h:02d}:00" for h in range(6, 23)]
    for t in times:
        st.text_input(f"{t}", key=f"sched_{t}")

    st.divider()
    st.subheader("Daily Tracker")
    for i in range(1, 9):
        data["tracker"][f"{i}"] = st.text_input(f"{i}", value=data["tracker"].get(f"{i}", ""), key=f"trk_{i}")

# --- Right Page ---
with col2:
    st.markdown("#### Daily Quote or Affirmation")
    data["quote"] = st.text_area("", value=data["quote"], height=80)
    st.divider()
    st.subheader("Daily Notes")
    data["notes"] = st.text_area("Notes", value=data["notes"], height=400)

if st.button("💾 Save"):
    save_day(str(selected_date), data)
    st.success("Saved!")

st.caption("Franklin Planner • Built with Streamlit")
