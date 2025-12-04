//-----------------------------------------------------------
// GLOBALS
//-----------------------------------------------------------
let CURRENT_DATE = new Date().toISOString().split("T")[0];

// Utility
function $(sel) {
    return document.querySelector(sel);
}
function $all(sel) {
    return Array.from(document.querySelectorAll(sel));
}

//-----------------------------------------------------------
// AUTH
//-----------------------------------------------------------
async function apiSignup(email, password) {
    const r = await fetch("/api/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password })
    });
    return r.json();
}

async function apiLogin(email, password) {
    const r = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password })
    });
    return r.json();
}

async function apiLogout() {
    await fetch("/api/logout", {
        method: "POST",
        credentials: "include"
    });
}

//-----------------------------------------------------------
// LOAD + SAVE DAY
//-----------------------------------------------------------
async function loadDay(date) {
    const r = await fetch(`/api/day/${date}`, {
        credentials: "include"
    });
    const data = await r.json();

    if (data.error === "unauthorized") {
        showLogin();
        return;
    }

    CURRENT_DATE = date;

    // Notes + tracker
    $("#notes").value = data.notes || "";
    $("#tracker").value = data.tracker || "";

    // Tasks
    $("#task-list").innerHTML = "";
    (data.tasks || []).forEach(t => addTaskRow(t.priority, t.description, t.checked));

    // Appointments
    $("#appt-list").innerHTML = "";
    (data.appointments || []).forEach(a => addApptRow(a.time, a.text));
}

async function saveDay() {
    const payload = {
        notes: $("#notes").value,
        tracker: $("#tracker").value,
        tasks: $all(".task-row").map(row => ({
            priority: row.querySelector(".t-priority").value,
            description: row.querySelector(".t-text").value,
            checked: row.querySelector(".t-check").checked
        })),
        appointments: $all(".appt-row").map(row => ({
            time: row.querySelector(".a-time").value,
            text: row.querySelector(".a-text").value
        }))
    };

    await fetch(`/api/day/${CURRENT_DATE}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload)
    });
}

//-----------------------------------------------------------
// UI HELPERS
//-----------------------------------------------------------
function showLogin() {
    $("#login-container").style.display = "block";
    $("#planner-container").style.display = "none";
}

function showPlanner() {
    $("#login-container").style.display = "none";
    $("#planner-container").style.display = "block";
    loadDay(CURRENT_DATE);
}

//-----------------------------------------------------------
// TASK + APPT ROWS
//-----------------------------------------------------------
function addTaskRow(priority = "A", text = "", checked = false) {
    const row = document.createElement("div");
    row.className = "task-row";
    row.innerHTML = `
        <input type="checkbox" class="t-check" ${checked ? "checked" : ""}>
        <select class="t-priority">
            <option ${priority === "A" ? "selected" : ""}>A</option>
            <option ${priority === "B" ? "selected" : ""}>B</option>
            <option ${priority === "C" ? "selected" : ""}>C</option>
        </select>
        <input class="t-text" value="${text}">
        <button class="task-del">X</button>
    `;
    row.querySelector(".task-del").onclick = () => row.remove();
    $("#task-list").appendChild(row);
}

function addApptRow(time = "", text = "") {
    const row = document.createElement("div");
    row.className = "appt-row";
    row.innerHTML = `
        <input class="a-time" value="${time}" placeholder="9:00 AM">
        <input class="a-text" value="${text}" placeholder="Appointment">
        <button class="appt-del">X</button>
    `;
    row.querySelector(".appt-del").onclick = () => row.remove();
    $("#appt-list").appendChild(row);
}

//-----------------------------------------------------------
// EVENT LISTENERS
//-----------------------------------------------------------

// LOGIN
$("#login-btn")?.addEventListener("click", async () => {
    const email = $("#login-email").value.trim();
    const pw = $("#login-password").value.trim();

    const result = await apiLogin(email, pw);

    if (result.error) {
        alert("Invalid login.");
        return;
    }

    showPlanner();
});

// SIGNUP
$("#signup-btn")?.addEventListener("click", async () => {
    const email = $("#login-email").value.trim();
    const pw = $("#login-password").value.trim();

    const result = await apiSignup(email, pw);

    if (result.error) {
        alert(result.error);
        return;
    }

    showPlanner();
});

// Logout
$("#logout-btn")?.addEventListener("click", async () => {
    await apiLogout();
    showLogin();
});

// Navigation arrows
$("#prev-day")?.addEventListener("click", () => {
    const dt = new Date(CURRENT_DATE);
    dt.setDate(dt.getDate() - 1);
    loadDay(dt.toISOString().split("T")[0]);
});
$("#next-day")?.addEventListener("click", () => {
    const dt = new Date(CURRENT_DATE);
    dt.setDate(dt.getDate() + 1);
    loadDay(dt.toISOString().split("T")[0]);
});

// Add rows
$("#add-task")?.addEventListener("click", () => addTaskRow());
$("#add-appt")?.addEventListener("click", () => addApptRow());

// Auto-save (basic)
$all("textarea, input").forEach(el => {
    el.addEventListener("change", saveDay);
    el.addEventListener("keyup", () => {
        clearTimeout(window._saveTimer);
        window._saveTimer = setTimeout(saveDay, 500);
    });
});

//-----------------------------------------------------------
// INITIAL CHECK
//-----------------------------------------------------------

(async function init() {
    const r = await fetch("/api/day/" + CURRENT_DATE, { credentials: "include" });
    const data = await r.json();

    if (data.error === "unauthorized") {
        showLogin();
    } else {
        showPlanner();
    }
})();
