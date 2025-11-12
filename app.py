# app.py – Franklin Planner (Left Page Only, compact + teal theme, 3 calendars inline)

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
}}

/* ---- Mini calendars: force all 3 inline on desktop ---- */
.calrow {{
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: nowrap;
  gap: 6px;
  margin-bottom: .4rem;
}}
.calbox {{
  flex: 0 0 28%;
  max-width: 28%;
  border: 1px solid {RULE};
  border-radius: 6px;
  padding: .18rem .22rem .24rem;
  background: white;
}}
/* On narrow screens, allow wrapping so it's readable 
@media (max-width: 820px) {{
  .calrow {{ flex-wrap: wrap; }}
  .calbox {{ flex: 0 0 100%; max-width: 100%; }}
}}
*/
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
.today  {{ outline: 1px solid {INK}; border-radius: 2px; }}

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
        return {"tasks":[],"tracker":{str(i):"" for i in range(1,9)},"sched":{}}
    tasks=[]
    for t in entry.get("tasks",[]):
        if not isinstance(t,dict): continue
        if "t" not in t and "task" in t: t["t"]=t["task"]
        t.setdefault("p","A"); t.setdefault("t",""); t.setdefault("done",False)
        tasks.append(t)
    entry["tasks"]=tasks
    tr=entry.get("tracker",{})
    entry["tracker"]={str(i):tr.get(str(i),"") for i in range(1,9)}
    entry.setdefault("sched",{})
    return entry

def load_day(d):
    c.execute("SELECT data FROM planner WHERE date=?", (str(d),))
    r=c.fetchone()
    if not r: return normalize({})
    try: return normalize(json.loads(r[0]))
    except: return normalize({})

def save_day(d,data):
    c.execute("REPLACE INTO planner (date,data) VALUES (?,?)",(str(d),json.dumps(normalize(data))))
    conn.commit()

# ---------- HELPERS ----------
def month_grid(y,m):
    f=dt.date(y,m,1)
    sw=(f.weekday()+1)%7
    nxt=dt.date(y+1,1,1) if m==12 else dt.date(y,m+1,1)
    dim=(nxt-dt.timedelta(days=1)).day
    return sw,dim

def render_calendar(target,today):
    sw,dim=month_grid(target.year,target.month)
    st.markdown(f'<div class="calbox"><div class="calcap">{target.strftime("%b %Y")}</div>',unsafe_allow_html=True)
    st.markdown('<div class="calgrid">'+"".join(f'<div class="calhdr">{d}</div>' for d in ["S","M","T","W","T","F","S"])+"</div>",unsafe_allow_html=True)
    html='<div class="calgrid">'
    html+="".join('<div></div>' for _ in range(sw))
    for day in range(1,dim+1):
        cls="today" if (target.year,target.month,day)==(today.year,today.month,today.day) else ""
        html+=f'<div class="{cls}">{day}</div>'
    html+="</div></div>"
    st.markdown(html,unsafe_allow_html=True)

def day_stamp(d):
    doy=d.timetuple().tm_yday
    total=366 if (d.year%4==0 and (d.year%100!=0 or d.year%400==0)) else 365
    left=total-doy
    week=d.isocalendar().week
    return f"{doy}th Day • {left} Left • Week {week}"

# ---------- PAGE ----------
today=dt.date.today()
date=st.date_input("",today,format="YYYY-MM-DD")
stored=load_day(date)

# Header
st.markdown(f"### {date.strftime('%A, %B %d, %Y')}")
st.markdown(f"<div style='text-align:right;font-weight:700'>{day_stamp(date)}</div>",unsafe_allow_html=True)

# Three calendars (single line on desktop)
st.markdown('<div class="calrow">',unsafe_allow_html=True)
prev=(date.replace(day=1)-dt.timedelta(days=1)).replace(day=1)
next_=(date.replace(day=28)+dt.timedelta(days=10)).replace(day=1)
for d in [prev,date.replace(day=1),next_]:
    render_calendar(d,date)
st.markdown('</div>',unsafe_allow_html=True)

# ABC Task List
st.markdown('<div class="section"><div class="section-title">ABC Prioritized Daily Task List</div>',unsafe_allow_html=True)
row=st.columns([0.15,0.7,0.15])
pri=row[0].selectbox("P",["A","B","C"],label_visibility="collapsed")
txt=row[1].text_input("Task","",label_visibility="collapsed",placeholder="Task description…")
if row[2].button("Add",use_container_width=True) and txt.strip():
    stored["tasks"].append({"p":pri,"t":txt.strip(),"done":False})
    save_day(date,stored); st.rerun()

for i,t in enumerate(stored["tasks"]):
    task_text=str(t.get("t") or t.get("task") or "")
    r=st.columns([0.08,0.08,0.72,0.12])
    done=r[0].checkbox("",value=t.get("done",False),key=f"td{i}")
    if done!=t.get("done",False):
        t["done"]=done; save_day(date,stored)
    r[1].markdown(f"**{t.get('p','')}**")
    r[2].markdown(task_text)
    if r[3].button("✕",key=f"tx{i}"):
        stored["tasks"].pop(i); save_day(date,stored); st.rerun()
st.markdown('</div>',unsafe_allow_html=True)

# Daily Tracker
st.markdown('<div class="section"><div class="section-title">Daily Tracker</div>',unsafe_allow_html=True)
for i in range(1,9):
    rr=st.columns([0.06,0.94])
    rr[0].markdown(f"**{i}**")
    stored["tracker"][str(i)]=rr[1].text_input(f"trk{i}",value=stored["tracker"].get(str(i),""),label_visibility="collapsed")
st.markdown('</div>',unsafe_allow_html=True)

# Appointment Schedule
st.markdown('<div class="section"><div class="section-title">Appointment Schedule</div>',unsafe_allow_html=True)
for h in range(6,23):
    hh=f"{h:02d}:00"
    st.markdown('<div class="schedule-row">',unsafe_allow_html=True)
    st.markdown(f'<div class="timecell">{hh}</div>',unsafe_allow_html=True)
    stored["sched"][hh]=st.text_input("",value=stored["sched"].get(hh,""),key=f"s{hh}",label_visibility="collapsed")
    st.markdown('</div>',unsafe_allow_html=True)
st.markdown('</div>',unsafe_allow_html=True)

# Save Bar
cols=st.columns([0.2,0.6,0.2])
if cols[0].button("💾 Save",use_container_width=True):
    save_day(date,stored); st.success("Saved ✔")
if cols[2].button("🗑 Clear",use_container_width=True):
    stored={"tasks":[],"tracker":{str(i):"" for i in range(1,9)},"sched":{}}
    save_day(date,stored); st.rerun()

st.caption("Franklin Daily Planner • Left Page Only • Compact Teal Layout (3 calendars inline)")
