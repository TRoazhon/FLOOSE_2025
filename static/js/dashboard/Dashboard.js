/**
 * Dashboard - Main entry point for the widget dashboard
 *
 * Coordinates all dashboard subsystems:
 * - LayoutManager for widget positioning
 * - StateManager for state persistence
 * - WidgetRegistry for widget types
 * - PerformanceMonitor for diagnostics
 */

import { DashboardConfig } from './core/config.js';
import { LayoutManager } from './core/LayoutManager.js';
import { getStateManager } from './core/StateManager.js';
import { WidgetRegistry } from './core/WidgetRegistry.js';
import { getPerformanceMonitor } from './utils/PerformanceMonitor.js';
import { showAIWidgetPicker } from './ai/AIWidgetPicker.js';

// Register all widget types
function registerWidgets() {
    // AI-powered widgets
    WidgetRegistry.register('ai-kpi', {
        loader: () => import('./widgets/AIKPIWidget.js'),
        name: 'KPI Intelligent (IA)',
        category: 'ai',
        defaultSize: { width: 4, height: 3 },
        priority: 1  // Highest priority for preloading
    });

    // Standard widgets
    WidgetRegistry.register('pie-chart', {
        loader: () => import('./widgets/PieChartWidget.js'),
        name: 'Répartition Budget',
        category: 'charts',
        defaultSize: { width: 4, height: 3 },
        priority: 10
    });

    WidgetRegistry.register('bar-chart', {
        loader: () => import('./widgets/BarChartWidget.js'),
        name: 'Comparaison',
        category: 'charts',
        defaultSize: { width: 6, height: 3 },
        priority: 10
    });

    WidgetRegistry.register('line-chart', {
        loader: () => import('./widgets/LineChartWidget.js'),
        name: 'Évolution',
        category: 'charts',
        defaultSize: { width: 6, height: 3 },
        priority: 10
    });

    WidgetRegistry.register('gauge', {
        loader: () => import('./widgets/GaugeWidget.js'),
        name: 'Jauge',
        category: 'charts',
        defaultSize: { width: 3, height: 3 },
        priority: 20
    });

    WidgetRegistry.register('kpi', {
        loader: () => import('./widgets/KPIWidget.js'),
        name: 'Indicateur Clé',
        category: 'metrics',
        defaultSize: { width: 3, height: 2 },
        priority: 5
    });

    WidgetRegistry.register('stats-grid', {
        loader: () => import('./widgets/StatsGridWidget.js'),
        name: 'Statistiques',
        category: 'metrics',
        defaultSize: { width: 6, height: 2 },
        priority: 5
    });
}

export class Dashboard {
    constructor(container, options = {}) {
        this.container = typeof container === 'string'
            ? document.querySelector(container)
            : container;

        if (!this.container) {
            throw new Error('Dashboard container not found');
        }

        this.options = {
            debug: false,
            autoLoad: true,
            ...options
        };

        this.layoutManager = null;
        this.stateManager = getStateManager();
        this.perfMonitor = getPerformanceMonitor({
            enabled: this.options.debug,
            showOverlay: this.options.debug
        });

        this._initialized = false;
        this._widgetPicker = null;
    }

    /**
     * Initialize the dashboard
     */
    async init() {
        if (this._initialized) return this;

        // Register widgets
        registerWidgets();

        // Preload priority widgets
        await WidgetRegistry.preloadPriority(20);

        // Initialize layout manager
        this.layoutManager = new LayoutManager(this.container);
        await this.layoutManager.init();

        // Start performance monitoring
        if (this.options.debug) {
            this.perfMonitor.start();
        }

        // Load default widgets if no layout saved
        if (this.options.autoLoad) {
            await this._loadDefaultWidgets();
        }

        this._initialized = true;

        // Dispatch ready event
        this.container.dispatchEvent(new CustomEvent('dashboard:ready', {
            detail: { dashboard: this }
        }));

        return this;
    }

    /**
     * Add a widget to the dashboard
     */
    async addWidget(type, config = {}) {
        return this.layoutManager.addWidget(type, config);
    }

    /**
     * Remove a widget from the dashboard
     */
    removeWidget(widgetId) {
        this.layoutManager.removeWidget(widgetId);
    }

    /**
     * Update widget data
     */
    updateWidget(widgetId, data) {
        this.layoutManager.updateWidgetData(widgetId, data);
    }

    /**
     * Get all available widget types
     */
    getWidgetTypes() {
        return WidgetRegistry.getByCategory();
    }

    /**
     * Get dashboard metrics
     */
    getMetrics() {
        return {
            layout: this.layoutManager?.getMetrics(),
            state: this.stateManager.getMetrics(),
            registry: WidgetRegistry.getStats(),
            performance: this.perfMonitor.getMetrics()
        };
    }

