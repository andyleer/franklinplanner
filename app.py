# app.py – Final Franklin Planner (compact, teal, responsive, Outlook-ready)

import streamlit as st
import datetime as dt
import json
import sqlite3
from pathlib import Path

# Optional Outlook integration
USE_OUTLOOK = True
try:
    from O365 import Account, FileSystemTokenBackend
except Exception:
    USE_OUTLOOK = False

# ------------------ CONFIG ------------------
st.set_page_config(page_title="Franklin Daily Planner", page_icon="📘", layout="wide")

INK = "#0b6b6c"
PAPER = "#f8fbfa"
RULE = "#9bc7c3"
LINES = "#d8ebe9"

# ------------------ STYLE ------------------
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
.block-container {{ padding-top: 0.5rem; max-width: 1150px; }}

h1,h2,h3,h4 {{ color: {INK}; margin: 0.2rem 0 0.3rem 0; }}

.section {{
  border: 1px solid {RULE};
  border-radius: 8px;
  background: white;
  padding: 0.3rem 0.45rem;
  margin-bottom: 0.3rem;
}}
.section-title {{
  font-variant-caps: small-caps;
  font-size: 0.85rem;
  font-weight: 700;
  border-bottom: 1px solid {RULE};
  margin-bottom: 0.2rem;
  padding-bottom: 0.15rem;
}}

.page-grid {{
  display: grid;
  grid-template-columns: 57% 43%;
  gap: 8px;
}}
@media (max-width: 950px) {{
  .page-grid {{ grid-template-columns: 1fr; }}
}}

