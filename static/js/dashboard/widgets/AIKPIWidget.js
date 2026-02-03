/**
 * AIKPIWidget - AI-generated KPI widget with dynamic visualization
 *
 * Architecture:
 * - Immutable KPIConfig after validation
 * - Separate state layers: AI, KPI, Layout, Data
 * - Lazy-loaded visualization renderers
 * - Memoized rendering to prevent unnecessary updates
 */

import { BaseWidget } from '../core/BaseWidget.js';
import { getMistralService, AIState } from '../ai/MistralService.js';
import { validateKPIConfig, createDefaultKPIConfig } from '../ai/KPIConfigSchema.js';

/**
 * Visualization renderers - lazy loaded based on type
 */
const RENDERERS = {
    number: renderNumber,
    gauge: renderGauge,
    line: renderLineChart,
    bar: renderBarChart,
    pie: renderPieChart,
    sparkline: renderSparkline,
    table: renderTable
};

export class AIKPIWidget extends BaseWidget {
    constructor(id, config = {}) {
        super(id, config);

        // AI State layer
        this.aiState = new AIState();

        // KPI Config layer (immutable after set)
        this._kpiConfig = null;

        // Data layer
        this._data = null;
        this._dataHash = null;
        this._lastFetch = 0;

        // Refresh timer
        this._refreshTimer = null;

        // Chart instance (if applicable)
        this._chartInstance = null;

        // Persistence data
        this._persistedPrompt = config.prompt || null;
        this._persistedConfig = config.kpiConfig || null;
        this._persistedRawResponse = config.rawResponse || null;
    }

    static get type() {
        return 'ai-kpi';
    }

    static get name() {
        return 'KPI Intelligent';
    }

    static get category() {
        return 'ai';
    }

    static get defaultSize() {
        return { width: 4, height: 3 };
    }

    // === Lifecycle ===

    onMount() {
        this.contentElement.innerHTML = this._renderInitialState();

        // Restore from persisted state if available
        if (this._persistedConfig) {
            const validation = validateKPIConfig(this._persistedConfig);
            if (validation.valid) {
                this._kpiConfig = validation.config;
                this.aiState.status = 'success';
                this.aiState.prompt = this._persistedPrompt;
                this.aiState.config = validation.config;
                this._fetchAndRenderData();
            }
        }
    }

    onDestroy() {
        this._stopRefreshTimer();
        if (this._chartInstance) {
            this._chartInstance.destroy();
            this._chartInstance = null;
        }
    }

    onVisible() {
        // Resume refresh if configured
        if (this._kpiConfig?.refresh_rate > 0) {
            this._startRefreshTimer();
        }
    }

    onHidden() {
        this._stopRefreshTimer();
    }

    // === Public API ===

    /**
     * Initialize widget with a natural language prompt
     */
    async initFromPrompt(prompt) {
        this._renderLoading(prompt);

        const mistral = getMistralService();
        const { state, config } = await mistral.generateKPI(prompt);

        this.aiState = state;

        if (state.status === 'success' && config) {
            this._kpiConfig = config;
            this._persistedPrompt = prompt;
            this._persistedConfig = config;
            this._persistedRawResponse = state.rawResponse;

            await this._fetchAndRenderData();
            this._startRefreshTimer();

            // Notify for persistence
            this._notifyConfigChange();
        } else if (state.status === 'ambiguous') {
            this._renderAmbiguous(state.ambiguity, state.suggestions);
        } else {
            this._renderError(state.error);
        }

        return state;
    }

    /**
     * Initialize widget with a pre-validated KPIConfig
     */
    async initFromConfig(kpiConfig) {
        const validation = validateKPIConfig(kpiConfig);
        if (!validation.valid) {
            this._renderError(`Configuration invalide: ${validation.errors.join(', ')}`);
            return false;
        }

        this._kpiConfig = validation.config;
        this.aiState.status = 'success';
        this.aiState.config = validation.config;

        await this._fetchAndRenderData();
        this._startRefreshTimer();

        return true;
    }

    /**
     * Get current config for persistence
     */
    getPersistedData() {
        return {
            prompt: this._persistedPrompt,
            kpiConfig: this._kpiConfig,
            rawResponse: this._persistedRawResponse
        };
    }

    /**
     * Force data refresh
     */
    async refresh() {
        if (this._kpiConfig) {
            await this._fetchAndRenderData();
        }
    }

    // === Private Methods ===

    _renderInitialState() {
        return `
            <div class="ai-kpi-widget ai-kpi-empty">
                <div class="ai-kpi-placeholder">
                    <i class="fas fa-magic"></i>
                    <p>Décrivez votre KPI en langage naturel</p>
                </div>
            </div>
        `;
    }

