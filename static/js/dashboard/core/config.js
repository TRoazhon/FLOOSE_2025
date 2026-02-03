/**
 * Dashboard Configuration
 * Performance-oriented settings for the widget system
 */
export const DashboardConfig = {
    // Grid configuration
    grid: {
        columns: 12,
        rowHeight: 80,
        gap: 16,
        breakpoints: {
            xl: { minWidth: 1400, columns: 12 },
            lg: { minWidth: 1200, columns: 10 },
            md: { minWidth: 900, columns: 8 },
            sm: { minWidth: 600, columns: 6 },
            xs: { minWidth: 0, columns: 4 }
        }
    },

    // Performance budgets
    performance: {
        maxRenderTimeMs: 16,          // 60fps budget
        dragThrottleMs: 16,           // RAF-aligned
        resizeDebounceMs: 150,
        scrollThrottleMs: 100,
        saveIdleDelayMs: 1000,
        maxWidgetsBeforeVirtualization: 15,
        viewportPadding: 200          // px outside viewport to keep rendered
    },

    // Widget defaults
    widget: {
        minWidth: 2,
        minHeight: 2,
        maxWidth: 12,
        maxHeight: 8,
        defaultWidth: 4,
        defaultHeight: 3
    },

    // Animation settings (GPU-friendly)
    animation: {
        dragTransition: 'none',
        dropTransition: 'transform 200ms cubic-bezier(0.2, 0, 0, 1)',
        resizeTransition: 'width 200ms ease, height 200ms ease'
    },

    // Storage keys
    storage: {
        layoutKey: 'floose_dashboard_layout',
        preferencesKey: 'floose_dashboard_prefs',
        version: 1
    },

    // API endpoints
    api: {
        saveLayout: '/api/dashboard/layout',
        loadLayout: '/api/dashboard/layout',
        widgetData: '/api/widgets'
    }
};

// Freeze config to prevent mutations
Object.freeze(DashboardConfig);
Object.freeze(DashboardConfig.grid);
Object.freeze(DashboardConfig.performance);
Object.freeze(DashboardConfig.widget);
Object.freeze(DashboardConfig.animation);
Object.freeze(DashboardConfig.storage);
Object.freeze(DashboardConfig.api);
