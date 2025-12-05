// planner.js — matches your final backend EXACTLY

(function () {
    let currentUserId = null;
    let saveTimer = null;

    /* ==========================================================
       AUTH
    ========================================================== */

    async function login(email, password) {
        const res = await fetch("/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Login failed");

        currentUserId = data.user_id;
    }

    async function signup(email, password) {
        const res = await fetch("/api/signup", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Signup failed");

        currentUserId = data.user_id;
    }

    async function logout() {
        await fetch("/api/logout", { method: "POST" });
        currentUserId = null;
    }

    /* ==========================================================
       UI TRANSITIONS
    ========================================================== */

    function showPlanner() {
        document.getElementById("auth-container").classList.add("hidden");
        document.getElementById("planner-container").classList.remove("hidden");
    }

    function showAuth() {
        document.getElementById("planner-container").classList.add("hidden");
        document.getElementById("auth-container").classList.remove("hidden");
    }

    /* ==========================================================
       MINI CALENDAR
    ========================================================== */

    function renderMiniCalendar(id, year, month) {
        const container = document.getElementById(id);
        container.innerHTML = "";

        const d = new Date(year, month, 1);
        const firstDay = new Date(year, month, 1).getDay();
        const lastDay = new Date(year, month + 1, 0).getDate();

        const title = document.createElement("div");
        title.style.textAlign = "center";
        title.style.fontWeight = "bold";
        title.textContent = d.toLocaleString("default", {
            month: "short",
            year: "numeric"
        });
        container.appendChild(title);

        const grid = document.createElement("div");
        grid.className = "mini-cal-grid";

        ["S","M","T","W","T","F","S"].forEach(w => {
            const cell = document.createElement("div");
            cell.className = "weekday-label";
            cell.textContent = w;
            grid.appendChild(cell);
        });

        for (let i = 0; i < firstDay; i++) {
            grid.appendChild(document.createElement("div"));
        }
        for (let day = 1; day <= lastDay; day++) {
            const cell = document.createElement("div");
            cell.textContent = day;
            grid.appendChild(cell);
        }

        container.appendChild(grid);
    }

    function updateHeader(dateStr) {
        const d = new Date(dateStr + "T00:00:00");
        document.getElementById("day-number").textContent = d.getDate();
        document.getElementById("weekday").textContent =
            d.toLocaleString("default", { weekday: "long" });
        document.getElementById("month-year").textContent =
            d.toLocaleString("default", { month: "long", year: "numeric" });

        const y = d.getFullYear();
        const m = d.getMonth();
        renderMiniCalendar("mini-current", y, m);
        renderMiniCalendar("mini-prev", y, m - 1);
        renderMiniCalendar("mini-next", y, m + 1);
    }

    /* ==========================================================
       TASK ROWS
    ========================================================== */

    function addBlankTask() {
        const row = document.createElement("div");
        row.className = "task-row";
        row.innerHTML = `
            <input type="checkbox">
            <select>
                <option>A</option>
                <option>B</option>
                <option>C</option>
            </select>
            <input type="text">
        `;
        document.getElementById("task-list").appendChild(row);
    }

    /* ==========================================================
       LOAD DAY
    ========================================================== */

    async function loadDay(dateStr) {
        const res = await fetch("/api/day/" + dateStr);
        const data = await res.json();

        if (!res.ok) {
            console.warn("Not loaded:", data.error);
            return;
        }

        updateHeader(dateStr);

        // Tasks
        const list = document.getElementById("task-list");
        list.innerHTML = "";
        data.tasks.forEach(t => {
            const row = document.createElement("div");
            row.className = "task-row";
            row.innerHTML = `
                <input type="checkbox" ${t.checked ? "checked" : ""}>
                <select>
                    <option ${t.priority === "A" ? "selected" : ""}>A</option>
                    <option ${t.priority === "B" ? "selected" : ""}>B</option>
                    <option ${t.priority === "C" ? "selected" : ""}>C</option>
                </select>
                <input type="text" value="${t.description || ""}">
            `;
            list.appendChild(row);
        });
        if (data.tasks.length === 0) {
            for (let i = 0; i < 6; i++) addBlankTask();
        }

        // Appointments
        const appts = document.querySelectorAll(".appt-row .appt-input");
        appts.forEach((input, idx) => {
            const a = data.appointments[idx];
            input.value = a ? (a.text || "") : "";
        });

        // Text areas
        document.getElementById("tracker").value = data.tracker || "";
        document.getElementById("notes").value = data.notes || "";
    }

    /* ==========================================================
       SAVE DAY
    ========================================================== */

    function collectState() {
        const dateStr = document.getElementById("date-input").value;

        const tasks = Array.from(document.querySelectorAll("#task-list .task-row"))
            .map(row => {
                const checkbox = row.querySelector("input[type=checkbox]");
                const select = row.querySelector("select");
                const text = row.querySelector("input[type=text]");
                return {
                    checked: checkbox.checked,
                    priority: select.value,
                    description: text.value
                };
            });

        const appts = Array.from(document.querySelectorAll(".appt-row")).map(r => ({
            time: r.children[0].textContent.trim(),
            text: r.querySelector(".appt-input").value
        }));

        return {
            date: dateStr,
            tasks,
            appointments: appts,
            tracker: document.getElementById("tracker").value,
            notes: document.getElementById("notes").value
        };
    }

    function saveDayDebounced() {
        clearTimeout(saveTimer);
        saveTimer = setTimeout(saveDay, 500);
    }

    async function saveDay() {
        const s = collectState();
        const res = await fetch("/api/day/" + s.date, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(s)
        });
        if (!res.ok) console.warn(await res.text());
    }

    /* ==========================================================
       INIT
    ========================================================== */

    function initEvents() {
        document.body.addEventListener("input", saveDayDebounced);
        document.body.addEventListener("change", saveDayDebounced);

        document.getElementById("add-task").addEventListener("click", () => {
            addBlankTask();
            saveDayDebounced();
        });

        document.getElementById("date-input").addEventListener("change", e => {
            loadDay(e.target.value);
        });

        document.getElementById("logout-btn").addEventListener("click", async () => {
            await logout();
            showAuth();
        });
    }

    /* ==========================================================
       AUTH UI BINDING
    ========================================================== */

    async function tryLoginOrSignup(action) {
        const email = document.getElementById("auth-email").value.trim();
        const password = document.getElementById
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
