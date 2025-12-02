/* -------------------------------------------------------
   Franklin Planner – Frontend Logic
------------------------------------------------------- */

let currentDate = null;

/* --------------------------
   LOGIN / SIGNUP HANDLERS
--------------------------- */

document.getElementById("login-btn").onclick = async () => {
    const email = document.getElementById("login-email").value.trim();
    const pw = document.getElementById("login-password").value;

    const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password: pw })
    });

    const data = await res.json();
    if (data.error) {
        alert(data.error);
        return;
    }

    showPlanner();
};

document.getElementById("signup-btn").onclick = async () => {
    const email = document.getElementById("signup-email").value.trim();
    const pw = document.getElementById("signup-password").value;

    const res = await fetch("/api/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password: pw })
    });

    const data = await res.json();
    if (data.error) {
        alert(data.error);
        return;
    }

    showPlanner();
};

function showPlanner() {
    document.getElementById("auth-screen").style.display = "none";
    document.getElementById("planner-screen").style.display = "block";

    const today = new Date().toISOString().slice(0, 10);
    loadDay(today);
}

/* --------------------------
   LOAD A DAY
--------------------------- */
async function loadDay(date) {
    currentDate = date;

    const res = await fetch(`/api/day/${date}`, {
        method: "GET",
        credentials: "include"
    });

    const data = await res.json();
    if (data.error) {
        alert("Session expired, please log in again.");
        location.reload();
        return;
    }

    document.getElementById("notes").value = data.notes || "";
    document.getElementById("tracker").value = data.tracker || "";

    // Tasks
    const taskList = document.getElementById("task-list");
    taskList.innerHTML = "";
    (data.tasks || []).forEach(t => addTask(t.priority, t.description, t.checked));

    // Appointments
    const apptList = document.getElementById("appointment-list");
    apptList.innerHTML = "";
    (data.appointments || []).forEach(a => addAppointment(a.time, a.text));
}

/* --------------------------
   SAVE A DAY
--------------------------- */
document.getElementById("save-btn").onclick = async () => {
    const payload = {
        notes: document.getElementById("notes").value,
        tracker: document.getElementById("tracker").value,
        tasks: gatherTasks(),
        appointments: gatherAppointments()
    };

    const res = await fetch(`/api/day/${currentDate}`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (data.status !== "ok") alert("Save failed");
};

function gatherTasks() {
    return [...document.querySelectorAll(".task-row")].map(row => ({
        priority: row.querySelector(".task-priority").value,
        description: row.querySelector(".task-desc").value,
        checked: row.querySelector(".task-check").checked
    }));
}

function gatherAppointments() {
    return [...document.querySelectorAll(".appt-row")].map(row => ({
        time: row.querySelector(".appt-time").value,
        text: row.querySelector(".appt-text").value
    }));
}

/* --------------------------
   TASK UI HELPERS
--------------------------- */
function addTask(priority = "A", description = "", checked = false) {
    const el = document.createElement("div");
    el.className = "task-row";
    el.innerHTML = `
        <input type="checkbox" class="task-check" ${checked ? "checked" : ""}>
        <select class="task-priority">
            <option value="A" ${priority === "A" ? "selected" : ""}>A</option>
            <option value="B" ${priority === "B" ? "selected" : ""}>B</option>
            <option value="C" ${priority === "C" ? "selected" : ""}>C</option>
        </select>
        <input class="task-desc" value="${description}">
        <button class="delete-task">X</button>
    `;

    el.querySelector(".delete-task").onclick = () => el.remove();
    document.getElementById("task-list").appendChild(el);
}

document.getElementById("add-task-btn").onclick = () => addTask();

/* --------------------------
   APPOINTMENT UI HELPERS
--------------------------- */
function addAppointment(time = "", text = "") {
    const el = document.createElement("div");
    el.className = "appt-row";
    el.innerHTML = `
        <input class="appt-time" type="time" value="${time}">
        <input class="appt-text" value="${text}">
        <button class="delete-appt">X</button>
    `;

    el.querySelector(".delete-appt").onclick = () => el.remove();
    document.getElementById("appointment-list").appendChild(el);
}

document.getElementById("add-appt-btn").onclick = () => addAppointment();

/* --------------------------
   DATE NAVIGATION
--------------------------- */
document.getElementById("prev-day").onclick = () => {
    const d = new Date(currentDate);
    d.setDate(d.getDate() - 1);
    loadDay(d.toISOString().slice(0, 10));
};

document.getElementById("next-day").onclick = () => {
    const d = new Date(currentDate);
    d.setDate(d.getDate() + 1);
    loadDay(d.toISOString().slice(0, 10));
};
