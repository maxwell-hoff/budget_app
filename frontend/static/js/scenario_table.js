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

    function renderTable(rows, goalParam) {
        const container = document.getElementById(containerId);
        container.innerHTML = '';

        if (!rows.length) {
            container.textContent = 'No data available.';
            return;
        }

        const table = document.createElement('table');
        table.className = 'table table-sm table-bordered';

        // Header
        const thead = document.createElement('thead');
        const hr = document.createElement('tr');
        ['Scenario', 'Sub-Scenario', 'Milestone', 'Scenario Param', 'Scenario Value', `Solved ${goalParam}`]
            .forEach(text => {
                const th = document.createElement('th');
                th.textContent = text;
                hr.appendChild(th);
            });
        thead.appendChild(hr);
        table.appendChild(thead);

        // Body
        const tbody = document.createElement('tbody');
        rows.forEach(r => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${r.scenario_id}</td>
                <td>${r.sub_scenario_id}</td>
                <td>${r.milestone_id}</td>
                <td>${r.scenario_parameter}</td>
                <td>${r.scenario_value}</td>
                <td>${Number(r.solved_value).toLocaleString()}</td>`;
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        container.appendChild(table);
    }

    // Auto-init on DOMContentLoaded
    document.addEventListener('DOMContentLoaded', init);
})(); 