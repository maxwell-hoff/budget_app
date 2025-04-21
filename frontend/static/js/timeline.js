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
        this.createAgeMarkers();
        this.createDefaultMilestones(currentAge);
        
        // Show timeline content and hide placeholder
        this.timelineContent.style.display = 'block';
        this.timelinePlaceholder.style.display = 'none';
    }

    clearTimeline() {
        this.timelineMarkers.innerHTML = '';
        this.timelineLabels.innerHTML = '';
        this.timelineMilestones.innerHTML = '';
    }

    createAgeMarkers() {
        const timelineWidth = this.timeline.offsetWidth - 40; // Account for padding
        const startAge = 20;
        const endAge = 100;
        const step = 10;

        for (let age = startAge; age <= endAge; age += step) {
            const position = ((age - startAge) / (endAge - startAge)) * timelineWidth + 20;
            
            // Create marker
            const marker = document.createElement('div');
            marker.className = 'age-marker';
            marker.style.left = `${position}px`;
            this.timelineMarkers.appendChild(marker);

            // Create label
            const label = document.createElement('div');
            label.className = 'age-label';
            label.textContent = age;
            label.style.left = `${position}px`;
            this.timelineLabels.appendChild(label);
        }
    }

    createDefaultMilestones(currentAge) {
        const timelineWidth = this.timeline.offsetWidth - 40; // Account for padding
        const startAge = 20;
        const endAge = 100;

        // Current age marker
        const currentPosition = ((currentAge - startAge) / (endAge - startAge)) * timelineWidth + 20;
        this.createMilestoneMarker('Current', currentPosition, 'current');

        // Inheritance marker (age 100)
        const inheritancePosition = ((100 - startAge) / (endAge - startAge)) * timelineWidth + 20;
        this.createMilestoneMarker('Inheritance', inheritancePosition, 'inheritance');
    }

    createMilestoneMarker(name, position, type) {
        // Create marker
        const marker = document.createElement('div');
        marker.className = `milestone-marker ${type}-marker`;
        marker.style.left = `${position}px`;
        this.timelineMilestones.appendChild(marker);

        // Create label
        const label = document.createElement('div');
        label.className = 'milestone-label';
        label.textContent = name;
        label.style.left = `${position}px`;
        this.timelineMilestones.appendChild(label);
    }

    showPlaceholder() {
        this.timelineContent.style.display = 'none';
        this.timelinePlaceholder.style.display = 'block';
    }
}

// Initialize timeline when the document is loaded
document.addEventListener('DOMContentLoaded', () => {
    new Timeline();
}); 