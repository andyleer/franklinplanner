# app.py — Franklin Two-Page Daily (compact, mobile-friendly, Outlook-aware)

import streamlit as st
import datetime as dt
import json
import sqlite3
from pathlib import Path

# ---- Optional Outlook integration (Microsoft Graph via O365) ----
USE_OUTLOOK = True
try:
    from O365 import Account, FileSystemTokenBackend
except Exception:
    USE_OUTLOOK = False

# ---------------- Page Setup ----------------
st.set_page_config(page_title="Franklin Two-Page Daily", page_icon="📘", layout="wide")

# ---------------- Theme / CSS ----------------
FRANKLIN_TEAL = "#0b6b6c"      # ink
PAPER = "#f7fbfa"              # paper
LINES = "#d7ece9"              # ruled lines
RULE = "#99cfc9"               # section headings / thin rules
ACCENT_BG = "#eef7f6"          # light boxes

# Always light: override dark tokens with light colors
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&display=swap');

:root {{
  --ink: {FRANKLIN_TEAL};
  --paper: {PAPER};
  --lines: {LINES};
  --rule: {RULE};
  --accent: {ACCENT_BG};
}}

/* Base + light mode lock */
html, body, .block-container {{
  background: var(--paper) !important;
  color: var(--ink) !important;
}}
* {{ color-scheme: only light; }}

.block-container {{
  padding-top: .5rem;
  padding-bottom: .25rem;
  max-width: 1200px;
  font-family: "Libre Baskerville", Georgia, serif;
}}
h1,h2,h3,h4,h5,h6 {{
  color: var(--ink) !important;
  margin: .25rem 0 .35rem;
  letter-spacing:.2px;
}}

/* Two-page grid that collapses on narrow screens */
.page-grid {{
  display: grid;
  grid-template-columns: 58% 42%;
  grid-column-gap: 14px;
}}
@media (max-width: 980px) {{
  .page-grid {{ grid-template-columns: 1fr; }}
}}

/* Section cards */
.section {{
  border: 1px solid var(--rule);
  border-radius: 10px;
  background: white;
  padding: .36rem .5rem .5rem;
  margin-bottom: .5rem;
}}
.section-title {{
  font-variant-caps: small-caps;
  font-weight: 700;
  font-size: .92rem;
  color: var(--ink);
  margin-bottom: .25rem;
  border-bottom: 1px solid var(--rule);
  padding-bottom: .15rem;
}}

/* Very compact inputs */
.stTextInput > div > div > input,
.stTextArea textarea {{
  font-size: .92rem;
  color: var(--ink) !important;
  background: white !important;
  padding: .35rem .45rem;
}}
.stCheckbox label {{ font-size: .92rem; }}

/* Lined paper effect */
.lined {{
  background-image: repeating-linear-gradient(
    to bottom,
    white 0px, white 21px,
    var(--lines) 21px, var(--lines) 22px
  );
  border: 1px solid var(--rule);
  border-radius: 8px;
  padding: .5rem .6rem;
}}

/* Month tabs (visual) */
.monthrail {{ display:flex; gap:6px; flex-wrap:wrap; margin: .25rem 0 .1rem; }}
.monthpill {{
  border:1px solid var(--rule); border-radius: 999px; padding: 1px 8px;
  font-size: .68rem; background: var(--accent); color: var(--ink);
}}

/* Mini calendars: extra small */
.calwrap {{ display:grid; grid-template-columns: repeat(3, 1fr); gap:8px; }}
@media (max-width: 980px) {{
  .calwrap {{ grid-template-columns: repeat(3, 1fr); }}
}}
.calbox {{ border:1px solid var(--rule); border-radius:8px; background:white; padding:.25rem .3rem; }}
.calcap {{ font-weight:700; font-size:.75rem; margin-bottom:2px; }}
.calgrid {{ display:grid; grid-template-columns: repeat(7, 1fr); gap:1px; }}
.calgrid div {{ text-align:center; padding:1px 0; font-size:.64rem; color:var(--ink); }}
.calhdr {{ font-weight:700; background: var(--accent); }}
.today {{ outline: 1.5px solid var(--ink); border-radius: 3px; }}

/* Schedule compact rows */
.schedule-row {{
  display:grid; grid-template-columns: 50px 1fr; align-items:center;
  gap:.4rem; padding: 1px 0; border-bottom: 1px solid var(--lines);
}}
.timecell {{ font-weight:700; font-size:.9rem; }}

/* Gutter binder-hole dots (decorative) */
.gutter {{
  display:flex; flex-direction:column; align-items:center;
  gap:16px; margin: 6px 0; opacity:.5;
}}
.hole {{
  width:8px; height:8px; border-radius:50%;
  background: var(--rule);
}}
@media (max-width: 980px) {{
  .gutter {{ display:none; }}
}}

/* Tighten Streamlit internal spacing a bit */
div[data-testid="stHorizontalBlock"] > div {{ margin-bottom: .35rem; }}
</style>
""", unsafe_allow_html=True)

# ---------------- Data Store ----------------
DB_PATH = Path("planner.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS planner (
  date TEXT PRIMARY KEY,
  data TEXT
)
""")
conn.commit()

