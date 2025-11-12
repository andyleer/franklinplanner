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

# ---------------- Page Setup ----------------
st.set_page_config(page_title="Franklin Two-Page Daily", page_icon="📘", layout="wide")

# ---------------- Theme / CSS ----------------
FRANKLIN_TEAL = "#0b6b6c"      # ink
PAPER = "#f6faf8"              # paper
LINES = "#cfe5e2"              # ruled lines
RULE = "#8ec1bc"               # section headings / thin rules
ACCENT_BG = "#e9f4f2"          # light boxes

st.markdown(f"""
<style>
:root {{
  --ink: {FRANKLIN_TEAL};
  --paper: {PAPER};
  --lines: {LINES};
  --rule: {RULE};
  --accent: {ACCENT_BG};
}}
/* Paper background + tighter layout */
html, body, .block-container {{
  background: var(--paper);
  color: var(--ink);
}}
.block-container {{
  padding-top: .75rem;
  padding-bottom: .25rem;
  max-width: 1400px;
}}
/* Franklin typography feel */
h1, h2, h3, h4, h5 {{
  color: var(--ink) !important;
  font-family: "Georgia", "Times New Roman", serif;
  letter-spacing: .2px;
}}
/* Compact inputs */
.stTextInput > div > div > input,
.stTextArea textarea {{
  font-size: 0.95rem;
  color: var(--ink) !important;
  background: white !important;
}}
/* Lined sections via repeating gradient */
.lined {{
  background-image: repeating-linear-gradient(
    to bottom,
    white 0px, white 24px,
    var(--lines) 24px, var(--lines) 25px
  );
  border: 1px solid var(--rule);
  border-radius: 8px;
  padding: .5rem .75rem;
}}
/* Headed boxes to mimic section labels */
.section {{
  border: 1px solid var(--rule);
  border-radius: 10px;
  padding: .4rem .6rem .6rem .6rem;
  background: white;
}}
.section-title {{
  font-variant-caps: small-caps;
  font-weight: 700;
  font-size: .95rem;
  color: var(--ink);
  margin-bottom: .25rem;
  border-bottom: 1px solid var(--rule);
  padding-bottom: .15rem;
}}
/* Tiny calendar grid */
.calgrid {{
  display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px;
  font-size: .75rem;
}}
.calgrid div {{
  text-align:center; padding: 2px 0; color: var(--ink);
}}
.calhdr {{ font-weight:700; background: var(--accent); }}
.today {{ outline: 2px solid var(--ink); border-radius: 3px; }}
/* Super compact checkboxes and buttons */
.stCheckbox label {{ font-size: .95rem; color: var(--ink); }}
button[kind="secondary"] {{ color: var(--ink); }}
/* Shrink default Streamlit spacing inside columns */
.css-1dp5vir, .css-1r6slb0, .css-12w0qpk {{
  margin-top: .35rem; margin-bottom: .15rem;
}}
/* Schedule row lines (narrow, ruled) */
.schedule-row {{
  display: grid; grid-template-columns: 54px 1fr; align-items:center;
  gap: .5rem; padding: 2px 0; border-bottom: 1px solid var(--lines);
}}
.timecell {{
  font-weight:700; font-size:.9rem; color: var(--ink);
}}
/* Tabs-like month rail (visual only) */
.monthrail {{
  display:flex; gap: 6px; flex-wrap: wrap; margin-bottom: .35rem;
}}
.monthpill {{
  border:1px solid var(--rule); border-radius: 999px; padding: 2px 8px;
  font-size: .70rem; color: var(--ink); background: var(--accent);
}}
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

        # Button-driven auth (first time)
        if not account.is_authenticated:
            st.button("Connect Outlook", key="connect", help="Authorize Microsoft 365 to read your calendar")
            st.info("Click **Connect Outlook** above, then come back after you grant access.")
            account.authenticate(scopes=['offline_access', 'Calendars.Read'])
            # Continue even on first open; if not authed yet, empty list
            if not account.is_authenticated:
                return []

        schedule = account.schedule()
        calendar = schedule.get_default_calendar()

        start = dt.datetime.combine(selected_date, dt.time(0, 0))
        end = dt.datetime.combine(selected_date, dt.time(23, 59, 59))
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
def mini_month(d: dt.date):
    """Return a 7xN grid for the month containing d."""
    first = d.replace(day=1)
    start_weekday = (first.weekday() + 1) % 7  # Monday=0 -> Sunday=0
    days_in_month = (first.replace(month=first.month % 12 + 1, day=1) - dt.timedelta(days=1)).day
    cells = ["Su","Mo","Tu","We","Th","Fr","Sa"] + list(range(1, days_in_month+1))
    # pad with blanks before first day
    blanks = [""] * start_weekday
    return cells[:7], blanks + list(range(1, days_in_month+1))

def ruled_textarea(key, value, height=250, placeholder=""):
    st.markdown(f'<div class="lined">', unsafe_allow_html=True)
    out = st.text_area(label="", key=key, value=value, height=height, placeholder=placeholder, label_visibility="collapsed")
    st.markdown(f'</div>', unsafe_allow_html=True)
    return out

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

# ---------------- Header Row ----------------
left, right = st.columns([1.35, 1.0], gap="small")

with left:
    # Month tabs visual
    st.markdown('<div class="monthrail">' + "".join([f'<span class="monthpill">{m}</span>' for m in
        ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]]) + "</div>", unsafe_allow_html=True)

    st.markdown(f"### {date.strftime('%A')} &nbsp;&nbsp; {date.strftime('%B %d, %Y')}")

    # ---------- Mini Calendars (prev/current/next) ----------
    mc_box = st.container(border=True)
    with mc_box:
        c1,c2,c3 = st.columns(3)
        for idx, target in enumerate([ (date - dt.timedelta(days=28)).replace(day=1),
                                       date.replace(day=1),
                                       (date + dt.timedelta(days=35)).replace(day=1) ]):
            hdr, days = mini_month(target)
            col = [c1,c2,c3][idx]
            with col:
                st.markdown(f"**{target.strftime('%B %Y')}**")
                st.markdown('<div class="calgrid">' + "".join([f'<div class="calhdr">{h}</div>' for h in hdr]) + "</div>", unsafe_allow_html=True)
                # render days
                html = '<div class="calgrid">'
                weekday = (target.weekday() + 1) % 7
                html += "".join('<div></div>' for _ in range(weekday))
                for dnum in range(1, (target.replace(month=target.month%12+1, day=1)-dt.timedelta(days=1)).day+1):
                    cls = "today" if (target.year, target.month, dnum) == (date.year, date.month, date.day) else ""
                    html += f'<div class="{cls}">{dnum}</div>'
                html += '</div>'
                st.markdown(html, unsafe_allow_html=True)

    st.markdown("")

    # ---------- Prioritized Task List ----------
    st.markdown('<div class="section"><div class="section-title">ABC Prioritized Daily Task List</div>', unsafe_allow_html=True)

    # Input row
    tcols = st.columns([0.14, 0.72, 0.14])
    pri = tcols[0].selectbox("Pri", ["A","B","C"], index=0, label_visibility="collapsed")
    txt = tcols[1].text_input("Add task", label_visibility="collapsed", placeholder="Task description…")
    add = tcols[2].button("Add", use_container_width=True)
    if add and txt.strip():
        stored["tasks"].append({"p": pri, "text": txt.strip(), "done": False})
        save_day(date, stored)
        st.rerun()

    # Table-ish list
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

    # ---------- Daily Tracker ----------
    st.markdown('<div class="section" style="margin-top:.5rem;"><div class="section-title">Daily Tracker</div>', unsafe_allow_html=True)
    for i in range(1,9):
        cc = st.columns([0.06, 0.94], gap="small")
        cc[0].markdown(f"**{i}**")
        stored["tracker"][str(i)] = cc[1].text_input(f"trk{i}", value=stored["tracker"].get(str(i), ""), label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    # ---------- Appointment Schedule ----------
    st.markdown('<div class="section" style="margin-top:.5rem;"><div class="section-title">Appointment Schedule</div>', unsafe_allow_html=True)

    # Pull Outlook events
    events = get_outlook_events(date) if USE_OUTLOOK else []
    event_map = {}
    for s,e,subj,loc in events:
        key = s
        desc = subj + (f" — {loc}" if loc else "")
        # if already has something, append
        event_map[key] = (event_map.get(key, "") + (" | " if key in event_map else "") + desc)

    hours = list(range(6, 23))  # 06 to 22
    for h in hours:
        hh = f"{h:02d}:00"
        display_text = event_map.get(hh, stored["manual_sched"].get(hh, ""))
        with st.container():
            st.markdown('<div class="schedule-row">', unsafe_allow_html=True)
            st.markdown(f'<div class="timecell">{hh}</div>', unsafe_allow_html=True)
            val = st.text_input(label=hh, value=display_text, key=f"s_{hh}", label_visibility="collapsed", placeholder="Add appointment / note…")
            st.markdown('</div>', unsafe_allow_html=True)
            stored["manual_sched"][hh] = val

    st.markdown('</div>', unsafe_allow_html=True)

with right:
    # ---------- Quote ----------
    st.markdown('<div class="section"><div class="section-title">Quote / Affirmation</div>', unsafe_allow_html=True)
    stored["quote"] = st.text_input("quote", value=stored["quote"], label_visibility="collapsed", placeholder="Fear less, hope more…")
    st.markdown('</div>', unsafe_allow_html=True)

    # ---------- Notes (ruled) ----------
    st.markdown('<div class="section" style="margin-top:.5rem;"><div class="section-title">Daily Notes</div>', unsafe_allow_html=True)
    stored["notes"] = ruled_textarea("notes", stored["notes"], height=560, placeholder="Notes, calls, ideas…")
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- Save Bar ----------------
sb1, sb2, sb3 = st.columns([0.15, 0.7, 0.15])
if sb1.button("💾 Save", use_container_width=True):
    save_day(date, stored)
    st.success("Saved ✔")

if sb3.button("🗑 Clear Day", use_container_width=True):
    stored = {"quote":"","notes":"","tasks":[],"tracker":{str(i):"" for i in range(1,9)},"manual_sched":{}}
    save_day(date, stored)
    st.rerun()

st.caption("Franklin-style Daily • compact teal layout • Outlook-aware")
