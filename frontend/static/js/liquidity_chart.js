class LiquidityChart {
    constructor() {
        this.chart = document.getElementById('liquidity-chart');
        this.chartContent = document.getElementById('liquidity-chart-content');
        this.chartBars = document.getElementById('liquidity-chart-bars');
        this.chartXAxis = document.getElementById('liquidity-chart-x-axis');
        this.chartYAxis = document.getElementById('liquidity-chart-y-axis');
        this.totalValue = document.querySelector('.liquidity-total-value');
        this.toggleButton = document.querySelector('.liquidity-toggle-button');
        this.toggleIcon = this.toggleButton.querySelector('.toggle-icon');
        this.isExpanded = false;
        
        // Add click event listener to toggle button
        this.toggleButton.addEventListener('click', () => this.toggleExpand());
    }
    
    toggleExpand() {
        this.isExpanded = !this.isExpanded;
        this.chart.classList.toggle('collapsed');
        this.toggleIcon.classList.toggle('expanded');
        this.updateChart(this.currentData);
    }
    
    updateChart(data) {
        if (!data || data.length === 0) {
            this.chartContent.style.display = 'none';
            return;
        }
        
        this.currentData = data;
        this.chartContent.style.display = 'block';
        
        // Clear existing chart content
        this.chartBars.innerHTML = '';
        this.chartXAxis.innerHTML = '';
        this.chartYAxis.innerHTML = '';
        
        // Find max and min values for scaling
        const maxValue = Math.max(...data.map(d => d.liquid_assets));
        const minValue = Math.min(...data.map(d => d.liquid_assets));
        const maxAbsValue = Math.max(Math.abs(maxValue), Math.abs(minValue));
        
        // Create y-axis
        this.createYAxis(maxAbsValue);
        
        // Create x-axis
        this.createXAxis(data);
        
        // Create line
        this.createLine(data, maxAbsValue);
        
        // Update total value
        const currentAge = 30; // TODO: Get from user settings
        const currentValue = data.find(d => d.age === currentAge)?.liquid_assets || 0;
        this.totalValue.textContent = this.formatValue(currentValue);
        this.totalValue.className = 'liquidity-total-value ' + (currentValue >= 0 ? 'positive' : 'negative');
    }
    
    createYAxis(maxAbsValue) {
        // Calculate interval for y-axis markers
        let interval = 100000;
        let numMarkers = Math.ceil(maxAbsValue / interval) * 2 + 1; // +1 for zero
        
        // Keep doubling the interval until we have 7 or fewer markers
        while (numMarkers > 7) {
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
            const position = this.chart.offsetHeight/2 - (value / roundedMax) * (this.chart.offsetHeight/2);
            
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
    
    createXAxis(data) {
        // Create x-axis line
        const line = document.createElement('div');
        line.className = 'x-axis-line';
        this.chartXAxis.appendChild(line);
        
        // Create markers and labels for each age
        data.forEach((point, index) => {
            const position = (index / (data.length - 1)) * (this.chart.offsetWidth - 40) + 20;
            
            // Create marker
            const marker = document.createElement('div');
            marker.className = 'x-axis-marker';
            marker.style.left = `${position}px`;
            this.chartXAxis.appendChild(marker);
            
            // Only create label if age is divisible by 5
            if (point.age % 5 === 0) {
                const label = document.createElement('div');
                label.className = 'x-axis-label';
                label.textContent = point.age;
                label.style.left = `${position}px`;
                this.chartXAxis.appendChild(label);
            }
        });
    }
    
    createLine(data, maxAbsValue) {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', '100%');
        svg.setAttribute('height', '100%');
        svg.style.position = 'absolute';
        svg.style.top = '0';
        svg.style.left = '0';
        
        // Create line segments
        for (let i = 0; i < data.length - 1; i++) {
            const currentData = data[i];
            const nextData = data[i + 1];
            
            const x1 = (i / (data.length - 1)) * (this.chart.offsetWidth - 40) + 20;
            const y1 = this.chart.offsetHeight/2 - (currentData.liquid_assets / maxAbsValue) * (this.chart.offsetHeight/2);
            const x2 = ((i + 1) / (data.length - 1)) * (this.chart.offsetWidth - 40) + 20;
            const y2 = this.chart.offsetHeight/2 - (nextData.liquid_assets / maxAbsValue) * (this.chart.offsetHeight/2);
            
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', x1);
            line.setAttribute('y1', y1);
            line.setAttribute('x2', x2);
            line.setAttribute('y2', y2);
            line.setAttribute('stroke', currentData.liquid_assets >= 0 ? '#4CAF50' : '#f44336');
            line.setAttribute('stroke-width', '2');
            
            // Add hover effect
            line.addEventListener('mouseover', () => {
                this.showTooltip(x1, y1, currentData);
            });
            
            line.addEventListener('mouseout', () => {
                this.hideTooltip();
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
    
    showTooltip(x, y, point) {
        const tooltip = document.createElement('div');
        tooltip.className = 'tooltip';
        tooltip.style.position = 'absolute';
        tooltip.style.left = `${x + 10}px`;
        tooltip.style.top = `${y - 10}px`;
        tooltip.style.backgroundColor = 'rgba(0, 0, 0, 0.8)';
        tooltip.style.color = '#fff';
        tooltip.style.padding = '5px 10px';
        tooltip.style.borderRadius = '4px';
        tooltip.style.fontSize = '12px';
        tooltip.style.pointerEvents = 'none';
        tooltip.style.zIndex = '1000';
        tooltip.textContent = `Age ${point.age}: ${this.formatValue(point.liquid_assets)}`;
        
        this.chartBars.appendChild(tooltip);
    }
    
    hideTooltip() {
        const tooltip = this.chartBars.querySelector('.tooltip');
        if (tooltip) {
            tooltip.remove();
        }
    }
}

// Initialize chart when the document is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, creating LiquidityChart instance');
    window.liquidityChart = new LiquidityChart();
}); 