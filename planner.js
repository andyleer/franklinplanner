// -------------------------------
// GLOBALS
// -------------------------------
let currentDate = null;

// -------------------------------
// AUTH HANDLERS
// -------------------------------
async function signup() {
    const email = document.getElementById("signup-email").value.trim();
    const pw = document.getElementById("signup-password").value.trim();

    const res = await fetch("/api/signup", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        credentials: "include",
        body: JSON.stringify({ email, password: pw })
    });

    const data = await res.json();
    console.log("Signup:", data);

    if (data.error) {
        alert(data.error);
        return;
    }

    hideAuthShowPlanner();
}

async function login() {
    const email = document.getElementById("login-email").value.trim();
    const pw = document.getElementById("login-password").value.trim();

    const res = await fetch("/api/login", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        credentials: "include",
        body: JSON.stringify({ email, password: pw })
    });

    const data = await res.json();
    console.log("Login:", data);

    if (data.error) {
        alert(data.error);
        return;
    }

    hideAuthShowPlanner();
    loadToday();
}

async function logout() {
    await fetch("/api/logout", {
        method: "POST",
        credentials: "include"
    });

    document.getElementById("auth-section").style.display = "block";
    document.getElementById("planner-section").style.display = "none";
}

// -------------------------------
// UI HELPERS
// -------------------------------
function hideAuthShowPlanner() {
    document.getElementById("auth-section").style.display = "none";
    document.getElementById("planner-section").style.display = "block";
}

// -------------------------------
// DATE HELPERS
// -------------------------------
function loadToday() {
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, "0");
    const dd = String(today.getDate()).padStart(2, "0");
    loadDay(`${yyyy}-${mm}-${dd}`);
}

async function loadDay(dateStr) {
    currentDate = dateStr;
    document.getElementById("current-date-label").innerText = dateStr;

    const res = await fetch(`/api/day/${dateStr}`, {
        method: "GET",
        credentials: "include"
    });

    const data = await res.json();
    console.log("Loaded Day:", data);

    if (data.error) {
        alert("Please log in again.");
        return;
    }

    renderTasks(data.tasks || []);
    renderAppointments(data.appointments || []);

    document.getElementById("notes").value = data.notes || "";
    document.getElementById("tracker").value = data.tracker || "";
}

async function saveDay() {
    if (!currentDate) return;

    const payload = {
        notes: document.getElementById("notes").value,
        tracker: document.getElementById("tracker").value,
        tasks: collectTasks(),
        appointments: collectAppointments()
    };

    console.log("Saving payload:", payload);

    const res = await fetch(`/api/day/${currentDate}`, {
        method: "POST",
        credentials: "include",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
    });

    const data = await res.json();
    console.log("Save Response:", data);
}

// -------------------------------
// TASKS
// -------------------------------
function renderTasks(tasks) {
    const container = document.getElementById("task-list");
    container.innerHTML = "";

    tasks.forEach(t => addTaskRow(t.priority, t.description, t.checked));
}

function addTaskRow(priority = "A", description = "", checked = false) {
    const container = document.getElementById("task-list");

    const row = document.createElement("div");
    row.className = "task-row";

    row.innerHTML = `
        <input type="checkbox" class="task-check" ${checked ? "checked" : ""}>
        <select class="task-priority">
            <option ${priority === "A" ? "selected" : ""}>A</option>
            <option ${priority === "B" ? "selected" : ""}>B</option>
            <option ${priority === "C" ? "selected" : ""}>C</option>
        </select>
        <input class="task-desc" value="${description}">
    `;

    container.appendChild(row);
}

function collectTasks() {
    const rows = document.querySelectorAll(".task-row");
    return Array.from(rows).map(row => ({
        checked: row.querySelector(".task-check").checked,
        priority: row.querySelector(".task-priority").value,
        description: row.querySelector(".task-desc").value
    }));
}

// -------------------------------
// APPOINTMENTS
// -------------------------------
function renderAppointments(appts) {
    const container = document.getElementById("appointment-list");
    container.innerHTML = "";

    appts.forEach(a => addAppointmentRow(a.time, a.text));
}

function addAppointmentRow(time = "", text = "") {
    const container = document.getElementById("appointment-list");

    const row = document.createElement("div");
    row.className = "appt-row";

    row.innerHTML = `
        <input class="appt-time" placeholder="Time" value="${time}">
        <input class="appt-text" placeholder="Description" value="${text}">
    `;

    container.appendChild(row);
}

function collectAppointments() {
    const rows = document.querySelectorAll(".appt-row");
    return Array.from(rows).map(row => ({
        time: row.querySelector(".appt-time").value,
        text: row.querySelector(".appt-text").value
    }));
}

// -------------------------------
// BUTTON HOOKS
// -------------------------------
document.getElementById("btn-save").onclick = saveDay;
document.getElementById("btn-add-task").onclick = () => addTaskRow();
document.getElementById("btn-add-appt").onclick = () => addAppointmentRow();
document.getElementById("btn-today").onclick = loadToday;