def load_day(d: dt.date):
    c.execute("SELECT data FROM planner WHERE date=?", (str(d),))
    row = c.fetchone()
    if row:
        try:
            return json.loads(row[0])
        except Exception:
            return None
    return None

def save_day(d: dt.date, data: dict):
    c.execute("REPLACE INTO planner (date, data) VALUES (?,?)", (str(d), json.dumps(data)))
    conn.commit()

# ---------------- Outlook Integration ----------------
def get_outlook_events(selected_date: dt.date):
    """Return [(start_time, end_time, subject, location)] for selected day, or []"""
    if not USE_OUTLOOK:
        return []
    try:
        client_id = st.secrets.get("client_id")
        client_secret = st.secrets.get("client_secret")
        tenant_id = st.secrets.get("tenant_id", "organizations")
        if not client_id or not client_secret:
            return []

        credentials = (client_id, client_secret)
        token_backend = FileSystemTokenBackend(token_path='.', token_filename='o365_token.txt')
        account = Account(credentials, token_backend=token_backend, tenant_id=tenant_id)

        if not account.is_authenticated:
            # First-time auth
            if st.button("Connect Outlook", key="connect_outlook", help="Authorize Microsoft 365 to read your calendar"):
                account.authenticate(scopes=['offline_access', 'Calendars.Read'])
            # If not authorized yet, return empty
            if not account.is_authenticated:
                return []

        schedule = account.schedule()
        calendar = schedule.get_default_calendar()

        start = dt.datetime.combine(selected_date, dt.time(0,0))
        end = dt.datetime.combine(selected_date, dt.time(23,59,59))
        q = calendar.new_query('start').greater_equal(start)
        q.chain('and').on_attribute('end').less_equal(end)
        items = []
        for ev in calendar.get_events(query=q, include_recurring=True):
            items.append((ev.start.astimezone().strftime("%H:%M"),
                          ev.end.astimezone().strftime("%H:%M"),
                          ev.subject or "(No title)",
                          getattr(ev, "location", None) and ev.location.get("displayName", "")))
        return items
    except Exception as e:
        st.warning(f"Outlook calendar not available: {e}")
        return []

# ---------------- Utilities ----------------
def month_grid(year: int, month: int):
    first = dt.date(year, month, 1)
    start_weekday = (first.weekday() + 1) % 7  # Sunday=0
    # days in month
    if month == 12:
        next_first = dt.date(year+1, 1, 1)
    else:
        next_first = dt.date(year, month+1, 1)
    dim = (next_first - dt.timedelta(days=1)).day
    return start_weekday, dim

def render_mini_calendar(target: dt.date, today: dt.date):
    sw, dim = month_grid(target.year, target.month)
    st.markdown(f'<div class="calbox"><div class="calcap">{target.strftime("%B %Y")}</div>', unsafe_allow_html=True)
    st.markdown('<div class="calgrid">' + "".join([f'<div class="calhdr">{h}</div>' for h in ["Su","Mo","Tu","We","Th","Fr","Sa"]]) + "</div>", unsafe_allow_html=True)
    html = '<div class="calgrid">'
    html += "".join('<div></div>' for _ in range(sw))
    for dnum in range(1, dim+1):
        cls = "today" if (target.year, target.month, dnum) == (today.year, today.month, today.day) else ""
        html += f'<div class="{cls}">{dnum}</div>'
    html += '</div></div>'
    st.markdown(html, unsafe_allow_html=True)

def ruled_textarea(key, value, height=420, placeholder=""):
    st.markdown(f'<div class="lined">', unsafe_allow_html=True)
    out = st.text_area(label="", key=key, value=value, height=height, placeholder=placeholder, label_visibility="collapsed")
    st.markdown(f'</div>', unsafe_allow_html=True)
    return out

def year_day_stamp(d: dt.date):
    day_of_year = d.timetuple().tm_yday
    is_leap = (d.year % 4 == 0 and (d.year % 100 != 0 or d.year % 400 == 0))
    total_days = 366 if is_leap else 365
    left = total_days - day_of_year
    week = d.isocalendar().week
    return f"{day_of_year}th Day • {left} Left • Week {week}"

# ---------------- State ----------------
today = dt.date.today()
date = st.date_input("Date", today, format="YYYY-MM-DD")

stored = load_day(date) or {
    "quote": "",
    "notes": "",
    "tasks": [],    # list of dicts: {"p":"A/B/C","text":"...", "done":False}
    "tracker": {str(i): "" for i in range(1,9)},
    "manual_sched": {}  # "HH:MM" -> "desc"
}

# ---------------- Header ----------------
st.markdown('<div class="monthrail">' + "".join([f'<span class="monthpill">{m}</span>' for m in
        ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]]) + "</div>", unsafe_allow_html=True)
st.markdown(f"### {date.strftime('%A')} &nbsp;&nbsp; {date.strftime('%B %d, %Y')}")

# ---------------- Two-Page Layout ----------------
st.markdown('<div class="page-grid">', unsafe_allow_html=True)

