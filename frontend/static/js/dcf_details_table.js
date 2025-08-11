/*
 * DCF Details Table Module
 * ------------------------
 * Displays detailed DCF values by age for the selected scenario.
 * Updates when user hovers or clicks on scenario table cells.
 */

(function () {
    const tableBodyId = 'dcf-details-tbody';
    const scenarioInfoId = 'dcf-details-scenario';
    
    let currentScenarioData = null;

    function init() {
        // Initialize the table as empty
        updateTable(null);
    }

    function formatCurrency(value) {
        if (value === null || value === undefined || isNaN(value)) {
            return '$0';
        }
        
        // Format as currency with appropriate sign
        const absValue = Math.abs(value);
        let formatted;
        
        if (absValue >= 1000000) {
            formatted = `$${(absValue / 1000000).toFixed(1)}M`;
        } else if (absValue >= 1000) {
            formatted = `$${(absValue / 1000).toFixed(0)}K`;
        } else {
            formatted = `$${absValue.toFixed(0)}`;
        }
        
        return value < 0 ? `-${formatted}` : formatted;
    }

    function getValueClass(value) {
        if (value === null || value === undefined || isNaN(value)) {
            return 'dcf-zero';
        }
        
        if (value > 0) {
            return 'dcf-positive';
        } else if (value < 0) {
            return 'dcf-negative';
        } else {
            return 'dcf-zero';
        }
    }

    function calculateDerivedValues(dcfRow) {
        // Calculate Net Worth: Beginning Assets - Beginning Liabilities
        const netWorth = dcfRow.beginning_assets - dcfRow.beginning_liabilities;
        
        // Calculate Cash Flow: Salary + Assets Income - Expenses - Liabilities Expense
        const cashFlow = dcfRow.salary + dcfRow.assets_income - dcfRow.expenses - dcfRow.liabilities_expense;
        
        return { netWorth, cashFlow };
    }

    function updateTable(dcfData) {
        const tbody = document.getElementById(tableBodyId);
        const scenarioInfo = document.getElementById(scenarioInfoId);
        
        if (!tbody || !scenarioInfo) {
            console.error('DCF details table elements not found');
            return;
        }

        // Clear existing rows
        tbody.innerHTML = '';

        if (!dcfData || !Array.isArray(dcfData) || dcfData.length === 0) {
            // Show empty state
            const emptyRow = document.createElement('tr');
            emptyRow.innerHTML = `
                <td colspan="9" class="text-center text-muted">
                    Select a scenario from the table above to view DCF details
                </td>
            `;
            tbody.appendChild(emptyRow);
            scenarioInfo.textContent = 'Select a scenario to view details';
            currentScenarioData = null;
            return;
        }

        // Update scenario info
        const firstRow = dcfData[0];
        const scenarioText = `${firstRow.scenario || 'Unknown'} - ${firstRow.sub_scenario || 'Unknown'} (${firstRow.scenario_parameter}: ${firstRow.scenario_value})`;
        scenarioInfo.textContent = scenarioText;

        // Sort by age to ensure proper order
        const sortedData = [...dcfData].sort((a, b) => a.age - b.age);

        // Create table rows
        sortedData.forEach(row => {
            const { netWorth, cashFlow } = calculateDerivedValues(row);
            
            const tr = document.createElement('tr');
            tr.classList.add('dcf-main-row');
            tr.dataset.age = row.age;
            
            // Age column (no color highlighting)
            const ageCell = document.createElement('td');
            ageCell.textContent = row.age;
            tr.appendChild(ageCell);

            // Beginning Assets
            const assetsCell = document.createElement('td');
            assetsCell.textContent = formatCurrency(row.beginning_assets);
            assetsCell.className = getValueClass(row.beginning_assets);
            tr.appendChild(assetsCell);

            // Assets Income
            const assetsIncomeCell = document.createElement('td');
            assetsIncomeCell.textContent = formatCurrency(row.assets_income);
            assetsIncomeCell.className = getValueClass(row.assets_income);
            tr.appendChild(assetsIncomeCell);

            // Beginning Liabilities
            const liabilitiesCell = document.createElement('td');
            liabilitiesCell.textContent = formatCurrency(row.beginning_liabilities);
            liabilitiesCell.className = getValueClass(row.beginning_liabilities);
            tr.appendChild(liabilitiesCell);

            // Liabilities Expense
            const liabilitiesExpenseCell = document.createElement('td');
            liabilitiesExpenseCell.textContent = formatCurrency(row.liabilities_expense);
            liabilitiesExpenseCell.className = getValueClass(row.liabilities_expense);
            tr.appendChild(liabilitiesExpenseCell);

            // Salary
            const salaryCell = document.createElement('td');
            salaryCell.textContent = formatCurrency(row.salary);
            salaryCell.className = getValueClass(row.salary);
            tr.appendChild(salaryCell);

            // Expenses
            const expensesCell = document.createElement('td');
            expensesCell.textContent = formatCurrency(row.expenses);
            expensesCell.className = getValueClass(row.expenses);
            tr.appendChild(expensesCell);

            // Net Worth (calculated)
            const netWorthCell = document.createElement('td');
            netWorthCell.textContent = formatCurrency(netWorth);
            netWorthCell.className = getValueClass(netWorth);
            netWorthCell.style.fontWeight = '600'; // Emphasize calculated values
            tr.appendChild(netWorthCell);

            // Cash Flow (calculated)
            const cashFlowCell = document.createElement('td');
            cashFlowCell.textContent = formatCurrency(cashFlow);
            cashFlowCell.className = getValueClass(cashFlow);
            cashFlowCell.style.fontWeight = '600'; // Emphasize calculated values
            tr.appendChild(cashFlowCell);

            tbody.appendChild(tr);

        });

        currentScenarioData = dcfData;
    }

    // Add column-expansion toggles for Salary and Expenses headers
    function enableColumnExpansion(goalParam, scenarioParameter, scenarioValue, scenarioName, subScenarioName) {
        const table = document.getElementById('dcf-details-table');
        if (!table) return;
        const headerCells = Array.from(table.querySelectorAll('thead th'));
        const labels = headerCells.map(th => th.textContent.trim());

        const salaryIdx = labels.indexOf('Salary');
        const expensesIdx = labels.indexOf('Expenses');
        const targets = [
            { idx: salaryIdx, key: 'salary', label: 'Salary' },
            { idx: expensesIdx, key: 'expenses', label: 'Expenses' },
        ].filter(t => t.idx >= 0);

        targets.forEach(target => {
            const th = headerCells[target.idx];
            if (!th || th.dataset.expandBound === '1') return;
            th.dataset.expandBound = '1';

            // Insert a toggle icon
            const toggle = document.createElement('button');
            toggle.className = 'btn btn-sm btn-link p-0 ms-1 dcf-toggle';
            toggle.innerHTML = '<i class="fas fa-plus-circle"></i>';
            toggle.setAttribute('aria-expanded', 'false');
            th.appendChild(toggle);

            let expandedState = { columns: [], insertedCount: 0 };

            toggle.addEventListener('click', () => {
                const expanded = toggle.getAttribute('aria-expanded') === 'true';
                if (expanded) {
                    // Collapse: remove inserted sub-columns
                    collapseColumns(target.idx, expandedState.insertedCount);
                    expandedState = { columns: [], insertedCount: 0 };
                    toggle.setAttribute('aria-expanded', 'false');
                    toggle.innerHTML = '<i class="fas fa-plus-circle"></i>';
                    return;
                }

                // Expand: fetch matrix and insert columns
                const url = `/api/dcf-breakdown-matrix?scenario=${encodeURIComponent(scenarioName)}&sub_scenario=${encodeURIComponent(subScenarioName)}${scenarioParameter?`&scenario_parameter=${encodeURIComponent(scenarioParameter)}`:''}${scenarioValue!==undefined?`&scenario_value=${encodeURIComponent(scenarioValue)}`:''}`;
                fetch(url)
                    .then(r => r.json())
                    .then(matrix => {
                        const set = matrix[target.key];
                        const columns = set.columns || [];
                        const data = set.data || [];
                        if (!columns.length) return;
                        expandedState.columns = columns.slice();
                        expandedState.insertedCount = insertColumns(target.idx, columns, data);
                        toggle.setAttribute('aria-expanded', 'true');
                        toggle.innerHTML = '<i class="fas fa-minus-circle"></i>';
                    })
                    .catch(err => console.error('Error loading breakdown matrix', err));
            });
        });

        function insertColumns(baseIdx, subColumnNames, matrixRows) {
            const theadRow = table.querySelector('thead tr');
            // Insert header cells after baseIdx
            subColumnNames.forEach((name, i) => {
                const th = document.createElement('th');
                th.textContent = name;
                th.className = 'text-center';
                theadRow.insertBefore(th, theadRow.children[baseIdx + 1 + i]);
            });

            // Insert data cells per row using matrixRows aligned by ages order of table body
            const bodyRows = Array.from(table.querySelectorAll('tbody tr'));
            bodyRows.forEach((tr, rIdx) => {
                // Get the cell value row; fallback zeros if out of range
                const values = matrixRows[rIdx] || Array(subColumnNames.length).fill(0);
                values.forEach((val, i) => {
                    const td = document.createElement('td');
                    td.textContent = formatCurrency(val);
                    td.className = getValueClass(val);
                    tr.insertBefore(td, tr.children[baseIdx + 1 + i]);
                });
            });

            return subColumnNames.length;
        }

        function collapseColumns(baseIdx, count) {
            if (!count) return;
            const theadRow = table.querySelector('thead tr');
            for (let i = 0; i < count; i++) {
                const idx = baseIdx + 1; // always remove the first inserted after base
                if (theadRow.children[idx]) theadRow.removeChild(theadRow.children[idx]);
                const bodyRows = Array.from(table.querySelectorAll('tbody tr'));
                bodyRows.forEach(tr => {
                    if (tr.children[idx]) tr.removeChild(tr.children[idx]);
                });
            }
        }
    }

    // Function to fetch and display DCF data for a specific scenario
    function loadDCFData(goalParameter, scenarioParameter, scenarioValue, scenarioName, subScenarioName) {
        if (!goalParameter || !scenarioParameter || scenarioValue === null || scenarioValue === undefined) {
            console.log('Missing parameters for DCF data fetch');
            updateTable(null);
            return;
        }

        let url = `/api/solved-dcf?goal=${encodeURIComponent(goalParameter)}&scenario_parameter=${encodeURIComponent(scenarioParameter)}&scenario_value=${encodeURIComponent(scenarioValue)}`;
        
        // Add scenario and sub-scenario filtering to get only one row per age
        if (scenarioName) {
            url += `&scenario=${encodeURIComponent(scenarioName)}`;
        }
        if (subScenarioName) {
            url += `&sub_scenario=${encodeURIComponent(subScenarioName)}`;
        }
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                console.log('DCF data received:', data);
                updateTable(data);
                // After table render, enable column expansion controls
                enableColumnExpansion(goalParameter, scenarioParameter, scenarioValue, scenarioName, subScenarioName);
            })
            .catch(error => {
                console.error('Error fetching DCF data:', error);
                updateTable(null);
            });
    }

    // Expose functions globally for integration with scenario table
    window.DCFDetailsTable = {
        init: init,
        updateTable: updateTable,
        loadDCFData: loadDCFData
    };

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();