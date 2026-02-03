/**
 * AIWidgetPicker - Modal UI for creating AI-powered KPI widgets
 *
 * Features:
 * - Natural language input for KPI description
 * - Real-time validation feedback
 * - Example prompts for guidance
 * - Manual fallback configuration
 * - Loading states and error handling
 */

import { getMistralService } from './MistralService.js';
import { getSchemaDocumentation, validateKPIConfig } from './KPIConfigSchema.js';

// Example prompts to guide users
const EXAMPLE_PROMPTS = [
    "Affiche le budget total de tous mes projets",
    "Montre l'évolution des dépenses par mois",
    "Compare les budgets entre catégories",
    "Jauge d'utilisation du budget en pourcentage",
    "Top 5 des projets par dépenses",
    "Nombre total de projets actifs",
    "Solde disponible sur tous mes comptes",
    "Taux de consommation mensuel (burn rate)"
];

export class AIWidgetPicker {
    constructor(options = {}) {
        this.onWidgetCreate = options.onWidgetCreate || (() => {});
        this.onClose = options.onClose || (() => {});

        this._overlay = null;
        this._modal = null;
        this._state = 'idle'; // idle | loading | error | manual
        this._currentPrompt = '';
        this._lastError = null;
    }

    /**
     * Show the picker modal
     */
    show() {
        this._createModal();
        document.body.appendChild(this._overlay);

        // Focus input
        setTimeout(() => {
            this._overlay.querySelector('.ai-prompt-input')?.focus();
        }, 100);
    }

    /**
     * Hide and cleanup
     */
    hide() {
        if (this._overlay) {
            this._overlay.remove();
            this._overlay = null;
            this._modal = null;
        }
        this.onClose();
    }

    /**
     * Create modal DOM
     */
    _createModal() {
        this._overlay = document.createElement('div');
        this._overlay.className = 'ai-picker-overlay';
        this._overlay.innerHTML = `
            <div class="ai-picker-modal">
                <div class="ai-picker-header">
                    <div class="ai-picker-title">
                        <i class="fas fa-magic"></i>
                        <h2>Créer un KPI Intelligent</h2>
                    </div>
                    <button class="ai-picker-close" aria-label="Fermer">&times;</button>
                </div>

                <div class="ai-picker-content">
                    <!-- Natural Language Input -->
                    <div class="ai-picker-section ai-prompt-section">
                        <label class="ai-picker-label">
                            Décrivez le KPI souhaité en langage naturel
                        </label>
                        <div class="ai-prompt-input-wrapper">
                            <textarea
                                class="ai-prompt-input"
                                placeholder="Ex: Affiche le budget total de tous mes projets en graphique..."
                                rows="3"
                                maxlength="500"
                            ></textarea>
                            <div class="ai-prompt-counter">
                                <span class="ai-prompt-count">0</span>/500
                            </div>
                        </div>

                        <div class="ai-prompt-examples">
                            <span class="ai-examples-label">Exemples:</span>
                            <div class="ai-examples-list">
                                ${EXAMPLE_PROMPTS.slice(0, 4).map(p => `
                                    <button class="ai-example-btn" data-prompt="${p}">
                                        ${p}
                                    </button>
                                `).join('')}
                            </div>
                        </div>
                    </div>

                    <!-- Status / Loading / Error -->
                    <div class="ai-picker-status" style="display: none;">
                        <div class="ai-status-loading">
                            <div class="ai-spinner"></div>
                            <p>L'IA analyse votre demande...</p>
                        </div>
                        <div class="ai-status-error" style="display: none;">
                            <i class="fas fa-exclamation-triangle"></i>
                            <p class="ai-error-message"></p>
                            <button class="btn btn-sm btn-outline ai-retry-btn">
                                <i class="fas fa-redo"></i> Réessayer
                            </button>
                        </div>
                    </div>

                    <!-- Manual Configuration Fallback -->
                    <div class="ai-picker-manual" style="display: none;">
                        <div class="ai-manual-header">
                            <span>Configuration manuelle</span>
                            <button class="ai-toggle-manual btn btn-sm btn-outline">
                                <i class="fas fa-robot"></i> Revenir à l'IA
                            </button>
                        </div>
                        <div class="ai-manual-form">
                            <div class="ai-form-row">
                                <label>Nom du KPI</label>
                                <input type="text" class="ai-manual-name" placeholder="Mon KPI">
                            </div>
                            <div class="ai-form-row">
                                <label>Métrique</label>
                                <select class="ai-manual-metric">
                                    <option value="budget_total">Budget Total</option>
                                    <option value="budget_spent">Budget Dépensé</option>
                                    <option value="budget_remaining">Budget Restant</option>
                                    <option value="project_count">Nombre de Projets</option>
                                    <option value="account_balance">Solde Comptes</option>
                                    <option value="burn_rate">Burn Rate</option>
                                </select>
                            </div>
                            <div class="ai-form-row">
                                <label>Visualisation</label>
                                <select class="ai-manual-viz">
                                    <option value="number">Nombre</option>
                                    <option value="gauge">Jauge</option>
                                    <option value="bar">Barres</option>
                                    <option value="line">Ligne</option>
                                    <option value="pie">Camembert</option>
                                </select>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="ai-picker-footer">
                    <button class="btn btn-outline ai-manual-trigger">
                        <i class="fas fa-sliders-h"></i> Configuration manuelle
                    </button>
                    <div class="ai-picker-actions">
                        <button class="btn btn-outline ai-cancel-btn">Annuler</button>
                        <button class="btn btn-primary ai-create-btn" disabled>
                            <i class="fas fa-magic"></i> Créer le KPI
                        </button>
                    </div>
                </div>
            </div>
        `;

        this._setupEventListeners();
    }

