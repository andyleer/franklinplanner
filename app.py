# franklin_left_page.py
# Date: 2025-11-12  (auto generated)
# Streamlit app recreating the Franklin Planner left page layout.

import streamlit as st
from datetime import date

st.set_page_config(page_title="Franklin Daily Planner", layout="wide")

# --- Custom CSS styling ---
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
        padding: 2rem 3rem;
        margin: 1rem auto;
        width: 90%;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-radius: 8px;
    }
    h1, h2, h3 {
        color: #004d4d;
        font-family: 'Georgia', serif;
        margin-bottom: 0.25rem;
    }
    .mini-calendar {
        font-size: 0.8rem;
        color: #004d4d;
        line-height: 1.1;
        text-align: center;
        margin-top: -0.5rem;
    }
    .appt-time {
        width: 40px;
        display: inline-block;
        font-weight: bold;
        color: #004d4d;
    }
    .appt-line {
        border-bottom: 1px solid #c9d7d6;
        height: 1.5em;
        width: 100%;
        margin-bottom: 0.2rem;
    }
    .abc-table {
        width: 100%;
        border-collapse: collapse;
    }
    .abc-table th {
        border-bottom: 2px solid #004d4d;
        text-align: left;
        padding-bottom: 4px;
        color: #004d4d;
    }
    .abc-table td {
        padding: 4px 4px;
        border-bottom: 1px solid #c9d7d6;
    }
    .daily-tracker {
        margin-top: 1rem;
        border-top: 2px solid #004d4d;
        padding-top: 0.5rem;
    }
    .add-btn {
        color: #004d4d;
        font-weight: bold;
        text-decoration: none;
        background-color: transparent;
        border: 1px solid #004d4d;
        border-radius: 4px;
        padding: 0 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- App Layout ---
with st.container():
    st.markdown("<div class='page'>", unsafe_allow_html=True)

    # --- Header with date and mini-calendars ---
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        st.markdown("### 15  \n**Tuesday**  \nApril 2025")
    with col2:
        st.markdown("""
        <div class='mini-calendar'>
        <b>March 2025</b><br>
        S M T W T F S<br>
        2 3 4 5 6 7 8<br>
        9 10 11 12 13 14 15<br>
        16 17 18 19 20 21 22<br>
        23 24 25 26 27 28 29<br>
        30 31
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class='mini-calendar'>
        <b>May 2025</b><br>
        S M T W T F S<br>
        4 5 6 7 8 9 10<br>
        11 12 13 14 15 16 17<br>
        18 19 20 21 22 23 24<br>
        25 26 27 28 29 30 31
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # --- Appointment Schedule ---
    st.markdown("#### Appointment Schedule")
    for hour in range(7, 21):
        st.markdown(f"<div><span class='appt-time'>{hour}</span><span class='appt-line'></span></div>", unsafe_allow_html=True)

    st.markdown("---")

    # --- ABC Prioritized Daily Task List ---
    st.markdown("#### ABC Prioritized Daily Task List")

    if "tasks" not in st.session_state:
        st.session_state.tasks = [{"done": False, "priority": "A", "desc": ""} for _ in range(6)]

    edited = False
    for i, task in enumerate(st.session_state.tasks):
        cols = st.columns([0.5, 0.8, 8])
        with cols[0]:
            st.session_state.tasks[i]["done"] = st.checkbox("", value=task["done"], key=f"done_{i}")
        with cols[1]:
            st.session_state.tasks[i]["priority"] = st.selectbox("", ["A", "B", "C"], key=f"priority_{i}", label_visibility="collapsed", index=["A","B","C"].index(task["priority"]))
        with cols[2]:
            st.session_state.tasks[i]["desc"] = st.text_input("", value=task["desc"], key=f"desc_{i}", label_visibility="collapsed")
        st.markdown("<hr style='border:0.5px solid #c9d7d6; margin:0.1rem 0;'>", unsafe_allow_html=True)

    if st.button("+ Add Task"):
        st.session_state.tasks.append({"done": False, "priority": "C", "desc": ""})

    # --- Daily Tracker ---
    st.markdown("<div class='daily-tracker'><b>Daily Tracker</b><br><small>Track expenses, email, voice mail, or other information.</small></div>", unsafe_allow_html=True)
    for i in range(1, 9):
        st.text_input(f"Tracker {i}", key=f"tracker_{i}", label_visibility="collapsed")

    st.markdown("</div>", unsafe_allow_html=True)
