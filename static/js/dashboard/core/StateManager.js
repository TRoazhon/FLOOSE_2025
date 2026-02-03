/**
 * StateManager - Minimal flat state management for dashboard
 *
 * Design principles:
 * - Flat map indexed by widget ID for O(1) access
 * - Separate ephemeral (drag) and persistent (layout) state
 * - No global recalculation on individual widget changes
 * - Idle callback persistence
 */
import { DashboardConfig } from './config.js';

export class StateManager {
    constructor() {
        // Persistent state - flat map indexed by widget ID
        this._layoutState = new Map();

        // Ephemeral state for drag operations
        this._ephemeralState = new Map();

        // Subscribers by widget ID for targeted updates
        this._subscribers = new Map();

        // Global subscribers for layout-wide changes
        this._globalSubscribers = new Set();

        // Pending save handle
        this._pendingSaveHandle = null;

        // Dirty tracking for efficient saves
        this._dirtyWidgets = new Set();

        // Performance metrics
        this._metrics = {
            updateCount: 0,
            lastSaveTime: 0
        };
    }

    /**
     * Initialize state from storage or defaults
     */
    async init() {
        const stored = this._loadFromStorage();
        if (stored) {
            for (const [id, state] of Object.entries(stored.widgets)) {
                this._layoutState.set(id, { ...state });
            }
        }
        return this;
    }

    /**
     * Get widget state by ID - O(1)
     */
    getWidgetState(widgetId) {
        return this._layoutState.get(widgetId) || null;
    }

    /**
     * Get all widget states as array (for iteration)
     */
    getAllWidgetStates() {
        return Array.from(this._layoutState.entries()).map(([id, state]) => ({
            id,
            ...state
        }));
    }

    /**
     * Set widget state - triggers targeted subscriber notification
     */
    setWidgetState(widgetId, newState, options = {}) {
        const { ephemeral = false, silent = false } = options;

        if (ephemeral) {
            // Ephemeral state for drag - never persisted
            this._ephemeralState.set(widgetId, { ...newState });
        } else {
            const currentState = this._layoutState.get(widgetId);
            const mergedState = currentState
                ? { ...currentState, ...newState }
                : { ...newState };

            this._layoutState.set(widgetId, mergedState);
            this._dirtyWidgets.add(widgetId);
            this._metrics.updateCount++;

            // Schedule idle save
            this._scheduleSave();
        }

        if (!silent) {
            this._notifySubscribers(widgetId, ephemeral);
        }
    }

    /**
     * Commit ephemeral state to persistent
     */
    commitEphemeralState(widgetId) {
        const ephemeral = this._ephemeralState.get(widgetId);
        if (ephemeral) {
            this.setWidgetState(widgetId, ephemeral, { ephemeral: false });
            this._ephemeralState.delete(widgetId);
        }
    }

    /**
     * Discard ephemeral state
     */
    discardEphemeralState(widgetId) {
        this._ephemeralState.delete(widgetId);
        this._notifySubscribers(widgetId, false);
    }

    /**
     * Get current position (ephemeral if exists, else persistent)
     */
    getCurrentPosition(widgetId) {
        const ephemeral = this._ephemeralState.get(widgetId);
        if (ephemeral) {
            return { x: ephemeral.x, y: ephemeral.y };
        }
        const persistent = this._layoutState.get(widgetId);
        return persistent ? { x: persistent.x, y: persistent.y } : null;
    }

    /**
     * Batch update multiple widgets - single notification
     */
    batchUpdate(updates) {
        const affectedIds = new Set();

        for (const { widgetId, state, ephemeral } of updates) {
            if (ephemeral) {
                this._ephemeralState.set(widgetId, { ...state });
            } else {
                const currentState = this._layoutState.get(widgetId);
                this._layoutState.set(widgetId, { ...currentState, ...state });
                this._dirtyWidgets.add(widgetId);
            }
            affectedIds.add(widgetId);
        }

        this._metrics.updateCount++;
        this._scheduleSave();

        // Notify global subscribers once
        this._notifyGlobalSubscribers();
    }

    /**
     * Subscribe to widget state changes
     */
    subscribe(widgetId, callback) {
        if (!this._subscribers.has(widgetId)) {
            this._subscribers.set(widgetId, new Set());
        }
        this._subscribers.get(widgetId).add(callback);

        return () => {
            this._subscribers.get(widgetId)?.delete(callback);
        };
    }

