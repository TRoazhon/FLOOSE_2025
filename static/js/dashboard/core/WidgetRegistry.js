/**
 * WidgetRegistry - Static registry for widget types with lazy loading
 *
 * Design principles:
 * - Static registration with dynamic instantiation
 * - Code splitting via dynamic imports
 * - Preloading for frequently used widgets
 * - Zero runtime overhead for unloaded widgets
 */

const registry = new Map();
const loadedModules = new Map();
const loadingPromises = new Map();
const usageStats = new Map();

export const WidgetRegistry = {
    /**
     * Register a widget type with its loader
     * @param {string} type - Widget type identifier
     * @param {Object} config - Widget configuration
     * @param {Function} config.loader - Dynamic import function
     * @param {string} config.name - Display name
     * @param {string} config.category - Widget category
     * @param {Object} config.defaultSize - Default {width, height}
     * @param {number} config.priority - Preload priority (lower = higher priority)
     */
    register(type, config) {
        if (registry.has(type)) {
            console.warn(`Widget type "${type}" already registered`);
            return;
        }

        registry.set(type, {
            type,
            loader: config.loader,
            name: config.name || type,
            category: config.category || 'general',
            defaultSize: config.defaultSize || { width: 4, height: 3 },
            priority: config.priority ?? 100,
            loaded: false
        });

        usageStats.set(type, 0);
    },

    /**
     * Get widget class by type - lazy loads if needed
     */
    async get(type) {
        const config = registry.get(type);
        if (!config) {
            throw new Error(`Widget type "${type}" not registered`);
        }

        // Track usage for preloading optimization
        usageStats.set(type, (usageStats.get(type) || 0) + 1);

        // Return cached module if already loaded
        if (loadedModules.has(type)) {
            return loadedModules.get(type);
        }

        // Return existing loading promise if in progress
        if (loadingPromises.has(type)) {
            return loadingPromises.get(type);
        }

        // Start loading
        const loadPromise = this._loadWidget(type, config);
        loadingPromises.set(type, loadPromise);

        try {
            const WidgetClass = await loadPromise;
            loadedModules.set(type, WidgetClass);
            config.loaded = true;
            return WidgetClass;
        } finally {
            loadingPromises.delete(type);
        }
    },

    /**
     * Check if widget type is registered
     */
    has(type) {
        return registry.has(type);
    },

    /**
     * Check if widget is loaded
     */
    isLoaded(type) {
        return loadedModules.has(type);
    },

    /**
     * Get all registered widget types
     */
    getTypes() {
        return Array.from(registry.keys());
    },

    /**
     * Get widget metadata (without loading)
     */
    getMeta(type) {
        const config = registry.get(type);
        if (!config) return null;

        return {
            type: config.type,
            name: config.name,
            category: config.category,
            defaultSize: { ...config.defaultSize },
            loaded: config.loaded
        };
    },

    /**
     * Get all widget metadata grouped by category
     */
    getByCategory() {
        const categories = {};
        for (const [type, config] of registry) {
            const category = config.category;
            if (!categories[category]) {
                categories[category] = [];
            }
            categories[category].push(this.getMeta(type));
        }
        return categories;
    },

    /**
     * Preload high-priority widgets
     */
    async preloadPriority(maxPriority = 50) {
        const toPreload = Array.from(registry.entries())
            .filter(([_, config]) => config.priority <= maxPriority && !config.loaded)
            .sort((a, b) => a[1].priority - b[1].priority)
            .map(([type]) => type);

        await Promise.all(toPreload.map(type => this.get(type).catch(() => null)));
    },

    /**
     * Preload widgets based on usage stats
     */
    async preloadMostUsed(count = 5) {
        const sorted = Array.from(usageStats.entries())
            .filter(([type]) => !loadedModules.has(type))
            .sort((a, b) => b[1] - a[1])
            .slice(0, count)
            .map(([type]) => type);

        await Promise.all(sorted.map(type => this.get(type).catch(() => null)));
    },

    /**
     * Unload a widget to free memory (for virtualization)
     */
    unload(type) {
        loadedModules.delete(type);
        const config = registry.get(type);
        if (config) {
            config.loaded = false;
        }
    },

    /**
     * Get loading statistics
     */
    getStats() {
        return {
            registered: registry.size,
            loaded: loadedModules.size,
            usage: Object.fromEntries(usageStats)
        };
    },

    // Private method for loading
    async _loadWidget(type, config) {
        const startTime = performance.now();

        try {
            const module = await config.loader();
            const WidgetClass = module.default || module[type] || Object.values(module)[0];

            if (!WidgetClass) {
                throw new Error(`No widget class exported from module for type "${type}"`);
            }

            const loadTime = performance.now() - startTime;
            if (loadTime > 100) {
                console.debug(`Widget "${type}" loaded in ${loadTime.toFixed(1)}ms`);
            }

            return WidgetClass;
        } catch (error) {
            console.error(`Failed to load widget "${type}":`, error);
            throw error;
        }
    }
};

// Freeze the registry API
Object.freeze(WidgetRegistry);
