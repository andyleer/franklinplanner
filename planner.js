// planner.js
// Franklin-style planner client-side logic (now with login + per-user data)

(function () {
    "use strict";

    /* -------------------------------------------------------------
       1. LOGIN HANDLING
    ------------------------------------------------------------- */

    async function checkLogin() {
        try {
            const res = await fetch("/me");
            if (!res.ok) return showLoginScreen();

            const user = await res.json();
            if (!user || !user.username) return showLoginScreen();

            document.getElementById("login-container").style.display = "none";
            document.getElementById("app-container").style.display = "block";
            return initPlanner();
        } catch (err) {
            console.error("Login check failed:", err);
            showLoginScreen();
        }
    }

    function showLoginScreen() {
        document.getElementById("login-container").style.display = "block";
        document.getElementById("app-container").style.display = "none";
    }

    async function handleLogin(e) {
        e.preventDefault();

        const username = document.getElementById("login-username").value.trim();
        const password = document.getElementById("login-password").value.trim();

        const res = await fetch("/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password })
        });

        if (res.ok) {
            checkLogin();
        } else {
            alert("Login failed. Check username/password.");
        }
    }

    async function handleLogout() {
        await fetch("/logout", { method: "POST" });
        showLoginScreen();
    }

    /* -------------------------------------------------------------
       2. UTIL – Get active date
    ------------------------------------------------------------- */
    function getActiveDate() {
        const dateInput = document.getElementById("date-input");
        const today = new Date().toISOString().slice(0, 10);
        if (!dateInput) return today;
        return dateInput.value || today;
    }

    /* -------------------------------------------------------------
       3. COLLECT + APPLY STATE
    ------------------------------------------------------------- */
    function collectPlannerState() {
        const tasks = Array.from(
            document.querySelectorAll("#task-list .task-row")
        ).map(row => ({
            checked: row.querySelector("input[type='checkbox']").checked,
            priority: row.querySelector("select").value,
            description: row.querySelector(".task-desc input").value
        }));

        const appointments = Array.from(
            document.querySelectorAll(".appt-row")
        ).map(row => ({
            time: row.querySelector(".appt-time").textContent.trim(),
            text: row.querySelector(".appt-input").value
        }));

        return {
            date: getActiveDate(),
            tasks,
            tracker: document.getElementById("tracker").value || "",
            appointments,
            notes: document.getElementById("notes").value || ""
        };
    }

    function applyPlannerState(data) {
        /* ----- TASKS ----- */
        const list = document.getElementById("task-list");
        list.innerHTML = "";

        const tasks = data.tasks ?? [];
        if (tasks.length === 0) {
            for (let i = 0; i < 6; i++) addBlankTask();
        } else {
            tasks.forEach(t => {
                const row = document.createElement("div");
                row.className = "task-row";
                const safe = (t.description || "")
                    .replace(/&/g,"&amp;")
                    .replace(/</g,"&lt;")
                    .replace(/>/g,"&gt;")
                    .replace(/"/g,"&quot;");
                row.innerHTML = `
                    <input type="checkbox" ${t.checked ? "checked" : ""}>
                    <select>
                        <option ${t.priority === "A" ? "selected":""}>A</option>
                        <option ${t.priority === "B" ? "selected":""}>B</option>
                        <option ${t.priority === "C" ? "selected":""}>C</option>
                    </select>
                    <div class="task-desc"><input type="text" value="${safe}"></div>
                `;
                list.appendChild(row);
            });
        }

        /* ----- TRACKER ----- */
        document.getElementById("tracker").value = data.tracker || "";

        /* ----- APPOINTMENTS ----- */
        const apptRows = document.querySelectorAll(".appt-row");
        (data.appointments ?? []).forEach((a, i) => {
            if (!apptRows[i]) return;
            apptRows[i].querySelector(".appt-input").value = a.text || "";
        });

        /* ----- NOTES ----- */
        document.getElementById("notes").value = data.notes || "";
    }

    /* -------------------------------------------------------------
       4. SAVE (debounced)
    ------------------------------------------------------------- */
    let saveTimer = null;

    function saveEntryDebounced() {
        clearTimeout(saveTimer);
        saveTimer = setTimeout(saveEntry, 600);
    }

    async function saveEntry() {
        const state = collectPlannerState();
        const date = state.date;

        try {
            const res = await fetch(`/api/day/${date}`, {
                method: "POST",
                headers: { "Content-Type":"application/json" },
                body: JSON.stringify(state)
            });

            if (res.ok) showSavedIndicator();
        } catch (err) {
            console.error("SAVE ERROR:",err);
        }
    }

    function showSavedIndicator() {
        let el = document.getElementById("saved-indicator");
        if (!el) {
            el = document.createElement("div");
            el.id = "saved-indicator";
            el.textContent = "Saved";
            Object.assign(el.style,{
                position:"fixed", bottom:"20px", right:"20px",
                padding:"6px 12px", background:"#003b3b",
                color:"#fff", borderRadius:"6px",
                transition:"opacity .3s", opacity:"0"
            });
            document.body.appendChild(el);
        }
        el.style.opacity = "1";
        setTimeout(()=> el.style.opacity="0",1000);
    }

    /* -------------------------------------------------------------
       5. LOAD ENTRY
    ------------------------------------------------------------- */
    async function loadEntry(dateStr) {
        const date = dateStr || getActiveDate();
        try {
            const res = await fetch(`/api/day/${date}`);
            const data = res.ok ? await res.json() : {};
            applyPlannerState(data);
        } catch (err) {
            console.error("Load error:", err);
            applyPlannerState({});
        }
    }

    /* -------------------------------------------------------------
       6. TASK ADDING
    ------------------------------------------------------------- */
    function addBlankTask() {
        const list = document.getElementById("task-list");
        const row = document.createElement("div");
        row.className = "task-row";
        row.innerHTML = `
            <input type="checkbox">
            <select><option>A</option><option>B</option><option>C</option></select>
            <div class="task-desc"><input type="text"></div>
        `;
        list.appendChild(row);
    }

    /* -------------------------------------------------------------
       7. CALENDAR RENDERING
    ------------------------------------------------------------- */
    function updateHeader(dateStr) {
        const d = new Date(dateStr + "T00:00:00");

        document.getElementById("day-number").textContent = d.getDate();

        const weekdays = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
        document.getElementById("weekday").textContent = weekdays[d.getDay()];

        document.getElementById("month-year").textContent =
            d.toLocaleString("default",{ month:"long", year:"numeric" });

        renderAllCalendars(d);
    }

    function renderMiniCalendar(containerId, year, month) {
        const c = document.getElementById(containerId);
        if (!c) return;

        c.innerHTML = "";
        const date = new Date(year,month,1);
        const title = document.createElement("div");
        title.className = "mini-cal-title";
        title.textContent = date.toLocaleString("default",{month:"short",year:"numeric"});

        const grid = document.createElement("div");
        grid.className = "mini-cal-grid";

        ["S","M","T","W","T","F","S"].forEach(d=>{
            const lbl=document.createElement("div");
            lbl.className="weekday-label";
            lbl.textContent=d;
            grid.appendChild(lbl);
        });

        const first = new Date(date.getFullYear(), date.getMonth(), 1);
        const last  = new Date(date.getFullYear(), date.getMonth()+1, 0);

        for (let i=0;i<first.getDay();i++) grid.appendChild(document.createElement("div"));

        for (let i=1;i<=last.getDate();i++){
            const dayCell=document.createElement("div");
            dayCell.textContent=i;
            grid.appendChild(dayCell);
        }

        c.appendChild(title);
        c.appendChild(grid);
    }

    function renderAllCalendars(d) {
        const y = d.getFullYear();
        const m = d.getMonth();
        renderMiniCalendar("mini-current",y,m);
        renderMiniCalendar("mini-prev",y,m-1);
        renderMiniCalendar("mini-next",y,m+1);
    }

    /* -------------------------------------------------------------
       8. PHONE VIEW MODE (auto detect)
    ------------------------------------------------------------- */
    function autoDetectPhone() {
        if (window.innerWidth < 720) {
            document.body.classList.add("phone-view");
            const spread=document.getElementById("spread");
            spread.classList.add("stacked");
        }
    }

    function setupPhoneButton() {
        const btn = document.getElementById("phoneViewBtn");
        btn.addEventListener("click", () => {
            const now = document.body.classList.toggle("phone-view");
            btn.textContent = now ? "Exit Phone View" : "Phone View";
            if (now) document.getElementById("spread").classList.add("stacked");
        });
    }

    /* -------------------------------------------------------------
       9. INIT PLANNER
    ------------------------------------------------------------- */
    function initPlanner() {
        autoDetectPhone();
        setupPhoneButton();

        const dateInput = document.getElementById("date-input");
        const today = new Date().toISOString().slice(0,10);
        if (!dateInput.value) dateInput.value = today;

        dateInput.addEventListener("change", e => {
            updateHeader(e.target.value);
            loadEntry(e.target.value);
        });

        updateHeader(dateInput.value);
        loadEntry(dateInput.value);

        document.body.addEventListener("input", saveEntryDebounced);
        document.body.addEventListener("change", saveEntryDebounced);
        document.getElementById("add-task").addEventListener("click",()=>{addBlankTask();saveEntryDebounced();});
    }

    /* -------------------------------------------------------------
       10. INITIALIZE APP
    ------------------------------------------------------------- */
    document.addEventListener("DOMContentLoaded", () => {
        document.getElementById("login-form").addEventListener("submit", handleLogin);
        document.getElementById("logoutBtn").addEventListener("click", handleLogout);
        checkLogin();
    });

})();
