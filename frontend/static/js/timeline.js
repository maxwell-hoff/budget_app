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
        
        // Redraw all milestones
        if (window.milestones) {
            window.milestones.forEach(milestone => {
                this.addMilestone(milestone);
            });
        }
        
        // Show timeline content and hide placeholder
        this.timelineContent.style.display = 'block';
        this.timelinePlaceholder.style.display = 'none';
    }

    clearTimeline() {
        this.timelineMarkers.innerHTML = '';
        this.timelineLabels.innerHTML = '';
        this.timelineMilestones.innerHTML = '';
        this.timelineLine.innerHTML = '';
        this.milestonePositions.clear();
        this.timeline.style.height = '75px'; // Reset to minimum height
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
            marker.style.left = `${position}px`;
            this.timelineMarkers.appendChild(marker);

            // Create label
            const label = document.createElement('div');
            label.className = 'age-label';
            label.textContent = age;
            label.style.position = 'absolute';
            label.style.left = `${position}px`;
            this.timelineLabels.appendChild(label);
        }
    }

    addMilestone(milestone) {
        const timelineWidth = this.timeline.offsetWidth - 40;  // Account for margins
        const currentAge = this.calculateAge(this.birthdayInput.value);
        const startAge = currentAge;
        const maxAge = 100;  // Maximum age shown on timeline
        
        // Calculate start position
        const startPosition = ((milestone.age_at_occurrence - startAge) / (maxAge - startAge)) * timelineWidth + 20;  // Add left margin
        
        // Calculate end position based on disbursement type
        let endPosition = null;
        if (milestone.disbursement_type === 'Fixed Duration' && milestone.duration) {
            // Calculate end age based on occurrence and duration
            let milestoneEndAge;
            if (milestone.occurrence === 'Monthly') {
                // For monthly, duration is in months, so convert to years
                milestoneEndAge = milestone.age_at_occurrence + (milestone.duration / 12);
            } else { // Yearly
                milestoneEndAge = milestone.age_at_occurrence + milestone.duration;
            }
            // Calculate position based on the actual end age
            endPosition = ((milestoneEndAge - startAge) / (maxAge - startAge)) * timelineWidth + 20;
        } else if (milestone.disbursement_type === 'Perpetuity') {
            // For perpetuity, use inheritance age (100)
            endPosition = ((maxAge - startAge) / (maxAge - startAge)) * timelineWidth + 20;
        }
        
        // Calculate vertical position for this milestone
        const verticalPosition = this.calculateVerticalPosition(milestone.id);
        
        this.createMilestoneMarker(
            milestone.name,
            startPosition,
            milestone.name === 'Current' ? 'current' : 'inheritance',
            milestone.id,
            endPosition,
            verticalPosition
        );
    }

    calculateVerticalPosition(milestoneId) {
        // If we already have a position for this milestone, use it
        if (this.milestonePositions.has(milestoneId)) {
            return this.milestonePositions.get(milestoneId);
        }
        
        // Find the next available vertical position
        // Start below the timeline line (20px) plus spacing
        let nextPosition = 20 + this.verticalSpacing;
        const existingPositions = Array.from(this.milestonePositions.values());
        
        while (existingPositions.includes(nextPosition)) {
            nextPosition += this.verticalSpacing;
        }
        
        // Store the position for this milestone
        this.milestonePositions.set(milestoneId, nextPosition);
        
        // Update timeline height if needed
        const requiredHeight = nextPosition + this.verticalSpacing + 20; // Add padding
        if (this.timeline.offsetHeight < requiredHeight) {
            this.timeline.style.height = `${requiredHeight}px`;
        }
        
        return nextPosition;
    }

    createMilestoneMarker(name, position, type, milestoneId, endPosition = null, verticalPosition) {
        // Create start marker
        const marker = document.createElement('div');
        marker.className = `milestone-marker ${type}-marker`;
        marker.setAttribute('data-id', milestoneId);
        marker.style.position = 'absolute';
        marker.style.top = `${verticalPosition}px`;
        marker.style.left = `${position}px`;
        
        // Add hover functionality to marker
        marker.addEventListener('mouseenter', () => {
            highlightMilestone(milestoneId);
        });
        
        marker.addEventListener('mouseleave', () => {
            unhighlightMilestone(milestoneId);
        });
        
        this.timelineMilestones.appendChild(marker);

        // Create start label
        const label = document.createElement('div');
        label.className = 'milestone-label';
        label.setAttribute('data-id', milestoneId);
        label.textContent = name;
        label.style.position = 'absolute';
        label.style.top = `${verticalPosition}px`;
        label.style.left = `${this.labelOffset}px`;
        
        // Add hover functionality to label
        label.addEventListener('mouseenter', () => {
            highlightMilestone(milestoneId);
        });
        
        label.addEventListener('mouseleave', () => {
            unhighlightMilestone(milestoneId);
        });
        
        this.timelineMilestones.appendChild(label);

        // Create end marker if needed
        if (endPosition && Math.abs(endPosition - position) > 5) { // Only create if positions are different enough
            const endMarker = document.createElement('div');
            endMarker.className = `milestone-marker ${type}-marker end-marker`;
            endMarker.setAttribute('data-id', milestoneId);
            endMarker.style.position = 'absolute';
            endMarker.style.top = `${verticalPosition}px`;
            endMarker.style.left = `${endPosition}px`;
            
            // Add hover functionality to end marker
            endMarker.addEventListener('mouseenter', () => {
                highlightMilestone(milestoneId);
            });
            
            endMarker.addEventListener('mouseleave', () => {
                unhighlightMilestone(milestoneId);
            });
            
            this.timelineMilestones.appendChild(endMarker);

            // Create connecting line
            const line = document.createElement('div');
            line.className = 'milestone-line';
            line.setAttribute('data-id', milestoneId);
            line.style.position = 'absolute';
            line.style.top = `${verticalPosition}px`;
            line.style.left = `${position}px`;
            line.style.width = `${endPosition - position}px`;
            
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
    window.timeline = new Timeline();
}); 