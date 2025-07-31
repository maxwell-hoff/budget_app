(function() {
    document.addEventListener('DOMContentLoaded', function () {
        const btn = document.getElementById('calculateButton');
        if (!btn) return;

        btn.addEventListener('click', async function () {
            const originalLabel = btn.textContent;
            btn.disabled = true;
            btn.textContent = 'Calculating...';

            try {
                // 1. Fetch all goal parameters
                const goals = await fetch('/api/goals').then(r => r.json());

                // 2. Trigger solver for each goal parameter sequentially
                for (const goal of goals) {
                    await fetch('/api/solve', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ goal })
                    });
                }

                // 2a. Run the full DCF projection so the `dcf` table gets refreshed.
                await fetch('/api/calculate-dcf', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });

                // 2b. Trigger Monte Carlo simulation (uses server defaults: 1000 iterations).
                await fetch('/api/run-monte-carlo', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });

                // 3. Refresh scenario table (fire change event on dropdown)
                const dropdown = document.getElementById('goalDropdown');
                if (dropdown) {
                    dropdown.dispatchEvent(new Event('change'));
                }

                // 4. Update charts
                if (typeof updateCharts === 'function') {
                    updateCharts();
                }
            } catch (err) {
                console.error('Error during calculation:', err);
                alert('Error during calculation. See console for details.');
            } finally {
                btn.disabled = false;
                btn.textContent = originalLabel;
            }
        });
    });
})(); 