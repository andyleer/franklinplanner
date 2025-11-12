# app.py – Franklin Planner (compact, mobile-friendly, Outlook-ready)
# Fixes:
# - Robust DB normalization of legacy task keys ("task" -> "t")
# - Mini calendars float left in a single row (desktop), with clearfix

import streamlit as st
import datetime as dt
import json
import sqlite3
from pathlib import Path

# ---------- Optional Outlook (Microsoft Graph via O365) ----------
USE_OUTLOOK = True
try:
    from O365 import Account, FileSystemTokenBackend
except Exception:
    USE_OUTLOOK = False

# ---------- Config ----------
st.set_page_config(page_title="Franklin Daily Planner", page_icon="📘", layout="wide")

INK  = "#0b6b6c"
PAPER= "#f8fbfa"
RULE = "#9bc7c3"
LINES= "#d8ebe9"

# ---------- Styles ----------
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&display=swap');

html, body, .block-container {{
  background: {PAPER};
  color: {INK};
  font-family: "Libre Baskerville", Georgia, serif;
  font-size: 0.88rem;
  line-height: 1.2em;
}}
* {{ color-scheme: only light; }}
.block-container {{ padding-top: .5rem; max-width: 1150px; }}

h1,h2,h3,h4 {{ color: {INK}; margin: .2rem 0 .3rem 0; }}

.section {{
  border: 1px solid {RULE};
  border-radius: 8px;
  background: white;
  padding: .3rem .45rem;
  margin-bottom: .3rem;
}}
.section-title {{
  font-variant-caps: small-caps;
  font-size: .85rem;
  font-weight: 700;
  border-bottom: 1px solid {RULE};
  margin-bottom: .2rem;
  padding-bottom: .15rem;
}}

.page-grid {{
  display: grid;
  grid-template-columns: 57% 43%;
  gap: 8px;
}}
@media (max-width: 950px) {{
  .page-grid {{ grid-template-columns: 1fr; }}
}}

.stTextInput > div > div > input,
.stTextArea textarea {{
  font-size: .85rem;
  padding: .3rem .4rem;
}}

.schedule-row {{
  display: grid;
  grid-template-columns: 48px 1fr;
  align-items: center;
  border-bottom: 1px solid {LINES};
  margin: 0;
}}
.timecell {{ font-weight: 700; font-size: .85rem; color: {INK}; }}

