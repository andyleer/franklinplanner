// planner.js
// Franklin-style daily planner front-end logic
// Backend endpoints:
//   POST /api/signup   {email, password}
//   POST /api/login    {email, password}
//   GET  /api/logout
//   GET  /api/day/<YYYY-MM-DD>
//   POST /api/day/<YYYY-MM-DD>

(function () {
  "use strict";

  /* =====================================================================
     0. SMALL HELPERS
     ===================================================================== */
  function todayString() {
    return new Date().toISOString().slice(0, 10);
  }

  function showToast(msg) {
    let el = document.getElementById("saved-indicator");
    if (!el) {
      el = document.createElement("div");
      el.id = "saved-indicator";
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
    el.textContent = msg;
    el.style.opacity = "1";
    setTimeout(() => { el.style.opacity = "0"; }, 1200);
  }

  async function apiFetch(path, options = {}) {
    const { method = "GET", body } = options;

    const fetchOptions = {
      method,
      credentials: "include", // IMPORTANT: send cookies for auth
      headers: {
        "Accept": "application/json"
      }
    };

    if (body !== undefined) {
      fetchOptions.headers["Content-Type"] = "application/json";
      fetchOptions.body = JSON.stringify(body);
    }

    const res = await fetch(path, fetchOptions);
    return res;
  }

  /* =====================================================================
     1. AUTH UI
     ===================================================================== */
  let currentEmail = null;

  function setAuthUI(loggedIn, email) {
    const loggedOutDiv = document.getElementById("auth-logged-out");
    const loggedInDiv = document.getElementById("auth-logged-in");
    const emailSpan = document.getElementById("auth-email-display");
    const statusSpan = document.getElementById("auth-status");

    if (loggedOutDiv && loggedInDiv) {
      if (loggedIn) {
        loggedOutDiv.style.display = "none";
        loggedInDiv.style.display = "flex";
        if (emailSpan) emailSpan.textContent = email || "";
        if (statusSpan) statusSpan.textContent = "";
      } else {
        loggedOutDiv.style.display = "flex";
        loggedInDiv.style.display = "none";
        if (statusSpan) statusSpan.textContent = "";
      }
    }
    currentEmail = loggedIn ? email : null;
  }

  async function handleSignup() {
    const emailInput = document.getElementById("auth-email");
    const passwordInput = document.getElementById("auth-password");
    if (!emailInput || !passwordInput) return;

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    if (!email || !password) {
      showToast("Email & password required");
      return;
    }

    try {
      const res = await apiFetch("/api/signup", {
        method: "POST",
        body: { email, password }
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        showToast(data.error || "Signup failed");
        return;
      }

      setAuthUI(true, email);
      showToast("Account created");
      // After signup, load today's data
      const activeDate = getActiveDate();
      updateHeader(activeDate);
      loadEntry(activeDate);
    } catch (err) {
      console.error("Signup error:", err);
      showToast("Signup error");
    }
  }

  async function handleLogin() {
    const emailInput = document.getElementById("auth-email");
    const passwordInput = document.getElementById("auth-password");
    if (!emailInput || !passwordInput) return;

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    if (!email || !password) {
      showToast("Email & password required");
      return;
    }

    try {
      const res = await apiFetch("/api/login", {
        method: "POST",
        body: { email, password }
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        showToast(data.error || "Login failed");
        return;
      }

      setAuthUI(true, email);
      showToast("Logged in");
      const activeDate = getActiveDate();
      updateHeader(activeDate);
      loadEntry(activeDate);
    } catch (err) {
      console.error("Login error:", err);
      showToast("Login error");
    }
  }

  async function handleLogout() {
    try {
      await apiFetch("/api/logout", { method: "GET" });
    } catch (err) {
      console.error("Logout error:", err);
    }
    setAuthUI(false, null);
    showToast("Logged out");
    // Clear planner UI
    applyPlannerState({
      tasks: [],
      tracker: "",
      appointments: [],
      notes: ""
    });
  }

  async function detectExistingSession() {
    // Simple check: try to load today's day; if 200, assume logged in
    const d = todayString();
    try {
      const res = await apiFetch(`/api/day/${d}`, { method: "GET" });
      if (res.status === 401) {
        setAuthUI(false, null);
        return;
      }
      if (res.ok) {
        // We don't know email from server, just mark as logged in.
        // User will see "Logged in" but not email unless they log in again.
        setAuthUI(true, currentEmail || "Session");
        const data = await res.json().catch(() => null);
        if (data && data.date) {
          // Use actual planner load later in initPlanner, this just sets auth state
        }
      } else {
        setAuthUI(false, null);
      }
    } catch (err) {
      console.error("Session check error:", err);
      setAuthUI(false, null);
    }
  }

  function initAuth() {
    const signupBtn = document.getElementById("auth-signup");
    const loginBtn = document.getElementById("auth-login");
    const logoutBtn = document.getElementById("auth-logout");

    if (signupBtn && !signupBtn._bound) {
      signupBtn.addEventListener("click", handleSignup);
      signupBtn._bound = true;
    }
    if (loginBtn && !loginBtn._bound) {
      loginBtn.addEventListener("click", handleLogin);
      loginBtn._bound = true;
    }
    if (logoutBtn && !logoutBtn._bound) {
      logoutBtn.addEventListener("click", handleLogout);
      logoutBtn._bound = true;
    }

    // Initial state: assume logged out, then probe
    setAuthUI(false, null);
    detectExistingSession();
  }

  /* =====================================================================
     2. DATE UTIL
     ===================================================================== */
  function getActiveDate() {
    const dateInput = document.getElementById("date-input");
    const today = todayString();
    if (!dateInput) return today;
    return dateInput.value || today;
  }

  /* =====================================================================
     3. COLLECT + APPLY STATE
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
      tracker: document.getElementById("tracker")?.value || "",
      appointments,
      notes: document.getElementById("notes")?.value || ""
    };
  }

  function applyPlannerState(data) {
    const tasks = Array.isArray(data.tasks) ? data.tasks : [];
    const appointments = Array.isArray(data.appointments) ? data.appointments : [];

    // ----- Tasks -----
    const list = document.getElementById("task-list");
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

      if (list.children.length === 0) {
        for (let i = 0; i < 6; i++) addBlankTask();
      }
    }

    // ----- Tracker -----
    const trackerEl = document.getElementById("tracker");
    if (trackerEl) trackerEl.value = data.tracker || "";

    // ----- Appointments -----
    const apptRows = document.querySelectorAll(".appt-row");
    appointments.forEach((a, i) => {
      if (!apptRows[i]) return;
      const input = apptRows[i].querySelector(".appt-input");
      if (input) input.value = a.text || "";
    });

    // ----- Notes -----
    const notesEl = document.getElementById("notes");
    if (notesEl) notesEl.value = data.notes || "";
  }

  /* =====================================================================
     4. SAVE (with debounce)
     ===================================================================== */
  let saveTimer = null;

  function saveEntryDebounced() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveEntry, 700);
  }

  async function saveEntry() {
    const state = collectPlannerState();
    const date = state.date || todayString();

    try {
      const res = await apiFetch(`/api/day/${date}`, {
        method: "POST",
        body: state
      });

      if (res.status === 401) {
        showToast("Please log in to save");
        setAuthUI(false, null);
        return;
      }

      if (!res.ok) {
        console.error("Save failed", res.status, await res.text());
        showToast("Save failed");
        return;
      }

      const json = await res.json().catch(() => ({}));
      if (json && (json.status === "ok" || json.status === "saved")) {
        showToast("Saved");
      } else {
        showToast("Saved");
      }
    } catch (err) {
      console.error("Save error:", err);
      showToast("Save error");
    }
  }

  /* =====================================================================
     5. LOAD
     ===================================================================== */
  async function loadEntry(dateStr) {
    const date = dateStr || getActiveDate();

    try {
      const res = await apiFetch(`/api/day/${date}`, { method: "GET" });

      if (res.status === 401) {
        console.warn("Not logged in when loading day");
        setAuthUI(false, null);
        applyPlannerState({
          tasks: [],
          tracker: "",
          appointments: [],
          notes: ""
        });
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
     6. TASK ROWS
     ===================================================================== */
  function addBlankTask() {
    const list = document.getElementById("task-list");
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
     7. DATE HEADER + MINI CALENDARS
     ===================================================================== */
  function updateHeader(dateStr) {
    if (!dateStr) return;
    const d = new Date(dateStr + "T00:00:00");

    const dayNumberEl = document.getElementById("day-number");
    const weekdayEl = document.getElementById("weekday");
    const monthYearEl = document.getElementById("month-year");

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

    for (let i = 0; i < first.getDay(); i++) {
      grid.appendChild(document.createElement("div"));
    }

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
     8. LAYOUT TOGGLES
     ===================================================================== */
  function setupLayoutToggle() {
    const toggleBtn = document.getElementById("toggleLayout");
    const spread = document.getElementById("spread");
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
    const phoneBtn = document.getElementById("phoneViewBtn");
    const spread = document.getElementById("spread");
    if (!phoneBtn) return;

    if (phoneBtn._plannerHooked) return;
    phoneBtn._plannerHooked = true;

    // Auto-enable on small screens
    if (window.innerWidth <= 768) {
      document.body.classList.add("phone-view");
      if (spread) spread.classList.add("stacked");
      phoneBtn.textContent = "Exit Phone View";
    }

    phoneBtn.addEventListener("click", () => {
      const body = document.body;
      const isPhone = body.classList.toggle("phone-view");

      phoneBtn.textContent = isPhone ? "Exit Phone View" : "Phone View";

      if (spread && isPhone) {
        spread.classList.add("stacked");
      }
    });
  }

  /* =====================================================================
     9. EVENT WIRING & INIT
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

  function initPlanner() {
    const dateInput = document.getElementById("date-input");
    const addTaskBtn = document.getElementById("add-task");

    const today = todayString();
    let activeDate = today;
    if (dateInput) {
      if (!dateInput.value) {
        dateInput.value = today;
      }
      activeDate = dateInput.value;
    }

    updateHeader(activeDate);
    attachAutoSaveListeners();
    setupLayoutToggle();
    setupPhoneViewToggle();

    if (dateInput && !dateInput._plannerHooked) {
      dateInput.addEventListener("change", onDateChange);
      dateInput._plannerHooked = true;
    }

    if (addTaskBtn && !addTaskBtn._plannerHooked) {
      addTaskBtn.addEventListener("click", () => {
        addBlankTask();
        saveEntryDebounced();
      });
      addTaskBtn._plannerHooked = true;
    }

    const list = document.getElementById("task-list");
    if (list && list.children.length === 0) {
      for (let i = 0; i < 6; i++) addBlankTask();
    }

    // Finally load data for the active date
    loadEntry(activeDate);
  }

  document.addEventListener("DOMContentLoaded", () => {
    initAuth();
    initPlanner();
  });

  /* =====================================================================
     10. Expose for debugging (optional)
     ===================================================================== */
  window.collectPlannerState = collectPlannerState;
  window.saveEntryDebounced = saveEntryDebounced;
  window.saveEntry = saveEntry;
  window.loadEntry = loadEntry;
  window.addBlankTask = addBlankTask;
  window.updateHeader = updateHeader;
  window.renderAllCalendars = renderAllCalendars;
})();
