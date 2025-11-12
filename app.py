# app.py – Franklin Planner Left Page (CSS Grid + Mini Calendars, fully editable)

import streamlit as st
import datetime as dt
import json
import sqlite3
from pathlib import Path
import calendar

st.set_page_config(page_title="Franklin Daily Planner", page_icon="📘", layout="wide")

INK = "#0b6b6c"
PAPER = "#f8fbfa"
RULE = "#9bc7c3"
LINES = "#d8ebe9"

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
.block-container {{
  padding-top: .5rem;
  max-width: 760px;
}}

h3.date-header {{
  font-size: 1.4rem;
  font-weight: 700;
  color: {INK};
  margin-bottom: .2rem;
}}

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

/* ---- Mini calendars ---- */
.calrow {{
  display: flex;
  justify-content: space-between;
  flex-wrap: nowrap;
  overflow-x: auto;
  margin-bottom: .3rem;
  gap: 10px;
}}
.calbox {{
  flex: 0 0 30%;
  max-width: 30%;
  border: 1px solid {RULE};
  border-radius: 6px;
  padding: .15rem .2rem .25rem;
  background: white;
}}
.calcap {{
  font-size: .68rem;
  font-weight: 700;
  text-align: center;
  margin-bottom: 2px;
}}
.calgrid {{
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
}}
.calgrid div {{
  text-align: center;
  font-size: .58rem;
  padding: 1px 0;
}}
.calhdr {{ font-weight: 700; background: #eef6f5; }}
.today {{ outline: 1px solid {INK}; border-radius: 2px; }}

/* ---- Schedule ---- */
.schedule-row {{
  display: grid;
  grid-template-columns: 48px 1fr;
  align-items: center;
  border-bottom: 1px solid {LINES};
}}
.timecell {{
  font-weight: 700;
  font-size: .85rem;
  color: {INK};
  padding-right: .2rem;
  text-align: right;
}}

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

def render_calendar(target, today):
    _, num_days = calendar.monthrange(target.year, target.month)
    first_day = dt.date(target.year, target.month, 1).weekday()
    st.markdown(f'<div class="calbox"><div class="calcap">{target.strftime("%B %Y")}</div>', unsafe_allow_html=True)
    st.markdown('<div class="calgrid">' + "".join(f'<div class="calhdr">{d}</div>' for d in ["S","M","T","W","T","F","S"]) + '</div>', unsafe_allow_html=True)
    html = '<div class="calgrid">'
    html += "".join('<div></div>' for _ in range((first_day + 1) % 7))
    for day in range(1, num_days + 1):
        cls = "today" if (target.year, target.month, day) == (today.year, today.month, today.day) else ""
        html += f'<div class="{cls}">{day}</div>'
    html += "</div></div>"
    st.markdown(html, unsafe_allow_html=True)

# ---------- PAGE ----------
today = dt.date.today()
date = st.date_input("", today, format="YYYY-MM-DD")
stored = load_day(date)

# Header
st.markdown(f"<h3 class='date-header'>{date.strftime('%A, %B %d, %Y')}</h3>", unsafe_allow_html=True)

# Mini calendars: previous, current, next
st.markdown('<div class="calrow">', unsafe_allow_html=True)
prev = (date.replace(day=1) - dt.timedelta(days=1)).replace(day=1)
next_ = (date.replace(day=28) + dt.timedelta(days=10)).replace(day=1)
for d in [prev, date.replace(day=1), next_]:
    render_calendar(d, date)
st.markdown('</div>', unsafe_allow_html=True)

# ABC Prioritized Daily Task List
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
    pval = cols[1].selectbox("", ["A", "B", "C"], key=f"pri{i}", index=["A", "B", "C"].index(t.get("p", "A")), label_visibility="collapsed")
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

# Daily Tracker
st.markdown('<div class="section"><div class="section-title">Daily Tracker</div>', unsafe_allow_html=True)
for i in range(1, 9):
    rr = st.columns([0.06, 0.94])
    rr[0].markdown(f"**{i}**")
    stored["tracker"][str(i)] = rr[1].text_input(f"trk{i}", value=stored["tracker"].get(str(i), ""), label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

# Appointment Schedule
st.markdown('<div class="section"><div class="section-title">Appointment Schedule</div>', unsafe_allow_html=True)
for h in range(8, 18):
    hh = f"{h}:00"
    st.markdown('<div class="schedule-row">', unsafe_allow_html=True)
    st.markdown(f'<div class="timecell">{hh}</div>', unsafe_allow_html=True)
    stored["sched"][hh] = st.text_input("", value=stored["sched"].get(hh, ""), key=f"s{hh}", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Save Bar
cols = st.columns([0.2, 0.6, 0.2])
if cols[0].button("💾 Save", use_container_width=True):
    save_day(date, stored)
    st.success("Saved ✔")
if cols[2].button("🗑 Clear", use_container_width=True):
    stored = {"tasks": [{"p": "A", "t": "", "done": False} for _ in range(6)], "tracker": {str(i): "" for i in range(1, 9)}, "sched": {}}
    save_day(date, stored)
    st.rerun()

st.caption("Franklin Daily Planner • Left Page • CSS Grid + Mini Calendars (Teal Theme)")