# ---------- LEFT PAGE ----------
left_col, right_col = st.columns([0.58, 0.42], gap="small")

with left_col:
    # Tiny three mini-calendars row
    cwrap = st.container()
    with cwrap:
        st.markdown('<div class="calwrap">', unsafe_allow_html=True)
        prev_month = (date.replace(day=1) - dt.timedelta(days=1)).replace(day=1)
        next_month = (date.replace(day=28) + dt.timedelta(days=10)).replace(day=1)
        for target in [prev_month, date.replace(day=1), next_month]:
            render_mini_calendar(target, date)
        st.markdown('</div>', unsafe_allow_html=True)

    # ABC Prioritized Task List
    st.markdown('<div class="section"><div class="section-title">ABC Prioritized Daily Task List</div>', unsafe_allow_html=True)

    tcols = st.columns([0.14, 0.72, 0.14])
    pri = tcols[0].selectbox("Pri", ["A","B","C"], index=0, label_visibility="collapsed")
    txt = tcols[1].text_input("Task", label_visibility="collapsed", placeholder="Task description…")
    add = tcols[2].button("Add", use_container_width=True)
    if add and txt.strip():
        stored["tasks"].append({"p": pri, "text": txt.strip(), "done": False})
        save_day(date, stored)
        st.rerun()

    if stored["tasks"]:
        for i, item in enumerate(stored["tasks"]):
            r = st.columns([0.08, 0.08, 0.70, 0.14], gap="small")
            done = r[0].checkbox("", value=item["done"], key=f"td{i}")
            if done != item["done"]:
                item["done"] = done
                save_day(date, stored)
            r[1].markdown(f"**{item['p']}**")
            r[2].markdown(item["text"])
            if r[3].button("✕", key=f"tx{i}"):
                stored["tasks"].pop(i)
                save_day(date, stored)
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Daily Tracker
    st.markdown('<div class="section"><div class="section-title">Daily Tracker</div>', unsafe_allow_html=True)
    for i in range(1,9):
        cc = st.columns([0.06, 0.94], gap="small")
        cc[0].markdown(f"**{i}**")
        stored["tracker"][str(i)] = cc[1].text_input(f"trk{i}", value=stored["tracker"].get(str(i), ""), label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    # Appointment Schedule (full-hour increments)
    st.markdown('<div class="section"><div class="section-title">Appointment Schedule</div>', unsafe_allow_html=True)
    events = get_outlook_events(date) if USE_OUTLOOK else []
    event_map = {}
    for s,e,subj,loc in events:
        key = s
        desc = subj + (f" — {loc}" if loc else "")
        event_map[key] = (event_map.get(key, "") + (" | " if key in event_map else "") + desc)

    hours = list(range(6, 23))
    for h in hours:
        hh = f"{h:02d}:00"
        display_text = event_map.get(hh, stored["manual_sched"].get(hh, ""))
        st.markdown('<div class="schedule-row">', unsafe_allow_html=True)
        st.markdown(f'<div class="timecell">{hh}</div>', unsafe_allow_html=True)
        val = st.text_input(label=hh, value=display_text, key=f"s_{hh}", label_visibility="collapsed", placeholder="Add appointment / note…")
        st.markdown('</div>', unsafe_allow_html=True)
        stored["manual_sched"][hh] = val

# ---------- GUTTER DOTS ----------
with right_col:
    # vertical dots left edge (only on wide screens; CSS hides on mobile)
    st.markdown('<div class="gutter">' + "".join('<div class="hole"></div>' for _ in range(10)) + '</div>', unsafe_allow_html=True)

# ---------- RIGHT PAGE ----------
with right_col:
    # Quote / stamp header row
    top = st.container()
    with top:
        cols = st.columns([0.65, 0.35])
        with cols[0]:
            st.markdown('<div class="section"><div class="section-title">Quote / Affirmation</div>', unsafe_allow_html=True)
            stored["quote"] = st.text_input("quote", value=stored["quote"], label_visibility="collapsed", placeholder="Fear less, hope more…")
            st.markdown('</div>', unsafe_allow_html=True)
        with cols[1]:
            st.markdown('<div class="section">', unsafe_allow_html=True)
            st.markdown(f"**{year_day_stamp(date)}**")
            st.markdown('</div>', unsafe_allow_html=True)

    # Notes (ruled)
    st.markdown('<div class="section"><div class="section-title">Daily Notes</div>', unsafe_allow_html=True)
    stored["notes"] = ruled_textarea("notes", stored["notes"], height=520, placeholder="Notes, calls, ideas…")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)  # end page-grid

# ---------------- Save Bar ----------------
sb1, sb2, sb3 = st.columns([0.2, 0.6, 0.2])
if sb1.button("💾 Save", use_container_width=True):
    save_day(date, stored)
    st.success("Saved ✔")

if sb3.button("🗑 Clear Day", use_container_width=True):
    stored = {"quote":"","notes":"","tasks":[],"tracker":{str(i):"" for i in range(1,9)},"manual_sched":{}}
    save_day(date, stored)
    st.rerun()

st.caption("Franklin-style Daily • compact teal layout • mobile-friendly • Outlook-aware")
