/**
 * LayoutManager - Orchestrator for widget layout with virtualization
 *
 * Design principles:
 * - Passive orchestrator - no business logic
 * - Viewport virtualization via IntersectionObserver
 * - Relative unit calculations
 * - Minimal reflow on breakpoint changes
 * - Debounced resize handling
 */

import { DashboardConfig } from './config.js';
import { getStateManager } from './StateManager.js';
import { WidgetRegistry } from './WidgetRegistry.js';
import { DragDropManager } from './DragDropManager.js';

export class LayoutManager {
    constructor(container) {
        this.container = container;
        this.stateManager = getStateManager();
        this.dragDropManager = null;

        // Active widget instances
        this._widgets = new Map();

        // Widget containers (DOM elements)
        this._containers = new Map();

        // Virtualization state
        this._visibleWidgets = new Set();
        this._intersectionObserver = null;

        // Current breakpoint
        this._currentBreakpoint = null;
        this._gridMetrics = null;

        // Resize handling
        this._resizeObserver = null;
        this._resizeTimeout = null;

        // Performance metrics
        this._metrics = {
            mountCount: 0,
            unmountCount: 0,
            resizeCount: 0
        };
    }

    /**
     * Initialize layout manager
     */
    async init() {
        // Setup container
        this.container.classList.add('dashboard-grid');
        this.container.style.position = 'relative';

        // Initialize state manager
        await this.stateManager.init();

        // Calculate initial grid metrics
        this._updateGridMetrics();

        // Setup virtualization observer
        this._setupIntersectionObserver();

        // Setup resize observer
        this._setupResizeObserver();

        // Initialize drag & drop
        this.dragDropManager = new DragDropManager(this);
        this.dragDropManager.init(this.container);

        // Subscribe to state changes
        this.stateManager.subscribeGlobal(this._onLayoutChange.bind(this));

        // Initial render
        await this._renderLayout();

        return this;
    }

    /**
     * Destroy and cleanup
     */
    destroy() {
        this.dragDropManager?.destroy();
        this._intersectionObserver?.disconnect();
        this._resizeObserver?.disconnect();

        // Destroy all widgets
        for (const [id, widget] of this._widgets) {
            widget.destroy();
        }

        this._widgets.clear();
        this._containers.clear();
        this._visibleWidgets.clear();
    }

    // --- Public API ---

    /**
     * Add a new widget to the layout
     */
    async addWidget(type, config = {}) {
        const widgetId = config.id || `widget-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const meta = WidgetRegistry.getMeta(type);

        if (!meta) {
            throw new Error(`Unknown widget type: ${type}`);
        }

        // Find available position
        const position = config.x !== undefined && config.y !== undefined
            ? { x: config.x, y: config.y }
            : this._findAvailablePosition(meta.defaultSize);

        // Add to state
        const state = this.stateManager.addWidget(widgetId, {
            type,
            x: position.x,
            y: position.y,
            width: config.width ?? meta.defaultSize.width,
            height: config.height ?? meta.defaultSize.height,
            data: config.data ?? {}
        });

        // Create and mount widget
        await this._mountWidget(widgetId, state);

        return widgetId;
    }

    /**
     * Remove a widget from the layout
     */
    removeWidget(widgetId) {
        this._unmountWidget(widgetId);
        this.stateManager.removeWidget(widgetId);
    }

    /**
     * Update widget data
     */
    updateWidgetData(widgetId, data) {
        const widget = this._widgets.get(widgetId);
        if (widget) {
            widget.update({ data });
        }
    }

    /**
     * Get all widgets
     */
    getWidgets() {
        return Array.from(this._widgets.entries()).map(([id, widget]) => ({
            id,
            type: widget.type,
            metrics: widget.getMetrics()
        }));
    }

    // --- Drag & Drop callbacks ---

    onDragStart(widgetId) {
        const container = this._containers.get(widgetId);
        if (container) {
            container.classList.add('is-dragging');
        }
    }

    onDragEnd(widgetId, gridX, gridY) {
        const container = this._containers.get(widgetId);
        if (container) {
            container.classList.remove('is-dragging');
            this._positionWidget(widgetId, container);
        }
    }

    // --- Private methods ---

    async _renderLayout() {
        const widgets = this.stateManager.getAllWidgetStates();

        // Sort by position for consistent rendering
        widgets.sort((a, b) => {
            if (a.y !== b.y) return a.y - b.y;
            return a.x - b.x;
        });

        // Mount widgets
        for (const state of widgets) {
            await this._mountWidget(state.id, state);
        }
    }

    async _mountWidget(widgetId, state) {
        // Skip if already mounted
        if (this._widgets.has(widgetId)) return;

        // Create container element
        const container = document.createElement('div');
        container.className = 'widget-container';
        container.dataset.widgetId = widgetId;
        container.dataset.widgetType = state.type;

        // Add header with drag handle
        const header = document.createElement('div');
        header.className = 'widget-header widget-drag-handle';
        header.innerHTML = `
            <span class="widget-title">${WidgetRegistry.getMeta(state.type)?.name || state.type}</span>
            <div class="widget-actions">
                <button class="widget-action-btn widget-refresh" title="Refresh">
                    <i class="fas fa-sync-alt"></i>
                </button>
                <button class="widget-action-btn widget-remove" title="Remove">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        container.appendChild(header);

        // Add content area
        const content = document.createElement('div');
        content.className = 'widget-body';
        container.appendChild(content);

        // Store container
        this._containers.set(widgetId, container);

        // Position container
        this._positionWidget(widgetId, container, state);

        // Add to DOM
        this.container.appendChild(container);

        // Setup action handlers
        this._setupWidgetActions(widgetId, container);

        // Observe for virtualization
        this._intersectionObserver?.observe(container);

        this._metrics.mountCount++;

        // Lazy load widget class if visible
        if (this._isInViewport(container)) {
            await this._activateWidget(widgetId, state, content);
        }
    }

