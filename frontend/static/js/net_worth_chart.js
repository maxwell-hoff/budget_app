// NOTE: Rewritten to use D3.js for band + line visualisation
// Dependencies: Make sure D3 v7+ is loaded before this script.

class NetWorthChart {
    constructor() {
        this.container = d3.select('#net-worth-chart');
        if (this.container.empty()) {
            console.error('NetWorthChart container not found');
            return;
        }

        // Prefer inner content wrapper to control sizing
        this.content = this.container.select('#net-worth-chart-content');
        if (this.content.empty()) {
            this.content = this.container; // fallback
        } else {
            // Ensure the content wrapper is visible
            this.content.style('display', 'block');
        }

        // Use the bars container (same element original chart used) for absolute positioning
        this.barsContainer = this.container.select('#net-worth-chart-bars');
        if (this.barsContainer.empty()) {
            this.barsContainer = this.content; // fallback
        }

        // Dimensions -------------------------------------------------------
        this.margin = { top: 20, right: 20, bottom: 40, left: 60 };
        this.width = this.container.node().clientWidth - this.margin.left - this.margin.right;
        this.height = 250; // fixed height for now

        // SVG setup --------------------------------------------------------
        this.svg = this.barsContainer
            .append('svg')
            .style('position','absolute')
            .style('top',0)
            .style('left',0)
            .attr('width', this.width + this.margin.left + this.margin.right)
            .attr('height', this.height + this.margin.top + this.margin.bottom)
            .append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);

        // Scales -----------------------------------------------------------
        this.xScale = d3.scaleLinear();
        this.yScale = d3.scaleLinear();

        // Axes -------------------------------------------------------------
        this.xAxisGroup = this.svg.append('g').attr('class', 'x-axis').attr('transform', `translate(0,${this.height})`);
        this.yAxisGroup = this.svg.append('g').attr('class', 'y-axis');

        // Area + line groups ----------------------------------------------
        this.areaGroup = this.svg.append('g').attr('class', 'range-area');
        // Monte Carlo band (drawn on top so colour stands out)
        this.mcAreaGroup = this.svg.append('g').attr('class', 'mc-range-area');
        this.lineGroup = this.svg.append('g').attr('class', 'scenario-line');

        // ------------------------------------------------------------------
        //  State for panning (vertical translation)
        // ------------------------------------------------------------------
        this.panOffset = 0; // additive offset in y-value units

        // Tooltip value display (reuse existing markup) --------------------
        this.valueDisplay = this.container.select('.net-worth-total-value');

        // Zoom factor ------------------------------------------------------
        this.zoomFactor = 1; // 1 = default scale
        this.minZoomFactor = 1/128; // allow up to 7 successive zoom-in clicks

        // Hook up zoom buttons -------------------------------------------
        const zoomInBtn = this.container.select('.net-worth-zoom-button.zoom-in');
        const zoomOutBtn = this.container.select('.net-worth-zoom-button.zoom-out');
        const panUpBtn = this.container.select('.net-worth-pan-button.pan-up');
        const panDownBtn = this.container.select('.net-worth-pan-button.pan-down');
        if (!zoomInBtn.empty()) {
            zoomInBtn.on('click', () => {
                // Halve the domain span (zoom in)
                this.zoomFactor = Math.max(this.zoomFactor / 2, this.minZoomFactor);
                this._render();
            });
        }
        if (!panUpBtn.empty()) {
            panUpBtn.on('click', () => {
                const span = this.yScale.domain()[1] - this.yScale.domain()[0];
                this.panOffset += span / 2;
                this._render();
            });
        }
        if (!panDownBtn.empty()) {
            panDownBtn.on('click', () => {
                const span = this.yScale.domain()[1] - this.yScale.domain()[0];
                this.panOffset -= span / 2;
                this._render();
            });
        }

        if (!zoomOutBtn.empty()) {
            zoomOutBtn.on('click', () => {
                // Double the domain span (zoom out) but cap at 1 (original)
                this.zoomFactor = Math.min(this.zoomFactor * 2, 1);
                this._render();
            });
        }

