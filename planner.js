// planner.js
// Franklin-style daily planner front-end logic
// Backend endpoints:
//   GET  /api/day/<YYYY-MM-DD>
//   POST /api/day/<YYYY-MM-DD>

(function () {
    "use strict";

    /* =====================================================================
       1. UTIL – Get active date (YYYY-MM-DD)
       ===================================================================== */
    function getActiveDate() {
        const dateInput = document.getElementById("date-input");
        const today = new Date().toISOString().slice(0, 10);
        if (!dateInput) return today;
        return dateInput.value || today;
    }

    /* =====================================================================
       2. COLLECT + APPLY STATE
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

            // If nothing in DB, or tasks array empty, create 6 blank rows
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
       3. SAVE (with debounce) – uses /api/day/<date>
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
                body: JSON.stringify(state)
            });

            if (!res.ok) {
                console.error("Save failed", res.status, await res.text());
                return;
            }

            const json = await res.json();
            if (json && (json.status === "ok" || json.status === "saved" || json.id)) {
                showSavedIndicator();
            } else {
                // still show: POST succeeded
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

    /* =====================================================================
       4. LOAD – uses /api/day/<date>
       ===================================================================== */
    async function loadEntry(dateStr) {
        const date = dateStr || getActiveDate();

        try {
            const res = await fetch(`/api/day/${date}`);
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

            const data = await res.json() || {};
            applyPlannerState(data);
        } catch (err) {
            console.error("Load error:", err);
            // fall back to empty
            applyPlannerState({
                tasks: [],
                tracker: "",
                appointments: [],
                notes: ""
            });
        }
    }

    /* =====================================================================
       5. TASK ROWS
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
       6. DATE HEADER + MINI CALENDARS
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

        // Let JS normalize months like m-1, m+1
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

    function setupLayoutToggle() {
        const toggleBtn = document.getElementById("toggleLayout");
        const spread = document.getElementById("spread");
        if (!toggleBtn || !spread) return;

        toggleBtn.addEventListener("click", () => {
            const stacked = spread.classList.toggle("stacked");
            toggleBtn.textContent = stacked
                ? "Switch to Side-by-Side View"
                : "Switch to Stacked View";
        });
    }

    function initPlanner() {
        const dateInput = document.getElementById("date-input");
        const addTaskBtn = document.getElementById("add-task");

        // Initialize date to today if empty
        const today = new Date().toISOString().slice(0, 10);
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

        // Start with blanks before we know if server has data
        const list = document.getElementById("task-list");
        if (list && list.children.length === 0) {
            for (let i = 0; i < 6; i++) addBlankTask();
        }

        // Finally, load from server (will overwrite blanks if data exists)
        loadEntry(activeDate);
    }

    document.addEventListener("DOMContentLoaded", initPlanner);

    /* =====================================================================
       8. OPTIONAL: expose a few functions on window (for debugging)
       ===================================================================== */
    window.collectPlannerState = collectPlannerState;
    window.saveEntryDebounced = saveEntryDebounced;
    window.saveEntry = saveEntry;
    window.loadEntry = loadEntry;
    window.addBlankTask = addBlankTask;
    window.updateHeader = updateHeader;
    window.renderAllCalendars = renderAllCalendars;
})();
