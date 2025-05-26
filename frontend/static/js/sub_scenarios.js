class SubScenarioManager {
    constructor() {
        this.subScenarioSelect = document.getElementById('subScenarioSelect');
        this.newButton = document.getElementById('newSubScenario');

        // Keep id in local storage per scenario for persistence
        this.parentScenarioSelect = document.getElementById('scenarioSelect');

        this.setupEventListeners();
        this.loadSubScenarios();
    }

    setupEventListeners() {
        // When user creates a new sub-scenario
        this.newButton.addEventListener('click', () => this.createNewSubScenario());

        // When user selects another sub-scenario, reload milestones
        this.subScenarioSelect.addEventListener('change', () => {
            const key = this.storageKeyForScenario();
            localStorage.setItem(key, this.subScenarioSelect.value);
            if (typeof loadMilestones === 'function') {
                loadMilestones();
            }
        });

        // When the parent scenario changes, we need to refresh available sub-scenarios
        this.parentScenarioSelect.addEventListener('change', () => {
            this.loadSubScenarios();
        });
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

            // Remove existing options
            this.subScenarioSelect.innerHTML = '';

            // Populate options
            subScenarios.forEach(s => {
                const option = document.createElement('option');
                option.value = s.id;
                option.textContent = s.name;
                this.subScenarioSelect.appendChild(option);
            });

            // Restore from local storage if available
            const stored = localStorage.getItem(this.storageKeyForScenario());
            if (stored && this.subScenarioSelect.querySelector(`option[value="${stored}"]`)) {
                this.subScenarioSelect.value = stored;
            }

            // Default to first sub-scenario if none selected
            if (!this.subScenarioSelect.value && subScenarios.length > 0) {
                this.subScenarioSelect.value = subScenarios[0].id;
            }

            // Trigger milestone load whenever sub-scenarios refreshed
            if (typeof loadMilestones === 'function') {
                loadMilestones();
            }
        } catch (err) {
            console.error('Error loading sub-scenarios', err);
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
}

// Initialize when DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.subScenarioManager = new SubScenarioManager();
}); 