/**
 * DragDropManager - GPU-optimized drag & drop system
 *
 * Design principles:
 * - transform: translate3d for GPU acceleration
 * - No DOM modifications during drag (RAF + inline styles only)
 * - Throttling via RAF alignment
 * - Ephemeral state during drag, commit only on drop
 * - Touch and mouse support
 */

import { DashboardConfig } from './config.js';
import { getStateManager } from './StateManager.js';

export class DragDropManager {
    constructor(layoutManager) {
        this.layoutManager = layoutManager;
        this.stateManager = getStateManager();

        // Drag state
        this._isDragging = false;
        this._dragWidget = null;
        this._dragElement = null;
        this._startPos = { x: 0, y: 0 };
        this._currentPos = { x: 0, y: 0 };
        this._offset = { x: 0, y: 0 };
        this._rafId = null;

        // Grid snapping
        this._gridSize = { x: 0, y: 0 };

        // Drop zones
        this._dropZones = [];
        this._currentDropZone = null;

        // Placeholder element
        this._placeholder = null;

        // Bound handlers
        this._onMouseDown = this._onMouseDown.bind(this);
        this._onMouseMove = this._onMouseMove.bind(this);
        this._onMouseUp = this._onMouseUp.bind(this);
        this._onTouchStart = this._onTouchStart.bind(this);
        this._onTouchMove = this._onTouchMove.bind(this);
        this._onTouchEnd = this._onTouchEnd.bind(this);

        // Performance tracking
        this._frameCount = 0;
        this._lastFrameTime = 0;
    }

    /**
     * Initialize drag handlers on container
     */
    init(container) {
        this.container = container;
        this._calculateGridSize();

        // Create placeholder element
        this._placeholder = document.createElement('div');
        this._placeholder.className = 'widget-placeholder';
        this._placeholder.style.display = 'none';

        // Mouse events (delegated)
        container.addEventListener('mousedown', this._onMouseDown, { passive: false });
        document.addEventListener('mousemove', this._onMouseMove, { passive: true });
        document.addEventListener('mouseup', this._onMouseUp, { passive: true });

        // Touch events
        container.addEventListener('touchstart', this._onTouchStart, { passive: false });
        document.addEventListener('touchmove', this._onTouchMove, { passive: false });
        document.addEventListener('touchend', this._onTouchEnd, { passive: true });

        // Recalculate grid on resize
        window.addEventListener('resize', () => {
            this._calculateGridSize();
        });

        return this;
    }

    /**
     * Destroy and cleanup
     */
    destroy() {
        if (this._rafId) {
            cancelAnimationFrame(this._rafId);
        }

        this.container?.removeEventListener('mousedown', this._onMouseDown);
        document.removeEventListener('mousemove', this._onMouseMove);
        document.removeEventListener('mouseup', this._onMouseUp);
        this.container?.removeEventListener('touchstart', this._onTouchStart);
        document.removeEventListener('touchmove', this._onTouchMove);
        document.removeEventListener('touchend', this._onTouchEnd);
    }

    // --- Event handlers ---

    _onMouseDown(e) {
        const handle = e.target.closest('.widget-drag-handle, .widget-header');
        if (!handle) return;

        const widgetEl = e.target.closest('.widget-container');
        if (!widgetEl) return;

        e.preventDefault();
        this._startDrag(widgetEl, e.clientX, e.clientY);
    }

    _onMouseMove(e) {
        if (!this._isDragging) return;
        this._updateDrag(e.clientX, e.clientY);
    }

    _onMouseUp(e) {
        if (!this._isDragging) return;
        this._endDrag();
    }

    _onTouchStart(e) {
        if (e.touches.length !== 1) return;

        const handle = e.target.closest('.widget-drag-handle, .widget-header');
        if (!handle) return;

        const widgetEl = e.target.closest('.widget-container');
        if (!widgetEl) return;

        e.preventDefault();
        const touch = e.touches[0];
        this._startDrag(widgetEl, touch.clientX, touch.clientY);
    }

    _onTouchMove(e) {
        if (!this._isDragging) return;
        e.preventDefault();
        const touch = e.touches[0];
        this._updateDrag(touch.clientX, touch.clientY);
    }

    _onTouchEnd(e) {
        if (!this._isDragging) return;
        this._endDrag();
    }

    // --- Drag operations ---

