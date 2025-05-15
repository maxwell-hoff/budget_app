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
        
        // Create y-axis
        const yAxisValues = this.calculateYAxisValues(minValue, maxValue);
        yAxisValues.forEach(value => {
            const marker = document.createElement('div');
            marker.className = 'y-axis-marker';
            marker.style.position = 'absolute';
            marker.style.left = '0';
            marker.style.width = '100%';
            marker.style.textAlign = 'right';
            marker.style.paddingRight = '10px';
            marker.style.fontSize = '12px';
            marker.style.color = '#a0a0a0';
            
            const y = this.getYPosition(value, minValue, maxValue);
            marker.style.top = `${y}px`;
            
            const label = document.createElement('div');
            label.className = 'y-axis-label';
            label.textContent = this.formatValue(value);
            marker.appendChild(label);
            
            this.chartYAxis.appendChild(marker);
        });
        
        // Create x-axis
        const xAxisValues = this.calculateXAxisValues(data);
        xAxisValues.forEach(age => {
            const marker = document.createElement('div');
            marker.className = 'x-axis-marker';
            marker.style.position = 'absolute';
            marker.style.bottom = '0';
            marker.style.width = '100%';
            marker.style.textAlign = 'center';
            marker.style.fontSize = '12px';
            marker.style.color = '#a0a0a0';
            
            const x = this.getXPosition(age, data[0].age, data[data.length - 1].age);
            marker.style.left = `${x}px`;
            
            const label = document.createElement('div');
            label.className = 'x-axis-label';
            label.textContent = age;
            marker.appendChild(label);
            
            this.chartXAxis.appendChild(marker);
        });
        
        // Create line segments
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', '100%');
        svg.setAttribute('height', '100%');
        svg.style.position = 'absolute';
        svg.style.top = '0';
        svg.style.left = '0';
        
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        let pathData = '';
        
        data.forEach((point, index) => {
            const x = this.getXPosition(point.age, data[0].age, data[data.length - 1].age);
            const y = this.getYPosition(point.liquid_assets, minValue, maxValue);
            
            if (index === 0) {
                pathData += `M ${x} ${y}`;
            } else {
                pathData += ` L ${x} ${y}`;
            }
            
            // Add hover effect
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('cx', x);
            circle.setAttribute('cy', y);
            circle.setAttribute('r', '4');
            circle.setAttribute('fill', '#3498db');
            circle.style.opacity = '0';
            circle.style.transition = 'opacity 0.2s';
            
            circle.addEventListener('mouseover', () => {
                circle.style.opacity = '1';
                this.showTooltip(x, y, point);
            });
            
            circle.addEventListener('mouseout', () => {
                circle.style.opacity = '0';
                this.hideTooltip();
            });
            
            svg.appendChild(circle);
        });
        
        path.setAttribute('d', pathData);
        path.setAttribute('stroke', '#3498db');
        path.setAttribute('stroke-width', '2');
        path.setAttribute('fill', 'none');
        
        svg.appendChild(path);
        this.chartBars.appendChild(svg);
        
        // Update total value
        const currentAge = 30; // TODO: Get from user settings
        const currentValue = data.find(d => d.age === currentAge)?.liquid_assets || 0;
        this.totalValue.textContent = this.formatValue(currentValue);
        this.totalValue.className = 'liquidity-total-value ' + (currentValue >= 0 ? 'positive' : 'negative');
    }
    
    calculateYAxisValues(min, max) {
        const range = max - min;
        const step = Math.pow(10, Math.floor(Math.log10(range / 5)));
        const values = [];
        
        for (let value = Math.floor(min / step) * step; value <= max; value += step) {
            values.push(value);
        }
        
        return values;
    }
    
    calculateXAxisValues(data) {
        const startAge = data[0].age;
        const endAge = data[data.length - 1].age;
        const step = Math.ceil((endAge - startAge) / 5);
        const values = [];
        
        for (let age = startAge; age <= endAge; age += step) {
            values.push(age);
        }
        
        return values;
    }
    
    getXPosition(age, startAge, endAge) {
        const chartWidth = this.chartBars.clientWidth;
        return ((age - startAge) / (endAge - startAge)) * chartWidth;
    }
    
    getYPosition(value, min, max) {
        const chartHeight = this.chartBars.clientHeight;
        return chartHeight - ((value - min) / (max - min)) * chartHeight;
    }
    
    formatValue(value) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(value);
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