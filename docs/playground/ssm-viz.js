/**
 * SSM Visualization Module for AAP Playground
 *
 * Renders self-similarity matrices and similarity timelines as interactive
 * canvas-based visualizations. Designed for behavioral drift analysis.
 *
 * Features:
 * - High-DPI/Retina display support
 * - Viridis color scale (perceptually uniform)
 * - Threshold highlighting
 * - Interactive tooltips
 * - Dark mode support
 * - Responsive canvas sizing
 * - Accessibility support
 *
 * @module ssm-viz
 */

/**
 * Viridis color scale - perceptually uniform, colorblind-friendly
 * Interpolated from matplotlib's viridis colormap
 */
const VIRIDIS = [
    [68, 1, 84],      // 0.0 - dark purple
    [72, 35, 116],    // 0.1
    [64, 67, 135],    // 0.2
    [52, 94, 141],    // 0.3
    [41, 120, 142],   // 0.4
    [32, 144, 140],   // 0.5
    [34, 167, 132],   // 0.6
    [68, 190, 112],   // 0.7
    [121, 209, 81],   // 0.8
    [189, 222, 38],   // 0.9
    [253, 231, 37],   // 1.0 - bright yellow
];

/**
 * Interpolate viridis color for a value in [0, 1]
 * @param {number} t - Value between 0 and 1
 * @returns {string} RGB color string
 */
function viridisColor(t) {
    t = Math.max(0, Math.min(1, t));
    const idx = t * (VIRIDIS.length - 1);
    const lower = Math.floor(idx);
    const upper = Math.min(lower + 1, VIRIDIS.length - 1);
    const frac = idx - lower;

    const r = Math.round(VIRIDIS[lower][0] + frac * (VIRIDIS[upper][0] - VIRIDIS[lower][0]));
    const g = Math.round(VIRIDIS[lower][1] + frac * (VIRIDIS[upper][1] - VIRIDIS[lower][1]));
    const b = Math.round(VIRIDIS[lower][2] + frac * (VIRIDIS[upper][2] - VIRIDIS[lower][2]));

    return `rgb(${r}, ${g}, ${b})`;
}

/**
 * Get contrasting text color (black or white) for a background
 * @param {number} t - Background value in [0, 1]
 * @returns {string} Text color
 */
function contrastColor(t) {
    // Viridis is dark at low values, light at high
    return t > 0.6 ? '#1a1a2e' : '#ffffff';
}

/**
 * SSMVisualizer class - renders self-similarity matrices and timelines
 */