    /**
     * Show widget picker UI
     */
    showWidgetPicker() {
        if (this._widgetPicker) {
            this._widgetPicker.remove();
        }

        const categories = this.getWidgetTypes();
        const picker = document.createElement('div');
        picker.className = 'widget-picker-overlay';

        // Category labels
        const categoryLabels = {
            'ai': 'Intelligence Artificielle',
            'charts': 'Graphiques',
            'metrics': 'Métriques',
            'general': 'Général'
        };

        picker.innerHTML = `
            <div class="widget-picker">
                <div class="widget-picker-header">
                    <h3>Ajouter un widget</h3>
                    <button class="widget-picker-close">&times;</button>
                </div>
                <div class="widget-picker-content">
                    <!-- AI Widget Prominent Section -->
                    <div class="widget-picker-ai-section">
                        <button class="widget-picker-ai-btn" id="aiWidgetBtn">
                            <div class="ai-btn-icon">
                                <i class="fas fa-magic"></i>
                            </div>
                            <div class="ai-btn-content">
                                <span class="ai-btn-title">Créer un KPI avec l'IA</span>
                                <span class="ai-btn-desc">Décrivez votre KPI en langage naturel</span>
                            </div>
                            <i class="fas fa-chevron-right ai-btn-arrow"></i>
                        </button>
                    </div>

                    <div class="widget-picker-divider">
                        <span>ou choisir un widget standard</span>
                    </div>

                    ${Object.entries(categories)
                        .filter(([cat]) => cat !== 'ai')
                        .map(([category, widgets]) => `
                        <div class="widget-picker-category">
                            <h4>${categoryLabels[category] || category}</h4>
                            <div class="widget-picker-grid">
                                ${widgets.map(w => `
                                    <button class="widget-picker-item" data-type="${w.type}">
                                        <span class="widget-picker-name">${w.name}</span>
                                        <span class="widget-picker-size">${w.defaultSize.width}x${w.defaultSize.height}</span>
                                    </button>
                                `).join('')}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

        // Event handlers
        picker.querySelector('.widget-picker-close').addEventListener('click', () => {
            picker.remove();
            this._widgetPicker = null;
        });

        picker.addEventListener('click', (e) => {
            if (e.target === picker) {
                picker.remove();
                this._widgetPicker = null;
            }
        });

        // AI Widget button
        picker.querySelector('#aiWidgetBtn').addEventListener('click', () => {
            picker.remove();
            this._widgetPicker = null;
            this.showAIWidgetPicker();
        });

        picker.querySelectorAll('.widget-picker-item').forEach(btn => {
            btn.addEventListener('click', async () => {
                const type = btn.dataset.type;
                await this.addWidget(type);
                picker.remove();
                this._widgetPicker = null;
            });
        });

        document.body.appendChild(picker);
        this._widgetPicker = picker;
    }

    /**
     * Show AI-powered widget creation modal
     */
    showAIWidgetPicker() {
        showAIWidgetPicker({
            onWidgetCreate: async (widgetData) => {
                try {
                    const widgetId = await this.addWidget(widgetData.type, {
                        ...widgetData.config,
                        data: widgetData.config
                    });

                    // Initialize the AI widget with its config
                    const widget = this.layoutManager._widgets.get(widgetId);
                    if (widget && widget.initFromConfig) {
                        await widget.initFromConfig(widgetData.config.kpiConfig);
                    }
                } catch (error) {
                    console.error('Failed to create AI widget:', error);
                }
            },
            onClose: () => {
                // Optional cleanup
            }
        });
    }

    /**
     * Destroy dashboard and cleanup
     */
    destroy() {
        this.layoutManager?.destroy();
        this.perfMonitor?.stop();
        this._widgetPicker?.remove();
        this._initialized = false;
    }

    // --- Private methods ---

    async _loadDefaultWidgets() {
        const existingWidgets = this.stateManager.getAllWidgetStates();

        // Skip if widgets already exist
        if (existingWidgets.length > 0) return;

        // Default widget layout
        const defaultWidgets = [
            { type: 'stats-grid', x: 0, y: 0, width: 8, height: 2 },
            { type: 'kpi', x: 8, y: 0, width: 4, height: 2 },
            { type: 'pie-chart', x: 0, y: 2, width: 4, height: 4 },
            { type: 'bar-chart', x: 4, y: 2, width: 4, height: 4 },
            { type: 'line-chart', x: 8, y: 2, width: 4, height: 4 },
            { type: 'gauge', x: 0, y: 6, width: 3, height: 3 }
        ];

        for (const config of defaultWidgets) {
            await this.addWidget(config.type, config);
        }
    }
}

// Export for use as ES module
export default Dashboard;

// Also expose globally for non-module usage
if (typeof window !== 'undefined') {
    window.Dashboard = Dashboard;
    window.WidgetRegistry = WidgetRegistry;
}