/* ---- Mini calendars: float left per your request ---- */
.calrow {{ 
  width: 100%;
  margin-bottom: .4rem;
  /* clearfix */
}}
.calrow::after {{
  content: "";
  display: table;
  clear: both;
}}
.calbox {{
  float: left;
  width: calc(33.333% - 8px);
  margin-right: 12px;
  border: 1px solid {RULE};
  border-radius: 6px;
  padding: .18rem .22rem .24rem;
  background: white;
}}
.calbox:last-child {{ margin-right: 0; }}
.calcap {{ font-size: .68rem; font-weight: 700; text-align: center; margin-bottom: 2px; }}
.calgrid {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 1px; }}
.calgrid div {{ text-align: center; font-size: .58rem; padding: 1px 0; }}
.calhdr {{ font-weight: 700; background: #eef6f5; }}
.today {{ outline: 1px solid {INK}; border-radius: 2px; }}

/* Gutter dots */
.gutter {{
  display: flex; flex-direction: column; align-items: center;
  gap: 14px; opacity: .45; margin-top: 12px;
}}
.hole {{ width: 6px; height: 6px; border-radius: 50%; background: {RULE}; }}
@media (max-width: 950px) {{ .gutter {{ display: none; }} }}

/* Ruled paper for notes */
.lined {{
  background-image: repeating-linear-gradient(
    to bottom,
    white 0px, white 20px,
    {LINES} 20px, {LINES} 21px
  );
  border: 1px solid {RULE};
  border-radius: 6px;
  padding: .4rem .5rem;
}}
</style>
""", unsafe_allow_html=True)

# ---------- DB ----------
DB = Path("planner.db")
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS planner (date TEXT PRIMARY KEY, data TEXT)")
conn.commit()

def _normalize_entry(entry: dict) -> dict:
    """Make sure entry has the expected schema; migrate legacy keys in-memory."""
    if not entry: 
        return {"quote":"","notes":"","tasks":[],"tracker":{str(i):"" for i in range(1,9)},"sched":{}}
    # tasks
    tasks = entry.get("tasks", [])
    fixed_tasks = []
    if isinstance(tasks, list):
        for t in tasks:
            if not isinstance(t, dict):
                continue
            # migrate "task" -> "t"
            if "t" not in t and "task" in t:
                t["t"] = t["task"]
            # default fields
            t.setdefault("p", "A")
            t.setdefault("t", "")
            t.setdefault("done", False)
            fixed_tasks.append(t)
    entry["tasks"] = fixed_tasks
    # tracker
    tr = entry.get("tracker") or {}
    entry["tracker"] = {str(i): tr.get(str(i), "") for i in range(1,9)}
    # schedule key standardization
    if "manual_sched" in entry and "sched" not in entry:
        entry["sched"] = entry.pop("manual_sched")
    entry.setdefault("sched", {})
    entry.setdefault("quote","")
    entry.setdefault("notes","")
    return entry

def _normalize_db_in_place():
    """Scan DB and permanently migrate legacy task keys ("task" -> "t")."""
    try:
        c.execute("SELECT date, data FROM planner")
        rows = c.fetchall()
        changed = 0
        for d, raw in rows:
            try:
                entry = json.loads(raw)
            except Exception:
                continue
            new_entry = _normalize_entry(entry)
            # determine if changed by comparing serialized normalized vs original
            if json.dumps(new_entry, sort_keys=True) != json.dumps(entry, sort_keys=True):
                c.execute("UPDATE planner SET data=? WHERE date=?", (json.dumps(new_entry), d))
                changed += 1
        if changed:
            conn.commit()
            st.sidebar.success(f"Database normalized: {changed} record(s) updated ✅")
    except Exception as e:
        st.sidebar.warning(f"Normalization skipped: {e}")

# Run normalization once on startup
_normalize_db_in_place()

def load_day(d):
    c.execute("SELECT data FROM planner WHERE date=?", (str(d),))
    r = c.fetchone()
    if not r: 
        return {"quote":"","notes":"","tasks":[],"tracker":{str(i):"" for i in range(1,9)},"sched":{}}
    try:
        entry = json.loads(r[0])
    except Exception:
        entry = {"quote":"","notes":"","tasks":[],"tracker":{str(i):"" for i in range(1,9)},"sched":{}}
    return _normalize_entry(entry)

def save_day(d, data):
    c.execute("REPLACE INTO planner (date, data) VALUES (?,?)", (str(d), json.dumps(_normalize_entry(data))))
    conn.commit()

# ---------- Outlook ----------
def get_outlook_events(d):
    if not USE_OUTLOOK: 
        return []
    try:
        cid = st.secrets.get("client_id")
        sec = st.secrets.get("client_secret")
        ten = st.secrets.get("tenant_id", "organizations")
        if not cid or not sec: 
            return []
        creds = (cid, sec)
        backend = FileSystemTokenBackend(token_path='.', token_filename='o365_token.txt')
        account = Account(creds, token_backend=backend, tenant_id=ten)
        if not account.is_authenticated:
            if st.button("Connect Outlook"):
                account.authenticate(scopes=['offline_access', 'Calendars.Read'])
            if not account.is_authenticated:
                return []
        cal = account.schedule().get_default_calendar()
        start = dt.datetime.combine(d, dt.time(0,0))
        end   = dt.datetime.combine(d, dt.time(23,59))
        q = cal.new_query('start').greater_equal(start)
        q.chain('and').on_attribute('end').less_equal(end)
        items = []
        for e in cal.get_events(query=q, include_recurring=True):
            items.append((e.start.astimezone().strftime("%H:%M"), e.subject or ""))
        return items
    except Exception as e:
        st.warning(f"Outlook not available: {e}")
        return []

# ---------- Helpers ----------
def month_grid(y, m):
    f = dt.date(y, m, 1)
    sw = (f.weekday() + 1) % 7
    nxt = dt.date(y+1,1,1) if m == 12 else dt.date(y, m+1, 1)
    dim = (nxt - dt.timedelta(days=1)).day
    return sw, dim

def render_mini_calendar(target, today):
    sw, dim = month_grid(target.year, target.month)
    st.markdown(f'<div class="calbox"><div class="calcap">{target.strftime("%b %Y")}</div>', unsafe_allow_html=True)
    st.markdown('<div class="calgrid">' + "".join(f'<div class="calhdr">{d}</div>' for d in ["S","M","T","W","T","F","S"]) + "</div>", unsafe_allow_html=True)
    html = '<div class="calgrid">'
    html += "".join('<div></div>' for _ in range(sw))
    for day in range(1, dim+1):
        cls = "today" if (target.year,target.month,day)==(today.year,today.month,today.day) else ""
        html += f'<div class="{cls}">{day}</div>'
    html += '</div></div>'
    st.markdown(html, unsafe_allow_html=True)

def ruled_textarea(key, value, height=450, placeholder=""):
    st.markdown('<div class="lined">', unsafe_allow_html=True)
    out = st.text_area("", value=value, key=key, height=height, placeholder=placeholder, label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
    return out

def day_stamp(d):
    doy = d.timetuple().tm_yday
    total = 366 if (d.year%4==0 and (d.year%100!=0 or d.year%400==0)) else 365
    left  = total - doy
    week  = d.isocalendar().week
    return f"{doy}th Day • {left} Left • Week {week}"

# ---------- State ----------
today = dt.date.today()
date  = st.date_input("", today, format="YYYY-MM-DD")
stored = load_day(date)  # normalized in-memory

# ---------- Header ----------
hdr = st.columns([0.6,0.4])
hdr[0].markdown(f"### {date.strftime('%A, %B %d, %Y')}")
hdr[1].markdown(f"<div style='text-align:right;font-weight:700;'>{day_stamp(date)}</div>", unsafe_allow_html=True)

# ---------- Page Grid ----------
st.markdown('<div class="page-grid">', unsafe_allow_html=True)

# Left page + gutter + right page columns
left, gutter, right = st.columns([0.57,0.03,0.4], gap="small")

# ----- LEFT -----
with left:
    # Mini calendars row (float-left)
    st.markdown('<div class="calrow">', unsafe_allow_html=True)
    prev  = (date.replace(day=1)-dt.timedelta(days=1)).replace(day=1)
    next_ = (date.replace(day=28)+dt.timedelta(days=10)).replace(day=1)
    for d in [prev, date.replace(day=1), next_]:
        render_mini_calendar(d, date)
    st.markdown('</div>', unsafe_allow_html=True)

    # Tasks
    st.markdown('<div class="section"><div class="section-title">ABC Prioritized Daily Task List</div>', unsafe_allow_html=True)
    row = st.columns([0.15,0.7,0.15])
    pri = row[0].selectbox("P",["A","B","C"],label_visibility="collapsed")
    txt = row[1].text_input("Task","",label_visibility="collapsed",placeholder="Task description…")
    if row[2].button("Add",use_container_width=True) and txt.strip():
        stored["tasks"].append({"p":pri,"t":txt.strip(),"done":False})
        save_day(date,stored); st.rerun()

    for i, t in enumerate(stored["tasks"]):
        # Compatibility ensured by _normalize_entry, but guard anyway:
        task_text = t.get("t", t.get("task", ""))
        r = st.columns([0.08,0.08,0.72,0.12])
        done = r[0].checkbox("",value=t.get("done",False),key=f"td{i}")
        if done != t.get("done",False):
            t["done"] = done; save_day(date,stored)
        r[1].markdown(f"**{t.get('p','')}**")
        r[2].markdown(task_text)
        if r[3].button("✕",key=f"tx{i}"):
            stored["tasks"].pop(i); save_day(date,stored); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Tracker
    st.markdown('<div class="section"><div class="section-title">Daily Tracker</div>', unsafe_allow_html=True)
    for i in range(1,9):
        rr = st.columns([0.06,0.94])
        rr[0].markdown(f"**{i}**")
        stored["tracker"][str(i)] = rr[1].text_input(f"trk{i}",value=stored["tracker"].get(str(i),""),label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    # Schedule (full-hour)
    st.markdown('<div class="section"><div class="section-title">Appointment Schedule</div>', unsafe_allow_html=True)
    events = get_outlook_events(date) if USE_OUTLOOK else []
    evmap  = {e[0]: e[1] for e in events}  # "HH:MM" -> subject
    for h in range(6,23):
        hh = f"{h:02d}:00"
        st.markdown('<div class="schedule-row">', unsafe_allow_html=True)
        st.markdown(f'<div class="timecell">{hh}</div>', unsafe_allow_html=True)
        stored["sched"][hh] = st.text_input(
            "", value=evmap.get(hh, stored["sched"].get(hh,"")),
            key=f"s{hh}", label_visibility="collapsed", placeholder=""
        )
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ----- GUTTER DOTS -----
with gutter:
    st.markdown('<div class="gutter">'+"".join('<div class="hole"></div>' for _ in range(10))+'</div>', unsafe_allow_html=True)

# ----- RIGHT -----
with right:
    # Quote
    st.markdown('<div class="section"><div class="section-title">Quote / Affirmation</div>', unsafe_allow_html=True)
    stored["quote"] = st.text_input("",stored["quote"],label_visibility="collapsed",placeholder="Fear less, hope more…")
    st.markdown('</div>', unsafe_allow_html=True)

    # Notes (ruled)
    st.markdown('<div class="section"><div class="section-title">Daily Notes</div>', unsafe_allow_html=True)
    stored["notes"] = ruled_textarea("notes", stored["notes"], height=470, placeholder="Notes, calls, ideas…")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # end page-grid

# ---------- Save Bar ----------
cols = st.columns([0.2,0.6,0.2])
if cols[0].button("💾 Save",use_container_width=True):
    save_day(date,stored); st.success("Saved ✔")
if cols[2].button("🗑 Clear",use_container_width=True):
    stored={"quote":"","notes":"","tasks":[],"tracker":{str(i):"" for i in range(1,9)},"sched":{}}
    save_day(date,stored); st.rerun()

st.caption("Franklin Daily Planner • compact teal design • single-row mini calendars • Outlook-aware")