class SSMVisualizer {
    /**
     * Create an SSM visualizer
     * @param {string} containerId - ID of the container element
     * @param {Object} options - Configuration options
     */
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            throw new Error(`Container element '${containerId}' not found`);
        }

        this.options = {
            width: options.width || 400,
            height: options.height || 400,
            margin: options.margin || { top: 40, right: 60, bottom: 50, left: 60 },
            threshold: options.threshold || 0.30,
            showLabels: options.showLabels !== false,
            showGrid: options.showGrid !== false,
            showTooltip: options.showTooltip !== false,
            animated: options.animated !== false,
            ...options
        };

        this._createCanvas();
        this._setupInteraction();

        // Track current data for re-rendering
        this._currentData = null;
        this._currentMode = null;
    }

    /**
     * Create and configure the canvas element
     * @private
     */
    _createCanvas() {
        // Create canvas element
        this.canvas = document.createElement('canvas');
        this.canvas.className = 'ssm-canvas';
        this.canvas.setAttribute('role', 'img');

        // High-DPI support
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width = this.options.width * dpr;
        this.canvas.height = this.options.height * dpr;
        this.canvas.style.width = `${this.options.width}px`;
        this.canvas.style.height = `${this.options.height}px`;

        this.ctx = this.canvas.getContext('2d');
        this.ctx.scale(dpr, dpr);

        // Clear container and add canvas
        this.container.innerHTML = '';
        this.container.appendChild(this.canvas);

        // Create tooltip element
        if (this.options.showTooltip) {
            this.tooltip = document.createElement('div');
            this.tooltip.className = 'ssm-tooltip';
            this.tooltip.setAttribute('role', 'tooltip');
            this.tooltip.hidden = true;
            this.container.appendChild(this.tooltip);
        }
    }

    /**
     * Set up mouse/touch interaction for tooltips
     * @private
     */
    _setupInteraction() {
        if (!this.options.showTooltip) return;

        let rafId = null;

        const handleMove = (e) => {
            if (rafId) return;
            rafId = requestAnimationFrame(() => {
                this._handleHover(e);
                rafId = null;
            });
        };

        this.canvas.addEventListener('mousemove', handleMove);
        this.canvas.addEventListener('mouseleave', () => {
            if (this.tooltip) this.tooltip.hidden = true;
        });

        // Touch support
        this.canvas.addEventListener('touchstart', (e) => {
            e.preventDefault();
            this._handleHover(e.touches[0]);
        });
    }

    /**
     * Handle hover/touch interaction
     * @private
     */
    _handleHover(e) {
        if (!this._currentData || !this.tooltip) return;

        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const { margin } = this.options;
        const plotWidth = this.options.width - margin.left - margin.right;
        const plotHeight = this.options.height - margin.top - margin.bottom;

        // Check if within plot area
        if (x < margin.left || x > margin.left + plotWidth ||
            y < margin.top || y > margin.top + plotHeight) {
            this.tooltip.hidden = true;
            return;
        }

        if (this._currentMode === 'matrix') {
            this._showMatrixTooltip(x, y, plotWidth, plotHeight);
        } else if (this._currentMode === 'timeline') {
            this._showTimelineTooltip(x, y, plotWidth, plotHeight);
        }
    }

    /**
     * Show tooltip for matrix hover
     * @private
     */
    _showMatrixTooltip(x, y, plotWidth, plotHeight) {
        const { matrix, traceIds } = this._currentData;
        const { margin } = this.options;

        const n = matrix.length;
        const cellWidth = plotWidth / n;
        const cellHeight = plotHeight / n;

        const col = Math.floor((x - margin.left) / cellWidth);
        const row = Math.floor((y - margin.top) / cellHeight);

        if (row >= 0 && row < n && col >= 0 && col < n) {
            const similarity = matrix[row][col];
            const isBelowThreshold = similarity < this.options.threshold && row !== col;

            this.tooltip.innerHTML = `
                <div class="ssm-tooltip-title">${traceIds[row]} &harr; ${traceIds[col]}</div>
                <div class="ssm-tooltip-value ${isBelowThreshold ? 'below-threshold' : ''}">
                    Similarity: <strong>${similarity.toFixed(4)}</strong>
                </div>
                ${isBelowThreshold ? '<div class="ssm-tooltip-warning">Below threshold</div>' : ''}
            `;

            this.tooltip.style.left = `${x + 10}px`;
            this.tooltip.style.top = `${y + 10}px`;
            this.tooltip.hidden = false;
        }
    }

    /**
     * Show tooltip for timeline hover
     * @private
     */
    _showTimelineTooltip(x, y, plotWidth, plotHeight) {
        const { similarities, traceIds, trend } = this._currentData;
        const { margin } = this.options;

        const n = similarities.length;
        const barWidth = plotWidth / n;
        const barIndex = Math.floor((x - margin.left) / barWidth);

        if (barIndex >= 0 && barIndex < n) {
            const similarity = similarities[barIndex];
            const isBelowThreshold = similarity < this.options.threshold;

            this.tooltip.innerHTML = `
                <div class="ssm-tooltip-title">${traceIds[barIndex]}</div>
                <div class="ssm-tooltip-value ${isBelowThreshold ? 'below-threshold' : ''}">
                    Similarity: <strong>${similarity.toFixed(4)}</strong>
                </div>
                ${isBelowThreshold ? '<div class="ssm-tooltip-warning">Below threshold</div>' : ''}
                <div class="ssm-tooltip-meta">Trace ${barIndex + 1} of ${n}</div>
            `;

            this.tooltip.style.left = `${x + 10}px`;
            this.tooltip.style.top = `${y + 10}px`;
            this.tooltip.hidden = false;
        }
    }

    /**
     * Render NxN self-similarity matrix as a heatmap
     * @param {Object} data - SSM data from SSMAnalyzer.analyze()
     * @param {Object} options - Render options
     */
    renderMatrix(data, options = {}) {
        const { matrix, traceIds, size } = data;

        if (!matrix || size === 0) {
            this._renderEmpty('No data to display');
            return;
        }

        this._currentData = data;
        this._currentMode = 'matrix';

        const threshold = options.threshold ?? this.options.threshold;
        const { margin } = this.options;
        const width = this.options.width;
        const height = this.options.height;
        const plotWidth = width - margin.left - margin.right;
        const plotHeight = height - margin.top - margin.bottom;

        // Clear canvas
        this.ctx.clearRect(0, 0, width, height);

        // Draw title
        this._drawTitle('Self-Similarity Matrix');

        // Calculate cell dimensions
        const n = matrix.length;
        const cellWidth = plotWidth / n;
        const cellHeight = plotHeight / n;

        // Draw cells
        for (let i = 0; i < n; i++) {
            for (let j = 0; j < n; j++) {
                const similarity = matrix[i][j];
                const x = margin.left + j * cellWidth;
                const y = margin.top + i * cellHeight;

                // Fill cell with viridis color
                this.ctx.fillStyle = viridisColor(similarity);
                this.ctx.fillRect(x, y, cellWidth, cellHeight);

                // Highlight below-threshold cells (not on diagonal)
                if (similarity < threshold && i !== j) {
                    this.ctx.strokeStyle = '#ff4444';
                    this.ctx.lineWidth = 2;
                    this.ctx.strokeRect(x + 1, y + 1, cellWidth - 2, cellHeight - 2);
                }

                // Show value in cell if cells are large enough
                if (cellWidth > 40 && cellHeight > 25) {
                    this.ctx.fillStyle = contrastColor(similarity);
                    this.ctx.font = '10px ui-monospace, monospace';
                    this.ctx.textAlign = 'center';
                    this.ctx.textBaseline = 'middle';
                    this.ctx.fillText(similarity.toFixed(2), x + cellWidth / 2, y + cellHeight / 2);
                }
            }
        }

        // Draw grid
        if (this.options.showGrid) {
            this.ctx.strokeStyle = this._getColor('border');
            this.ctx.lineWidth = 0.5;
            for (let i = 0; i <= n; i++) {
                // Vertical lines
                this.ctx.beginPath();
                this.ctx.moveTo(margin.left + i * cellWidth, margin.top);
                this.ctx.lineTo(margin.left + i * cellWidth, margin.top + plotHeight);
                this.ctx.stroke();
                // Horizontal lines
                this.ctx.beginPath();
                this.ctx.moveTo(margin.left, margin.top + i * cellHeight);
                this.ctx.lineTo(margin.left + plotWidth, margin.top + i * cellHeight);
                this.ctx.stroke();
            }
        }

        // Draw axis labels
        if (this.options.showLabels && traceIds) {
            this._drawMatrixLabels(traceIds, cellWidth, cellHeight);
        }

        // Draw color scale legend
        this._drawColorScale(threshold);

        // Update ARIA label
        this.canvas.setAttribute('aria-label',
            `Self-similarity matrix with ${n} traces. ` +
            `${this._countBelowThreshold(matrix, threshold)} pairs below threshold ${threshold}.`
        );
    }

    /**
     * Render similarity timeline as a bar chart
     * @param {Object} data - Data from SSMAnalyzer.analyze_against_card()
     * @param {Object} options - Render options
     */
    renderTimeline(data, options = {}) {
        const { similarities, traceIds, mean_similarity, min_similarity, trend } = data;

        if (!similarities || similarities.length === 0) {
            this._renderEmpty('No data to display');
            return;
        }

        this._currentData = data;
        this._currentMode = 'timeline';

        const threshold = options.threshold ?? this.options.threshold;
        const { margin } = this.options;
        const width = this.options.width;
        const height = this.options.height;
        const plotWidth = width - margin.left - margin.right;
        const plotHeight = height - margin.top - margin.bottom;

        // Clear canvas
        this.ctx.clearRect(0, 0, width, height);

        // Draw title
        this._drawTitle('Trace-to-Card Similarity');

        const n = similarities.length;
        const barWidth = (plotWidth / n) * 0.8;
        const barSpacing = (plotWidth / n) * 0.2;
        const maxSim = 1.0;

        // Draw threshold line
        const thresholdY = margin.top + plotHeight * (1 - threshold / maxSim);
        this.ctx.strokeStyle = '#ff6b6b';
        this.ctx.lineWidth = 2;
        this.ctx.setLineDash([6, 4]);
        this.ctx.beginPath();
        this.ctx.moveTo(margin.left, thresholdY);
        this.ctx.lineTo(margin.left + plotWidth, thresholdY);
        this.ctx.stroke();
        this.ctx.setLineDash([]);

        // Draw threshold label
        this.ctx.fillStyle = '#ff6b6b';
        this.ctx.font = '11px system-ui, sans-serif';
        this.ctx.textAlign = 'left';
        this.ctx.fillText(`Threshold: ${threshold.toFixed(2)}`, margin.left + plotWidth + 5, thresholdY + 4);

        // Draw mean line
        const meanY = margin.top + plotHeight * (1 - mean_similarity / maxSim);
        this.ctx.strokeStyle = this._getColor('primary');
        this.ctx.lineWidth = 1.5;
        this.ctx.setLineDash([4, 2]);
        this.ctx.beginPath();
        this.ctx.moveTo(margin.left, meanY);
        this.ctx.lineTo(margin.left + plotWidth, meanY);
        this.ctx.stroke();
        this.ctx.setLineDash([]);

        // Draw mean label
        this.ctx.fillStyle = this._getColor('primary');
        this.ctx.fillText(`Mean: ${mean_similarity.toFixed(2)}`, margin.left + plotWidth + 5, meanY + 4);

        // Draw bars
        for (let i = 0; i < n; i++) {
            const sim = similarities[i];
            const barHeight = (sim / maxSim) * plotHeight;
            const x = margin.left + i * (barWidth + barSpacing) + barSpacing / 2;
            const y = margin.top + plotHeight - barHeight;

            // Color based on threshold
            const isBelowThreshold = sim < threshold;
            this.ctx.fillStyle = isBelowThreshold ? '#ff6b6b' : viridisColor(sim);

            // Draw bar with rounded top
            this._drawRoundedBar(x, y, barWidth, barHeight, 3);

            // Draw value label above bar
            if (barWidth > 30) {
                this.ctx.fillStyle = this._getColor('text-secondary');
                this.ctx.font = '10px ui-monospace, monospace';
                this.ctx.textAlign = 'center';
                this.ctx.fillText(sim.toFixed(2), x + barWidth / 2, y - 5);
            }
        }

        // Draw axes
        this._drawAxes(plotWidth, plotHeight, n, traceIds);

        // Draw trend indicator
        if (trend !== undefined) {
            this._drawTrendIndicator(trend, plotWidth, plotHeight);
        }

        // Update ARIA label
        const belowCount = similarities.filter(s => s < threshold).length;
        this.canvas.setAttribute('aria-label',
            `Similarity timeline with ${n} traces. ` +
            `Mean similarity: ${mean_similarity.toFixed(2)}. ` +
            `${belowCount} traces below threshold ${threshold}.`
        );
    }

    /**
     * Update threshold and re-render
     * @param {number} threshold - New threshold value
     */
    setThreshold(threshold) {
        this.options.threshold = threshold;
        if (this._currentData && this._currentMode) {
            if (this._currentMode === 'matrix') {
                this.renderMatrix(this._currentData, { threshold });
            } else if (this._currentMode === 'timeline') {
                this.renderTimeline(this._currentData, { threshold });
            }
        }
    }

    /**
     * Resize the visualization
     * @param {number} width - New width
     * @param {number} height - New height
     */
    resize(width, height) {
        this.options.width = width;
        this.options.height = height;

        const dpr = window.devicePixelRatio || 1;
        this.canvas.width = width * dpr;
        this.canvas.height = height * dpr;
        this.canvas.style.width = `${width}px`;
        this.canvas.style.height = `${height}px`;

        this.ctx = this.canvas.getContext('2d');
        this.ctx.scale(dpr, dpr);

        // Re-render with current data
        if (this._currentData && this._currentMode) {
            if (this._currentMode === 'matrix') {
                this.renderMatrix(this._currentData);
            } else if (this._currentMode === 'timeline') {
                this.renderTimeline(this._currentData);
            }
        }
    }

    /**
     * Clear the visualization
     */
    clear() {
        this.ctx.clearRect(0, 0, this.options.width, this.options.height);
        this._currentData = null;
        this._currentMode = null;
        if (this.tooltip) this.tooltip.hidden = true;
    }

    // ============ Private Helper Methods ============

    /**
     * Draw title text
     * @private
     */
    _drawTitle(text) {
        this.ctx.fillStyle = this._getColor('text');
        this.ctx.font = 'bold 14px system-ui, sans-serif';
        this.ctx.textAlign = 'center';
        this.ctx.fillText(text, this.options.width / 2, 20);
    }

    /**
     * Draw empty state message
     * @private
     */
    _renderEmpty(message) {
        const { width, height } = this.options;
        this.ctx.clearRect(0, 0, width, height);

        this.ctx.fillStyle = this._getColor('text-secondary');
        this.ctx.font = '14px system-ui, sans-serif';
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.fillText(message, width / 2, height / 2);
    }

    /**
     * Draw matrix axis labels
     * @private
     */
    _drawMatrixLabels(traceIds, cellWidth, cellHeight) {
        const { margin } = this.options;
        const n = traceIds.length;

        this.ctx.fillStyle = this._getColor('text-secondary');
        this.ctx.font = '10px ui-monospace, monospace';

        for (let i = 0; i < n; i++) {
            // Truncate long IDs
            const label = traceIds[i].length > 8
                ? traceIds[i].slice(0, 6) + '..'
                : traceIds[i];

            // X-axis labels (bottom)
            this.ctx.save();
            this.ctx.translate(
                margin.left + i * cellWidth + cellWidth / 2,
                margin.top + n * cellHeight + 10
            );
            this.ctx.rotate(-Math.PI / 4);
            this.ctx.textAlign = 'right';
            this.ctx.fillText(label, 0, 0);
            this.ctx.restore();

            // Y-axis labels (left)
            this.ctx.textAlign = 'right';
            this.ctx.textBaseline = 'middle';
            this.ctx.fillText(label, margin.left - 5, margin.top + i * cellHeight + cellHeight / 2);
        }
    }

    /**
     * Draw axes for timeline chart
     * @private
     */
    _drawAxes(plotWidth, plotHeight, n, traceIds) {
        const { margin } = this.options;

        // Y-axis
        this.ctx.strokeStyle = this._getColor('border');
        this.ctx.lineWidth = 1;
        this.ctx.beginPath();
        this.ctx.moveTo(margin.left, margin.top);
        this.ctx.lineTo(margin.left, margin.top + plotHeight);
        this.ctx.lineTo(margin.left + plotWidth, margin.top + plotHeight);
        this.ctx.stroke();

        // Y-axis ticks and labels
        this.ctx.fillStyle = this._getColor('text-secondary');
        this.ctx.font = '10px ui-monospace, monospace';
        this.ctx.textAlign = 'right';
        this.ctx.textBaseline = 'middle';

        for (let i = 0; i <= 10; i += 2) {
            const y = margin.top + plotHeight * (1 - i / 10);
            const value = i / 10;

            // Tick
            this.ctx.beginPath();
            this.ctx.moveTo(margin.left - 5, y);
            this.ctx.lineTo(margin.left, y);
            this.ctx.stroke();

            // Label
            this.ctx.fillText(value.toFixed(1), margin.left - 8, y);
        }

        // Y-axis title
        this.ctx.save();
        this.ctx.translate(15, margin.top + plotHeight / 2);
        this.ctx.rotate(-Math.PI / 2);
        this.ctx.textAlign = 'center';
        this.ctx.fillStyle = this._getColor('text');
        this.ctx.font = '11px system-ui, sans-serif';
        this.ctx.fillText('Similarity Score', 0, 0);
        this.ctx.restore();

        // X-axis labels
        if (this.options.showLabels && traceIds) {
            const barWidth = plotWidth / n;
            this.ctx.textAlign = 'center';

            for (let i = 0; i < n; i++) {
                const x = margin.left + i * barWidth + barWidth / 2;

                // Show every label if few traces, otherwise show subset
                if (n <= 10 || i % Math.ceil(n / 10) === 0) {
                    this.ctx.save();
                    this.ctx.translate(x, margin.top + plotHeight + 10);
                    this.ctx.rotate(-Math.PI / 4);
                    this.ctx.textAlign = 'right';
                    this.ctx.fillStyle = this._getColor('text-secondary');
                    this.ctx.font = '9px ui-monospace, monospace';

                    const label = traceIds[i].length > 10
                        ? traceIds[i].slice(0, 8) + '..'
                        : traceIds[i];
                    this.ctx.fillText(label, 0, 0);
                    this.ctx.restore();
                }
            }
        }

        // X-axis title
        this.ctx.fillStyle = this._getColor('text');
        this.ctx.font = '11px system-ui, sans-serif';
        this.ctx.textAlign = 'center';
        this.ctx.fillText('Trace Sequence', margin.left + plotWidth / 2, this.options.height - 5);
    }

    /**
     * Draw color scale legend
     * @private
     */
    _drawColorScale(threshold) {
        const { margin, width, height } = this.options;
        const legendWidth = 15;
        const legendHeight = height - margin.top - margin.bottom;
        const x = width - margin.right + 15;
        const y = margin.top;

        // Draw gradient
        for (let i = 0; i < legendHeight; i++) {
            const t = 1 - (i / legendHeight);
            this.ctx.fillStyle = viridisColor(t);
            this.ctx.fillRect(x, y + i, legendWidth, 1);
        }

        // Draw border
        this.ctx.strokeStyle = this._getColor('border');
        this.ctx.lineWidth = 1;
        this.ctx.strokeRect(x, y, legendWidth, legendHeight);

        // Draw threshold marker
        const thresholdY = y + legendHeight * (1 - threshold);
        this.ctx.strokeStyle = '#ff4444';
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();
        this.ctx.moveTo(x - 3, thresholdY);
        this.ctx.lineTo(x + legendWidth + 3, thresholdY);
        this.ctx.stroke();

        // Draw scale labels
        this.ctx.fillStyle = this._getColor('text-secondary');
        this.ctx.font = '9px ui-monospace, monospace';
        this.ctx.textAlign = 'left';
        this.ctx.fillText('1.0', x + legendWidth + 5, y + 4);
        this.ctx.fillText('0.5', x + legendWidth + 5, y + legendHeight / 2);
        this.ctx.fillText('0.0', x + legendWidth + 5, y + legendHeight);
    }

    /**
     * Draw trend indicator arrow
     * @private
     */
    _drawTrendIndicator(trend, plotWidth, plotHeight) {
        const { margin } = this.options;
        const x = margin.left + plotWidth - 60;
        const y = margin.top + 15;

        // Draw background
        this.ctx.fillStyle = this._getColor('bg-elevated');
        this.ctx.strokeStyle = this._getColor('border');
        this.ctx.lineWidth = 1;
        this.ctx.beginPath();
        this.ctx.roundRect(x - 5, y - 12, 55, 22, 4);
        this.ctx.fill();
        this.ctx.stroke();

        // Draw trend label and arrow
        this.ctx.fillStyle = trend > 0.01 ? '#28a745' : trend < -0.01 ? '#dc3545' : this._getColor('text-secondary');
        this.ctx.font = '10px system-ui, sans-serif';
        this.ctx.textAlign = 'left';

        const arrow = trend > 0.01 ? '↗' : trend < -0.01 ? '↘' : '→';
        const label = trend > 0.01 ? 'Rising' : trend < -0.01 ? 'Falling' : 'Stable';

        this.ctx.fillText(`${arrow} ${label}`, x, y + 3);
    }

    /**
     * Draw a bar with rounded top corners
     * @private
     */
    _drawRoundedBar(x, y, width, height, radius) {
        if (height < radius * 2) {
            this.ctx.fillRect(x, y, width, height);
            return;
        }

        this.ctx.beginPath();
        this.ctx.moveTo(x + radius, y);
        this.ctx.lineTo(x + width - radius, y);
        this.ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
        this.ctx.lineTo(x + width, y + height);
        this.ctx.lineTo(x, y + height);
        this.ctx.lineTo(x, y + radius);
        this.ctx.quadraticCurveTo(x, y, x + radius, y);
        this.ctx.closePath();
        this.ctx.fill();
    }

    /**
     * Count pairs below threshold in matrix
     * @private
     */
    _countBelowThreshold(matrix, threshold) {
        let count = 0;
        const n = matrix.length;
        for (let i = 0; i < n; i++) {
            for (let j = i + 1; j < n; j++) {
                if (matrix[i][j] < threshold) count++;
            }
        }
        return count;
    }

    /**
     * Get color from CSS custom properties (dark mode aware)
     * @private
     */
    _getColor(name) {
        const colorMap = {
            'text': getComputedStyle(document.documentElement).getPropertyValue('--color-text').trim() || '#1a1a2e',
            'text-secondary': getComputedStyle(document.documentElement).getPropertyValue('--color-text-secondary').trim() || '#4a4a68',
            'border': getComputedStyle(document.documentElement).getPropertyValue('--color-border').trim() || '#e1e4e8',
            'bg': getComputedStyle(document.documentElement).getPropertyValue('--color-bg').trim() || '#f8f9fa',
            'bg-elevated': getComputedStyle(document.documentElement).getPropertyValue('--color-bg-elevated').trim() || '#ffffff',
            'primary': getComputedStyle(document.documentElement).getPropertyValue('--color-primary').trim() || '#0066cc',
        };
        return colorMap[name] || '#000000';
    }
}

// Export for use in playground.js
window.SSMVisualizer = SSMVisualizer;
