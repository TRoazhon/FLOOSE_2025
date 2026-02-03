/**
 * MistralService - AI service layer for KPI generation via Mistral API
 *
 * Handles:
 * - Prompt engineering and context building
 * - API communication with error handling
 * - Response parsing and validation
 * - Decision logging for debugging
 */

import {
    parseAndValidateKPIConfig,
    createDefaultKPIConfig,
    getSchemaDocumentation,
    AVAILABLE_METRICS,
    AVAILABLE_DIMENSIONS,
    VISUALIZATIONS,
    AGGREGATIONS
} from './KPIConfigSchema.js';

// System prompt for Mistral - defines behavior and output format
const SYSTEM_PROMPT = `Tu es un assistant expert en Business Intelligence et KPIs financiers.
Tu dois convertir des descriptions en langage naturel en configurations KPI structurées.

RÈGLES STRICTES:
1. Tu réponds UNIQUEMENT avec du JSON valide, sans texte avant ou après.
2. Tu dois utiliser les métriques, agrégations et visualisations disponibles dans le système.
3. Si la demande est ambiguë ou impossible, renvoie un objet JSON avec "error": "description du problème".
4. Ne fais jamais d'hypothèses non fondées - demande des clarifications via le champ "ambiguity".

MÉTRIQUES DISPONIBLES:
- budget_total: Budget total alloué
- budget_spent: Montant total dépensé
- budget_remaining: Budget restant disponible
- expense_count: Nombre de dépenses
- expense_amount: Montant des dépenses
- project_count: Nombre de projets
- project_budget: Budget par projet
- account_balance: Solde des comptes
- account_count: Nombre de comptes
- category_spending: Dépenses par catégorie
- burn_rate: Taux de consommation du budget
- savings_rate: Taux d'épargne
- budget_utilization: Pourcentage d'utilisation du budget

AGRÉGATIONS: sum, avg, count, min, max

VISUALISATIONS:
- number: Valeur unique avec tendance
- gauge: Jauge de pourcentage (0-100)
- line: Graphique linéaire temporel
- bar: Graphique en barres comparatif
- pie: Camembert de répartition
- table: Tableau de données
- sparkline: Mini graphique de tendance

DIMENSIONS DE GROUPEMENT: project, category, account, month, week, day, type

PÉRIODES: today, yesterday, last_7_days, last_30_days, this_month, last_month, this_quarter, this_year

SCHÉMA DE SORTIE OBLIGATOIRE:
{
  "kpi_name": "Nom affiché du KPI",
  "metric": "nom_de_la_metrique",
  "aggregation": "sum|avg|count|min|max",
  "time_range": "this_month",
  "filters": [{"field": "champ", "operator": "=", "value": "valeur"}],
  "dimensions": ["dimension1"],
  "visualization": "number|gauge|line|bar|pie|table|sparkline",
  "refresh_rate": 60
}

En cas d'ambiguïté, retourne:
{
  "error": "ambiguous",
  "ambiguity": "Description de ce qui n'est pas clair",
  "suggestions": ["suggestion1", "suggestion2"]
}`;

// User prompt template
const USER_PROMPT_TEMPLATE = `Contexte utilisateur FLOOSE:
- Application de gestion budgétaire professionnelle
- L'utilisateur gère des projets avec des budgets alloués
- Chaque projet peut avoir des dépenses
- L'utilisateur a des comptes bancaires avec des soldes

Demande utilisateur:
"{USER_PROMPT}"

Génère la configuration KPI correspondante en JSON.`;

/**
 * AI State management
 */
export class AIState {
    constructor() {
        this.status = 'idle'; // idle | loading | success | error | ambiguous
        this.prompt = null;
        this.rawResponse = null;
        this.config = null;
        this.error = null;
        this.ambiguity = null;
        this.suggestions = null;
        this.timestamp = null;
        this.latencyMs = null;
    }

    setLoading(prompt) {
        this.status = 'loading';
        this.prompt = prompt;
        this.timestamp = Date.now();
        this.error = null;
        this.ambiguity = null;
    }

    setSuccess(rawResponse, config) {
        this.status = 'success';
        this.rawResponse = rawResponse;
        this.config = config;
        this.latencyMs = Date.now() - this.timestamp;
    }

    setError(error, rawResponse = null) {
        this.status = 'error';
        this.error = error;
        this.rawResponse = rawResponse;
        this.latencyMs = Date.now() - this.timestamp;
    }

    setAmbiguous(ambiguity, suggestions = [], rawResponse = null) {
        this.status = 'ambiguous';
        this.ambiguity = ambiguity;
        this.suggestions = suggestions;
        this.rawResponse = rawResponse;
        this.latencyMs = Date.now() - this.timestamp;
    }

    toJSON() {
        return {
            status: this.status,
            prompt: this.prompt,
            rawResponse: this.rawResponse,
            config: this.config,
            error: this.error,
            ambiguity: this.ambiguity,
            suggestions: this.suggestions,
            timestamp: this.timestamp,
            latencyMs: this.latencyMs
        };
    }
}

/**
 * Mistral Service class
 */
