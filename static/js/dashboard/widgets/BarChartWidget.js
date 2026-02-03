/**
 * BarChartWidget - Bar chart widget for comparisons
 */

import { ChartWidget } from './ChartWidget.js';

export class BarChartWidget extends ChartWidget {
    static get type() {
        return 'bar-chart';
    }

    static get name() {
        return 'Comparaison';
    }

    static get defaultSize() {
        return { width: 6, height: 3 };
    }

    getChartType() {
        return this.config.horizontal ? 'bar' : 'bar';
    }

    getChartConfig(data) {
        return {
            type: 'bar',
            data: {
                labels: data.labels || [],
                datasets: (data.datasets || [{ values: data.values || [] }]).map((ds, i) => ({
                    label: ds.label || 'Données',
                    data: ds.values || ds.data || [],
                    backgroundColor: ds.color || ['#D97757', '#22C55E', '#3B82F6', '#F59E0B'][i % 4],
                    borderRadius: 4,
                    borderSkipped: false
                }))
            },
            options: {
                indexAxis: this.config.horizontal ? 'y' : 'x',
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

export default BarChartWidget;
