# franklin_left_page_layout.py
# Date: 2025-11-12
# Streamlit app replicating Franklin Planner left page layout with two-column structure.

import streamlit as st

st.set_page_config(page_title="Franklin Planner Left Page", layout="wide")

# ----------  CSS Styling ----------
st.markdown("""
<style>
    body {
        background-color: #f7f9f8;
        font-family: 'Georgia', serif;
        color: #004d4d;
    }
    .page {
        background-color: #e9f1f0;
        border: 1px solid #c9d7d6;
        padding: 1.5rem 2.5rem;
        margin: 1rem auto;
        width: 95%;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-radius: 8px;
    }
    h3, h4 {
        color: #004d4d;
        font-family: 'Georgia', serif;
        margin-bottom: 0.25rem;
    }
    .mini-calendar {
        font-size: 0.8rem;
        color: #004d4d;
        line-height: 1.1;
        text-align: center;
    }
    .appt-time {
        width: 40px;
        display: inline-block;
        font-weight: bold;
        color: #004d4d;
    }
    .appt-line {
        border-bottom: 1px solid #c9d7d6;
        height: 1.4em;
        width: 100%;
        margin-bottom: 0.25rem;
        display: inline-block;
    }
    .abc-header {
        border-bottom: 2px solid #004d4d;
        margin-top: 0.5rem;
        margin-bottom: 0.3rem;
        padding-bottom: 0.25rem;
        font-weight: bold;
    }
    hr.line {
        border: 0.5px solid #c9d7d6;
        margin: 0.2rem 0;
    }
    .daily-tracker {
        margin-top: 1rem;
        border-top: 2px solid #004d4d;
        padding-top: 0.5rem;
    }
    .add-btn {
        color: #004d4d;
        border: 1px solid #004d4d;
        background-color: transparent;
        padding: 0 8px;
        border-radius: 4px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ----------  Main Page Container ----------
st.markdown("<div class='page'>", unsafe_allow_html=True)

colA, colB = st.columns([1.2, 1.1])  # Proportion similar to real planner

# ----------  LEFT COLUMN ----------
with colA:
    # Date + mini calendars
    st.markdown("### 15  \n**Tuesday**  \nApril 2025")
    st.markdown("""
    <div style="display:flex; justify-content:space-between; margin-top:-0.5rem;">
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

    # ABC Prioritized Task List
    st.markdown("<div class='abc-header'>ABC Prioritized Daily Task List</div>", unsafe_allow_html=True)

    if "tasks" not in st.session_state:
        st.session_state.tasks = [{"done": False, "priority": "A", "desc": ""} for _ in range(6)]

    for i, task in enumerate(st.session_state.tasks):
        cols = st.columns([0.5, 0.8, 6])
        with cols[0]:
            st.session_state.tasks[i]["done"] = st.checkbox("", value=task["done"], key=f"done_{i}")
        with cols[1]:
            st.session_state.tasks[i]["priority"] = st.selectbox(
                "", ["A", "B", "C"], key=f"priority_{i}", label_visibility="collapsed",
                index=["A", "B", "C"].index(task["priority"])
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
    for i in range(1, 9):
        st.text_input(f"Tracker {i}", key=f"tracker_{i}", label_visibility="collapsed")

# ----------  RIGHT COLUMN ----------
with colB:
    st.markdown("#### Appointment Schedule")
    for hour in range(7, 21):
        st.markdown(f"<div><span class='appt-time'>{hour}</span><span class='appt-line'></span></div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)