export class MistralService {
    constructor(options = {}) {
        this.apiEndpoint = options.apiEndpoint || '/api/ai/generate-kpi';
        this.timeout = options.timeout || 30000;
        this.maxRetries = options.maxRetries || 2;

        // Decision logging
        this._logs = [];
        this._maxLogs = 100;
    }

    /**
     * Generate KPI config from natural language prompt
     * @param {string} userPrompt - Natural language description
     * @returns {Promise<{state: AIState, config: KPIConfig|null}>}
     */
    async generateKPI(userPrompt) {
        const state = new AIState();
        state.setLoading(userPrompt);

        this._log('REQUEST', { prompt: userPrompt });

        if (!userPrompt || userPrompt.trim().length < 3) {
            state.setError('Le prompt est trop court. Décrivez le KPI souhaité.');
            return { state, config: null };
        }

        try {
            const response = await this._callAPI(userPrompt);
            return this._processResponse(response, state);
        } catch (error) {
            this._log('ERROR', { error: error.message });
            state.setError(this._formatError(error));
            return { state, config: null };
        }
    }

    /**
     * Call the backend API
     */
    async _callAPI(userPrompt, retryCount = 0) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        try {
            const response = await fetch(this.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    prompt: userPrompt,
                    system_prompt: SYSTEM_PROMPT,
                    user_prompt_template: USER_PROMPT_TEMPLATE
                }),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            clearTimeout(timeoutId);

            if (error.name === 'AbortError') {
                throw new Error('La requête a expiré. Veuillez réessayer.');
            }

            // Retry logic
            if (retryCount < this.maxRetries && this._isRetryable(error)) {
                this._log('RETRY', { attempt: retryCount + 1, error: error.message });
                await this._delay(1000 * (retryCount + 1));
                return this._callAPI(userPrompt, retryCount + 1);
            }

            throw error;
        }
    }

    /**
     * Process Mistral response
     */
    _processResponse(response, state) {
        const rawContent = response.content || response.response || '';
        this._log('RESPONSE', { raw: rawContent.substring(0, 500) });

        // Check for error response from Mistral
        if (response.error) {
            state.setError(response.error, rawContent);
            return { state, config: null };
        }

        // Try to parse as JSON
        const validation = parseAndValidateKPIConfig(rawContent);

        // Check for ambiguity response
        try {
            const parsed = JSON.parse(rawContent.match(/\{[\s\S]*\}/)?.[0] || '{}');
            if (parsed.error === 'ambiguous' || parsed.ambiguity) {
                state.setAmbiguous(
                    parsed.ambiguity || parsed.error,
                    parsed.suggestions || [],
                    rawContent
                );
                this._log('AMBIGUOUS', { ambiguity: parsed.ambiguity });
                return { state, config: null };
            }
        } catch (e) {
            // Not a JSON error response, continue with validation
        }

        if (validation.valid) {
            state.setSuccess(rawContent, validation.config);
            this._log('SUCCESS', {
                kpi_name: validation.config.kpi_name,
                visualization: validation.config.visualization,
                warnings: validation.warnings
            });
            return { state, config: validation.config };
        }

        // Validation failed
        state.setError(
            `Configuration invalide: ${validation.errors.join(', ')}`,
            rawContent
        );
        this._log('VALIDATION_FAILED', { errors: validation.errors });
        return { state, config: null };
    }

    /**
     * Build the full prompt for Mistral
     */
    buildPrompt(userPrompt) {
        return USER_PROMPT_TEMPLATE.replace('{USER_PROMPT}', userPrompt);
    }

    /**
     * Get system prompt
     */
    getSystemPrompt() {
        return SYSTEM_PROMPT;
    }

    /**
     * Format error message for display
     */
    _formatError(error) {
        if (error.message.includes('fetch')) {
            return 'Erreur de connexion au serveur IA.';
        }
        if (error.message.includes('timeout') || error.message.includes('expiré')) {
            return 'La requête a pris trop de temps. Veuillez réessayer.';
        }
        return error.message || 'Une erreur inattendue s\'est produite.';
    }

    /**
     * Check if error is retryable
     */
    _isRetryable(error) {
        const message = error.message.toLowerCase();
        return message.includes('network') ||
               message.includes('timeout') ||
               message.includes('503') ||
               message.includes('502');
    }

    /**
     * Delay helper
     */
    _delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Log decision for debugging
     */
    _log(type, data) {
        const entry = {
            timestamp: new Date().toISOString(),
            type,
            data
        };

        this._logs.push(entry);

        // Keep only recent logs
        if (this._logs.length > this._maxLogs) {
            this._logs.shift();
        }

        // Also log to console in debug mode
        if (window.__FLOOSE_DEBUG__) {
            console.log(`[MistralService:${type}]`, data);
        }
    }

    /**
     * Get decision logs
     */
    getLogs() {
        return [...this._logs];
    }

    /**
     * Clear logs
     */
    clearLogs() {
        this._logs = [];
    }

    /**
     * Get available schema for manual configuration
     */
    getSchema() {
        return getSchemaDocumentation();
    }
}

// Singleton instance
let instance = null;

export function getMistralService(options) {
    if (!instance) {
        instance = new MistralService(options);
    }
    return instance;
}

export { SYSTEM_PROMPT, USER_PROMPT_TEMPLATE };