.calwrap {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 5px;
  margin-bottom: 0.4rem;
}}
.calbox {{
  border: 1px solid {RULE};
  border-radius: 6px;
  padding: 0.2rem;
  background: white;
}}
.calcap {{ font-size: 0.7rem; font-weight: 700; text-align: center; margin-bottom: 2px; }}
.calgrid {{
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
}}
.calgrid div {{
  text-align: center;
  font-size: 0.6rem;
  padding: 1px 0;
}}
.calhdr {{ font-weight: 700; background: #eef6f5; }}
.today {{ outline: 1px solid {INK}; border-radius: 2px; }}

.schedule-row {{
  display: grid;
  grid-template-columns: 48px 1fr;
  align-items: center;
  border-bottom: 1px solid {LINES};
  margin: 0;
}}
.timecell {{
  font-weight: 700;
  font-size: 0.85rem;
  color: {INK};
}}
.stTextInput > div > div > input,
.stTextArea textarea {{
  font-size: 0.85rem;
  padding: 0.3rem 0.4rem;
}}
.lined {{
  background-image: repeating-linear-gradient(
    to bottom,
    white 0px, white 20px,
    {LINES} 20px, {LINES} 21px
  );
  border: 1px solid {RULE};
  border-radius: 6px;
  padding: 0.4rem 0.5rem;
}}
.gutter {{
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  opacity: 0.45;
  margin-top: 12px;
}}
.hole {{
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: {RULE};
}}
@media (max-width: 950px) {{
  .gutter {{ display: none; }}
}}
</style>
""", unsafe_allow_html=True)

# ------------------ DB ------------------
DB = Path("planner.db")
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS planner (date TEXT PRIMARY KEY, data TEXT)")
conn.commit()

def load_day(d):
    c.execute("SELECT data FROM planner WHERE date=?", (str(d),))
    r = c.fetchone()
    if r: 
        try: return json.loads(r[0])
        except: return None
    return None

def save_day(d, data):
    c.execute("REPLACE INTO planner (date, data) VALUES (?,?)", (str(d), json.dumps(data)))
    conn.commit()

# --- One-time database cleanup for legacy task field names ---
try:
    c.execute("SELECT date, data FROM planner")
    rows = c.fetchall()
    updated = 0
    for d, raw in rows:
        try:
            entry = json.loads(raw)
            changed = False
            if "tasks" in entry:
                for t in entry["tasks"]:
                    if "task" in t and "t" not in t:
                        t["t"] = t["task"]
                        changed = True
                if changed:
                    c.execute("UPDATE planner SET data=? WHERE date=?", (json.dumps(entry), d))
                    updated += 1
        except Exception:
            pass
    if updated:
        conn.commit()
        st.sidebar.success(f"Database cleaned: {updated} record(s) fixed ✅")
except Exception as e:
    st.sidebar.warning(f"Cleanup skipped: {e}")




# ------------------ OUTLOOK ------------------
def get_outlook_events(d):
    if not USE_OUTLOOK: return []
    try:
        cid = st.secrets.get("client_id")
        sec = st.secrets.get("client_secret")
        ten = st.secrets.get("tenant_id", "organizations")
        if not cid or not sec: return []
        creds = (cid, sec)
        backend = FileSystemTokenBackend(token_path='.', token_filename='o365_token.txt')
        account = Account(creds, token_backend=backend, tenant_id=ten)
        if not account.is_authenticated:
            if st.button("Connect Outlook"):
                account.authenticate(scopes=['offline_access', 'Calendars.Read'])
            if not account.is_authenticated: return []
        cal = account.schedule().get_default_calendar()
        start = dt.datetime.combine(d, dt.time(0,0))
        end = dt.datetime.combine(d, dt.time(23,59))
        q = cal.new_query('start').greater_equal(start)
        q.chain('and').on_attribute('end').less_equal(end)
        items = []
        for e in cal.get_events(query=q, include_recurring=True):
            items.append((e.start.astimezone().strftime("%H:%M"), e.subject or ""))
        return items
    except Exception as e:
        st.warning(f"Outlook not available: {e}")
        return []

# ------------------ HELPERS ------------------
def month_grid(y, m):
    f = dt.date(y, m, 1)
    sw = (f.weekday() + 1) % 7
    if m == 12: nxt = dt.date(y+1,1,1)
    else: nxt = dt.date(y, m+1, 1)
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
    left = total - doy
    week = d.isocalendar().week
    return f"{doy}th Day • {left} Left • Week {week}"

# ------------------ DATA ------------------
today = dt.date.today()
date = st.date_input("", today, format="YYYY-MM-DD")
stored = load_day(date) or {"quote":"","notes":"","tasks":[],"tracker":{str(i):"" for i in range(1,9)},"sched":{}}

# ------------------ HEADER ------------------
hdr = st.columns([0.6,0.4])
hdr[0].markdown(f"### {date.strftime('%A, %B %d, %Y')}")
hdr[1].markdown(f"<div style='text-align:right;font-weight:700;'>{day_stamp(date)}</div>", unsafe_allow_html=True)

# ------------------ PAGE GRID ------------------
st.markdown('<div class="page-grid">', unsafe_allow_html=True)

# ---------- LEFT PAGE ----------
with st.container():
    left, gutter, right = st.columns([0.57,0.03,0.4], gap="small")

    with left:
        # Mini calendars row
        st.markdown('<div class="calwrap">', unsafe_allow_html=True)
        prev = (date.replace(day=1)-dt.timedelta(days=1)).replace(day=1)
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
            save_day(date,stored)
            st.rerun()
        for i,t in enumerate(stored["tasks"]):
            r = st.columns([0.08,0.08,0.72,0.12])
            done = r[0].checkbox("",value=t["done"],key=f"td{i}")
            if done!=t["done"]:
                t["done"]=done; save_day(date,stored)
            r[1].markdown(f"**{t['p']}**")
            r[2].markdown(t["t"])
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

        # Schedule
        st.markdown('<div class="section"><div class="section-title">Appointment Schedule</div>', unsafe_allow_html=True)
        events = get_outlook_events(date) if USE_OUTLOOK else []
        evmap = {e[0]:e[1] for e in events}
        for h in range(6,23):
            hh=f"{h:02d}:00"
            st.markdown('<div class="schedule-row">',unsafe_allow_html=True)
            st.markdown(f'<div class="timecell">{hh}</div>',unsafe_allow_html=True)
            stored["sched"][hh]=st.text_input("",value=evmap.get(hh,stored["sched"].get(hh,"")),key=f"s{hh}",label_visibility="collapsed",placeholder="")
            st.markdown('</div>',unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Binder dots
    with gutter:
        st.markdown('<div class="gutter">'+"".join('<div class="hole"></div>' for _ in range(10))+'</div>',unsafe_allow_html=True)

    # ---------- RIGHT PAGE ----------
    with right:
        # Quote and Notes
        st.markdown('<div class="section"><div class="section-title">Quote / Affirmation</div>', unsafe_allow_html=True)
        stored["quote"] = st.text_input("",stored["quote"],label_visibility="collapsed",placeholder="Fear less, hope more…")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="section"><div class="section-title">Daily Notes</div>', unsafe_allow_html=True)
        stored["notes"]=ruled_textarea("notes",stored["notes"],height=470,placeholder="Notes, calls, ideas…")
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ------------------ SAVE BAR ------------------
cols = st.columns([0.2,0.6,0.2])
if cols[0].button("💾 Save",use_container_width=True):
    save_day(date,stored)
    st.success("Saved ✔")
if cols[2].button("🗑 Clear",use_container_width=True):
    stored={"quote":"","notes":"","tasks":[],"tracker":{str(i):"" for i in range(1,9)},"sched":{}}
    save_day(date,stored)
    st.rerun()

st.caption("Franklin Daily Planner • compact teal design • responsive • Outlook-aware")
