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

    // Remember last *clicked* scenario's line so hover previews can temporarily
    // override it and then revert on mouse leave.
    let lastClickedLineData = null;

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
        // paramValues = { param: [val1,val2,...] }
        const paramValues = {};
        rows.forEach(r => {
            if (!paramValues[r.scenario_parameter]) paramValues[r.scenario_parameter] = new Set();
            paramValues[r.scenario_parameter].add(r.scenario_value);
        });

        // convert sets to sorted arrays
        Object.keys(paramValues).forEach(p => {
            paramValues[p] = Array.from(paramValues[p]).sort((a,b)=>a-b);
        });

        const paramOrder = Object.keys(paramValues).sort();

        // Group by row key
        const keyFn = r => `${r.scenario}|${r.sub_scenario}|${r.milestone}`;
        const groups = {};
        rows.forEach(r => {
            const k = keyFn(r);
            if (!groups[k]) {
                groups[k] = { scenario: r.scenario, sub_scenario: r.sub_scenario, milestone: r.milestone, data: {} };
            }
            const rowData = groups[k].data;
            if (!rowData[r.scenario_parameter]) rowData[r.scenario_parameter] = {};
            rowData[r.scenario_parameter][r.scenario_value] = r.solved_value;
        });

        return {paramValues, paramOrder, grouped: Object.values(groups)};
    }

    function renderTable(rows, goalParam) {
        const container = document.getElementById(containerId);
        container.innerHTML = '';

        if (!rows.length) {
            container.textContent = 'No data available.';
            return;
        }

        const {paramValues, paramOrder, grouped} = groupRows(rows);

        const totalValueCols = paramOrder.reduce((acc,p)=>acc+paramValues[p].length,0);

        const table = document.createElement('table');
        table.className = 'table table-sm table-bordered';
        table.style.minWidth = `${150 + totalValueCols*120}px`;

        // Make container scrollable
        container.style.overflowX = 'auto';

        const thead = document.createElement('thead');

        // Row 1: parameter group labels
        const r1 = document.createElement('tr');
        ['Scenario','Sub-Scenario','Milestone'].forEach(text=>{
            const th=document.createElement('th'); th.textContent=text; th.rowSpan=2; r1.appendChild(th);
        });
        paramOrder.forEach(p=>{
            const th=document.createElement('th');
            th.textContent=p; th.colSpan=paramValues[p].length; r1.appendChild(th);
        });
        thead.appendChild(r1);

        // Row 2: individual values
        const r2=document.createElement('tr');
        paramOrder.forEach(p=>{
            paramValues[p].forEach(val=>{
                const th=document.createElement('th'); th.textContent=val; r2.appendChild(th);
            });
        });
        thead.appendChild(r2);

        table.appendChild(thead);

        const tbody = document.createElement('tbody');
        grouped.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `<td>${row.scenario}</td><td>${row.sub_scenario}</td><td>${row.milestone}</td>`;
            const scenarioName = row.scenario;
            const subScenarioName = row.sub_scenario;

            paramOrder.forEach(p=>{
                const vals=paramValues[p];
                vals.forEach(v=>{
                    const solved = (row.data[p] && row.data[p][v]!==undefined)? Number(row.data[p][v]).toLocaleString():'';
                    const td = document.createElement('td');
                    td.textContent = solved;
                    td.dataset.param = p;
                    td.dataset.value = v;
                    // Hover preview for parameter cell
                    td.addEventListener('mouseenter', () => {
                        fetch(`/api/net-worth-line?scenario=${encodeURIComponent(scenarioName)}&sub_scenario=${encodeURIComponent(subScenarioName)}&scenario_parameter=${encodeURIComponent(p)}&scenario_value=${encodeURIComponent(v)}`)
                            .then(r => r.json())
                            .then(lineData => {
                                if (window.netWorthChart && typeof window.netWorthChart.setLineData === 'function') {
                                    window.netWorthChart.setLineData(lineData);
                                }
                            })
                            .catch(err => console.error('Error fetching param preview line', err));
                    });
                    td.addEventListener('mouseleave', () => {
                        if (lastClickedLineData && window.netWorthChart && typeof window.netWorthChart.setLineData === 'function') {
                            window.netWorthChart.setLineData(lastClickedLineData);
                        }
                    });
                    tr.appendChild(td);
                });
            });
            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        container.appendChild(table);

        // Attach click handler to body rows to update Net Worth chart
        tbody.addEventListener('click', (ev) => {
            const cell = ev.target.closest('td');
            const tr = ev.target.closest('tr');
            if (!tr || !cell) return;

            // Extract scenario / sub-scenario
            const cells = tr.querySelectorAll('td');
            if (cells.length < 2) return;
            const scenarioName = cells[0].textContent.trim();
            const subScenarioName = cells[1].textContent.trim();

            // Detect if a parameter cell was clicked
            const param = cell.dataset.param;
            const value = cell.dataset.value;

            let url = `/api/net-worth-line?scenario=${encodeURIComponent(scenarioName)}&sub_scenario=${encodeURIComponent(subScenarioName)}`;
            if (param && value) {
                url += `&scenario_parameter=${encodeURIComponent(param)}&scenario_value=${encodeURIComponent(value)}`;
            }

            fetch(url)
                .then(r => r.json())
                .then(lineData => {
                    if (window.netWorthChart && typeof window.netWorthChart.setLineData === 'function') {
                        window.netWorthChart.setLineData(lineData);
                        // Persist this exact selection (including parameter filter) so hover-out reverts correctly
                        lastClickedLineData = lineData;
                    }
                })
                .catch(err => console.error('Error fetching scenario net-worth line', err));
        });

        // Add mouseleave on entire table to revert when exiting the table altogether
        table.addEventListener('mouseleave', () => {
            if (lastClickedLineData && window.netWorthChart && typeof window.netWorthChart.setLineData === 'function') {
                window.netWorthChart.setLineData(lastClickedLineData);
            }
        });
    }

    // Auto-init on DOMContentLoaded
    document.addEventListener('DOMContentLoaded', init);
})(); 