/**
 * LineChartWidget - Line/Area chart widget for trends
 */

import { ChartWidget } from './ChartWidget.js';

export class LineChartWidget extends ChartWidget {
    static get type() {
        return 'line-chart';
    }

    static get name() {
        return 'Évolution';
    }

    static get defaultSize() {
        return { width: 6, height: 3 };
    }

    getChartType() {
        return 'line';
    }

    getChartConfig(data) {
        const primaryColor = '#D97757';
        const secondaryColor = '#3B82F6';

        return {
            type: 'line',
            data: {
                labels: data.labels || [],
                datasets: (data.datasets || [{ values: data.values || [] }]).map((ds, i) => ({
                    label: ds.label || 'Évolution',
                    data: ds.values || ds.data || [],
                    borderColor: ds.color || (i === 0 ? primaryColor : secondaryColor),
                    backgroundColor: this.config.filled
                        ? `${ds.color || primaryColor}20`
                        : 'transparent',
                    fill: this.config.filled || false,
                    tension: 0.4,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                    borderWidth: 2
                }))
            },
            options: {
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { font: { size: 11 } }
                    },
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(0,0,0,0.05)' },
                        ticks: {
                            font: { size: 11 },
                            callback: (value) => value.toLocaleString('fr-FR') + '€'
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                return `${context.dataset.label}: ${context.raw.toLocaleString('fr-FR')}€`;
                            }
                        }
                    }
                }
            }
        };
    }
}

export default LineChartWidget;
