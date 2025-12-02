// planner.js
// Frontend for Franklin Planner backend in app.py
// Uses cookie-based session auth and per-user/per-day data.

const API_BASE = ""; // same origin

let currentDate = new Date(); // JS Date object

// ---------- DOM HELPERS ----------
function $(id) {
  return document.getElementById(id);
}

// Sections
const authSection = $("auth-section");
const plannerSection = $("planner-section");

// Auth elements
const loginForm = $("login-form");
const signupForm = $("signup-form");
const loginEmailInput = $("login-email");
const loginPasswordInput = $("login-password");
const signupEmailInput = $("signup-email");
const signupPasswordInput = $("signup-password");
const logoutBtn = $("logout-btn");

// Date navigation
const dateDisplay = $("date-display");
const prevDayBtn = $("prev-day");
const nextDayBtn = $("next-day");

// Planner elements
const tasksBody = $("tasks-body");
const addTaskBtn = $("add-task");
const apptBody = $("appointments-body");
const addApptBtn = $("add-appointment");
const notesInput = $("notes");
const trackerInput = $("tracker");
const saveDayBtn = $("save-day");

// ---------- DATE HELPERS ----------
function pad2(n) {
  return n < 10 ? "0" + n : "" + n;
}

function dateToString(d) {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

function stringToDate(s) {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function formatPrettyDate(d) {
  return d.toLocaleDateString(undefined, {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

// ---------- UI TOGGLING ----------
function showAuth() {
  if (authSection) authSection.style.display = "block";
  if (plannerSection) plannerSection.style.display = "none";
}

function showPlanner() {
  if (authSection) authSection.style.display = "none";
  if (plannerSection) plannerSection.style.display = "block";
}

// ---------- ROW BUILDERS ----------
function createTaskRow(task = {}) {
  const tr = document.createElement("tr");

  // Priority (A/B/C)
  const tdPriority = document.createElement("td");
  const sel = document.createElement("select");
  sel.className = "task-priority";
  ["A", "B", "C"].forEach((p) => {
    const opt = document.createElement("option");
    opt.value = p;
    opt.textContent = p;
    if (task.priority === p) opt.selected = true;
  });
  tdPriority.appendChild(sel);

  // Description
  const tdDesc = document.createElement("td");
  const descInput = document.createElement("input");
  descInput.type = "text";
  descInput.className = "task-desc";
  descInput.value = task.description || "";
  tdDesc.appendChild(descInput);

  // Checked
  const tdChecked = document.createElement("td");
  const cb = document.createElement("input");
  cb.type = "checkbox";
  cb.className = "task-checked";
  cb.checked = !!task.checked;
  tdChecked.appendChild(cb);

  tr.appendChild(tdPriority);
  tr.appendChild(tdDesc);
  tr.appendChild(tdChecked);

  return tr;
}

function createApptRow(appt = {}) {
  const tr = document.createElement("tr");

  const tdTime = document.createElement("td");
  const timeInput = document.createElement("input");
  timeInput.className = "appt-time";
  // You can change type to "time" if your HTML supports it
  timeInput.type = "time";
  timeInput.value = appt.time || "";
  tdTime.appendChild(timeInput);

  const tdText = document.createElement("td");
  const textInput = document.createElement("input");
  textInput.type = "text";
  textInput.className = "appt-text";
  textInput.value = appt.text || "";
  tdText.appendChild(textInput);

  tr.appendChild(tdTime);
  tr.appendChild(tdText);
  return tr;
}

// ---------- RENDER DAY ----------
function renderDay(data) {
  const dateStr = data.date;
  currentDate = stringToDate(dateStr);

  if (dateDisplay) {
    dateDisplay.textContent = formatPrettyDate(currentDate);
  }

  if (notesInput) notesInput.value = data.notes || "";
  if (trackerInput) trackerInput.value = data.tracker || "";

  // Tasks
  if (tasksBody) {
    tasksBody.innerHTML = "";
    const tasks = data.tasks || [];
    if (tasks.length === 0) {
      // Start with a few blank rows for convenience
      for (let i = 0; i < 6; i++) {
        tasksBody.appendChild(createTaskRow());
      }
    } else {
      tasks.forEach((t) => tasksBody.appendChild(createTaskRow(t)));
    }
  }

  // Appointments
  if (apptBody) {
    apptBody.innerHTML = "";
    const appts = data.appointments || [];
    if (appts.length === 0) {
      // Start with some blank rows
      for (let i = 0; i < 8; i++) {
        apptBody.appendChild(createApptRow());
      }
    } else {
      appts.forEach((a) => apptBody.appendChild(createApptRow(a)));
    }
  }
}

// ---------- COLLECT DATA FROM UI ----------
function collectTasksFromUI() {
  if (!tasksBody) return [];
  const rows = Array.from(tasksBody.querySelectorAll("tr"));
  const tasks = [];

  rows.forEach((row) => {
    const pr = row.querySelector(".task-priority");
    const desc = row.querySelector(".task-desc");
    const chk = row.querySelector(".task-checked");

    const description = desc ? desc.value.trim() : "";
    const priority = pr ? pr.value || "A" : "A";
    const checked = chk ? chk.checked : false;

    // If row is totally blank, skip it
    if (!description && !checked) return;

    tasks.push({ priority, description, checked });
  });

  return tasks;
}

function collectAppointmentsFromUI() {
  if (!apptBody) return [];
  const rows = Array.from(apptBody.querySelectorAll("tr"));
  const appts = [];

  rows.forEach((row) => {
    const timeInput = row.querySelector(".appt-time");
    const textInput = row.querySelector(".appt-text");

    const time = timeInput ? timeInput.value.trim() : "";
    const text = textInput ? textInput.value.trim() : "";

    // Skip empty rows
    if (!time && !text) return;

    appts.push({ time, text });
  });

  return appts;
}

// ---------- API CALLS ----------
async function apiGetDay(dateStr) {
  const resp = await fetch(`${API_BASE}/api/day/${dateStr}`, {
    credentials: "include",
  });

  if (resp.status === 401) {
    showAuth();
    throw new Error("unauthorized");
  }

  if (!resp.ok) {
    throw new Error("Failed to load day");
  }

  const data = await resp.json();
  return data;
}

async function apiSaveDay(dateStr) {
  const payload = {
    date: dateStr,
    notes: notesInput ? notesInput.value : "",
    tracker: trackerInput ? trackerInput.value : "",
    tasks: collectTasksFromUI(),
    appointments: collectAppointmentsFromUI(),
  };

  const resp = await fetch(`${API_BASE}/api/day/${dateStr}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify(payload),
  });

  if (resp.status === 401) {
    showAuth();
    throw new Error("unauthorized");
  }

  if (!resp.ok) {
    throw new Error("Failed to save day");
  }

  return resp.json();
}

// ---------- AUTH HANDLERS ----------
async function handleLogin(e) {
  e.preventDefault();
  if (!loginEmailInput || !loginPasswordInput) return;

  const email = loginEmailInput.value.trim();
  const password = loginPasswordInput.value;

  if (!email || !password) {
    alert("Email and password required");
    return;
  }

  const resp = await fetch(`${API_BASE}/api/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    alert(err.error || "Login failed");
    return;
  }

  showPlanner();
  // Load today's day after login
  loadCurrentDate();
}

async function handleSignup(e) {
  e.preventDefault();
  if (!signupEmailInput || !signupPasswordInput) return;

  const email = signupEmailInput.value.trim();
  const password = signupPasswordInput.value;

  if (!email || !password) {
    alert("Email and password required");
    return;
  }

  const resp = await fetch(`${API_BASE}/api/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    alert(err.error || "Signup failed");
    return;
  }

  showPlanner();
  loadCurrentDate();
}

async function handleLogout() {
  await fetch(`${API_BASE}/api/logout`, {
    method: "POST",
    credentials: "include",
  }).catch(() => {});
  showAuth();
}

// ---------- DAY NAVIGATION ----------
async function loadCurrentDate() {
  const dateStr = dateToString(currentDate);
  try {
    const data = await apiGetDay(dateStr);
    renderDay(data);
  } catch (err) {
    console.error(err);
  }
}

function goToPreviousDay() {
  currentDate.setDate(currentDate.getDate() - 1);
  loadCurrentDate();
}

function goToNextDay() {
  currentDate.setDate(currentDate.getDate() + 1);
  loadCurrentDate();
}

// ---------- INIT ----------
document.addEventListener("DOMContentLoaded", () => {
  // Wire auth
  if (loginForm) loginForm.addEventListener("submit", handleLogin);
  if (signupForm) signupForm.addEventListener("submit", handleSignup);
  if (logoutBtn) logoutBtn.addEventListener("click", handleLogout);

  // Wire planner buttons
  if (prevDayBtn) prevDayBtn.addEventListener("click", goToPreviousDay);
  if (nextDayBtn) nextDayBtn.addEventListener("click", goToNextDay);

  if (addTaskBtn && tasksBody) {
    addTaskBtn.addEventListener("click", () => {
      tasksBody.appendChild(createTaskRow());
    });
  }

  if (addApptBtn && apptBody) {
    addApptBtn.addEventListener("click", () => {
      apptBody.appendChild(createApptRow());
    });
  }

  if (saveDayBtn) {
    saveDayBtn.addEventListener("click", async () => {
      try {
        await apiSaveDay(dateToString(currentDate));
        // You could show a subtle “Saved” indicator here if you want
      } catch (err) {
        console.error(err);
        alert("Failed to save");
      }
    });
  }

  // On first load, try to load today's date.
  // If not logged in, backend returns 401 and we fall back to login UI.
  currentDate = new Date();
  apiGetDay(dateToString(currentDate))
    .then((data) => {
      showPlanner();
      renderDay(data);
    })
    .catch((err) => {
      console.log("Not logged in yet or error:", err);
      showAuth();
    });
});
