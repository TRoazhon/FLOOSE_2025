/**
 * PieChartWidget - Pie/Doughnut chart widget
 */

import { ChartWidget } from './ChartWidget.js';

export class PieChartWidget extends ChartWidget {
    static get type() {
        return 'pie-chart';
    }

    static get name() {
        return 'Répartition Budget';
    }

    static get defaultSize() {
        return { width: 4, height: 3 };
    }

    getChartType() {
        return this.config.doughnut ? 'doughnut' : 'pie';
    }

    getChartConfig(data) {
        const colors = [
            '#D97757', '#22C55E', '#3B82F6', '#F59E0B',
            '#8B5CF6', '#EC4899', '#14B8A6', '#F97316'
        ];

        return {
            type: this.getChartType(),
            data: {
                labels: data.labels || [],
                datasets: [{
                    data: data.values || [],
                    backgroundColor: data.colors || colors.slice(0, data.values?.length || 0),
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                cutout: this.config.doughnut ? '60%' : 0,
                plugins: {
                    legend: {
                        position: 'right'
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const value = context.raw;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${context.label}: ${value.toLocaleString('fr-FR')}€ (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        };
    }
}

export default PieChartWidget;
