# franklin_left_page_refined.py
# Date: 2025-11-12
# Refined Franklin Planner left-page layout with compact tasks, visible ABC dropdown, multiline tracker, centered page.

import streamlit as st

st.set_page_config(page_title="Franklin Planner Left Page", layout="wide")

# ----------  CSS ----------
st.markdown("""
<style>
body {
    background-color: #f7f9f8;
    font-family: 'Georgia', serif;
    color: #004d4d;
}
.main {
    display: flex;
    justify-content: center;
    align-items: flex-start;
    min-height: 95vh;
}
.page {
    background-color: #e9f1f0;
    border: 1px solid #c9d7d6;
    padding: 1.2rem 2rem;
    width: 85%;
    max-width: 1200px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
    border-radius: 8px;
}
h3, h4 {
    color: #004d4d;
    margin-bottom: 0.25rem;
}
.mini-calendar {
    font-size: 0.7rem;
    line-height: 1.05;
    text-align: center;
}
.abc-header {
    border-bottom: 1.5px solid #004d4d;
    margin-top: 0.4rem;
    margin-bottom: 0.2rem;
    padding-bottom: 0.1rem;
    font-weight: bold;
    font-size: 0.9rem;
}
hr.line {
    border: 0.5px solid #c9d7d6;
    margin: 0.1rem 0;
}
.appt-time {
    width: 30px;
    display: inline-block;
    font-weight: bold;
    font-size: 0.8rem;
}
.appt-line {
    border-bottom: 1px solid #c9d7d6;
    height: 1.1em;
    width: 90%;
    margin-bottom: 0.15rem;
    display: inline-block;
}
.daily-tracker {
    margin-top: 0.8rem;
    border-top: 1.5px solid #004d4d;
    padding-top: 0.4rem;
    font-size: 0.85rem;
}
.tracker-box {
    background: repeating-linear-gradient(
        white, white 22px,
        #c9d7d6 23px, #c9d7d6 24px
    );
    border: 1px solid #c9d7d6;
    width: 100%;
    min-height: 180px;
    font-family: 'Georgia', serif;
    font-size: 0.85rem;
    color: #004d4d;
    padding: 4px 6px;
}
input[type=text], select, textarea {
    font-size: 0.8rem !important;
    padding: 2px 4px !important;
}
div[data-baseweb="select"] > div {
    font-size: 0.8rem !important;
    min-height: 1.3em !important;
    padding: 0 0.25rem !important;
    overflow: visible !important;
}
label, .stCheckbox label, .stSelectbox label {
    font-size: 0.8rem !important;
}
.stTextInput, .stSelectbox {
    margin-bottom: 0rem !important;
}
</style>
""", unsafe_allow_html=True)

# ----------  PAGE ----------
st.markdown("<div class='main'><div class='page'>", unsafe_allow_html=True)

colA, colB = st.columns([1.2, 1.1])

# ---------- LEFT COLUMN ----------
with colA:
    st.markdown("### 15  \n**Tuesday**  \nApril 2025")

    # Mini calendars
    st.markdown("""
    <div style="display:flex; justify-content:space-between; margin-top:-0.4rem;">
        <div class='mini-calendar'>
        <b>March 2025</b><br>
        S M T W T F S<br>
        2 3 4 5 6 7 8<br>
        9 10 11 12 13 14 15<br>
        16 17 18 19 20 21 22<br>
        23 24 25 26 27 28 29<br>
        30 31
        </div>
        <div class='mini-calendar'>
        <b>May 2025</b><br>
        S M T W T F S<br>
        4 5 6 7 8 9 10<br>
        11 12 13 14 15 16 17<br>
        18 19 20 21 22 23 24<br>
        25 26 27 28 29 30 31
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Task list
    st.markdown("<div class='abc-header'>ABC Prioritized Daily Task List</div>", unsafe_allow_html=True)

    if "tasks" not in st.session_state:
        st.session_state.tasks = [{"done": False, "priority": "A", "desc": ""} for _ in range(6)]

    for i, task in enumerate(st.session_state.tasks):
        cols = st.columns([0.35, 0.6, 6])
        with cols[0]:
            st.session_state.tasks[i]["done"] = st.checkbox("", value=task["done"], key=f"done_{i}")
        with cols[1]:
            st.session_state.tasks[i]["priority"] = st.selectbox(
                "", ["A", "B", "C"], key=f"priority_{i}", label_visibility="collapsed",
                index=["A","B","C"].index(task["priority"])
            )
        with cols[2]:
            st.session_state.tasks[i]["desc"] = st.text_input(
                "", value=task["desc"], key=f"desc_{i}", label_visibility="collapsed"
            )
        st.markdown("<hr class='line'>", unsafe_allow_html=True)

    if st.button("+ Add Task"):
        st.session_state.tasks.append({"done": False, "priority": "C", "desc": ""})

    # Daily Tracker
    st.markdown("<div class='daily-tracker'><b>Daily Tracker</b><br><small>Track expenses, email, voice mail, or other information.</small></div>", unsafe_allow_html=True)
    st.text_area("Daily Tracker Box", "", height=180, key="tracker_notes", label_visibility="collapsed")

# ---------- RIGHT COLUMN ----------
with colB:
    st.markdown("#### Appointment Schedule")
    for hour in range(7, 21):
        st.markdown(f"<div><span class='appt-time'>{hour}</span><span class='appt-line'></span></div>", unsafe_allow_html=True)

st.markdown("</div></div>", unsafe_allow_html=True)
