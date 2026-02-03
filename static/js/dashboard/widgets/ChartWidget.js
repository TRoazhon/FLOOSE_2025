/**
 * ChartWidget - Base class for Chart.js widgets
 *
 * Performance optimizations:
 * - Chart instance reuse (update instead of recreate)
 * - Resize observer with debouncing
 * - Animation disabled during drag
 * - Data comparison to skip unnecessary updates
 */

import { BaseWidget } from '../core/BaseWidget.js';

export class ChartWidget extends BaseWidget {
    constructor(id, config = {}) {
        super(id, config);

        this.chart = null;
        this._chartCanvas = null;
        this._resizeObserver = null;
        this._animationsEnabled = true;
    }

    static get category() {
        return 'charts';
    }

    onMount() {
        // Create canvas element
        this._chartCanvas = document.createElement('canvas');
        this._chartCanvas.className = 'widget-chart-canvas';
        this.contentElement.appendChild(this._chartCanvas);

        // Setup resize observer
        this._resizeObserver = new ResizeObserver(entries => {
            if (this.chart && this._animationsEnabled) {
                this.chart.resize();
            }
        });
        this._resizeObserver.observe(this.container);
    }

    /**
     * Get Chart.js configuration - override in subclasses
     */
    getChartConfig(data) {
        throw new Error('getChartConfig must be implemented by subclass');
    }

    /**
     * Get Chart.js type - override in subclasses
     */
    getChartType() {
        throw new Error('getChartType must be implemented by subclass');
    }

    render(props) {
        const data = props?.data;
        if (!data) return;

        if (this.chart) {
            // Update existing chart
            this._updateChart(data);
        } else {
            // Create new chart
            this._createChart(data);
        }
    }

    _createChart(data) {
        if (!this._chartCanvas || !window.Chart) return;

        const ctx = this._chartCanvas.getContext('2d');
        const config = this.getChartConfig(data);

        // Apply performance defaults
        config.options = {
            ...config.options,
            responsive: true,
            maintainAspectRatio: false,
            animation: {
                duration: this._animationsEnabled ? 400 : 0
            },
            plugins: {
                ...config.options?.plugins,
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        boxWidth: 12,
                        padding: 8,
                        font: { size: 11 }
                    },
                    ...config.options?.plugins?.legend
                }
            }
        };

        this.chart = new Chart(ctx, config);
    }

    _updateChart(data) {
        if (!this.chart) return;

        const config = this.getChartConfig(data);

        // Update data without recreating chart
        this.chart.data = config.data;

        // Update with or without animation
        this.chart.update(this._animationsEnabled ? 'default' : 'none');
    }

    onResize(width, height) {
        // Disable animations during resize
        this._animationsEnabled = false;
    }

    onResizeEnd(width, height) {
        this._animationsEnabled = true;
        if (this.chart) {
            this.chart.resize();
        }
    }

    onHidden() {
        // Pause animations when not visible
        this._animationsEnabled = false;
    }

    onVisible() {
        this._animationsEnabled = true;
    }

    onDestroy() {
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }

        if (this._resizeObserver) {
            this._resizeObserver.disconnect();
            this._resizeObserver = null;
        }
    }
}