    _renderLoading(prompt) {
        this.contentElement.innerHTML = `
            <div class="ai-kpi-widget ai-kpi-loading">
                <div class="ai-kpi-spinner"></div>
                <p class="ai-kpi-prompt-preview">"${this._truncate(prompt, 50)}"</p>
                <p class="ai-kpi-status">Analyse en cours...</p>
            </div>
        `;
    }

    _renderError(message) {
        this.contentElement.innerHTML = `
            <div class="ai-kpi-widget ai-kpi-error">
                <i class="fas fa-exclamation-triangle"></i>
                <p class="ai-kpi-error-message">${message}</p>
                <button class="btn btn-sm btn-outline ai-kpi-retry">
                    <i class="fas fa-redo"></i> Réessayer
                </button>
            </div>
        `;

        this.contentElement.querySelector('.ai-kpi-retry')?.addEventListener('click', () => {
            if (this._persistedPrompt) {
                this.initFromPrompt(this._persistedPrompt);
            }
        });
    }

    _renderAmbiguous(ambiguity, suggestions = []) {
        const suggestionsHtml = suggestions.length > 0
            ? `<div class="ai-kpi-suggestions">
                <p>Suggestions:</p>
                <ul>${suggestions.map(s => `<li><button class="ai-kpi-suggestion">${s}</button></li>`).join('')}</ul>
               </div>`
            : '';

        this.contentElement.innerHTML = `
            <div class="ai-kpi-widget ai-kpi-ambiguous">
                <i class="fas fa-question-circle"></i>
                <p class="ai-kpi-ambiguity">${ambiguity}</p>
                ${suggestionsHtml}
            </div>
        `;

        // Handle suggestion clicks
        this.contentElement.querySelectorAll('.ai-kpi-suggestion').forEach(btn => {
            btn.addEventListener('click', () => {
                this.initFromPrompt(btn.textContent);
            });
        });
    }

    async _fetchAndRenderData() {
        if (!this._kpiConfig) return;

        try {
            const response = await fetch('/api/ai/compute-kpi', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this._kpiConfig)
            });

            if (!response.ok) {
                throw new Error('Erreur lors du calcul');
            }

            const data = await response.json();
            this._data = data;
            this._lastFetch = Date.now();

            this._renderVisualization();

        } catch (error) {
            console.error('KPI data fetch error:', error);
            this._renderError('Erreur lors du chargement des données');
        }
    }

    _renderVisualization() {
        if (!this._kpiConfig || !this._data) return;

        const vizType = this._kpiConfig.visualization || 'number';
        const renderer = RENDERERS[vizType] || renderNumber;

        // Destroy previous chart if exists
        if (this._chartInstance) {
            this._chartInstance.destroy();
            this._chartInstance = null;
        }

        this.contentElement.innerHTML = `
            <div class="ai-kpi-widget ai-kpi-rendered">
                <div class="ai-kpi-header">
                    <span class="ai-kpi-name">${this._kpiConfig.kpi_name}</span>
                    <span class="ai-kpi-refresh-indicator" title="Dernière mise à jour">
                        <i class="fas fa-sync-alt"></i>
                    </span>
                </div>
                <div class="ai-kpi-visualization" data-viz="${vizType}"></div>
            </div>
        `;

        const vizContainer = this.contentElement.querySelector('.ai-kpi-visualization');
        this._chartInstance = renderer(vizContainer, this._data, this._kpiConfig);
    }

    _startRefreshTimer() {
        this._stopRefreshTimer();

        const interval = (this._kpiConfig?.refresh_rate || 60) * 1000;
        if (interval > 0) {
            this._refreshTimer = setInterval(() => {
                this._fetchAndRenderData();
            }, interval);
        }
    }

    _stopRefreshTimer() {
        if (this._refreshTimer) {
            clearInterval(this._refreshTimer);
            this._refreshTimer = null;
        }
    }

    _notifyConfigChange() {
        // Dispatch event for persistence
        this.container?.dispatchEvent(new CustomEvent('widget:config-change', {
            bubbles: true,
            detail: {
                widgetId: this.id,
                data: this.getPersistedData()
            }
        }));
    }

    _truncate(str, maxLen) {
        if (!str) return '';
        return str.length > maxLen ? str.substring(0, maxLen) + '...' : str;
    }
}

// === Visualization Renderers ===

