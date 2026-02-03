/**
 * DashboardIntegration - Connects widget dashboard with FLOOSE APIs
 *
 * Handles:
 * - Fetching data from existing APIs
 * - Widget data transformation
 * - Real-time updates
 * - Legacy system interop
 */

import { Dashboard } from './Dashboard.js';

export class DashboardIntegration {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this._refreshIntervals = new Map();
        this._dataCache = new Map();
    }

    /**
     * Initialize with default widgets and data
     */
    async init() {
        // Fetch initial data
        await this._fetchAllData();

        // Setup refresh intervals
        this._setupAutoRefresh();

        return this;
    }

    /**
     * Fetch all data from APIs
     */
    async _fetchAllData() {
        try {
            const [kpis, quickNumbers, timeline, categories] = await Promise.all([
                this._fetchJSON('/api/analytics/kpis'),
                this._fetchJSON('/api/widgets/quick-numbers'),
                this._fetchJSON('/api/analytics/timeline'),
                this._fetchJSON('/api/analytics/category-breakdown')
            ]);

            this._dataCache.set('kpis', kpis);
            this._dataCache.set('quickNumbers', quickNumbers);
            this._dataCache.set('timeline', timeline);
            this._dataCache.set('categories', categories);

            // Update widgets with data
            this._updateWidgetsWithData();

        } catch (error) {
            console.error('Failed to fetch dashboard data:', error);
        }
    }

    /**
     * Update widgets with cached data
     */
    _updateWidgetsWithData() {
        const kpis = this._dataCache.get('kpis');
        const quickNumbers = this._dataCache.get('quickNumbers');
        const timeline = this._dataCache.get('timeline');
        const categories = this._dataCache.get('categories');

        // Find widgets by type and update them
        const widgets = this.dashboard.layoutManager?.getWidgets() || [];

        for (const { id, type } of widgets) {
            switch (type) {
                case 'stats-grid':
                    this._updateStatsGrid(id, quickNumbers);
                    break;
                case 'kpi':
                    this._updateKPI(id, kpis);
                    break;
                case 'pie-chart':
                    this._updatePieChart(id, categories);
                    break;
                case 'bar-chart':
                    this._updateBarChart(id, kpis);
                    break;
                case 'line-chart':
                    this._updateLineChart(id, timeline);
                    break;
                case 'gauge':
                    this._updateGauge(id, kpis);
                    break;
            }
        }
    }

    _updateStatsGrid(widgetId, data) {
        if (!data) return;

        this.dashboard.updateWidget(widgetId, {
            stats: [
                {
                    label: 'Budget Total',
                    value: data.total_budget || data.budget_total || 0,
                    unit: '€',
                    color: 'primary',
                    subtitle: `${data.projects_count || data.nombre_projets || 0} projets`
                },
                {
                    label: 'Dépensé',
                    value: data.spent_today || data.total_depense || 0,
                    unit: '€',
                    color: 'warning',
                    subtitle: `Taux: ${(data.burn_rate || 0).toFixed(0)}€/mois`
                },
                {
                    label: 'Cash Disponible',
                    value: data.cash_available || data.total_restant || 0,
                    unit: '€',
                    color: 'success'
                },
                {
                    label: 'Projets OK',
                    value: data.projects_on_track || 0,
                    unit: `/${data.projects_count || 0}`,
                    color: 'info',
                    subtitle: 'Dans le budget'
                }
            ]
        });
    }

    _updateKPI(widgetId, data) {
        if (!data) return;

        const healthScore = data.financial_health_score ?? data.sante_financiere ?? 75;

        this.dashboard.updateWidget(widgetId, {
            label: 'Santé Financière',
            value: healthScore,
            unit: '%',
            icon: 'fas fa-heartbeat',
            color: healthScore >= 70 ? 'success' : healthScore >= 40 ? 'warning' : 'danger',
            trend: healthScore >= 50 ? 'up' : 'down',
            trendValue: Math.abs(healthScore - 50)
        });
    }

    _updatePieChart(widgetId, data) {
        if (!data || !data.categories) return;

        this.dashboard.updateWidget(widgetId, {
            labels: data.categories.map(c => c.nom || c.name),
            values: data.categories.map(c => c.montant || c.amount || 0),
            colors: data.categories.map(c => c.color || c.couleur)
        });
    }

    _updateBarChart(widgetId, data) {
        if (!data || !data.projets) return;

        const projets = data.projets.slice(0, 6);

        this.dashboard.updateWidget(widgetId, {
            labels: projets.map(p => p.nom || p.name),
            datasets: [
                {
                    label: 'Budget',
                    values: projets.map(p => p.budget || 0),
                    color: '#3B82F6'
                },
                {
                    label: 'Dépensé',
                    values: projets.map(p => p.depense || p.spent || 0),
                    color: '#D97757'
                }
            ]
        });
    }

    _updateLineChart(widgetId, data) {
        if (!data || !data.timeline) return;

        this.dashboard.updateWidget(widgetId, {
            labels: data.timeline.map(t => t.date || t.label),
            datasets: [
                {
                    label: 'Dépenses',
                    values: data.timeline.map(t => t.depenses || t.value || 0),
                    color: '#D97757'
                }
            ]
        });
    }

    _updateGauge(widgetId, data) {
        if (!data) return;

        const used = data.pourcentage_utilise || data.percentage_used || 0;

        this.dashboard.updateWidget(widgetId, {
            value: used,
            max: 100,
            label: 'Budget utilisé',
            unit: '%'
        });
    }

    /**
     * Setup auto-refresh for widgets
     */
    _setupAutoRefresh() {
        // Refresh every 5 minutes
        const intervalId = setInterval(() => {
            this._fetchAllData();
        }, 5 * 60 * 1000);

        this._refreshIntervals.set('main', intervalId);
    }

    /**
     * Fetch JSON from API
     */
    async _fetchJSON(url) {
        try {
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.warn(`Failed to fetch ${url}:`, error);
            return null;
        }
    }

    /**
     * Force refresh all data
     */
    async refresh() {
        await this._fetchAllData();
    }

    /**
     * Cleanup
     */
    destroy() {
        for (const intervalId of this._refreshIntervals.values()) {
            clearInterval(intervalId);
        }
        this._refreshIntervals.clear();
        this._dataCache.clear();
    }
}

/**
 * Initialize the FLOOSE dashboard
 */
export async function initFlooseDashboard(containerId, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Dashboard container "${containerId}" not found`);
        return null;
    }

    // Create dashboard
    const dashboard = new Dashboard(container, {
        debug: options.debug || false,
        autoLoad: true
    });

    // Initialize
    await dashboard.init();

    // Setup integration
    const integration = new DashboardIntegration(dashboard);
    await integration.init();

    // Expose globally for debugging
    if (options.debug) {
        window.__flooseDashboard = dashboard;
        window.__flooseIntegration = integration;
    }

    // Add "Add Widget" button
    const addBtn = document.createElement('button');
    addBtn.className = 'btn btn-primary dashboard-add-widget-btn';
    addBtn.innerHTML = '<i class="fas fa-plus"></i> Ajouter Widget';
    addBtn.style.cssText = 'position: fixed; bottom: 24px; right: 24px; z-index: 100;';
    addBtn.addEventListener('click', () => dashboard.showWidgetPicker());
    document.body.appendChild(addBtn);

    return { dashboard, integration };
}

// Expose globally
if (typeof window !== 'undefined') {
    window.initFlooseDashboard = initFlooseDashboard;
}
