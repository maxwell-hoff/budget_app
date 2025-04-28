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
        
        // Track milestone positions
        this.milestonePositions = new Map();
        this.verticalSpacing = 30; // pixels between milestone rows
        this.labelOffset = 100; // pixels from left edge for labels
        this.padding = 20; // Padding around the timeline
        
        // Initialize the timeline
        this.setupEventListeners();
        
        // Add window resize listener
        window.addEventListener('resize', () => {
            // Add a small delay to prevent multiple refreshes during continuous resizing
            clearTimeout(this.resizeTimeout);
            this.resizeTimeout = setTimeout(() => {
                window.location.reload();
            }, 250);
        });
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
        console.log('Updating timeline...');
        console.log('Current milestones:', milestones);
        
        // Clear existing content
        this.timelineMarkers.innerHTML = '';
        this.timelineLabels.innerHTML = '';
        this.timelineMilestones.innerHTML = '';
        
        // Get parent milestones (those without a parent)
        const parentMilestones = milestones.filter(m => !m.parent_milestone_id);
        console.log('Parent milestones:', parentMilestones);
        
        if (!parentMilestones || parentMilestones.length === 0) {
            console.log('No parent milestones, showing placeholder');
            this.timelineContent.style.display = 'none';
            this.timelinePlaceholder.style.display = 'block';
            return;
        }

        console.log('Showing timeline content');
        this.timelineContent.style.display = 'block';
        this.timelinePlaceholder.style.display = 'none';
        
        // Calculate timeline dimensions
        const timelineWidth = this.timeline.offsetWidth - 2 * this.padding;
        const timelineHeight = parentMilestones.length * this.verticalSpacing + this.padding;
        
        // Set timeline height
        this.timeline.style.height = `${timelineHeight}px`;
        
        // Create age markers and labels
        this.createAgeMarkers(timelineWidth);
        
        // Add each parent milestone to the timeline
        parentMilestones.forEach((milestone, index) => {
            this.addParentMilestone(milestone, index, timelineWidth);
        });
    }

    createAgeMarkers(timelineWidth) {
        // Create age markers every 10 years from 20 to 100
        for (let age = 20; age <= 100; age += 10) {
            const position = (age / 100) * timelineWidth;
            
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

    addParentMilestone(milestone, index, timelineWidth) {
        // Get all sub-milestones for this parent
        const subMilestones = milestones.filter(m => m.parent_milestone_id === milestone.id);
        
        // Calculate min and max age for this parent milestone
        let minAge = milestone.age_at_occurrence;
        let maxAge = milestone.age_at_occurrence;
        
        if (subMilestones.length > 0) {
            minAge = Math.min(...subMilestones.map(m => m.age_at_occurrence));
            maxAge = Math.max(...subMilestones.map(m => m.age_at_occurrence));
        }
        
        // Calculate positions
        const minPosition = (minAge / 100) * timelineWidth;
        const maxPosition = (maxAge / 100) * timelineWidth;
        const top = index * this.verticalSpacing + this.padding;
        
        // Create start marker
        const startMarker = document.createElement('div');
        startMarker.className = 'milestone-marker';
        startMarker.style.left = `${minPosition}px`;
        startMarker.style.top = `${top}px`;
        startMarker.setAttribute('data-id', milestone.id);
        startMarker.setAttribute('data-type', 'start');
        
        // Add hover functionality
        startMarker.addEventListener('mouseenter', () => {
            highlightMilestone(milestone.id);
        });
        
        startMarker.addEventListener('mouseleave', () => {
            unhighlightMilestone(milestone.id);
        });
        
        this.timelineMilestones.appendChild(startMarker);
        
        // Create end marker if different from start
        if (maxAge !== minAge) {
            const endMarker = document.createElement('div');
            endMarker.className = 'milestone-marker end-marker';
            endMarker.style.left = `${maxPosition}px`;
            endMarker.style.top = `${top}px`;
            endMarker.setAttribute('data-id', milestone.id);
            endMarker.setAttribute('data-type', 'end');
            
            // Add hover functionality
            endMarker.addEventListener('mouseenter', () => {
                highlightMilestone(milestone.id);
            });
            
            endMarker.addEventListener('mouseleave', () => {
                unhighlightMilestone(milestone.id);
            });
            
            this.timelineMilestones.appendChild(endMarker);
        }
        
        // Create milestone label
        const label = document.createElement('div');
        label.className = 'milestone-label';
        label.textContent = milestone.name;
        label.style.left = `${minPosition}px`;
        label.style.top = `${top - 20}px`;
        label.setAttribute('data-id', milestone.id);
        
        // Add hover functionality
        label.addEventListener('mouseenter', () => {
            highlightMilestone(milestone.id);
        });
        
        label.addEventListener('mouseleave', () => {
            unhighlightMilestone(milestone.id);
        });
        
        this.timelineMilestones.appendChild(label);
        
        // If there are sub-milestones, create a line connecting them
        if (subMilestones.length > 0) {
            const line = document.createElement('div');
            line.className = 'milestone-line';
            line.style.left = `${minPosition}px`;
            line.style.width = `${maxPosition - minPosition}px`;
            line.style.top = `${top}px`;
            line.setAttribute('data-id', milestone.id);
            
            // Add hover functionality
            line.addEventListener('mouseenter', () => {
                highlightMilestone(milestone.id);
            });
            
            line.addEventListener('mouseleave', () => {
                unhighlightMilestone(milestone.id);
            });
            
            this.timelineMilestones.appendChild(line);
        }
    }

    showPlaceholder() {
        this.timelineContent.style.display = 'none';
        this.timelinePlaceholder.style.display = 'block';
    }
}

// Initialize timeline when the document is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing timeline');
    window.timeline = new Timeline();
    
    // Check if we have a birthday and milestones loaded
    const birthdayInput = document.getElementById('birthday');
    if (birthdayInput.value && window.milestones) {
        console.log('Birthday and milestones found, updating timeline');
        window.timeline.updateTimeline();
    } else {
        console.log('No birthday or milestones found, showing placeholder');
        window.timeline.showPlaceholder();
    }
}); 