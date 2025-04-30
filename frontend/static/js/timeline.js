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
        
        // Load parent milestones
        $.ajax({
            url: '/api/parent-milestones',
            method: 'GET',
            success: (parentMilestones) => {
                // Add each parent milestone to the timeline
                parentMilestones.forEach(milestone => {
                    this.addParentMilestone(milestone);
                });
                
                // Show timeline content and hide placeholder
                this.timelineContent.style.display = 'block';
                this.timelinePlaceholder.style.display = 'none';
            },
            error: (error) => {
                console.error('Error loading parent milestones:', error);
            }
        });
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
        const timelineWidth = this.timeline.offsetWidth - 170;  // Account for left margin and container padding
        const startAge = currentAge;
        const endAge = 100;
        
        // Calculate the position of the current age marker
        const startPosition = 0;  // Let CSS handle the margin
        const endPosition = timelineWidth;  // End at the right edge of the timeline
        
        const line = document.createElement('div');
        line.className = 'timeline-line';
        line.style.position = 'absolute';
        line.style.top = '50%';
        line.style.left = `${startPosition}px`;
        line.style.width = `${endPosition}px`;
        line.style.height = '2px';
        line.style.backgroundColor = '#333';
        line.style.transform = 'translateY(-50%)';
        this.timelineLine.appendChild(line);
    }

    createAgeMarkers(currentAge) {
        const timelineWidth = this.timeline.offsetWidth - 170;  // Account for left margin and container padding
        const startAge = currentAge;
        const endAge = 100;
        const step = 10;

        for (let age = startAge; age <= endAge; age += step) {
            const position = ((age - startAge) / (endAge - startAge)) * timelineWidth;  // Let CSS handle the margin
            
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
            label.style.top = '0';
            this.timelineLabels.appendChild(label);
        }
    }

    addParentMilestone(milestone) {
        const timelineWidth = this.timeline.offsetWidth - 170;  // Account for left margin and container padding
        const currentAge = this.calculateAge(this.birthdayInput.value);
        const startAge = currentAge;
        const endAge = 100;  // Maximum age shown on timeline
        
        // Calculate positions based on min and max age
        const startPosition = ((milestone.min_age - startAge) / (endAge - startAge)) * timelineWidth + 20;
        const endPosition = ((milestone.max_age - startAge) / (endAge - startAge)) * timelineWidth + 20;
        
        // Calculate vertical position for this milestone
        const verticalPosition = this.calculateVerticalPosition(milestone.id);
        
        this.createMilestoneMarker(
            milestone.name,
            startPosition,
            'parent',
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
        label.style.top = `${verticalPosition - 12}px`;  // Move label up by 5px
        
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