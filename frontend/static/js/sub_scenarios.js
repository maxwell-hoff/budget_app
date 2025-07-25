class SubScenarioManager {
    constructor() {
        this.subScenarioSelect = document.getElementById('subScenarioSelect');
        this.newButton = document.getElementById('newSubScenario');
        this.renameButton = document.getElementById('renameSubScenario');
        this.deleteButton = document.getElementById('deleteSubScenario');
        // Checkbox used to mark the current sub-scenario as the target
        this.targetCheckbox = document.getElementById('targetSubScenario');

        // Keep id in local storage per scenario for persistence
        this.parentScenarioSelect = document.getElementById('scenarioSelect');

        this.setupEventListeners();
        this.loadSubScenarios();
    }

    setupEventListeners() {
        // When user creates a new sub-scenario
        this.newButton.addEventListener('click', () => this.createNewSubScenario());

        // When user selects another sub-scenario, reload milestones
        this.subScenarioSelect.addEventListener('change', async () => {
            const key = this.storageKeyForScenario();
            localStorage.setItem(key, this.subScenarioSelect.value);
            if (typeof loadMilestones === 'function') {
                loadMilestones();
            }

            // Update target checkbox state when changing selection
            await this.refreshTargetCheckbox();
        });

        // When the parent scenario changes, we need to refresh available sub-scenarios
        this.parentScenarioSelect.addEventListener('change', () => {
            this.loadSubScenarios();
        });

        // When user clicks to rename a sub-scenario
        this.renameButton.addEventListener('click', () => this.renameCurrentSubScenario());

        // When user clicks to delete a sub-scenario
        this.deleteButton.addEventListener('click', () => this.deleteCurrentSubScenario());

        // When user toggles the "Target" checkbox
        this.targetCheckbox.addEventListener('change', () => this.onTargetToggle());
    }

    storageKeyForScenario() {
        const scenarioId = this.parentScenarioSelect.value || 'default';
        return `selectedSubScenarioId_${scenarioId}`;
    }

    async loadSubScenarios() {
        const scenarioId = this.parentScenarioSelect.value;
        if (!scenarioId) {
            // Clear select if no scenario chosen
            this.subScenarioSelect.innerHTML = '';
            return;
        }

        try {
            const response = await fetch(`/api/sub-scenarios?scenario_id=${scenarioId}`);
            const subScenarios = await response.json();

            // Clear existing options
            this.subScenarioSelect.innerHTML = '';

            // Populate options
            let defaultId = '';
            subScenarios.forEach(s => {
                const option = document.createElement('option');
                option.value = s.id;
                option.textContent = s.name;
                this.subScenarioSelect.appendChild(option);

                // Remember id of "2 Kids" if present
                if (s.name.toLowerCase() === '2 kids') {
                    defaultId = s.id;
                }
            });

            // Restore from local storage if available
            const stored = localStorage.getItem(this.storageKeyForScenario());
            if (stored && this.subScenarioSelect.querySelector(`option[value="${stored}"]`)) {
                this.subScenarioSelect.value = stored;
            }

            if (subScenarios.length === 0) {
                // Ensure no residual value from previous scenario is shown
                this.subScenarioSelect.value = '';
                // Remove any stored selection for this scenario
                localStorage.removeItem(this.storageKeyForScenario());
            } else if (!this.subScenarioSelect.value) {
                // Default to "2 Kids" if exists, otherwise first sub-scenario
                this.subScenarioSelect.value = defaultId || subScenarios[0].id;
            }

            // After populating the dropdown, refresh the target checkbox state
            await this.refreshTargetCheckbox();

            // Trigger milestone load whenever sub-scenarios refreshed
            if (typeof loadMilestones === 'function') {
                loadMilestones();
            }
        } catch (err) {
            console.error('Error loading sub-scenarios', err);
        }
    }

    /**
     * Fetch the current target sub-scenario for the selected scenario and update
     * the checkbox accordingly.
     */
    async refreshTargetCheckbox() {
        const scenarioId = this.parentScenarioSelect.value;
        if (!scenarioId) {
            this.targetCheckbox.checked = false;
            this.targetCheckbox.disabled = true;
            return;
        }

        try {
            const resp = await fetch(`/api/target-sub-scenarios?scenario_id=${scenarioId}`);
            if (!resp.ok) throw new Error('Failed to fetch target sub-scenario');
            const data = await resp.json(); // expected { sub_scenario_id: <id> } or null

            const currentSubId = this.subScenarioSelect.value;
            this.targetCheckbox.checked = data && data.sub_scenario_id && data.sub_scenario_id.toString() === currentSubId.toString();
            this.targetCheckbox.indeterminate = data && data.sub_scenario_id && data.sub_scenario_id.toString() !== currentSubId.toString();
            this.targetCheckbox.disabled = false;
        } catch (err) {
            console.error('Error loading target sub-scenario', err);
            this.targetCheckbox.checked = false;
            this.targetCheckbox.disabled = true;
        }
    }

    /** Handle user toggling of target checkbox */
    async onTargetToggle() {
        const scenarioId = this.parentScenarioSelect.value;
        const subScenarioId = this.subScenarioSelect.value;
        if (!scenarioId || !subScenarioId) {
            alert('Select a scenario and sub-scenario first');
            this.targetCheckbox.checked = false;
            return;
        }

        try {
            if (this.targetCheckbox.checked) {
                // Mark as target
                const resp = await fetch('/api/target-sub-scenarios', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ scenario_id: parseInt(scenarioId), sub_scenario_id: parseInt(subScenarioId) })
                });
                if (!resp.ok) throw new Error('Failed to set target');
            } else {
                // Remove target
                const resp = await fetch(`/api/target-sub-scenarios?scenario_id=${scenarioId}`, { method: 'DELETE' });
                if (!resp.ok) throw new Error('Failed to clear target');
            }

            // Refresh checkbox state to reflect any server-side enforcement (e.g., only one target)
            await this.refreshTargetCheckbox();
        } catch (err) {
            console.error('Error updating target sub-scenario', err);
            alert('Error updating target sub-scenario');
            // Revert checkbox visual state on error
            await this.refreshTargetCheckbox();
        }
    }

    async createNewSubScenario() {
        const name = prompt('Enter a name for the new sub-scenario:');
        if (!name) return;
        const scenarioId = this.parentScenarioSelect.value;
        if (!scenarioId) {
            alert('Please select a parent scenario first');
            return;
        }

        try {
            const response = await fetch('/api/sub-scenarios', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name,
                    scenario_id: parseInt(scenarioId)
                })
            });

            if (response.ok) {
                const newSub = await response.json();
                // Persist selection
                localStorage.setItem(this.storageKeyForScenario(), newSub.id.toString());
                await this.loadSubScenarios();
                alert('New sub-scenario created successfully');
            } else {
                throw new Error('Failed to create sub-scenario');
            }
        } catch (err) {
            console.error('Error creating sub-scenario', err);
            alert('Error creating sub-scenario');
        }
    }

    async renameCurrentSubScenario() {
        const subScenarioId = this.subScenarioSelect.value;
        if (!subScenarioId) {
            alert('Please select a sub-scenario to rename');
            return;
        }

        const currentName = this.subScenarioSelect.options[this.subScenarioSelect.selectedIndex].textContent;
        const name = prompt('Enter a new name for the sub-scenario:', currentName);
        if (!name || name.trim() === '') return;

        try {
            const response = await fetch(`/api/sub-scenarios/${subScenarioId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ name })
            });

            if (response.ok) {
                await this.loadSubScenarios();
                alert('Sub-scenario renamed successfully');
            } else {
                throw new Error('Failed to rename sub-scenario');
            }
        } catch (err) {
            console.error('Error renaming sub-scenario', err);
            alert('Error renaming sub-scenario');
        }
    }

    async deleteCurrentSubScenario() {
        const subScenarioId = this.subScenarioSelect.value;
        if (!subScenarioId) {
            alert('Please select a sub-scenario to delete');
            return;
        }

        const confirmDelete = confirm('Are you sure you want to delete this sub-scenario? This action cannot be undone.');
        if (!confirmDelete) return;

        try {
            const response = await fetch(`/api/sub-scenarios/${subScenarioId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                // Remove stored selection for this scenario-sub combination if it matches
                if (localStorage.getItem(this.storageKeyForScenario()) === subScenarioId) {
                    localStorage.removeItem(this.storageKeyForScenario());
                }

                await this.loadSubScenarios();
                alert('Sub-scenario deleted successfully');
            } else {
                throw new Error('Failed to delete sub-scenario');
            }
        } catch (err) {
            console.error('Error deleting sub-scenario', err);
            alert('Error deleting sub-scenario');
        }
    }
}

// Initialize when DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.subScenarioManager = new SubScenarioManager();
}); 