    async _activateWidget(widgetId, state, contentElement) {
        try {
            // Get widget class from registry
            const WidgetClass = await WidgetRegistry.get(state.type);

            // Create instance
            const widget = new WidgetClass(widgetId, state.data);

            // Mount to content element
            widget.mount(contentElement);

            // Store instance
            this._widgets.set(widgetId, widget);
            this._visibleWidgets.add(widgetId);

            // Initial render
            widget.update({ data: state.data });
            widget.onVisible();

        } catch (error) {
            console.error(`Failed to activate widget ${widgetId}:`, error);
            contentElement.innerHTML = `
                <div class="widget-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>Failed to load widget</span>
                </div>
            `;
        }
    }

    _deactivateWidget(widgetId) {
        const widget = this._widgets.get(widgetId);
        if (widget) {
            widget.onHidden();
            widget.destroy();
            this._widgets.delete(widgetId);
            this._visibleWidgets.delete(widgetId);
            this._metrics.unmountCount++;
        }
    }

    _unmountWidget(widgetId) {
        // Deactivate first
        this._deactivateWidget(widgetId);

        // Remove container
        const container = this._containers.get(widgetId);
        if (container) {
            this._intersectionObserver?.unobserve(container);
            container.remove();
            this._containers.delete(widgetId);
        }
    }

    _positionWidget(widgetId, container, state) {
        state = state || this.stateManager.getWidgetState(widgetId);
        if (!state) return;

        const { columnWidth, rowHeight, gap } = this._gridMetrics;

        const left = state.x * (columnWidth + gap);
        const top = state.y * (rowHeight + gap);
        const width = state.width * columnWidth + (state.width - 1) * gap;
        const height = state.height * rowHeight + (state.height - 1) * gap;

        container.style.position = 'absolute';
        container.style.left = `${left}px`;
        container.style.top = `${top}px`;
        container.style.width = `${width}px`;
        container.style.height = `${height}px`;
    }

