/**
 * GaugeWidget - Gauge/meter display widget
 */

import { ChartWidget } from './ChartWidget.js';

export class GaugeWidget extends ChartWidget {
    static get type() {
        return 'gauge';
    }

    static get name() {
        return 'Jauge';
    }

    static get defaultSize() {
        return { width: 3, height: 3 };
    }

    getChartType() {
        return 'doughnut';
    }

    getChartConfig(data) {
        const value = data.value ?? 0;
        const max = data.max ?? 100;
        const percentage = Math.min(100, Math.max(0, (value / max) * 100));
        const remaining = 100 - percentage;

        // Color based on threshold
        let color = '#22C55E'; // Green
        if (percentage > 80) {
            color = '#EF4444'; // Red
        } else if (percentage > 60) {
            color = '#F59E0B'; // Orange
        }

        return {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [percentage, remaining],
                    backgroundColor: [color, '#E5E7EB'],
                    borderWidth: 0,
                    circumference: 180,
                    rotation: 270
                }]
            },
            options: {
                cutout: '75%',
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                }
            }
        };
    }

    render(props) {
        const data = props?.data || {};
        const value = data.value ?? 0;
        const max = data.max ?? 100;
        const label = data.label || 'Score';
        const unit = data.unit || '%';

        // Call parent to render chart
        super.render(props);

        // Add center label
        const percentage = Math.round((value / max) * 100);

        const centerLabel = document.createElement('div');
        centerLabel.className = 'gauge-center-label';
        centerLabel.style.cssText = `
            position: absolute;
            bottom: 20%;
            left: 50%;
            transform: translateX(-50%);
            text-align: center;
        `;
        centerLabel.innerHTML = `
            <div style="font-size: 1.5rem; font-weight: 700; color: #1a1a1a;">${percentage}${unit}</div>
            <div style="font-size: 0.75rem; color: #666;">${label}</div>
        `;

        // Remove existing label if any
        const existingLabel = this.contentElement.querySelector('.gauge-center-label');
        if (existingLabel) {
            existingLabel.remove();
        }

        this.contentElement.style.position = 'relative';
        this.contentElement.appendChild(centerLabel);
    }
}

export default GaugeWidget;
