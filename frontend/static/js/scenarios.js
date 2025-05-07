class ScenarioManager {
    constructor() {
        this.scenarioSelect = document.getElementById('scenarioSelect');
        this.saveButton = document.getElementById('saveScenario');
        this.newButton = document.getElementById('newScenario');
        
        this.setupEventListeners();
        this.loadScenarios();
    }
    
    setupEventListeners() {
        this.saveButton.addEventListener('click', () => this.saveCurrentScenario());
        this.newButton.addEventListener('click', () => this.createNewScenario());
        this.scenarioSelect.addEventListener('change', () => this.loadSelectedScenario());
    }
    
    async loadScenarios() {
        try {
            const response = await fetch('/api/scenarios');
            const scenarios = await response.json();
            
            // Clear existing options except the first one
            while (this.scenarioSelect.options.length > 1) {
                this.scenarioSelect.remove(1);
            }
            
            // Add scenarios to select
            scenarios.forEach(scenario => {
                const option = document.createElement('option');
                option.value = scenario.id;
                option.textContent = scenario.name;
                this.scenarioSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading scenarios:', error);
        }
    }
    
    async saveCurrentScenario() {
        const selectedId = this.scenarioSelect.value;
        if (!selectedId) {
            alert('Please select a scenario to save to');
            return;
        }
        
        try {
            // Collect all current parameters
            const parameters = this.collectCurrentParameters();
            
            const response = await fetch(`/api/scenarios/${selectedId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ parameters })
            });
            
            if (response.ok) {
                alert('Scenario saved successfully');
            } else {
                throw new Error('Failed to save scenario');
            }
        } catch (error) {
            console.error('Error saving scenario:', error);
            alert('Error saving scenario');
        }
    }
    
    async createNewScenario() {
        const name = prompt('Enter a name for the new scenario:');
        if (!name) return;
        
        try {
            // Collect all current parameters
            const parameters = this.collectCurrentParameters();
            
            const response = await fetch('/api/scenarios', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name,
                    parameters
                })
            });
            
            if (response.ok) {
                await this.loadScenarios();
                alert('New scenario created successfully');
            } else {
                throw new Error('Failed to create scenario');
            }
        } catch (error) {
            console.error('Error creating scenario:', error);
            alert('Error creating scenario');
        }
    }
    
    async loadSelectedScenario() {
        const selectedId = this.scenarioSelect.value;
        if (!selectedId) return;
        
        try {
            const response = await fetch(`/api/scenarios/${selectedId}`);
            const scenario = await response.json();
            
            // Apply the loaded parameters
            this.applyParameters(scenario.parameters);
        } catch (error) {
            console.error('Error loading scenario:', error);
            alert('Error loading scenario');
        }
    }
    
    collectCurrentParameters() {
        // Collect all milestone parameters
        const milestones = [];
        document.querySelectorAll('.milestone-form').forEach(form => {
            const milestoneId = form.dataset.id;
            const inputs = form.querySelectorAll('input, select');
            const milestoneData = {
                id: milestoneId,
                parameters: {}
            };
            
            inputs.forEach(input => {
                if (input.name) {
                    milestoneData.parameters[input.name] = input.value;
                }
            });
            
            milestones.push(milestoneData);
        });
        
        // Collect user profile parameters
        const profileData = {
            birthday: document.getElementById('birthday').value,
            currentAge: document.getElementById('currentAge').value
        };
        
        return {
            milestones,
            profile: profileData
        };
    }
    
    applyParameters(parameters) {
        // Apply profile parameters
        if (parameters.profile) {
            document.getElementById('birthday').value = parameters.profile.birthday;
            document.getElementById('currentAge').value = parameters.profile.currentAge;
            
            // Trigger change event to update timeline
            document.getElementById('birthday').dispatchEvent(new Event('change'));
        }
        
        // Apply milestone parameters
        if (parameters.milestones) {
            parameters.milestones.forEach(milestoneData => {
                const form = document.querySelector(`.milestone-form[data-id="${milestoneData.id}"]`);
                if (form) {
                    Object.entries(milestoneData.parameters).forEach(([name, value]) => {
                        const input = form.querySelector(`[name="${name}"]`);
                        if (input) {
                            input.value = value;
                            // Trigger change event to update calculations
                            input.dispatchEvent(new Event('change'));
                        }
                    });
                }
            });
        }
        
        // Update charts and timeline
        if (window.timeline) {
            window.timeline.updateTimeline();
        }
        if (window.netWorthChart) {
            updateCharts();
        }
    }
}

// Initialize scenario manager when the document is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.scenarioManager = new ScenarioManager();
}); 