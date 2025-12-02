// -----------------------------------------------------------
// GLOBAL STATE
// -----------------------------------------------------------
let currentDate = null;
let isSaving = false;

// -----------------------------------------------------------
// DATE HELPERS
// -----------------------------------------------------------
function formatDateForAPI(dateObj) {
    const y = dateObj.getFullYear();
    const m = String(dateObj.getMonth() + 1).padStart(2, "0");
    const d = String(dateObj.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
}

// -----------------------------------------------------------
// AUTH UI
// -----------------------------------------------------------
async function signup() {
    const email = document.getElementById("signup-email").value.trim();
    const pw = document.getElementById("signup-password").value;

    const res = await fetch("/api/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password: pw }),
        credentials: "include"
    });

    const data = await res.json();
    if (data.error) {
        alert(data.error);
        return;
    }

    document.getElementById("auth-section").style.display = "none";
    document.getElementById("planner-section").style.display = "block";
    loadToday();
}

async function login() {
    const email = document.getElementById("login-email").value.trim();
    const pw = document.getElementById("login-password").value;

    const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password: pw }),
        credentials: "include"
    });

    const data = await res.json();
    if (data.error) {
        alert(data.error);
        return;
    }

    document.getElementById("auth-section").style.display = "none";
    document.getElementById("planner-section").style.display = "block";
    loadToday();
}

async function logout() {
    await fetch("/api/logout", { method: "POST", credentials: "include" });
    location.reload();
}

// -----------------------------------------------------------
// LOAD DAY
// -----------------------------------------------------------
async function loadDay(dateObj) {
    currentDate = dateObj;

    const dateStr = formatDateForAPI(dateObj);

    const res = await fetch(`/api/day/${dateStr}`, {
        method: "GET",
        credentials: "include"
    });

    if (res.status === 401) {
        alert("Session expired. Please log in again.");
        location.reload();
        return;
    }

    const data = await res.json();
    renderDay(data);
}

function loadToday() {
    loadDay(new Date());
}

// -----------------------------------------------------------
// RENDER DAY INTO UI
// -----------------------------------------------------------
function renderDay(dayObj) {
    const tasks = dayObj.tasks || [];
    const appts = dayObj.appointments || [];

    // Tasks
    const taskContainer = document.getElementById("task-list");
    taskContainer.innerHTML = "";

    tasks.forEach(t => {
        const row = document.createElement("div");
        row.className = "task-row";

        row.innerHTML = `
            <input type="checkbox" class="task-check" ${t.checked ? "checked" : ""}>
            <select class="task-priority">
                <option value="A" ${t.priority === "A" ? "selected" : ""}>A</option>
                <option value="B" ${t.priority === "B" ? "selected" : ""}>B</option>
                <option value="C" ${t.priority === "C" ? "selected" : ""}>C</option>
            </select>
            <input type="text" class="task-desc" value="${t.description}">
        `;

        taskContainer.appendChild(row);
    });

    // Notes + Tracker
    document.getElementById("notes").value = dayObj.notes || "";
    document.getElementById("tracker").value = dayObj.tracker || "";

    // Appointments
    const apptContainer = document.getElementById("appointment-list");
    apptContainer.innerHTML = "";

    appts.forEach(a => {
        const row = document.createElement("div");
        row.className = "appt-row";
        row.innerHTML = `
            <input class="appt-time" value="${a.time}">
            <input class="appt-text" value="${a.text}">
        `;
        apptContainer.appendChild(row);
    });
}

// -----------------------------------------------------------
// COLLECT DATA FROM UI
// -----------------------------------------------------------
function collectDayData() {
    const tasks = [];
    const taskRows = document.querySelectorAll(".task-row");

    taskRows.forEach(r => {
        tasks.push({
            checked: r.querySelector(".task-check").checked,
            priority: r.querySelector(".task-priority").value,
            description: r.querySelector(".task-desc").value.trim()
        });
    });

    const appointments = [];
    const apptRows = document.querySelectorAll(".appt-row");

    apptRows.forEach(r => {
        appointments.push({
            time: r.querySelector(".appt-time").value.trim(),
            text: r.querySelector(".appt-text").value.trim()
        });
    });

    return {
        tasks,
        appointments,
        notes: document.getElementById("notes").value,
        tracker: document.getElementById("tracker").value
    };
}

// -----------------------------------------------------------
// AUTO SAVE
// -----------------------------------------------------------
async function saveDay() {
    if (!currentDate || isSaving) return;

    isSaving = true;
    const dateStr = formatDateForAPI(currentDate);
    const payload = collectDayData();

    await fetch(`/api/day/${dateStr}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload)
    });

    isSaving = false;
}

// Auto-save on change
document.addEventListener("input", () => {
    saveDay();
});

// -----------------------------------------------------------
// ADD ROWS
// -----------------------------------------------------------
function addTask() {
    const container = document.getElementById("task-list");
    const row = document.createElement("div");
    row.className = "task-row";
    row.innerHTML = `
        <input type="checkbox" class="task-check">
        <select class="task-priority">
            <option value="A">A</option>
            <option value="B">B</option>
            <option value="C" selected>C</option>
        </select>
        <input type="text" class="task-desc">
    `;
    container.appendChild(row);
}

function addAppointment() {
    const container = document.getElementById("appointment-list");
    const row = document.createElement("div");
    row.className = "appt-row";
    row.innerHTML = `
        <input class="appt-time" placeholder="9:00 AM">
        <input class="appt-text" placeholder="Description">
    `;
    container.appendChild(row);
}

// -----------------------------------------------------------
// NAVIGATION
// -----------------------------------------------------------
function goPrevDay() {
    const d = new Date(currentDate);
    d.setDate(d.getDate() - 1);
    loadDay(d);
}

function goNextDay() {
    const d = new Date(currentDate);
    d.setDate(d.getDate() + 1);
    loadDay(d);
}
