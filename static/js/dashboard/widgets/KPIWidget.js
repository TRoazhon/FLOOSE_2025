/**
 * KPIWidget - Key Performance Indicator display widget
 */

import { BaseWidget } from '../core/BaseWidget.js';

export class KPIWidget extends BaseWidget {
    static get type() {
        return 'kpi';
    }

    static get name() {
        return 'Indicateur Clé';
    }

    static get category() {
        return 'metrics';
    }

    static get defaultSize() {
        return { width: 3, height: 2 };
    }

    render(props) {
        const data = props?.data || {};

        const value = data.value ?? 0;
        const label = data.label || 'Métrique';
        const unit = data.unit || '';
        const trend = data.trend; // 'up', 'down', or null
        const trendValue = data.trendValue;
        const icon = data.icon || 'fas fa-chart-line';
        const color = data.color || 'primary';

        const colorMap = {
            primary: '#D97757',
            success: '#22C55E',
            warning: '#F59E0B',
            danger: '#EF4444',
            info: '#3B82F6'
        };

        const accentColor = colorMap[color] || color;

        const formattedValue = typeof value === 'number'
            ? value.toLocaleString('fr-FR')
            : value;

        const trendIcon = trend === 'up' ? 'fa-arrow-up' : trend === 'down' ? 'fa-arrow-down' : '';
        const trendColor = trend === 'up' ? '#22C55E' : trend === 'down' ? '#EF4444' : 'inherit';

        this.contentElement.innerHTML = `
            <div class="kpi-widget" style="height: 100%; display: flex; flex-direction: column; justify-content: center; padding: 1rem;">
                <div class="kpi-header" style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;">
                    <div class="kpi-icon" style="
                        width: 40px;
                        height: 40px;
                        border-radius: 10px;
                        background: ${accentColor}15;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    ">
                        <i class="${icon}" style="color: ${accentColor}; font-size: 1.1rem;"></i>
                    </div>
                    <span class="kpi-label" style="
                        color: #666;
                        font-size: 0.85rem;
                        font-weight: 500;
                    ">${label}</span>
                </div>
                <div class="kpi-value-row" style="display: flex; align-items: baseline; gap: 0.5rem;">
                    <span class="kpi-value" style="
                        font-size: 1.75rem;
                        font-weight: 700;
                        color: #1a1a1a;
                        line-height: 1.2;
                    ">${formattedValue}${unit ? `<span style="font-size: 1rem; font-weight: 500;">${unit}</span>` : ''}</span>
                    ${trend ? `
                        <span class="kpi-trend" style="
                            display: inline-flex;
                            align-items: center;
                            gap: 0.25rem;
                            font-size: 0.8rem;
                            color: ${trendColor};
                            font-weight: 500;
                        ">
                            <i class="fas ${trendIcon}"></i>
                            ${trendValue ? `${trendValue}%` : ''}
                        </span>
                    ` : ''}
                </div>
            </div>
        `;
    }
}

export default KPIWidget;
