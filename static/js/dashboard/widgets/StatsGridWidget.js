/**
 * StatsGridWidget - Multi-stat display widget
 */

import { BaseWidget } from '../core/BaseWidget.js';

export class StatsGridWidget extends BaseWidget {
    static get type() {
        return 'stats-grid';
    }

    static get name() {
        return 'Statistiques';
    }

    static get category() {
        return 'metrics';
    }

    static get defaultSize() {
        return { width: 6, height: 2 };
    }

    render(props) {
        const data = props?.data || {};
        const stats = data.stats || [];

        const colorMap = {
            primary: '#D97757',
            success: '#22C55E',
            warning: '#F59E0B',
            danger: '#EF4444',
            info: '#3B82F6'
        };

        const statsHtml = stats.map(stat => {
            const accentColor = colorMap[stat.color] || stat.color || '#D97757';
            const formattedValue = typeof stat.value === 'number'
                ? stat.value.toLocaleString('fr-FR')
                : stat.value;

            return `
                <div class="stat-item" style="
                    display: flex;
                    flex-direction: column;
                    padding: 0.75rem;
                    background: linear-gradient(135deg, ${accentColor}08, ${accentColor}03);
                    border-radius: 8px;
                    border-left: 3px solid ${accentColor};
                ">
                    <span class="stat-label" style="
                        font-size: 0.75rem;
                        color: #666;
                        margin-bottom: 0.25rem;
                    ">${stat.label || 'Stat'}</span>
                    <span class="stat-value" style="
                        font-size: 1.25rem;
                        font-weight: 700;
                        color: #1a1a1a;
                    ">${formattedValue}${stat.unit || ''}</span>
                    ${stat.subtitle ? `
                        <span class="stat-subtitle" style="
                            font-size: 0.7rem;
                            color: #888;
                            margin-top: 0.25rem;
                        ">${stat.subtitle}</span>
                    ` : ''}
                </div>
            `;
        }).join('');

        const columns = Math.min(stats.length, 4);

        this.contentElement.innerHTML = `
            <div class="stats-grid" style="
                display: grid;
                grid-template-columns: repeat(${columns}, 1fr);
                gap: 0.75rem;
                height: 100%;
                padding: 0.5rem;
                align-content: center;
            ">
                ${statsHtml}
            </div>
        `;
    }
}

export default StatsGridWidget;
