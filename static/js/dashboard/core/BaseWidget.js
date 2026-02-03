/**
 * BaseWidget - Abstract base class for all dashboard widgets
 *
 * Design principles:
 * - Complete isolation - no cross-widget dependencies
 * - Unidirectional data flow (props → render)
 * - Memoization-ready with shouldUpdate check
 * - Lifecycle hooks for performance optimization
 * - Self-contained cleanup
 */

export class BaseWidget {
    /**
     * @param {string} id - Unique widget instance ID
     * @param {Object} config - Widget configuration
     */
    constructor(id, config = {}) {
        this.id = id;
        this.type = this.constructor.type || 'base';
        this.config = { ...config };

        // DOM references
        this.container = null;
        this.contentElement = null;

        // State tracking for memoization
        this._lastProps = null;
        this._lastDataHash = null;
        this._mounted = false;
        this._destroyed = false;

        // Render metrics
        this._renderCount = 0;
        this._lastRenderTime = 0;

        // Bound methods for event handlers
        this._boundHandlers = new Map();
    }

    // --- Static properties (override in subclasses) ---

    static get type() {
        return 'base';
    }

    static get name() {
        return 'Base Widget';
    }

    static get category() {
        return 'general';
    }

    static get defaultSize() {
        return { width: 4, height: 3 };
    }

    // --- Lifecycle methods ---

    /**
     * Mount widget to DOM container
     */
    mount(container) {
        if (this._destroyed) {
            throw new Error(`Cannot mount destroyed widget ${this.id}`);
        }

        this.container = container;
        this.container.classList.add('widget', `widget-${this.type}`);
        this.container.dataset.widgetId = this.id;
        this.container.dataset.widgetType = this.type;

        // Create inner content wrapper
        this.contentElement = document.createElement('div');
        this.contentElement.className = 'widget-content';
        this.container.appendChild(this.contentElement);

        // Call subclass initialization
        this.onMount();
        this._mounted = true;

        return this;
    }

    /**
     * Called after mounting - override in subclasses
     */
    onMount() {
        // Override in subclasses
    }

    /**
     * Update widget with new props/data
     */
    update(props) {
        if (!this._mounted || this._destroyed) return false;

        // Memoization check
        if (!this.shouldUpdate(props, this._lastProps)) {
            return false;
        }

        const startTime = performance.now();

        this._lastProps = this._cloneProps(props);
        this.render(props);

        this._renderCount++;
        this._lastRenderTime = performance.now() - startTime;

        return true;
    }

    /**
     * Check if widget should re-render - override for custom logic
     */
    shouldUpdate(nextProps, prevProps) {
        if (!prevProps) return true;

        // Default: shallow comparison of data
        const nextData = nextProps?.data;
        const prevData = prevProps?.data;

        if (!nextData && !prevData) return false;
        if (!nextData || !prevData) return true;

        // Fast hash comparison for data
        const nextHash = this._hashData(nextData);
        if (nextHash !== this._lastDataHash) {
            this._lastDataHash = nextHash;
            return true;
        }

        return false;
    }

    /**
     * Render widget content - MUST override in subclasses
     */
    render(props) {
        throw new Error('render() must be implemented by subclass');
    }

    /**
     * Called when widget becomes visible in viewport
     */
    onVisible() {
        // Override in subclasses for lazy initialization
    }

    /**
     * Called when widget leaves viewport
     */
    onHidden() {
        // Override in subclasses for resource cleanup
    }

    /**
     * Called when widget is being resized
     */
    onResize(width, height) {
        // Override in subclasses
    }

    /**
     * Called when resize is complete
     */
    onResizeEnd(width, height) {
        // Override in subclasses
    }

    /**
     * Destroy widget and cleanup
     */
    destroy() {
        if (this._destroyed) return;

        this.onDestroy();

        // Remove event handlers
        this._boundHandlers.forEach((handler, key) => {
            const [element, event] = key.split(':');
            document.querySelector(element)?.removeEventListener(event, handler);
        });
        this._boundHandlers.clear();

        // Clear DOM
        if (this.container) {
            this.container.innerHTML = '';
            this.container.classList.remove('widget', `widget-${this.type}`);
        }

        this.container = null;
        this.contentElement = null;
        this._mounted = false;
        this._destroyed = true;
    }

    /**
     * Called during destroy - override for custom cleanup
     */
    onDestroy() {
        // Override in subclasses
    }

    // --- Utility methods ---

    /**
     * Register event handler with automatic cleanup
     */
    on(element, event, handler) {
        const boundHandler = handler.bind(this);
        element.addEventListener(event, boundHandler);

        const key = `${element.id || element.className}:${event}`;
        this._boundHandlers.set(key, boundHandler);

        return boundHandler;
    }

    /**
     * Get metrics for debugging
     */
    getMetrics() {
        return {
            id: this.id,
            type: this.type,
            mounted: this._mounted,
            renderCount: this._renderCount,
            lastRenderTime: this._lastRenderTime
        };
    }

    /**
     * Set loading state
     */
    setLoading(loading) {
        if (!this.container) return;
        this.container.classList.toggle('widget-loading', loading);
    }

    /**
     * Set error state
     */
    setError(error) {
        if (!this.contentElement) return;

        this.container.classList.add('widget-error');
        this.contentElement.innerHTML = `
            <div class="widget-error-content">
                <i class="fas fa-exclamation-triangle"></i>
                <span>${error?.message || 'Error loading widget'}</span>
            </div>
        `;
    }

    // --- Private methods ---

    _cloneProps(props) {
        if (!props) return null;
        try {
            return JSON.parse(JSON.stringify(props));
        } catch {
            return { ...props };
        }
    }

    _hashData(data) {
        // Fast hash for shallow data comparison
        if (!data) return 0;
        const str = JSON.stringify(data);
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return hash;
    }
}
