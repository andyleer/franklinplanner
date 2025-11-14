// ==============================
// SIMPLE PLANNER STATE
// ==============================
let currentDate = null;

// ==============================
// API HELPERS
// ==============================
async function apiGet(url) {
    const r = await fetch(url);
    return await r.json();
}

async function apiPost(url, data) {
    const r = await fetch(url, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(data)
    });
    return await r.json();
}

// ==============================
// LOAD A DAY
// ==============================
async function loadDay(dateStr) {
    currentDate = dateStr;

    const data = await apiGet(`/api/day/${dateStr}`);

    // NOTES (right page)
    const notesEl = document.getElementById("notes");
    if (notesEl) {
        notesEl.value = data.notes || "";
    }

    // TRACKER (left page bottom)
    const trackerEl = document.getElementById("tracker");
    if (trackerEl) {
        trackerEl.value = data.tracker || "";
    }

    // TASKS (A/B/C list)
    const tasksContainer = document.getElementById("tasks");
    if (tasksContainer) {
        tasksContainer.innerHTML = "";
        data.tasks.forEach((t) => {
            const row = document.createElement("div");
            row.className = "task-row";

            row.innerHTML = `
                <input type="checkbox" class="task-done" ${t.done ? "checked" : ""}>
                <select class="task-priority">
                    <option value="A" ${t.priority === "A" ? "selected" : ""}>A</option>
                    <option value="B" ${t.priority === "B" ? "selected" : ""}>B</option>
                    <option value="C" ${t.priority === "C" ? "selected" : ""}>C</option>
                </select>
                <input type="text" class="task-text" value="${t.text}">
            `;

            tasksContainer.appendChild(row);
        });
    }

    // APPOINTMENTS (time slots)
    const apptContainer = document.querySelector(".schedule-list");
    if (apptContainer) {
        apptContainer.querySelectorAll(".schedule-item input").forEach((input) => {
            const time = input.dataset.time;
            const match = data.appointments.find(a => a.time === time);
            input.value = match ? match.text : "";
        });
    }
}

// ==============================
// SAVE CURRENT DAY
// ==============================
async function saveCurrentDay() {
    if (!currentDate) return;

    console.log("Saving", currentDate);

    // NOTES
    const notes = document.getElementById("notes")?.value || "";

    // TRACKER
    const tracker = document.getElementById("tracker")?.value || "";

    // TASKS
    const tasks = [];
    document.querySelectorAll("#tasks .task-row").forEach(row => {
        tasks.push({
            priority: row.querySelector(".task-priority").value,
            text: row.querySelector(".task-text").value,
            done: row.querySelector(".task-done").checked
        });
    });

    // APPOINTMENTS
    const appointments = [];
    document.querySelectorAll(".schedule-item input").forEach(input => {
        appointments.push({
            time: input.dataset.time,
            text: input.value
        });
    });

    const payload = {
        notes,
        tracker,
        tasks,
        appointments
    };

    await apiPost(`/api/day/${currentDate}`, payload);
}

// ==============================
// AUTO-SAVE every 10s
// ==============================
setInterval(saveCurrentDay, 10000);

// ==============================
// On load, default to today
// ==============================
document.addEventListener("DOMContentLoaded", () => {
    const today = new Date().toISOString().slice(0, 10);
    loadDay(today);
});