    _setupWidgetActions(widgetId, container) {
        // Remove button
        const removeBtn = container.querySelector('.widget-remove');
        removeBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.removeWidget(widgetId);
        });

        // Refresh button
        const refreshBtn = container.querySelector('.widget-refresh');
        refreshBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            const widget = this._widgets.get(widgetId);
            if (widget) {
                widget._lastDataHash = null; // Force re-render
                widget.update({ data: this.stateManager.getWidgetState(widgetId)?.data });
            }
        });
    }

    _findAvailablePosition(size) {
        const widgets = this.stateManager.getAllWidgetStates();
        const { columns } = DashboardConfig.grid;

        // Simple grid placement - find first available position
        const grid = new Set();

        for (const widget of widgets) {
            for (let x = widget.x; x < widget.x + widget.width; x++) {
                for (let y = widget.y; y < widget.y + widget.height; y++) {
                    grid.add(`${x},${y}`);
                }
            }
        }

        // Find first available position
        for (let y = 0; y < 100; y++) {
            for (let x = 0; x <= columns - size.width; x++) {
                let available = true;

                for (let dx = 0; dx < size.width && available; dx++) {
                    for (let dy = 0; dy < size.height && available; dy++) {
                        if (grid.has(`${x + dx},${y + dy}`)) {
                            available = false;
                        }
                    }
                }

                if (available) {
                    return { x, y };
                }
            }
        }

        return { x: 0, y: 0 };
    }

    // --- Virtualization ---

    _setupIntersectionObserver() {
        const { viewportPadding, maxWidgetsBeforeVirtualization } = DashboardConfig.performance;

        this._intersectionObserver = new IntersectionObserver(
            (entries) => {
                // Skip virtualization if few widgets
                if (this._containers.size < maxWidgetsBeforeVirtualization) return;

                for (const entry of entries) {
                    const widgetId = entry.target.dataset.widgetId;
                    if (!widgetId) continue;

                    if (entry.isIntersecting) {
                        // Widget entering viewport
                        if (!this._widgets.has(widgetId)) {
                            const state = this.stateManager.getWidgetState(widgetId);
                            const content = entry.target.querySelector('.widget-body');
                            if (state && content) {
                                this._activateWidget(widgetId, state, content);
                            }
                        }
                    } else {
                        // Widget leaving viewport - deactivate to save memory
                        this._deactivateWidget(widgetId);
                    }
                }
            },
            {
                root: null,
                rootMargin: `${viewportPadding}px`,
                threshold: 0
            }
        );
    }

    _isInViewport(element) {
        const rect = element.getBoundingClientRect();
        const padding = DashboardConfig.performance.viewportPadding;

        return (
            rect.bottom >= -padding &&
            rect.right >= -padding &&
            rect.top <= (window.innerHeight || document.documentElement.clientHeight) + padding &&
            rect.left <= (window.innerWidth || document.documentElement.clientWidth) + padding
        );
    }

    // --- Resize handling ---

    _setupResizeObserver() {
        this._resizeObserver = new ResizeObserver((entries) => {
            // Debounce resize handling
            if (this._resizeTimeout) {
                clearTimeout(this._resizeTimeout);
            }

            this._resizeTimeout = setTimeout(() => {
                this._onContainerResize();
            }, DashboardConfig.performance.resizeDebounceMs);
        });

        this._resizeObserver.observe(this.container);
    }

    _onContainerResize() {
        const oldBreakpoint = this._currentBreakpoint;
        this._updateGridMetrics();

        // Only reflow if breakpoint changed
        if (this._currentBreakpoint !== oldBreakpoint) {
            this._reflowLayout();
        } else {
            // Just reposition without full reflow
            for (const [widgetId, container] of this._containers) {
                this._positionWidget(widgetId, container);
            }
        }

        // Notify visible widgets
        for (const widgetId of this._visibleWidgets) {
            const widget = this._widgets.get(widgetId);
            const container = this._containers.get(widgetId);
            if (widget && container) {
                widget.onResize(container.offsetWidth, container.offsetHeight);
            }
        }

        this._metrics.resizeCount++;
    }

    _updateGridMetrics() {
        const containerWidth = this.container.offsetWidth;
        const { breakpoints, rowHeight, gap } = DashboardConfig.grid;

        // Determine current breakpoint
        let currentBreakpoint = 'xs';
        for (const [name, config] of Object.entries(breakpoints)) {
            if (containerWidth >= config.minWidth) {
                currentBreakpoint = name;
            }
        }

        const columns = breakpoints[currentBreakpoint].columns;
        const columnWidth = (containerWidth - gap * (columns - 1)) / columns;

        this._currentBreakpoint = currentBreakpoint;
        this._gridMetrics = {
            columns,
            columnWidth,
            rowHeight,
            gap,
            containerWidth
        };
    }

    _reflowLayout() {
        // Recalculate positions for new breakpoint
        const widgets = this.stateManager.getAllWidgetStates();
        const { columns } = this._gridMetrics;

        // Simple reflow - clamp x positions to fit
        for (const state of widgets) {
            if (state.x + state.width > columns) {
                const newX = Math.max(0, columns - state.width);
                this.stateManager.setWidgetState(state.id, { x: newX }, { silent: true });
            }
        }

        // Reposition all widgets
        for (const [widgetId, container] of this._containers) {
            this._positionWidget(widgetId, container);
        }
    }

    _onLayoutChange(widgets) {
        // Reposition all widgets
        for (const widget of widgets) {
            const container = this._containers.get(widget.id);
            if (container) {
                this._positionWidget(widget.id, container, widget);
            }
        }
    }

    /**
     * Get metrics for debugging
     */
    getMetrics() {
        return {
            ...this._metrics,
            totalWidgets: this._containers.size,
            activeWidgets: this._widgets.size,
            visibleWidgets: this._visibleWidgets.size,
            breakpoint: this._currentBreakpoint
        };
    }
}
