class NetWorthChart {
    constructor() {
        console.log('Initializing NetWorthChart');
        this.chart = document.getElementById('net-worth-chart');
        this.chartContent = document.getElementById('net-worth-chart-content');
        this.chartBars = document.getElementById('net-worth-chart-bars');
        this.chartXAxis = document.getElementById('net-worth-chart-x-axis');
        this.chartYAxis = document.getElementById('net-worth-chart-y-axis');
        
        console.log('Chart elements:', {
            chart: this.chart,
            content: this.chartContent,
            bars: this.chartBars,
            xAxis: this.chartXAxis,
            yAxis: this.chartYAxis
        });
        
        this.verticalSpacing = 30;
        this.padding = 20;
        this.chartHeight = 150; // Half of the original 300px height
        
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
        console.log('Updating net worth chart with data:', netWorthData);
        
        // Clear existing content
        this.chartBars.innerHTML = '';
        this.chartXAxis.innerHTML = '';
        this.chartYAxis.innerHTML = '';
        
        if (!netWorthData || netWorthData.length === 0) {
            console.log('No net worth data, hiding chart content');
            this.chartContent.style.display = 'none';
            return;
        }

        console.log('Showing chart content');
        this.chartContent.style.display = this.isExpanded ? 'block' : 'none';

        // Find max and min values for scaling
        const maxValue = Math.max(...netWorthData.map(d => d.net_worth));
        const minValue = Math.min(...netWorthData.map(d => d.net_worth));
        const maxAbsValue = Math.max(Math.abs(maxValue), Math.abs(minValue));
        
        console.log('Chart values:', { maxValue, minValue, maxAbsValue });
        
        // Create y-axis
        this.createYAxis(maxAbsValue);
        
        // Create x-axis
        this.createXAxis(netWorthData);
        
        // Create line
        this.createLine(netWorthData, maxAbsValue);
        
        // Adjust chart height based on expanded state
        if (this.isExpanded) {
            this.chart.style.height = `${this.chartHeight}px`;
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
            const position = this.chartHeight/2 - (value / roundedMax) * (this.chartHeight/2); // Half of chart height
            
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
            const position = (index / (netWorthData.length - 1)) * (this.chart.offsetWidth - 2 * this.padding) + this.padding;
            
            // Create marker
            const marker = document.createElement('div');
            marker.className = 'x-axis-marker';
            marker.style.left = `${position}px`;
            this.chartXAxis.appendChild(marker);
            
            // Only create label if age is divisible by 5
            if (data.age % 5 === 0) {
                const label = document.createElement('div');
                label.className = 'x-axis-label';
                label.textContent = data.age;
                label.style.left = `${position}px`;
                this.chartXAxis.appendChild(label);
            }
        });
    }

    createLine(netWorthData, maxAbsValue) {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', '100%');
        svg.setAttribute('height', '100%');
        svg.style.position = 'absolute';
        svg.style.top = '0';
        svg.style.left = '0';
        
        // Get the value display element
        const valueDisplay = this.chart.querySelector('.net-worth-total-value');
        
        // Create line segments
        for (let i = 0; i < netWorthData.length - 1; i++) {
            const currentData = netWorthData[i];
            const nextData = netWorthData[i + 1];
            
            const x1 = (i / (netWorthData.length - 1)) * (this.chart.offsetWidth - 2 * this.padding) + this.padding;
            const y1 = this.chartHeight/2 - (currentData.net_worth / maxAbsValue) * (this.chartHeight/2);
            const x2 = ((i + 1) / (netWorthData.length - 1)) * (this.chart.offsetWidth - 2 * this.padding) + this.padding;
            const y2 = this.chartHeight/2 - (nextData.net_worth / maxAbsValue) * (this.chartHeight/2);
            
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', x1);
            line.setAttribute('y1', y1);
            line.setAttribute('x2', x2);
            line.setAttribute('y2', y2);
            line.setAttribute('stroke', currentData.net_worth >= 0 ? '#4CAF50' : '#f44336');
            line.setAttribute('stroke-width', '2');
            
            // Add hover effect
            line.addEventListener('mouseover', (e) => {
                valueDisplay.textContent = this.formatValue(currentData.net_worth);
                valueDisplay.className = `net-worth-total-value ${currentData.net_worth >= 0 ? 'positive' : 'negative'}`;
            });
            
            svg.appendChild(line);
        }
        
        this.chartBars.appendChild(svg);
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
    console.log('DOM loaded, creating NetWorthChart instance');
    window.netWorthChart = new NetWorthChart();
}); 