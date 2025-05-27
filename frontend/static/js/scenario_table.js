/*
 * Scenario Table Module (first pass)
 * ----------------------------------
 * Loads available goal parameters, renders dropdown, fetches solved values and
 * draws a simple <table> (one row per milestone ▸ scenario_parameter ▸ value).
 * Real pivoting will be added later or by integrating Tabulator/DataTables.
 */

(function () {
    const dropdownId = 'goalDropdown';
    const containerId = 'scenarioTableContainer';

    function init() {
        const container = document.getElementById(containerId);
        if (!container) return; // section may be hidden/removed

        fetchGoals().then(goals => {
            buildDropdown(goals);
            if (goals.length) {
                loadTable(goals[0]);
            }
        });
    }

    function buildDropdown(goals) {
        const select = document.getElementById(dropdownId);
        select.innerHTML = '';
        goals.forEach(g => {
            const opt = document.createElement('option');
            opt.value = g;
            opt.textContent = g;
            select.appendChild(opt);
        });
        select.addEventListener('change', ev => loadTable(ev.target.value));
    }

    function fetchGoals() {
        return fetch('/api/goals').then(r => r.json());
    }

    function loadTable(goalParam) {
        fetch(`/api/scenario-table?goal=${encodeURIComponent(goalParam)}`)
            .then(r => r.json())
            .then(rows => renderTable(rows, goalParam));
    }

    function groupRows(rows) {
        // Build list of unique scenario values (columns)
        const uniqueValues = [...new Set(rows.map(r => r.scenario_value))].sort((a,b)=>a-b);

        // Group by composite key
        const keyFn = r => `${r.scenario}|${r.sub_scenario}|${r.milestone}`;
        const groups = {};
        rows.forEach(r => {
            const k = keyFn(r);
            if (!groups[k]) {
                groups[k] = { scenario: r.scenario, sub_scenario: r.sub_scenario, milestone: r.milestone };
            }
            groups[k][r.scenario_value] = r.solved_value;
        });
        return {uniqueValues, grouped: Object.values(groups)};
    }

    function renderTable(rows, goalParam) {
        const container = document.getElementById(containerId);
        container.innerHTML = '';

        if (!rows.length) {
            container.textContent = 'No data available.';
            return;
        }

        const {uniqueValues, grouped} = groupRows(rows);

        const table = document.createElement('table');
        table.className = 'table table-sm table-bordered';
        table.style.minWidth = `${150 + uniqueValues.length*120}px`;

        // Make container scrollable
        container.style.overflowX = 'auto';

        const thead = document.createElement('thead');
        const hr = document.createElement('tr');
        ['Scenario', 'Sub-Scenario', 'Milestone', ...uniqueValues.map(v => `${v}`)].forEach(text => {
            const th = document.createElement('th');
            th.textContent = text;
            hr.appendChild(th);
        });
        thead.appendChild(hr);
        table.appendChild(thead);

        const tbody = document.createElement('tbody');
        grouped.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${row.scenario}</td>
                <td>${row.sub_scenario}</td>
                <td>${row.milestone}</td>`;
            uniqueValues.forEach(val => {
                const cellVal = row[val] !== undefined ? Number(row[val]).toLocaleString() : '';
                tr.innerHTML += `<td>${cellVal}</td>`;
            });
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        container.appendChild(table);
    }

    // Auto-init on DOMContentLoaded
    document.addEventListener('DOMContentLoaded', init);
})(); 