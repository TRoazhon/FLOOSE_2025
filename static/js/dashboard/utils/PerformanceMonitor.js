/**
 * PerformanceMonitor - FPS tracking and render diagnostics
 *
 * Provides real-time performance metrics for the dashboard:
 * - FPS counter
 * - Render count tracking
 * - Frame budget alerts
 * - Memory usage (if available)
 */

import { DashboardConfig } from '../core/config.js';

export class PerformanceMonitor {
    constructor(options = {}) {
        this._enabled = options.enabled ?? false;
        this._showOverlay = options.showOverlay ?? false;

        // FPS tracking
        this._frames = [];
        this._lastFrameTime = 0;
        this._fps = 0;

        // Render tracking
        this._renderCounts = new Map();
        this._totalRenders = 0;

        // Budget tracking
        this._budgetViolations = 0;
        this._maxRenderTime = DashboardConfig.performance.maxRenderTimeMs;

        // Overlay element
        this._overlay = null;

        // RAF handle
        this._rafId = null;
    }

    /**
     * Start monitoring
     */
    start() {
        if (!this._enabled) return this;

        this._lastFrameTime = performance.now();
        this._tick();

        if (this._showOverlay) {
            this._createOverlay();
        }

        return this;
    }

    /**
     * Stop monitoring
     */
    stop() {
        if (this._rafId) {
            cancelAnimationFrame(this._rafId);
            this._rafId = null;
        }

        this._removeOverlay();
    }

    /**
     * Enable/disable monitoring
     */
    setEnabled(enabled) {
        this._enabled = enabled;
        if (enabled) {
            this.start();
        } else {
            this.stop();
        }
    }

    /**
     * Track a render operation
     */
    trackRender(componentId, duration) {
        if (!this._enabled) return;

        const current = this._renderCounts.get(componentId) || 0;
        this._renderCounts.set(componentId, current + 1);
        this._totalRenders++;

        if (duration > this._maxRenderTime) {
            this._budgetViolations++;
            console.warn(
                `[Perf] Budget violation: ${componentId} took ${duration.toFixed(2)}ms (budget: ${this._maxRenderTime}ms)`
            );
        }
    }

    /**
     * Measure a function's execution time
     */
    measure(name, fn) {
        if (!this._enabled) return fn();

        const start = performance.now();
        const result = fn();
        const duration = performance.now() - start;

        this.trackRender(name, duration);

        return result;
    }

    /**
     * Async measure
     */
    async measureAsync(name, fn) {
        if (!this._enabled) return fn();

        const start = performance.now();
        const result = await fn();
        const duration = performance.now() - start;

        this.trackRender(name, duration);

        return result;
    }

    /**
     * Get current metrics
     */
    getMetrics() {
        return {
            fps: Math.round(this._fps),
            totalRenders: this._totalRenders,
            budgetViolations: this._budgetViolations,
            rendersByComponent: Object.fromEntries(this._renderCounts),
            memory: this._getMemoryUsage()
        };
    }

    /**
     * Reset metrics
     */
    reset() {
        this._renderCounts.clear();
        this._totalRenders = 0;
        this._budgetViolations = 0;
        this._frames = [];
    }

    /**
     * Log metrics to console
     */
    log() {
        const metrics = this.getMetrics();
        console.group('[Dashboard Performance]');
        console.log(`FPS: ${metrics.fps}`);
        console.log(`Total Renders: ${metrics.totalRenders}`);
        console.log(`Budget Violations: ${metrics.budgetViolations}`);
        if (metrics.memory) {
            console.log(`Memory: ${(metrics.memory.usedJSHeapSize / 1048576).toFixed(2)}MB`);
        }
        console.log('Renders by Component:', metrics.rendersByComponent);
        console.groupEnd();
    }

    // --- Private methods ---

    _tick() {
        const now = performance.now();
        const delta = now - this._lastFrameTime;
        this._lastFrameTime = now;

        // Track frame times (keep last 60)
        this._frames.push(delta);
        if (this._frames.length > 60) {
            this._frames.shift();
        }

        // Calculate FPS
        const avgFrameTime = this._frames.reduce((a, b) => a + b, 0) / this._frames.length;
        this._fps = 1000 / avgFrameTime;

        // Update overlay
        this._updateOverlay();

        // Schedule next tick
        this._rafId = requestAnimationFrame(() => this._tick());
    }

    _createOverlay() {
        this._overlay = document.createElement('div');
        this._overlay.className = 'perf-monitor-overlay';
        this._overlay.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: rgba(0, 0, 0, 0.8);
            color: #0f0;
            font-family: monospace;
            font-size: 12px;
            padding: 8px 12px;
            border-radius: 4px;
            z-index: 99999;
            pointer-events: none;
            min-width: 120px;
        `;
        document.body.appendChild(this._overlay);
    }

    _removeOverlay() {
        if (this._overlay) {
            this._overlay.remove();
            this._overlay = null;
        }
    }

    _updateOverlay() {
        if (!this._overlay) return;

        const fpsColor = this._fps >= 55 ? '#0f0' : this._fps >= 30 ? '#ff0' : '#f00';
        const memory = this._getMemoryUsage();

        this._overlay.innerHTML = `
            <div style="color: ${fpsColor}">FPS: ${Math.round(this._fps)}</div>
            <div>Renders: ${this._totalRenders}</div>
            <div>Violations: ${this._budgetViolations}</div>
            ${memory ? `<div>Mem: ${(memory.usedJSHeapSize / 1048576).toFixed(1)}MB</div>` : ''}
        `;
    }

    _getMemoryUsage() {
        // Only available in Chrome
        if (performance.memory) {
            return {
                usedJSHeapSize: performance.memory.usedJSHeapSize,
                totalJSHeapSize: performance.memory.totalJSHeapSize
            };
        }
        return null;
    }
}

// Singleton instance
let instance = null;

export function getPerformanceMonitor(options) {
    if (!instance) {
        instance = new PerformanceMonitor(options);
    }
    return instance;
}