    /**
     * Setup event listeners
     */
    _setupEventListeners() {
        // Close button
        this._overlay.querySelector('.ai-picker-close').addEventListener('click', () => this.hide());

        // Cancel button
        this._overlay.querySelector('.ai-cancel-btn').addEventListener('click', () => this.hide());

        // Click outside to close
        this._overlay.addEventListener('click', (e) => {
            if (e.target === this._overlay) this.hide();
        });

        // Escape key to close
        document.addEventListener('keydown', this._handleKeydown = (e) => {
            if (e.key === 'Escape') this.hide();
        });

        // Prompt input
        const promptInput = this._overlay.querySelector('.ai-prompt-input');
        const charCounter = this._overlay.querySelector('.ai-prompt-count');
        const createBtn = this._overlay.querySelector('.ai-create-btn');

        promptInput.addEventListener('input', (e) => {
            const length = e.target.value.length;
            charCounter.textContent = length;
            this._currentPrompt = e.target.value;
            createBtn.disabled = length < 10;
        });

        // Example buttons
        this._overlay.querySelectorAll('.ai-example-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                promptInput.value = btn.dataset.prompt;
                promptInput.dispatchEvent(new Event('input'));
                promptInput.focus();
            });
        });

        // Create button
        createBtn.addEventListener('click', () => this._handleCreate());

        // Enter key to submit
        promptInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.metaKey && !createBtn.disabled) {
                this._handleCreate();
            }
        });

        // Manual configuration toggle
        this._overlay.querySelector('.ai-manual-trigger').addEventListener('click', () => {
            this._showManualMode();
        });

        const toggleManualBtn = this._overlay.querySelector('.ai-toggle-manual');
        if (toggleManualBtn) {
            toggleManualBtn.addEventListener('click', () => {
                this._showAIMode();
            });
        }

        // Retry button
        this._overlay.querySelector('.ai-retry-btn').addEventListener('click', () => {
            this._handleCreate();
        });
    }

    /**
     * Handle create button click
     */
    async _handleCreate() {
        if (this._state === 'manual') {
            this._createFromManual();
            return;
        }

        if (!this._currentPrompt || this._currentPrompt.length < 10) {
            return;
        }

        this._showLoading();

        try {
            const mistral = getMistralService();
            const { state, config } = await mistral.generateKPI(this._currentPrompt);

            if (state.status === 'success' && config) {
                this._createWidget(config, this._currentPrompt, state.rawResponse);
            } else if (state.status === 'ambiguous') {
                this._showError(state.ambiguity, state.suggestions);
            } else {
                this._showError(state.error);
            }
        } catch (error) {
            console.error('AI Widget creation error:', error);
            this._showError('Une erreur est survenue. Veuillez réessayer.');
        }
    }

    /**
     * Create widget from manual configuration
     */
    _createFromManual() {
        const name = this._overlay.querySelector('.ai-manual-name').value || 'KPI Personnalisé';
        const metric = this._overlay.querySelector('.ai-manual-metric').value;
        const viz = this._overlay.querySelector('.ai-manual-viz').value;

        const config = {
            kpi_name: name,
            metric: metric,
            aggregation: 'sum',
            time_range: 'this_month',
            filters: [],
            dimensions: metric.includes('budget') ? ['project'] : [],
            visualization: viz,
            refresh_rate: 60
        };

        const validation = validateKPIConfig(config);
        if (validation.valid) {
            this._createWidget(validation.config, `[Manuel] ${name}`, null);
        } else {
            this._showError(validation.errors.join(', '));
        }
    }

    /**
     * Create the widget and close modal
     */
    _createWidget(config, prompt, rawResponse) {
        this.onWidgetCreate({
            type: 'ai-kpi',
            config: {
                prompt: prompt,
                kpiConfig: config,
                rawResponse: rawResponse
            }
        });
        this.hide();
    }

    /**
     * Show loading state
     */
    _showLoading() {
        this._state = 'loading';
        const status = this._overlay.querySelector('.ai-picker-status');
        const loading = this._overlay.querySelector('.ai-status-loading');
        const error = this._overlay.querySelector('.ai-status-error');
        const createBtn = this._overlay.querySelector('.ai-create-btn');

        status.style.display = 'block';
        loading.style.display = 'flex';
        error.style.display = 'none';
        createBtn.disabled = true;
        createBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Génération...';
    }

    /**
     * Show error state
     */
    _showError(message, suggestions = []) {
        this._state = 'error';
        this._lastError = message;

        const status = this._overlay.querySelector('.ai-picker-status');
        const loading = this._overlay.querySelector('.ai-status-loading');
        const error = this._overlay.querySelector('.ai-status-error');
        const errorMsg = this._overlay.querySelector('.ai-error-message');
        const createBtn = this._overlay.querySelector('.ai-create-btn');

        status.style.display = 'block';
        loading.style.display = 'none';
        error.style.display = 'flex';
        errorMsg.textContent = message;
        createBtn.disabled = false;
        createBtn.innerHTML = '<i class="fas fa-magic"></i> Créer le KPI';
    }

    /**
     * Show manual configuration mode
     */
    _showManualMode() {
        this._state = 'manual';
        this._overlay.querySelector('.ai-prompt-section').style.display = 'none';
        this._overlay.querySelector('.ai-picker-status').style.display = 'none';
        this._overlay.querySelector('.ai-picker-manual').style.display = 'block';
        this._overlay.querySelector('.ai-manual-trigger').style.display = 'none';

        const createBtn = this._overlay.querySelector('.ai-create-btn');
        createBtn.disabled = false;
        createBtn.innerHTML = '<i class="fas fa-plus"></i> Créer';
    }

    /**
     * Show AI mode (from manual)
     */
    _showAIMode() {
        this._state = 'idle';
        this._overlay.querySelector('.ai-prompt-section').style.display = 'block';
        this._overlay.querySelector('.ai-picker-status').style.display = 'none';
        this._overlay.querySelector('.ai-picker-manual').style.display = 'none';
        this._overlay.querySelector('.ai-manual-trigger').style.display = 'inline-flex';

        const createBtn = this._overlay.querySelector('.ai-create-btn');
        createBtn.innerHTML = '<i class="fas fa-magic"></i> Créer le KPI';
        createBtn.disabled = this._currentPrompt.length < 10;
    }

    /**
     * Cleanup
     */
    destroy() {
        if (this._handleKeydown) {
            document.removeEventListener('keydown', this._handleKeydown);
        }
        this.hide();
    }
}

// Singleton instance
let pickerInstance = null;

export function showAIWidgetPicker(options) {
    if (pickerInstance) {
        pickerInstance.destroy();
    }
    pickerInstance = new AIWidgetPicker(options);
    pickerInstance.show();
    return pickerInstance;
}

export function hideAIWidgetPicker() {
    if (pickerInstance) {
        pickerInstance.hide();
        pickerInstance = null;
    }
}
