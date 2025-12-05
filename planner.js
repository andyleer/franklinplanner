// planner.js

(function () {
  // ---- DOM helpers ----
  const qs = (sel) => document.querySelector(sel);
  const qsa = (sel) => Array.from(document.querySelectorAll(sel));

  // Auth
  const authSection = qs("#auth-section");
  const loginForm = qs("#login-form");
  const signupForm = qs("#signup-form");
  const loginEmail = qs("#login-email");
  const loginPassword = qs("#login-password");
  const signupEmail = qs("#signup-email");
  const signupPassword = qs("#signup-password");
  const toggleToSignup = qs("#toggle-to-signup");
  const headerRight = qs("#header-right");

  // Planner
  const plannerSection = qs("#planner-section");
  const userChip = qs("#user-chip");
  const dateInput = qs("#date-input");
  const currentDateLabel = qs("#current-date-label");
  const prevDayBtn = qs("#prev-day-btn");
  const nextDayBtn = qs("#next-day-btn");
  const todayBtn = qs("#today-btn");
  const logoutBtn = qs("#logout-btn");
  const saveBtn = qs("#save-btn");
  const tasksBody = qs("#tasks-body");
  const appointmentsBody = qs("#appointments-body");
  const addTaskBtn = qs("#add-task-btn");
  const addAppointmentBtn = qs("#add-appointment-btn");
  const notesEl = qs("#notes");
  const trackerEl = qs("#tracker");
  const statusBar = qs("#status-bar");

  let currentDate = null; // YYYY-MM-DD
  let lastEmailUsed = "";

  // ---- Status messaging ----
  function setStatus(msg, kind = "") {
    statusBar.textContent = msg || "";
    statusBar.classList.remove("ok", "error");
    if (kind) statusBar.classList.add(kind);
  }

  function setSaving(isSaving) {
    if (isSaving) {
      saveBtn.disabled = true;
      saveBtn.textContent = "Saving…";
      setStatus("Saving…");
    } else {
      saveBtn.disabled = false;
      saveBtn.textContent = "Save";
    }
  }

  // ---- Date helpers ----
  function todayYMD() {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }

  function formatDateNice(ymd) {
    const [y, m, d] = ymd.split("-").map((x) => parseInt(x, 10));
    const date = new Date(y, m - 1, d);
    return date.toLocaleDateString(undefined, {
      weekday: "long",
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function shiftDate(ymd, deltaDays) {
    const [y, m, d] = ymd.split("-").map((x) => parseInt(x, 10));
    const date = new Date(y, m - 1, d);
    date.setDate(date.getDate() + deltaDays);
    const ny = date.getFullYear();
    const nm = String(date.getMonth() + 1).padStart(2, "0");
    const nd = String(date.getDate()).padStart(2, "0");
    return `${ny}-${nm}-${nd}`;
  }

  function setCurrentDate(ymd, load = true) {
    currentDate = ymd;
    if (dateInput) dateInput.value = ymd;
    if (currentDateLabel) currentDateLabel.textContent = formatDateNice(ymd);
    if (load) {
      loadDay(ymd);
    }
  }

  // ---- UI section toggles ----
  function showAuth() {
    authSection.classList.remove("hidden");
    plannerSection.classList.add("hidden");
    headerRight.textContent = "Daily planning sheet";
  }

  function showPlanner() {
    authSection.classList.add("hidden");
    plannerSection.classList.remove("hidden");
    headerRight.textContent = "Plan your day";
  }

  // ---- Row factories ----
  function createTaskRow(task = {}) {
    const tr = document.createElement("tr");

    const checked = !!task.checked;
    const priority = task.priority || "A";
    const description = task.description || "";

    // Checkbox
    const tdCheck = document.createElement("td");
    tdCheck.className = "checkbox-cell";
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = checked;
    tdCheck.appendChild(cb);

    // Priority
    const tdPriority = document.createElement("td");
    const sel = document.createElement("select");
    ["A", "B", "C"].forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p;
      opt.textContent = p;
      if (p === priority) opt.selected = true;
      sel.appendChild(opt);
    });
    tdPriority.appendChild(sel);

    // Description
    const tdDesc = document.createElement("td");
    const input = document.createElement("input");
    input.type = "text";
    input.value = description;
    input.placeholder = "Task / next action";
    tdDesc.appendChild(input);

    tr.appendChild(tdCheck);
    tr.appendChild(tdPriority);
    tr.appendChild(tdDesc);
    return tr;
  }

  function createAppointmentRow(appt = {}) {
    const tr = document.createElement("tr");

    const time = appt.time || "";
    const text = appt.text || "";

    const tdTime = document.createElement("td");
    const timeInput = document.createElement("input");
    timeInput.type = "time";
    timeInput.className = "time-input";
    if (time) {
      // Only assign if we think it's a valid time string
      timeInput.value = time;
    }
    tdTime.appendChild(timeInput);

    const tdText = document.createElement("td");
    const textInput = document.createElement("input");
    textInput.type = "text";
    textInput.value = text;
    textInput.placeholder = "Meeting, call, event…";
    tdText.appendChild(textInput);

    tr.appendChild(tdTime);
    tr.appendChild(tdText);
    return tr;
  }

  // ---- Collect data from DOM ----
  function collectTasksFromDOM() {
    const rows = qsa("#tasks-body tr");
    const tasks = [];
    rows.forEach((tr) => {
      const cb = tr.querySelector('input[type="checkbox"]');
      const sel = tr.querySelector("select");
      const input = tr.querySelector('input[type="text"]');
      if (!sel || !input) return;
      const desc = (input.value || "").trim();
      const pri = sel.value || "A";
      const done = !!cb?.checked;
      // Only store rows that have some content
      if (desc || done) {
        tasks.push({
          priority: pri,
          description: desc,
          checked: done,
        });
      }
    });
    return tasks;
  }

  function collectAppointmentsFromDOM() {
    const rows = qsa("#appointments-body tr");
    const appts = [];
    rows.forEach((tr) => {
      const timeInput = tr.querySelector('input[type="time"]');
      const textInput = tr.querySelector('input[type="text"]');
      if (!timeInput || !textInput) return;

      const timeVal = (timeInput.value || "").trim();
      const textVal = (textInput.value || "").trim();

      if (timeVal || textVal) {
        appts.push({
          time: timeVal,
          text: textVal,
        });
      }
    });
    return appts;
  }

  // ---- Apply data to DOM ----
  function populatePlannerFromData(data) {
    notesEl.value = data.notes || "";
    trackerEl.value = data.tracker || "";

    tasksBody.innerHTML = "";
    (data.tasks || []).forEach((t) => {
      tasksBody.appendChild(createTaskRow(t));
    });
    if (!data.tasks || data.tasks.length === 0) {
      // Always show at least 5 blank rows to start
      for (let i = 0; i < 5; i++) {
        tasksBody.appendChild(createTaskRow({ priority: i === 0 ? "A" : "B" }));
      }
    }

    appointmentsBody.innerHTML = "";
    (data.appointments || []).forEach((a) => {
      appointmentsBody.appendChild(createAppointmentRow(a));
    });
    if (!data.appointments || data.appointments.length === 0) {
      // Some starter rows
      ["09:00", "11:00", "14:00", "16:00"].forEach((time) => {
        appointmentsBody.appendChild(
          createAppointmentRow({ time, text: "" })
        );
      });
    }
  }

  // ---- API calls ----
  async function apiLogin(email, password) {
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || "Login failed");
    }
    return res.json();
  }

  async function apiSignup(email, password) {
    const res = await fetch("/api/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || "Signup failed");
    }
    return res.json();
  }

  async function apiLogout() {
    await fetch("/api/logout", {
      method: "POST",
      credentials: "same-origin",
    }).catch(() => {});
  }

  async function loadDay(ymd) {
    setStatus("Loading day…");
    try {
      const res = await fetch(`/api/day/${encodeURIComponent(ymd)}`, {
        method: "GET",
        credentials: "same-origin",
      });

      if (res.status === 401) {
        // Not logged in
        showAuth();
        setStatus("Please log in to see your planner.", "error");
        return;
      }

      if (!res.ok) {
        throw new Error(`Failed to load: ${res.status}`);
      }

      const data = await res.json();
      populatePlannerFromData(data);
      setStatus(`Loaded ${formatDateNice(ymd)}.`, "ok");
    } catch (err) {
      console.error(err);
      setStatus("Error loading day.", "error");
    }
  }

  async function saveCurrentDay() {
    if (!currentDate) return;
    setSaving(true);
    try {
      const payload = {
        date: currentDate,
        notes: notesEl.value || "",
        tracker: trackerEl.value || "",
        tasks: collectTasksFromDOM(),
        appointments: collectAppointmentsFromDOM(),
      };

      const res = await fetch(`/api/day/${encodeURIComponent(currentDate)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });

      if (res.status === 401) {
        showAuth();
        setStatus("Session expired. Log in again to save.", "error");
        return;
      }

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || "Save failed");
      }

      setSaving(false);
      setStatus("Saved.", "ok");
    } catch (err) {
      console.error(err);
      setSaving(false);
      setStatus("Error saving day.", "error");
    }
  }

  // ---- Event wiring ----
  function wireAuthHandlers() {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = loginEmail.value.trim().toLowerCase();
      const pw = loginPassword.value;
      if (!email || !pw) {
        setStatus("Email and password required.", "error");
        return;
      }
      setStatus("Logging in…");
      try {
        await apiLogin(email, pw);
        lastEmailUsed = email;
        userChip.textContent = email;
        showPlanner();
        setStatus("Logged in.", "ok");
        // Load today by default
        setCurrentDate(todayYMD(), true);
      } catch (err) {
        console.error(err);
        setStatus(err.message || "Login failed.", "error");
      }
    });

    signupForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = signupEmail.value.trim().toLowerCase();
      const pw = signupPassword.value;
      if (!email || !pw) {
        setStatus("Email and password required to sign up.", "error");
        return;
      }
      setStatus("Creating account…");
      try {
        await apiSignup(email, pw);
        lastEmailUsed = email;
        userChip.textContent = email;
        loginEmail.value = email;
        showPlanner();
        setStatus("Account created & logged in.", "ok");
        setCurrentDate(todayYMD(), true);
      } catch (err) {
        console.error(err);
        setStatus(err.message || "Signup failed.", "error");
      }
    });

    toggleToSignup.addEventListener("click", () => {
      signupEmail.focus();
      setStatus("Fill in the signup form below.");
    });
  }

  function wirePlannerHandlers() {
    prevDayBtn.addEventListener("click", () => {
      if (!currentDate) return;
      setCurrentDate(shiftDate(currentDate, -1), true);
    });

    nextDayBtn.addEventListener("click", () => {
      if (!currentDate) return;
      setCurrentDate(shiftDate(currentDate, 1), true);
    });

    todayBtn.addEventListener("click", () => {
      setCurrentDate(todayYMD(), true);
    });

    dateInput.addEventListener("change", () => {
      if (!dateInput.value) return;
      setCurrentDate(dateInput.value, true);
    });

    logoutBtn.addEventListener("click", async () => {
      await apiLogout();
      showAuth();
      setStatus("Logged out.");
    });

    saveBtn.addEventListener("click", () => {
      saveCurrentDay();
    });

    addTaskBtn.addEventListener("click", () => {
      tasksBody.appendChild(createTaskRow({ priority: "A" }));
    });

    addAppointmentBtn.addEventListener("click", () => {
      appointmentsBody.appendChild(createAppointmentRow({}));
    });
  }

  // ---- Initial bootstrap ----
  function bootstrap() {
    wireAuthHandlers();
    wirePlannerHandlers();

    // Start with auth visible.
    showAuth();
    setStatus("Log in or create an account to begin.");
  }

  document.addEventListener("DOMContentLoaded", bootstrap);
})();