        // Data holders -----------------------------------------------------
        this.rangeData = [];
        this.mcRangeData = [];
        this.lineData = [];
    }

    setRangeData(rangeData) {
        this.rangeData = rangeData || [];
        this._render();
    }

    setMcRangeData(mcRangeData) {
        this.mcRangeData = mcRangeData || [];
        this._render();
    }

    setLineData(lineData) {
        this.lineData = lineData || [];
        this._render();
    }

    _render() {
        // Refresh dimensions in case container resized after first load
        const newW = this.container.node().clientWidth - this.margin.left - this.margin.right;
        if (newW !== this.width && newW > 0) {
            this.width = newW;
            // Update SVG outer width
            this.barsContainer.select('svg')
                .attr('width', this.width + this.margin.left + this.margin.right);
        }

        if (!this.rangeData.length && !this.mcRangeData.length && !this.lineData.length) return;

        // Combine data to compute domains ---------------------------------
        const ages = [...new Set([
            ...this.rangeData.map(d => d.age),
            ...this.lineData.map(d => d.age),
            ...this.mcRangeData.map(d => d.age),
        ])];
        if (!ages.length) return;

        const xMin = d3.min(ages);
        const xMax = d3.max(ages);

        let yVals = [];
        if (this.rangeData.length) {
            yVals.push(d3.min(this.rangeData, d => d.min_net_worth));
            yVals.push(d3.max(this.rangeData, d => d.max_net_worth));
        }
        if (this.mcRangeData.length) {
            yVals.push(d3.min(this.mcRangeData, d => d.min_net_worth));
            yVals.push(d3.max(this.mcRangeData, d => d.max_net_worth));
        }
        if (this.lineData.length) {
            yVals.push(d3.min(this.lineData, d => d.net_worth));
            yVals.push(d3.max(this.lineData, d => d.net_worth));
        }
        const rawYMin = d3.min(yVals);
        const rawYMax = d3.max(yVals);

        let yMin = rawYMin;
        let yMax = rawYMax;
        if (this.zoomFactor !== 1) {
            const mid = (rawYMin + rawYMax) / 2;
            const halfSpan = (rawYMax - rawYMin) * this.zoomFactor / 2;
            yMin = mid - halfSpan;
            yMax = mid + halfSpan;
        }

        this.xScale.domain([xMin, xMax]).range([0, this.width]);
        // Apply vertical panning offset ----------------------------------
        yMin += this.panOffset;
        yMax += this.panOffset;

        this.yScale.domain([yMin, yMax]).range([this.height, 0]).nice();

        // Render axes ------------------------------------------------------
        const xAxis = d3.axisBottom(this.xScale).tickFormat(d => d).ticks(10);
        const yAxis = d3.axisLeft(this.yScale).ticks(6).tickFormat(this._formatValue);

        this.xAxisGroup.call(xAxis);
        this.yAxisGroup.call(yAxis);

        // Range area -------------------------------------------------------
        if (this.rangeData.length) {
            // Sort by age to ensure correct path
            const sorted = [...this.rangeData].sort((a, b) => a.age - b.age);
            const areaGenerator = d3.area()
                .x(d => this.xScale(d.age))
                .y0(d => this.yScale(d.min_net_worth))
                .y1(d => this.yScale(d.max_net_worth));

            const areaSelection = this.areaGroup.selectAll('path').data([sorted]);
            areaSelection.join('path')
                .attr('d', areaGenerator)
                .attr('fill', '#b3d3f3')
                .attr('opacity', 0.5);
        }

        // Monte Carlo range -------------------------------------------------
        if (this.mcRangeData.length) {
            const sortedMc = [...this.mcRangeData].sort((a, b) => a.age - b.age);
            const mcArea = d3.area()
                .x(d => this.xScale(d.age))
                .y0(d => this.yScale(d.min_net_worth))
                .y1(d => this.yScale(d.max_net_worth));

            const mcSel = this.mcAreaGroup.selectAll('path').data([sortedMc]);
            mcSel.join('path')
                .attr('d', mcArea)
                .attr('fill', '#ffcc99')
                .attr('opacity', 0.5);
        }

        // Scenario line ----------------------------------------------------
        if (this.lineData.length) {
            const sortedLine = [...this.lineData].sort((a, b) => a.age - b.age);
            const lineGenerator = d3.line()
                .x(d => this.xScale(d.age))
                .y(d => this.yScale(d.net_worth));

            const lineSel = this.lineGroup.selectAll('path').data([sortedLine]);
            lineSel.join('path')
                .attr('d', lineGenerator)
                .attr('fill', 'none')
                .attr('stroke', '#0d6efd')
                .attr('stroke-width', 2);

            // Update value display on latest age
            const last = sortedLine[sortedLine.length - 1];
            if (this.valueDisplay && last) {
                this.valueDisplay.text(this._formatValue(last.net_worth));
            }
        }
    }

    _formatValue = (val) => {
        const abs = Math.abs(val);
        if (abs >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`;
        if (abs >= 1_000) return `$${(val / 1_000).toFixed(1)}K`;
        return `$${val.toFixed(0)}`;
    }
}

// Global initialisation -----------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
    window.netWorthChart = new NetWorthChart();
}); 