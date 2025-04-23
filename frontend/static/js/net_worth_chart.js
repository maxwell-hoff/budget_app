class NetWorthChart {
    constructor() {
        this.chart = document.getElementById('net-worth-chart');
        this.chartContent = document.getElementById('net-worth-chart-content');
        this.chartBars = document.getElementById('net-worth-chart-bars');
        this.chartXAxis = document.getElementById('net-worth-chart-x-axis');
        this.chartYAxis = document.getElementById('net-worth-chart-y-axis');
        this.verticalSpacing = 30;
        this.barWidth = 20;
        this.padding = 20;
        
        // Create toggle button
        this.toggleButton = document.createElement('button');
        this.toggleButton.className = 'net-worth-toggle-button';
        this.toggleButton.innerHTML = '<i class="fas fa-chevron-up toggle-icon"></i>';
        this.toggleButton.addEventListener('click', () => this.toggleChart());
        this.chart.appendChild(this.toggleButton);
        
        // Initialize chart state
        this.isExpanded = true;
    }

    toggleChart() {
        this.isExpanded = !this.isExpanded;
        
        if (this.isExpanded) {
            // If expanding, refresh the page
            window.location.reload();
        } else {
            // If collapsing, just update the UI
            this.chart.classList.add('collapsed');
            this.toggleButton.querySelector('.toggle-icon').classList.add('expanded');
            this.chart.style.height = 'auto';
        }
    }

    updateChart(netWorthData) {
        // Clear existing content
        this.chartBars.innerHTML = '';
        this.chartXAxis.innerHTML = '';
        this.chartYAxis.innerHTML = '';
        
        if (!netWorthData || netWorthData.length === 0) {
            this.chartContent.style.display = 'none';
            return;
        }

        this.chartContent.style.display = this.isExpanded ? 'block' : 'none';

        // Find max and min values for scaling
        const maxValue = Math.max(...netWorthData.map(d => d.net_worth));
        const minValue = Math.min(...netWorthData.map(d => d.net_worth));
        const maxAbsValue = Math.max(Math.abs(maxValue), Math.abs(minValue));
        
        // Create y-axis
        this.createYAxis(maxAbsValue);
        
        // Create x-axis
        this.createXAxis(netWorthData);
        
        // Create bars
        this.createBars(netWorthData, maxAbsValue);
        
        // Adjust chart height based on expanded state
        if (this.isExpanded) {
            const requiredHeight = 300; // Fixed height for the chart
            this.chart.style.height = `${requiredHeight}px`;
        } else {
            this.chart.style.height = 'auto';
        }
    }

    createYAxis(maxAbsValue) {
        // Calculate interval for y-axis markers
        let interval = 100000;
        let numMarkers = Math.ceil(maxAbsValue / interval) * 2 + 1; // +1 for zero
        
        // Keep doubling the interval until we have 10 or fewer markers
        while (numMarkers > 10) {
            interval *= 2;
            numMarkers = Math.ceil(maxAbsValue / interval) * 2 + 1;
        }

        // Round maxAbsValue up to nearest multiple of interval
        const roundedMax = Math.ceil(maxAbsValue / interval) * interval;
        
        // Create y-axis line
        const line = document.createElement('div');
        line.className = 'y-axis-line';
        this.chartYAxis.appendChild(line);
        
        // Create markers and labels
        for (let value = -roundedMax; value <= roundedMax; value += interval) {
            const position = 150 - (value / roundedMax) * 150; // 150 is half the chart height
            
            // Create marker
            const marker = document.createElement('div');
            marker.className = 'y-axis-marker';
            marker.style.top = `${position}px`;
            this.chartYAxis.appendChild(marker);
            
            // Create label
            const label = document.createElement('div');
            label.className = 'y-axis-label';
            label.textContent = this.formatValue(value);
            label.style.top = `${position}px`;
            this.chartYAxis.appendChild(label);
        }
    }

    createXAxis(netWorthData) {
        // Create x-axis line
        const line = document.createElement('div');
        line.className = 'x-axis-line';
        this.chartXAxis.appendChild(line);
        
        // Create markers and labels for each age
        netWorthData.forEach((data, index) => {
            const position = index * (this.barWidth + 10) + this.padding;
            
            // Create marker
            const marker = document.createElement('div');
            marker.className = 'x-axis-marker';
            marker.style.left = `${position}px`;
            this.chartXAxis.appendChild(marker);
            
            // Create label
            const label = document.createElement('div');
            label.className = 'x-axis-label';
            label.textContent = data.age;
            label.style.left = `${position}px`;
            this.chartXAxis.appendChild(label);
        });
    }

    createBars(netWorthData, maxAbsValue) {
        netWorthData.forEach((data, index) => {
            const position = index * (this.barWidth + 10) + this.padding;
            const height = Math.abs(data.net_worth / maxAbsValue) * 150; // 150 is half the chart height
            const top = data.net_worth >= 0 ? 150 - height : 150; // 150 is half the chart height
            
            // Create bar
            const bar = document.createElement('div');
            bar.className = `net-worth-bar ${data.net_worth >= 0 ? 'positive' : 'negative'}`;
            bar.style.left = `${position}px`;
            bar.style.top = `${top}px`;
            bar.style.width = `${this.barWidth}px`;
            bar.style.height = `${height}px`;
            
            // Add tooltip
            bar.title = `Age ${data.age}: ${this.formatValue(data.net_worth)}`;
            
            this.chartBars.appendChild(bar);
        });
    }

    formatValue(value) {
        if (Math.abs(value) >= 1000000) {
            return `$${(value / 1000000).toFixed(1)}M`;
        } else if (Math.abs(value) >= 1000) {
            return `$${(value / 1000).toFixed(1)}K`;
        }
        return `$${value.toFixed(0)}`;
    }
}

// Initialize chart when the document is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.netWorthChart = new NetWorthChart();
}); 