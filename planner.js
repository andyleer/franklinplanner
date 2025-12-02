// planner.js
// Franklin-style daily planner front-end logic
// Backend endpoints (session-based):
//   POST /api/signup  -> {status, user_id} or {error}
//   POST /api/login   -> {status, user_id} or {error}
//   GET  /api/day/<YYYY-MM-DD>
//   POST /api/day/<YYYY-MM-DD>

(function () {
  "use strict";

  /* =====================================================================
     0. SIMPLE HELPERS
     ===================================================================== */
  function qs(sel) {
    return document.querySelector(sel);
  }

  function showAuthPanel(show) {
    const auth = qs("#auth-panel");
    const shell = qs("#planner-shell");
    if (!auth || !shell) return;

    auth.style.display = show ? "block" : "none";
    shell.style.display = show ? "none" : "block";
  }

  function setAuthError(msg) {
    const el = qs("#auth-error");
    if (!el) return;
    if (!msg) {
      el.style.display = "none";
      el.textContent = "";
    } else {
      el.style.display = "block";
      el.textContent = msg;
    }
  }

  function getActiveDate() {
    const dateInput = qs("#date-input");
    const today = new Date().toISOString().slice(0, 10);
    if (!dateInput) return today;
    return dateInput.value || today;
  }

  /* =====================================================================
     1. AUTH – SIGNUP + LOGIN
     ===================================================================== */
  async function apiSignup(email, password) {
    const res = await fetch("/api/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password })
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || "Sign up failed");
    }
    return data;
  }

  async function apiLogin(email, password) {
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password })
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.error || "Login failed");
    }
    return data;
  }

  function wireAuthHandlers() {
    const loginBtn = qs("#login-btn");
    const signupBtn = qs("#signup-btn");
    const emailInput = qs("#auth-email");
    const pwInput = qs("#auth-password");

    if (loginBtn) {
      loginBtn.addEventListener("click", async () => {
        setAuthError("");
        const email = (emailInput?.value || "").trim();
        const pw = pwInput?.value || "";
        if (!email || !pw) {
          setAuthError("Email and password are required.");
          return;
        }
        try {
          await apiLogin(email, pw);
          await onAuthenticated();
        } catch (err) {
          setAuthError(err.message || "Login failed");
        }
      });
    }

    if (signupBtn) {
      signupBtn.addEventListener("click", async () => {
        setAuthError("");
        const email = (emailInput?.value || "").trim();
        const pw = pwInput?.value || "";
        if (!email || !pw) {
          setAuthError("Email and password are required.");
          return;
        }
        try {
          await apiSignup(email, pw);
          await onAuthenticated();
        } catch (err) {
          setAuthError(err.message || "Sign up failed");
        }
      });
    }
  }

  /* =====================================================================
     2. PLANNER DATA – COLLECT & APPLY
     ===================================================================== */
  function collectPlannerState() {
    const tasks = Array.from(
      document.querySelectorAll("#task-list .task-row")
    ).map(row => {
      const checkbox = row.querySelector("input[type='checkbox']");
      const select = row.querySelector("select");
      const descInput = row.querySelector(".task-desc input");

      return {
        checked: checkbox ? checkbox.checked : false,
        priority: select ? select.value : "A",
        description: descInput ? descInput.value : ""
      };
    });

    const appointments = Array.from(
      document.querySelectorAll(".appt-row")
    ).map(row => {
      const timeEl = row.querySelector(".appt-time");
      const input = row.querySelector(".appt-input");
      return {
        time: timeEl ? timeEl.textContent.trim() : "",
        text: input ? input.value : ""
      };
    });

    return {
      date: getActiveDate(),
      tasks,
      tracker: qs("#tracker")?.value || "",
      appointments,
      notes: qs("#notes")?.value || ""
    };
  }

  function applyPlannerState(data) {
    const tasks = Array.isArray(data.tasks) ? data.tasks : [];
    const appointments = Array.isArray(data.appointments) ? data.appointments : [];

    // TASKS
    const list = qs("#task-list");
    if (list) {
      list.innerHTML = "";

      if (tasks.length > 0) {
        tasks.forEach(t => {
          const row = document.createElement("div");
          row.className = "task-row";

          const safeDesc = (t.description || "")
            .replace(/&/g, "&amp;")
            .replace(/"/g, "&quot;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");

          row.innerHTML = `
            <input type="checkbox" ${t.checked ? "checked" : ""}>
            <select>
              <option ${t.priority === "A" ? "selected" : ""}>A</option>
              <option ${t.priority === "B" ? "selected" : ""}>B</option>
              <option ${t.priority === "C" ? "selected" : ""}>C</option>
            </select>
            <div class="task-desc">
              <input type="text" value="${safeDesc}">
            </div>
          `;
          list.appendChild(row);
        });
      }

      // If no tasks from DB, create 6 blank rows
      if (list.children.length === 0) {
        for (let i = 0; i < 6; i++) addBlankTask();
      }
    }

    // TRACKER
    const trackerEl = qs("#tracker");
    if (trackerEl) trackerEl.value = data.tracker || "";

    // APPOINTMENTS
    const apptRows = document.querySelectorAll(".appt-row");
    appointments.forEach((a, i) => {
      if (!apptRows[i]) return;
      const input = apptRows[i].querySelector(".appt-input");
      if (input) input.value = a.text || "";
    });

    // NOTES
    const notesEl = qs("#notes");
    if (notesEl) notesEl.value = data.notes || "";
  }

  /* =====================================================================
     3. SAVE / LOAD (with debounce)
     ===================================================================== */
  let saveTimer = null;

  function saveEntryDebounced() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveEntry, 700);
  }

  async function saveEntry() {
    const state = collectPlannerState();
    const date = state.date || new Date().toISOString().slice(0, 10);

    try {
      const res = await fetch(`/api/day/${date}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(state)
      });

      if (!res.ok) {
        // If unauthorized, kick back to login
        if (res.status === 401) {
          showAuthPanel(true);
        }
        console.error("Save failed", res.status, await res.text());
        return;
      }

      const json = await res.json().catch(() => ({}));
      if (json && (json.status === "ok" || json.status === "saved" || json.id)) {
        showSavedIndicator();
      } else {
        showSavedIndicator();
      }
    } catch (err) {
      console.error("Save error:", err);
    }
  }

  function showSavedIndicator() {
    let el = document.getElementById("saved-indicator");
    if (!el) {
      el = document.createElement("div");
      el.id = "saved-indicator";
      el.textContent = "Saved";
      Object.assign(el.style, {
        position: "fixed",
        bottom: "20px",
        right: "20px",
        background: "#003b3b",
        color: "#ffffff",
        padding: "6px 12px",
        borderRadius: "6px",
        fontSize: "0.8rem",
        opacity: "0",
        transition: "opacity 0.25s ease",
        zIndex: "9999"
      });
      document.body.appendChild(el);
    }
    el.style.opacity = "1";
    setTimeout(() => {
      el.style.opacity = "0";
    }, 1100);
  }

  async function loadEntry(dateStr) {
    const date = dateStr || getActiveDate();

    try {
      const res = await fetch(`/api/day/${date}`, {
        method: "GET",
        credentials: "include"
      });

      if (res.status === 401) {
        // Not logged in
        showAuthPanel(true);
        return;
      }

      if (!res.ok) {
        console.warn("No saved entry for", date, "status:", res.status);
        applyPlannerState({
          tasks: [],
          tracker: "",
          appointments: [],
          notes: ""
        });
        return;
      }

      const data = await res.json().catch(() => ({}));
      applyPlannerState(data || {});
    } catch (err) {
      console.error("Load error:", err);
      applyPlannerState({
        tasks: [],
        tracker: "",
        appointments: [],
        notes: ""
      });
    }
  }

  /* =====================================================================
     4. TASK ROWS
     ===================================================================== */
  function addBlankTask() {
    const list = qs("#task-list");
    if (!list) return;

    const row = document.createElement("div");
    row.className = "task-row";
    row.innerHTML = `
      <input type="checkbox">
      <select>
        <option>A</option>
        <option>B</option>
        <option>C</option>
      </select>
      <div class="task-desc">
        <input type="text">
      </div>
    `;
    list.appendChild(row);
  }

  /* =====================================================================
     5. DATE HEADER + MINI CALENDARS
     ===================================================================== */
  function updateHeader(dateStr) {
    if (!dateStr) return;
    const d = new Date(dateStr + "T00:00:00");

    const dayNumberEl = qs("#day-number");
    const weekdayEl = qs("#weekday");
    const monthYearEl = qs("#month-year");

    if (dayNumberEl) dayNumberEl.textContent = d.getDate();

    if (weekdayEl) {
      const names = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
      weekdayEl.textContent = names[d.getDay()];
    }

    if (monthYearEl) {
      monthYearEl.textContent = d.toLocaleString("default", {
        month: "long",
        year: "numeric"
      });
    }

    renderAllCalendars(d);
  }

  function renderMiniCalendar(containerId, year, month) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = "";

    const shownDate = new Date(year, month, 1);
    const shownYear = shownDate.getFullYear();
    const shownMonth = shownDate.getMonth();

    const title = document.createElement("div");
    title.className = "mini-cal-title";
    title.textContent = shownDate.toLocaleString("default", {
      month: "short",
      year: "numeric"
    });

    const grid = document.createElement("div");
    grid.className = "mini-cal-grid";

    const weekdays = ["S","M","T","W","T","F","S"];
    weekdays.forEach(d => {
      const cell = document.createElement("div");
      cell.className = "weekday-label";
      cell.textContent = d;
      grid.appendChild(cell);
    });

    const first = new Date(shownYear, shownMonth, 1);
    const last = new Date(shownYear, shownMonth + 1, 0);

    // leading blanks
    for (let i = 0; i < first.getDay(); i++) {
      grid.appendChild(document.createElement("div"));
    }

    // days
    for (let day = 1; day <= last.getDate(); day++) {
      const div = document.createElement("div");
      div.textContent = day;
      grid.appendChild(div);
    }

    container.appendChild(title);
    container.appendChild(grid);
  }

  function renderAllCalendars(d) {
    const y = d.getFullYear();
    const m = d.getMonth();

    renderMiniCalendar("mini-current", y, m);
    renderMiniCalendar("mini-prev", y, m - 1);
    renderMiniCalendar("mini-next", y, m + 1);
  }

  /* =====================================================================
     6. LAYOUT TOGGLES & PHONE VIEW
     ===================================================================== */
  function setupLayoutToggle() {
    const toggleBtn = qs("#toggleLayout");
    const spread = qs("#spread");
    if (!toggleBtn || !spread) return;

    if (toggleBtn._plannerHooked) return;
    toggleBtn._plannerHooked = true;

    toggleBtn.addEventListener("click", () => {
      const stacked = spread.classList.toggle("stacked");
      toggleBtn.textContent = stacked
        ? "Switch to Side-by-Side View"
        : "Switch to Stacked View";
    });
  }

  function setupPhoneViewToggle() {
    const phoneBtn = qs("#phoneViewBtn");
    const spread = qs("#spread");
    if (!phoneBtn || !spread) return;

    if (phoneBtn._plannerHooked) return;
    phoneBtn._plannerHooked = true;

    phoneBtn.addEventListener("click", () => {
      const body = document.body;
      const isPhone = body.classList.toggle("phone-view");
      phoneBtn.textContent = isPhone ? "Exit Phone View" : "Phone View";
      if (isPhone && spread) {
        spread.classList.add("stacked");
      }
    });

    // Auto-enable phone view on small screens initially
    if (window.innerWidth <= 768) {
      document.body.classList.add("phone-view");
      phoneBtn.textContent = "Exit Phone View";
      const spreadEl = qs("#spread");
      if (spreadEl) spreadEl.classList.add("stacked");
    }
  }

  /* =====================================================================
     7. EVENT WIRING & INIT
     ===================================================================== */
  function attachAutoSaveListeners() {
    if (document.body._plannerBound) return;
    document.body._plannerBound = true;

    document.body.addEventListener("input", saveEntryDebounced);
    document.body.addEventListener("change", saveEntryDebounced);
  }

  function onDateChange(e) {
    const date = e.target.value;
    if (!date) return;
    updateHeader(date);
    loadEntry(date);
  }

  let plannerInitialized = false;

  async function initPlanner(activeDate, initialData) {
    const dateInput = qs("#date-input");
    const addTaskBtn = qs("#add-task");

    // Initialize date to provided or today
    const today = new Date().toISOString().slice(0, 10);
    const dateToUse = activeDate || today;

    if (dateInput) {
      if (!dateInput.value) {
        dateInput.value = dateToUse;
      } else {
        // if value already set, keep it
      }
    }

    updateHeader(dateToUse);
    attachAutoSaveListeners();
    setupLayoutToggle();
    setupPhoneViewToggle();

    // Date change handler
    if (dateInput && !dateInput._plannerHooked) {
      dateInput.addEventListener("change", onDateChange);
      dateInput._plannerHooked = true;
    }

    // Add-task button
    if (addTaskBtn && !addTaskBtn._plannerHooked) {
      addTaskBtn.addEventListener("click", () => {
        addBlankTask();
        saveEntryDebounced();
      });
      addTaskBtn._plannerHooked = true;
    }

    // Ensure blank rows exist before loading
    const list = qs("#task-list");
    if (list && list.children.length === 0) {
      for (let i = 0; i < 6; i++) addBlankTask();
    }

    if (initialData) {
      applyPlannerState(initialData);
    } else {
      await loadEntry(dateToUse);
    }

    plannerInitialized = true;
  }

  async function onAuthenticated() {
    // Hide auth, show planner, then load today's data
    showAuthPanel(false);

    const today = new Date().toISOString().slice(0, 10);
    if (!plannerInitialized) {
      await initPlanner(today, null);
    } else {
      // If planner already initialized (e.g., user logged in after 401 during save),
      // just reload the current date.
      await loadEntry(getActiveDate());
    }
  }

  async function bootstrap() {
    wireAuthHandlers();

    // Try to auto-detect an existing session by probing today's day
    const today = new Date().toISOString().slice(0, 10);

    try {
      const res = await fetch(`/api/day/${today}`, {
        method: "GET",
        credentials: "include"
      });

      if (res.status === 401) {
        // Not logged in
        showAuthPanel(true);
        return;
      }

      if (!res.ok) {
        // Logged in but no data yet – still go to planner
        showAuthPanel(false);
        await initPlanner(today, {
          date: today,
          tasks: [],
          appointments: [],
          tracker: "",
          notes: ""
        });
        return;
      }

      const data = await res.json().catch(() => ({}));
      showAuthPanel(false);
      await initPlanner(today, data || {});
    } catch (err) {
      console.error("Bootstrap error:", err);
      showAuthPanel(true);
    }
  }

  document.addEventListener("DOMContentLoaded", bootstrap);

  /* =====================================================================
     8. Expose some helpers for console debugging if needed
     ===================================================================== */
  window._planner = {
    collectPlannerState,
    saveEntry,
    loadEntry,
    updateHeader,
    renderAllCalendars,
    addBlankTask
  };
})();
