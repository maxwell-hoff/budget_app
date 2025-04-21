class Timeline {
    constructor() {
        this.timeline = document.getElementById('timeline');
        this.timelineContent = document.getElementById('timeline-content');
        this.timelinePlaceholder = document.getElementById('timeline-placeholder');
        this.timelineLine = document.getElementById('timeline-line');
        this.timelineMarkers = document.getElementById('timeline-markers');
        this.timelineLabels = document.getElementById('timeline-labels');
        this.timelineMilestones = document.getElementById('timeline-milestones');
        this.birthdayInput = document.getElementById('birthday');
        this.currentAgeInput = document.getElementById('currentAge');
        
        // Initialize the timeline
        this.showPlaceholder();
        this.setupEventListeners();
        
        // Add window resize listener
        window.addEventListener('resize', () => this.updateTimeline());
    }

    setupEventListeners() {
        this.birthdayInput.addEventListener('change', () => this.updateTimeline());
    }

    calculateAge(birthday) {
        const today = new Date();
        const birthDate = new Date(birthday);
        let age = today.getFullYear() - birthDate.getFullYear();
        const monthDiff = today.getMonth() - birthDate.getMonth();
        
        if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
            age--;
        }
        
        return age;
    }

    updateTimeline() {
        const birthday = this.birthdayInput.value;
        if (!birthday) {
            this.showPlaceholder();
            return;
        }

        const currentAge = this.calculateAge(birthday);
        this.currentAgeInput.value = currentAge;
        
        this.clearTimeline();
        this.createTimelineLine(currentAge);
        this.createAgeMarkers(currentAge);
        
        // Show timeline content and hide placeholder
        this.timelineContent.style.display = 'block';
        this.timelinePlaceholder.style.display = 'none';
    }

    clearTimeline() {
        this.timelineMarkers.innerHTML = '';
        this.timelineLabels.innerHTML = '';
        this.timelineMilestones.innerHTML = '';
        this.timelineLine.innerHTML = '';
    }

    createTimelineLine(currentAge) {
        const timelineWidth = this.timeline.offsetWidth - 40;  // Account for margins
        const startAge = currentAge;
        const endAge = 100;
        
        // Calculate the position of the current age marker
        const startPosition = 20;  // Left margin
        const endPosition = timelineWidth + 20;  // Right margin
        
        const line = document.createElement('div');
        line.className = 'timeline-line';
        line.style.position = 'absolute';
        line.style.top = '50%';
        line.style.left = `${startPosition}px`;
        line.style.width = `${endPosition - startPosition}px`;
        line.style.height = '2px';
        line.style.backgroundColor = '#333';
        line.style.transform = 'translateY(-50%)';
        this.timelineLine.appendChild(line);
    }

    createAgeMarkers(currentAge) {
        const timelineWidth = this.timeline.offsetWidth - 40;  // Account for margins
        const startAge = currentAge;
        const endAge = 100;
        const step = 10;

        for (let age = startAge; age <= endAge; age += step) {
            const position = ((age - startAge) / (endAge - startAge)) * timelineWidth + 20;  // Add left margin
            
            // Create marker
            const marker = document.createElement('div');
            marker.className = 'age-marker';
            marker.style.position = 'absolute';
            marker.style.top = '50%';
            marker.style.left = `${position}px`;
            marker.style.width = '1px';
            marker.style.height = '10px';
            marker.style.backgroundColor = '#666';
            marker.style.transform = 'translateY(-50%)';
            this.timelineMarkers.appendChild(marker);

            // Create label
            const label = document.createElement('div');
            label.className = 'age-label';
            label.textContent = age;
            label.style.position = 'absolute';
            label.style.bottom = '-20px';
            label.style.left = `${position}px`;
            label.style.transform = 'translateX(-50%)';
            label.style.fontSize = '0.8em';
            label.style.color = '#666';
            this.timelineLabels.appendChild(label);
        }
    }

    addMilestone(milestone) {
        const timelineWidth = this.timeline.offsetWidth - 40;  // Account for margins
        const currentAge = this.calculateAge(this.birthdayInput.value);
        const startAge = currentAge;
        const endAge = 100;
        const position = ((milestone.age_at_occurrence - startAge) / (endAge - startAge)) * timelineWidth + 20;  // Add left margin
        
        this.createMilestoneMarker(milestone.name, position, milestone.name === 'Current' ? 'current' : 'inheritance');
    }

    createMilestoneMarker(name, position, type) {
        // Create marker
        const marker = document.createElement('div');
        marker.className = `milestone-marker ${type}-marker`;
        marker.style.position = 'absolute';
        marker.style.top = '50%';
        marker.style.left = `${position}px`;
        marker.style.width = '12px';
        marker.style.height = '12px';
        marker.style.backgroundColor = type === 'current' ? '#28a745' : '#dc3545';
        marker.style.borderRadius = '50%';
        marker.style.transform = 'translate(-50%, -50%)';
        marker.style.cursor = 'pointer';
        this.timelineMilestones.appendChild(marker);

        // Create label
        const label = document.createElement('div');
        label.className = 'milestone-label';
        label.textContent = name;
        label.style.position = 'absolute';
        label.style.top = '-20px';
        label.style.left = `${position}px`;
        label.style.transform = 'translateX(-50%)';
        label.style.fontSize = '0.9em';
        label.style.color = '#333';
        label.style.whiteSpace = 'nowrap';
        label.style.backgroundColor = 'rgba(255, 255, 255, 0.9)';
        label.style.padding = '2px 5px';
        label.style.borderRadius = '3px';
        this.timelineMilestones.appendChild(label);
    }

    showPlaceholder() {
        this.timelineContent.style.display = 'none';
        this.timelinePlaceholder.style.display = 'block';
    }
}

// Initialize timeline when the document is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.timeline = new Timeline();
}); 