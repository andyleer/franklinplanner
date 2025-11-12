# app.py – Franklin Planner (Left Page Only, Compact, 6 Preloaded Tasks + Inline Add)

import streamlit as st
import datetime as dt
import json
import sqlite3
from pathlib import Path

st.set_page_config(page_title="Franklin Daily Planner", page_icon="📘", layout="wide")

INK  = "#0b6b6c"
PAPER= "#f8fbfa"
RULE = "#9bc7c3"
LINES= "#d8ebe9"

# ---------- STYLE ----------
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&display=swap');

html, body, .block-container {{
  background: {PAPER};
  color: {INK};
  font-family: "Libre Baskerville", Georgia, serif;
  font-size: 0.9rem;
  line-height: 1.25em;
}}
* {{ color-scheme: only light; }}
.block-container {{ padding-top: .5rem; max-width: 780px; }}

.section {{
  border: 1px solid {RULE};
  border-radius: 8px;
  background: white;
  padding: .3rem .5rem;
  margin-bottom: .4rem;
}}
.section-title {{
  font-variant-caps: small-caps;
  font-size: .85rem;
  font-weight: 700;
  border-bottom: 1px solid {RULE};
  margin-bottom: .25rem;
  padding-bottom: .1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}}
.add-btn {{
  background: none;
  border: none;
  color: {INK};
  font-size: 1.1rem;
  cursor: pointer;
}}
.add-btn:hover {{ color: #058; }}

.schedule-row {{
  display: grid;
  grid-template-columns: 48px 1fr;
  align-items: center;
  border-bottom: 1px solid {LINES};
}}
.timecell {{ font-weight: 700; font-size: .85rem; color: {INK}; }}

.stTextInput > div > div > input {{
  font-size: .85rem;
  padding: .25rem .4rem;
}}
</style>
""", unsafe_allow_html=True)

# ---------- DB ----------
DB = Path("planner.db")
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS planner (date TEXT PRIMARY KEY, data TEXT)")
conn.commit()

def normalize(entry: dict) -> dict:
    if not entry:
        entry = {"tasks": [], "tracker": {str(i): "" for i in range(1, 9)}, "sched": {}}
    tasks = []
    for t in entry.get("tasks", []):
        if not isinstance(t, dict):
            continue
        if "t" not in t and "task" in t:
            t["t"] = t["task"]
        t.setdefault("p", "A")
        t.setdefault("t", "")
        t.setdefault("done", False)
        tasks.append(t)
    # pad to 6 blank tasks
    while len(tasks) < 6:
        tasks.append({"p": "A", "t": "", "done": False})
    entry["tasks"] = tasks
    tr = entry.get("tracker", {})
    entry["tracker"] = {str(i): tr.get(str(i), "") for i in range(1, 9)}
    entry.setdefault("sched", {})
    return entry

def load_day(d):
    c.execute("SELECT data FROM planner WHERE date=?", (str(d),))
    r = c.fetchone()
    if not r:
        return normalize({})
    try:
        return normalize(json.loads(r[0]))
    except:
        return normalize({})

def save_day(d, data):
    c.execute("REPLACE INTO planner (date, data) VALUES (?,?)", (str(d), json.dumps(normalize(data))))
    conn.commit()

def day_stamp(d):
    doy = d.timetuple().tm_yday
    total = 366 if (d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0)) else 365
    left = total - doy
    week = d.isocalendar().week
    return f"{doy}th Day • {left} Left • Week {week}"

# ---------- PAGE ----------
today = dt.date.today()
date = st.date_input("", today, format="YYYY-MM-DD")
stored = load_day(date)

# Header
st.markdown(f"### {date.strftime('%A, %B %d, %Y')}")
st.markdown(f"<div style='text-align:right;font-weight:700'>{day_stamp(date)}</div>", unsafe_allow_html=True)

# ---------- ABC TASK LIST ----------
col_header = st.columns([0.9, 0.1])
with col_header[0]:
    st.markdown('<div class="section-title">ABC Prioritized Daily Task List</div>', unsafe_allow_html=True)
with col_header[1]:
    if st.button("＋", use_container_width=True):
        stored["tasks"].append({"p": "A", "t": "", "done": False})
        save_day(date, stored)
        st.rerun()

st.markdown('<div class="section">', unsafe_allow_html=True)
for i, t in enumerate(stored["tasks"]):
    cols = st.columns([0.08, 0.12, 0.68, 0.12])
    done = cols[0].checkbox("", value=t.get("done", False), key=f"td{i}")
    if done != t.get("done", False):
        t["done"] = done
        save_day(date, stored)
    pval = cols[1].selectbox("", ["A", "B", "C"], key=f"pri{i}", index=["A","B","C"].index(t.get("p","A")), label_visibility="collapsed")
    if pval != t.get("p", "A"):
        t["p"] = pval
        save_day(date, stored)
    task_text = cols[2].text_input("", value=t.get("t", ""), key=f"txt{i}", label_visibility="collapsed", placeholder="Task...")
    if task_text != t.get("t", ""):
        t["t"] = task_text
        save_day(date, stored)
    if cols[3].button("✕", key=f"del{i}"):
        stored["tasks"].pop(i)
        save_day(date, stored)
        st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# ---------- DAILY TRACKER ----------
st.markdown('<div class="section"><div class="section-title">Daily Tracker</div>', unsafe_allow_html=True)
for i in range(1, 9):
    rr = st.columns([0.06, 0.94])
    rr[0].markdown(f"**{i}**")
    stored["tracker"][str(i)] = rr[1].text_input(f"trk{i}", value=stored["tracker"].get(str(i), ""), label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

# ---------- APPOINTMENT SCHEDULE ----------
st.markdown('<div class="section"><div class="section-title">Appointment Schedule</div>', unsafe_allow_html=True)
for h in range(6, 23):
    hh = f"{h:02d}:00"
    st.markdown('<div class="schedule-row">', unsafe_allow_html=True)
    st.markdown(f'<div class="timecell">{hh}</div>', unsafe_allow_html=True)
    stored["sched"][hh] = st.text_input("", value=stored["sched"].get(hh, ""), key=f"s{hh}", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ---------- SAVE BAR ----------
cols = st.columns([0.2, 0.6, 0.2])
if cols[0].button("💾 Save", use_container_width=True):
    save_day(date, stored)
    st.success("Saved ✔")
if cols[2].button("🗑 Clear", use_container_width=True):
    stored = {"tasks": [{"p": "A", "t": "", "done": False} for _ in range(6)],
              "tracker": {str(i): "" for i in range(1, 9)}, "sched": {}}
    save_day(date, stored)
    st.rerun()

st.caption("Franklin Daily Planner • Compact Left Page • 6 Preloaded Tasks + Inline Add")