    _startDrag(element, clientX, clientY) {
        const widgetId = element.dataset.widgetId;
        if (!widgetId) return;

        this._isDragging = true;
        this._dragElement = element;
        this._dragWidget = widgetId;

        // Get initial position
        const rect = element.getBoundingClientRect();
        const containerRect = this.container.getBoundingClientRect();

        this._startPos = {
            x: rect.left - containerRect.left,
            y: rect.top - containerRect.top
        };

        this._offset = {
            x: clientX - rect.left,
            y: clientY - rect.top
        };

        this._currentPos = { ...this._startPos };

        // Style for dragging - GPU layer promotion
        element.style.transition = DashboardConfig.animation.dragTransition;
        element.style.zIndex = '1000';
        element.style.willChange = 'transform';
        element.classList.add('widget-dragging');

        // Show placeholder
        this._showPlaceholder(element);

        // Notify layout manager
        this.layoutManager?.onDragStart?.(widgetId);
    }

    _updateDrag(clientX, clientY) {
        if (!this._isDragging || !this._dragElement) return;

        // RAF-aligned updates only
        if (this._rafId) return;

        this._rafId = requestAnimationFrame(() => {
            this._rafId = null;

            const containerRect = this.container.getBoundingClientRect();

            // Calculate new position
            const newX = clientX - containerRect.left - this._offset.x;
            const newY = clientY - containerRect.top - this._offset.y;

            // Snap to grid
            const snappedX = Math.round(newX / this._gridSize.x) * this._gridSize.x;
            const snappedY = Math.round(newY / this._gridSize.y) * this._gridSize.y;

            // Clamp to container bounds
            const maxX = containerRect.width - this._dragElement.offsetWidth;
            const maxY = containerRect.height - this._dragElement.offsetHeight;

            this._currentPos = {
                x: Math.max(0, Math.min(snappedX, maxX)),
                y: Math.max(0, Math.min(snappedY, maxY))
            };

            // Apply transform (GPU-accelerated)
            const deltaX = this._currentPos.x - this._startPos.x;
            const deltaY = this._currentPos.y - this._startPos.y;

            this._dragElement.style.transform = `translate3d(${deltaX}px, ${deltaY}px, 0)`;

            // Update placeholder position
            this._updatePlaceholder(this._currentPos.x, this._currentPos.y);

            // Update ephemeral state
            const gridX = Math.round(this._currentPos.x / this._gridSize.x);
            const gridY = Math.round(this._currentPos.y / this._gridSize.y);

            this.stateManager.setWidgetState(this._dragWidget, {
                x: gridX,
                y: gridY
            }, { ephemeral: true, silent: true });

            this._frameCount++;
        });
    }

    _endDrag() {
        if (!this._isDragging) return;

        if (this._rafId) {
            cancelAnimationFrame(this._rafId);
            this._rafId = null;
        }

        const widgetId = this._dragWidget;
        const element = this._dragElement;

        // Calculate final grid position
        const gridX = Math.round(this._currentPos.x / this._gridSize.x);
        const gridY = Math.round(this._currentPos.y / this._gridSize.y);

        // Commit ephemeral state to persistent
        this.stateManager.commitEphemeralState(widgetId);

        // Animate to final position
        element.style.transition = DashboardConfig.animation.dropTransition;

        // Reset transform and apply final position via layout manager
        requestAnimationFrame(() => {
            element.style.transform = '';
            element.style.zIndex = '';
            element.style.willChange = '';
            element.classList.remove('widget-dragging');

            // Hide placeholder
            this._hidePlaceholder();

            // Notify layout manager to apply final position
            this.layoutManager?.onDragEnd?.(widgetId, gridX, gridY);

            // Clear transition after animation
            setTimeout(() => {
                element.style.transition = '';
            }, 200);
        });

        // Reset drag state
        this._isDragging = false;
        this._dragElement = null;
        this._dragWidget = null;
    }

    // --- Placeholder management ---

    _showPlaceholder(element) {
        if (!this._placeholder.parentNode) {
            this.container.appendChild(this._placeholder);
        }

        this._placeholder.style.width = `${element.offsetWidth}px`;
        this._placeholder.style.height = `${element.offsetHeight}px`;
        this._placeholder.style.display = 'block';
        this._updatePlaceholder(this._startPos.x, this._startPos.y);
    }

    _updatePlaceholder(x, y) {
        this._placeholder.style.transform = `translate3d(${x}px, ${y}px, 0)`;
    }

    _hidePlaceholder() {
        this._placeholder.style.display = 'none';
    }

    // --- Grid calculations ---

    _calculateGridSize() {
        if (!this.container) return;

        const containerWidth = this.container.offsetWidth;
        const { columns, gap } = DashboardConfig.grid;

        this._gridSize = {
            x: (containerWidth - gap * (columns - 1)) / columns + gap,
            y: DashboardConfig.grid.rowHeight + gap
        };
    }

    // --- Public API ---

    /**
     * Check if currently dragging
     */
    isDragging() {
        return this._isDragging;
    }

    /**
     * Get drag metrics
     */
    getMetrics() {
        return {
            frameCount: this._frameCount,
            isDragging: this._isDragging
        };
    }
}