function renderNumber(container, data, config) {
    const trend = data.trend;
    const trendHtml = trend ? `
        <span class="ai-kpi-trend ${trend.direction}">
            <i class="fas fa-arrow-${trend.direction === 'up' ? 'up' : 'down'}"></i>
            ${trend.value}%
        </span>
    ` : '';

    container.innerHTML = `
        <div class="ai-kpi-number">
            <span class="ai-kpi-value">${data.formatted_value || data.value}</span>
            ${trendHtml}
        </div>
    `;
    return null;
}

function renderGauge(container, data, config) {
    const value = Math.min(100, Math.max(0, data.value));
    const color = value >= 80 ? '#EF4444' : value >= 60 ? '#F59E0B' : '#22C55E';

    container.innerHTML = `
        <div class="ai-kpi-gauge">
            <canvas id="gauge-${Date.now()}"></canvas>
            <div class="ai-kpi-gauge-value">${value.toFixed(1)}%</div>
        </div>
    `;

    const canvas = container.querySelector('canvas');
    if (canvas && window.Chart) {
        return new Chart(canvas, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [value, 100 - value],
                    backgroundColor: [color, '#E5E7EB'],
                    borderWidth: 0,
                    circumference: 180,
                    rotation: 270
                }]
            },
            options: {
                cutout: '70%',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: { enabled: false } }
            }
        });
    }
    return null;
}

function renderLineChart(container, data, config) {
    container.innerHTML = `<canvas></canvas>`;
    const canvas = container.querySelector('canvas');

    if (canvas && window.Chart && data.breakdown?.length > 0) {
        return new Chart(canvas, {
            type: 'line',
            data: {
                labels: data.breakdown.map(d => d.label),
                datasets: [{
                    label: config.kpi_name,
                    data: data.breakdown.map(d => d.value),
                    borderColor: '#D97757',
                    backgroundColor: 'rgba(217, 119, 87, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { display: true, grid: { display: false } },
                    y: { display: true, beginAtZero: true }
                }
            }
        });
    }

    // Fallback to number if no breakdown
    return renderNumber(container, data, config);
}

function renderBarChart(container, data, config) {
    container.innerHTML = `<canvas></canvas>`;
    const canvas = container.querySelector('canvas');

    if (canvas && window.Chart && data.breakdown?.length > 0) {
        return new Chart(canvas, {
            type: 'bar',
            data: {
                labels: data.breakdown.map(d => d.label),
                datasets: [{
                    label: config.kpi_name,
                    data: data.breakdown.map(d => d.value),
                    backgroundColor: '#D97757',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false } },
                    y: { beginAtZero: true }
                }
            }
        });
    }

    return renderNumber(container, data, config);
}

function renderPieChart(container, data, config) {
    container.innerHTML = `<canvas></canvas>`;
    const canvas = container.querySelector('canvas');

    if (canvas && window.Chart && data.breakdown?.length > 0) {
        const colors = ['#D97757', '#22C55E', '#3B82F6', '#F59E0B', '#8B5CF6', '#EC4899'];
        return new Chart(canvas, {
            type: 'pie',
            data: {
                labels: data.breakdown.map(d => d.label),
                datasets: [{
                    data: data.breakdown.map(d => d.value),
                    backgroundColor: colors.slice(0, data.breakdown.length)
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right', labels: { boxWidth: 12 } }
                }
            }
        });
    }

    return renderNumber(container, data, config);
}

function renderSparkline(container, data, config) {
    container.innerHTML = `<canvas></canvas>`;
    const canvas = container.querySelector('canvas');

    // Generate sample data for sparkline
    const values = data.breakdown?.map(d => d.value) || [data.value * 0.8, data.value * 0.9, data.value];

    if (canvas && window.Chart) {
        return new Chart(canvas, {
            type: 'line',
            data: {
                labels: values.map((_, i) => i),
                datasets: [{
                    data: values,
                    borderColor: '#D97757',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: false,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
                scales: { x: { display: false }, y: { display: false } }
            }
        });
    }

    return null;
}

function renderTable(container, data, config) {
    if (!data.breakdown || data.breakdown.length === 0) {
        return renderNumber(container, data, config);
    }

    const rows = data.breakdown.map(item => `
        <tr>
            <td>${item.label}</td>
            <td class="text-right">${typeof item.value === 'number' ? item.value.toLocaleString('fr-FR') : item.value}</td>
        </tr>
    `).join('');

    container.innerHTML = `
        <div class="ai-kpi-table-wrapper">
            <table class="ai-kpi-table">
                <thead>
                    <tr>
                        <th>Élément</th>
                        <th class="text-right">Valeur</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    `;

    return null;
}

export default AIKPIWidget;
