class NPVChart {
    constructor() {
        this.chart = document.getElementById('npv-chart');
        this.chartContent = document.getElementById('npv-chart-content');
        this.chartBars = document.getElementById('npv-chart-bars');
        this.chartXAxis = document.getElementById('npv-chart-x-axis');
        this.verticalSpacing = 30; // Match timeline's vertical spacing
        this.barHeight = 6; // Reduced from 20 to match timeline marker height
        this.padding = 20; // padding around the chart
    }

    updateChart(milestones) {
        // Clear existing content
        this.chartBars.innerHTML = '';
        this.chartXAxis.innerHTML = '';
        
        if (!milestones || milestones.length === 0) {
            this.chartContent.style.display = 'none';
            return;
        }

        this.chartContent.style.display = 'block';

        // Calculate NPVs for all milestones
        const npvs = this.calculateNPVs(milestones);
        
        // Calculate total NPV
        const totalNPV = npvs.reduce((sum, npv) => sum + npv.value, 0);
        
        // Add total NPV as first row
        npvs.unshift({
            name: 'Present Surplus / Shortfall',
            value: totalNPV,
            isTotal: true
        });

        // Find max absolute value for x-axis scaling
        const maxAbsValue = Math.max(...npvs.map(npv => Math.abs(npv.value)));
        
        // Create x-axis markers and labels
        this.createXAxis(maxAbsValue);
        
        // Create bars for each NPV
        npvs.forEach((npv, index) => {
            this.createBar(npv, index, maxAbsValue);
        });

        // Adjust chart height based on number of bars
        const requiredHeight = (npvs.length * (this.barHeight + this.verticalSpacing)) + this.padding;
        this.chart.style.height = `${requiredHeight}px`;
    }

    createXAxis(maxAbsValue) {
        // Calculate initial interval of 100,000
        let interval = 100000;
        
        // Calculate how many markers we would have with current interval
        let numMarkers = Math.ceil(maxAbsValue / interval) * 2 + 1; // +1 for zero
        
        // Keep doubling the interval until we have 10 or fewer markers
        while (numMarkers > 10) {
            interval *= 2;
            numMarkers = Math.ceil(maxAbsValue / interval) * 2 + 1;
        }

        // Round maxAbsValue up to nearest multiple of interval
        const roundedMax = Math.ceil(maxAbsValue / interval) * interval;

        // Create markers and labels
        const chartWidth = this.chart.offsetWidth;
        const center = chartWidth / 2;
        
        // Add x-axis line
        const line = document.createElement('div');
        line.className = 'x-axis-line';
        this.chartXAxis.appendChild(line);
        
        for (let value = -roundedMax; value <= roundedMax; value += interval) {
            const position = center + (value / roundedMax) * (chartWidth / 2);
            
            // Create marker
            const marker = document.createElement('div');
            marker.className = 'x-axis-marker';
            marker.style.left = `${position}px`;
            this.chartXAxis.appendChild(marker);

            // Create label
            const label = document.createElement('div');
            label.className = 'x-axis-label';
            label.textContent = this.formatValue(value);
            label.style.left = `${position}px`;
            this.chartXAxis.appendChild(label);
        }
    }

    createBar(npv, index, maxAbsValue) {
        const chartWidth = this.chart.offsetWidth;
        const center = chartWidth / 2;
        const barWidth = Math.abs(npv.value / maxAbsValue) * (chartWidth / 2);
        const top = index * (this.barHeight + this.verticalSpacing) + this.padding;
        
        // Create bar
        const bar = document.createElement('div');
        bar.className = `npv-bar ${npv.value >= 0 ? 'positive' : 'negative'}`;
        bar.style.top = `${top}px`;
        bar.style.height = `${this.barHeight}px`;
        
        if (npv.value >= 0) {
            bar.style.left = `${center}px`;
            bar.style.width = `${barWidth}px`;
        } else {
            bar.style.left = `${center - barWidth}px`;
            bar.style.width = `${barWidth}px`;
        }
        
        // Add data-id attribute if not the total row
        if (!npv.isTotal) {
            bar.setAttribute('data-id', npv.id);
            
            // Add hover functionality
            bar.addEventListener('mouseenter', () => {
                highlightMilestone(npv.id);
            });
            
            bar.addEventListener('mouseleave', () => {
                unhighlightMilestone(npv.id);
            });
        }
        
        this.chartBars.appendChild(bar);

        // Create label
        const label = document.createElement('div');
        label.className = `npv-label ${npv.isTotal ? 'bold' : ''}`;
        label.textContent = npv.name;
        label.style.top = `${top - 10}px`;
        
        // Add data-id attribute and hover functionality if not the total row
        if (!npv.isTotal) {
            label.setAttribute('data-id', npv.id);
            
            label.addEventListener('mouseenter', () => {
                highlightMilestone(npv.id);
            });
            
            label.addEventListener('mouseleave', () => {
                unhighlightMilestone(npv.id);
            });
        }
        
        this.chartBars.appendChild(label);
    }

    formatValue(value) {
        if (Math.abs(value) >= 1000000) {
            return `$${(value / 1000000).toFixed(1)}M`;
        } else if (Math.abs(value) >= 1000) {
            return `$${(value / 1000).toFixed(1)}K`;
        }
        return `$${value.toFixed(0)}`;
    }

    calculateNPVs(milestones) {
        return milestones.map(milestone => {
            let npv = 0;
            
            if (milestone.milestone_type === 'Expense' || milestone.milestone_type === 'Income') {
                if (milestone.disbursement_type === 'Fixed Duration') {
                    npv = this.calculateAnnuityNPV(
                        milestone.amount,
                        milestone.rate_of_return,
                        milestone.duration,
                        milestone.occurrence === 'Monthly'
                    );
                }
            } else if (milestone.milestone_type === 'Asset' || milestone.milestone_type === 'Liability') {
                npv = this.calculateLoanNPV(
                    milestone.amount,
                    milestone.payment,
                    milestone.rate_of_return,
                    milestone.duration,
                    milestone.occurrence === 'Monthly'
                );
            }

            // Invert NPV for expenses and liabilities
            if (milestone.milestone_type === 'Expense' || milestone.milestone_type === 'Liability') {
                npv = -npv;
            }

            return {
                name: milestone.name,
                value: npv,
                id: milestone.id // Add milestone ID to the NPV object
            };
        });
    }

    calculateAnnuityNPV(amount, rate, periods, isMonthly) {
        // Convert annual rate to periodic rate if monthly
        const periodicRate = isMonthly ? rate / 12 : rate;
        const n = isMonthly ? periods : periods;
        
        // Calculate NPV using annuity formula
        if (periodicRate === 0) {
            return amount * n;
        }
        
        return amount * (1 - Math.pow(1 + periodicRate, -n)) / periodicRate;
    }

    calculateLoanNPV(principal, payment, rate, periods, isMonthly) {
        // Convert annual rate to periodic rate if monthly
        const periodicRate = isMonthly ? rate / 12 : rate;
        const n = isMonthly ? periods : periods;
        
        // Calculate NPV using loan formula
        if (periodicRate === 0) {
            return principal - (payment * n);
        }
        
        const pvOfPayments = payment * (1 - Math.pow(1 + periodicRate, -n)) / periodicRate;
        return principal - pvOfPayments;
    }
}

// Initialize chart when the document is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.npvChart = new NPVChart();
}); 