    /**
     * Subscribe to all layout changes
     */
    subscribeGlobal(callback) {
        this._globalSubscribers.add(callback);
        return () => this._globalSubscribers.delete(callback);
    }

    /**
     * Add new widget to state
     */
    addWidget(widgetId, config) {
        const state = {
            type: config.type,
            x: config.x ?? 0,
            y: config.y ?? 0,
            width: config.width ?? DashboardConfig.widget.defaultWidth,
            height: config.height ?? DashboardConfig.widget.defaultHeight,
            data: config.data ?? {},
            visible: true
        };

        this._layoutState.set(widgetId, state);
        this._dirtyWidgets.add(widgetId);
        this._scheduleSave();
        this._notifyGlobalSubscribers();

        return state;
    }

    /**
     * Remove widget from state
     */
    removeWidget(widgetId) {
        this._layoutState.delete(widgetId);
        this._ephemeralState.delete(widgetId);
        this._subscribers.delete(widgetId);
        this._dirtyWidgets.add(widgetId);
        this._scheduleSave();
        this._notifyGlobalSubscribers();
    }

    /**
     * Export layout for serialization
     */
    exportLayout() {
        const widgets = {};
        for (const [id, state] of this._layoutState) {
            // Compact serialization - only essential fields
            widgets[id] = {
                t: state.type,
                x: state.x,
                y: state.y,
                w: state.width,
                h: state.height
            };
        }
        return {
            v: DashboardConfig.storage.version,
            widgets
        };
    }

    /**
     * Import layout from serialized data
     */
    importLayout(data) {
        if (!data || data.v !== DashboardConfig.storage.version) {
            console.warn('Layout version mismatch, using defaults');
            return false;
        }

        this._layoutState.clear();

        for (const [id, compact] of Object.entries(data.widgets)) {
            this._layoutState.set(id, {
                type: compact.t,
                x: compact.x,
                y: compact.y,
                width: compact.w,
                height: compact.h,
                data: {},
                visible: true
            });
        }

        this._notifyGlobalSubscribers();
        return true;
    }

    // --- Private methods ---

    _notifySubscribers(widgetId, isEphemeral) {
        const subscribers = this._subscribers.get(widgetId);
        if (subscribers) {
            const state = isEphemeral
                ? this._ephemeralState.get(widgetId)
                : this._layoutState.get(widgetId);

            for (const callback of subscribers) {
                callback(state, isEphemeral);
            }
        }
    }

    _notifyGlobalSubscribers() {
        for (const callback of this._globalSubscribers) {
            callback(this.getAllWidgetStates());
        }
    }

    _scheduleSave() {
        if (this._pendingSaveHandle) {
            cancelIdleCallback(this._pendingSaveHandle);
        }

        this._pendingSaveHandle = requestIdleCallback(() => {
            this._persistToStorage();
            this._pendingSaveHandle = null;
        }, { timeout: DashboardConfig.performance.saveIdleDelayMs });
    }

    _persistToStorage() {
        if (this._dirtyWidgets.size === 0) return;

        const startTime = performance.now();
        const layout = this.exportLayout();

        try {
            localStorage.setItem(
                DashboardConfig.storage.layoutKey,
                JSON.stringify(layout)
            );
            this._dirtyWidgets.clear();
            this._metrics.lastSaveTime = performance.now() - startTime;
        } catch (e) {
            console.error('Failed to persist layout:', e);
        }
    }

    _loadFromStorage() {
        try {
            const stored = localStorage.getItem(DashboardConfig.storage.layoutKey);
            if (stored) {
                const data = JSON.parse(stored);
                // Expand compact format
                const widgets = {};
                for (const [id, compact] of Object.entries(data.widgets)) {
                    widgets[id] = {
                        type: compact.t,
                        x: compact.x,
                        y: compact.y,
                        width: compact.w,
                        height: compact.h,
                        data: {},
                        visible: true
                    };
                }
                return { ...data, widgets };
            }
        } catch (e) {
            console.error('Failed to load layout:', e);
        }
        return null;
    }

    /**
     * Get performance metrics
     */
    getMetrics() {
        return { ...this._metrics };
    }
}

// Singleton instance
let instance = null;

export function getStateManager() {
    if (!instance) {
        instance = new StateManager();
    }
    return instance;
}
