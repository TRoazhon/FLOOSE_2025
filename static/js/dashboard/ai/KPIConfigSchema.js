/**
 * KPIConfigSchema - Strict schema validation for AI-generated KPI configurations
 *
 * Ensures Mistral output conforms to expected structure before widget rendering.
 * Provides detailed validation errors for debugging and fallback handling.
 */

// Valid enum values
export const AGGREGATIONS = ['sum', 'avg', 'count', 'min', 'max'];
export const OPERATORS = ['=', '!=', '>', '<', '>=', '<=', 'in', 'not_in', 'contains'];
export const VISUALIZATIONS = ['line', 'bar', 'pie', 'gauge', 'table', 'number', 'sparkline'];
export const TIME_RANGES = ['today', 'yesterday', 'last_7_days', 'last_30_days', 'this_month', 'last_month', 'this_quarter', 'this_year', 'custom'];

// Available metrics in FLOOSE system
export const AVAILABLE_METRICS = [
    'budget_total',
    'budget_spent',
    'budget_remaining',
    'expense_count',
    'expense_amount',
    'project_count',
    'project_budget',
    'account_balance',
    'account_count',
    'category_spending',
    'burn_rate',
    'savings_rate',
    'budget_utilization'
];

// Available dimensions for grouping
export const AVAILABLE_DIMENSIONS = [
    'project',
    'category',
    'account',
    'month',
    'week',
    'day',
    'type'
];

/**
 * KPIConfig TypeScript-equivalent schema
 * @typedef {Object} KPIConfig
 * @property {string} kpi_name - Display name for the KPI
 * @property {string} metric - The metric to compute
 * @property {string} aggregation - Aggregation function
 * @property {string} time_range - Time period for data
 * @property {Array<Filter>} filters - Data filters
 * @property {Array<string>} dimensions - Grouping dimensions
 * @property {string} visualization - Chart type
 * @property {number} refresh_rate - Refresh interval in seconds
 */

/**
 * @typedef {Object} Filter
 * @property {string} field - Field to filter on
 * @property {string} operator - Comparison operator
 * @property {string|number|Array} value - Filter value
 */

/**
 * Validation result structure
 * @typedef {Object} ValidationResult
 * @property {boolean} valid - Whether config is valid
 * @property {KPIConfig|null} config - Validated config or null
 * @property {Array<string>} errors - List of validation errors
 * @property {Array<string>} warnings - Non-blocking issues
 */

/**
 * Validate a KPIConfig object
 * @param {Object} raw - Raw object to validate
 * @returns {ValidationResult}
 */
export function validateKPIConfig(raw) {
    const errors = [];
    const warnings = [];

    // Check if input is an object
    if (!raw || typeof raw !== 'object') {
        return {
            valid: false,
            config: null,
            errors: ['KPIConfig must be a non-null object'],
            warnings: []
        };
    }

    // Required fields validation
    const requiredFields = ['kpi_name', 'metric', 'aggregation', 'visualization'];
    for (const field of requiredFields) {
        if (!raw[field]) {
            errors.push(`Missing required field: ${field}`);
        }
    }

    // kpi_name validation
    if (raw.kpi_name) {
        if (typeof raw.kpi_name !== 'string') {
            errors.push('kpi_name must be a string');
        } else if (raw.kpi_name.length > 100) {
            errors.push('kpi_name exceeds maximum length of 100 characters');
        }
    }

    // metric validation
    if (raw.metric) {
        if (typeof raw.metric !== 'string') {
            errors.push('metric must be a string');
        } else if (!AVAILABLE_METRICS.includes(raw.metric)) {
            warnings.push(`metric "${raw.metric}" is not a known metric, will attempt custom calculation`);
        }
    }

    // aggregation validation
    if (raw.aggregation) {
        if (!AGGREGATIONS.includes(raw.aggregation)) {
            errors.push(`aggregation must be one of: ${AGGREGATIONS.join(', ')}`);
        }
    }

    // time_range validation
    if (raw.time_range) {
        if (typeof raw.time_range !== 'string') {
            errors.push('time_range must be a string');
        }
    } else {
        raw.time_range = 'this_month'; // Default
    }

    // filters validation
    if (raw.filters !== undefined) {
        if (!Array.isArray(raw.filters)) {
            errors.push('filters must be an array');
        } else {
            raw.filters.forEach((filter, index) => {
                if (!filter.field || typeof filter.field !== 'string') {
                    errors.push(`filters[${index}].field must be a non-empty string`);
                }
                if (!filter.operator || !OPERATORS.includes(filter.operator)) {
                    errors.push(`filters[${index}].operator must be one of: ${OPERATORS.join(', ')}`);
                }
                if (filter.value === undefined) {
                    errors.push(`filters[${index}].value is required`);
                }
            });
        }
    } else {
        raw.filters = [];
    }

    // dimensions validation
    if (raw.dimensions !== undefined) {
        if (!Array.isArray(raw.dimensions)) {
            errors.push('dimensions must be an array');
        } else {
            raw.dimensions.forEach((dim, index) => {
                if (typeof dim !== 'string') {
                    errors.push(`dimensions[${index}] must be a string`);
                } else if (!AVAILABLE_DIMENSIONS.includes(dim)) {
                    warnings.push(`dimensions[${index}] "${dim}" is not a known dimension`);
                }
            });
        }
    } else {
        raw.dimensions = [];
    }

    // visualization validation
    if (raw.visualization) {
        if (!VISUALIZATIONS.includes(raw.visualization)) {
            errors.push(`visualization must be one of: ${VISUALIZATIONS.join(', ')}`);
        }
    }

    // refresh_rate validation
    if (raw.refresh_rate !== undefined) {
        if (typeof raw.refresh_rate !== 'number' || raw.refresh_rate < 0) {
            errors.push('refresh_rate must be a non-negative number');
        } else if (raw.refresh_rate > 0 && raw.refresh_rate < 10) {
            warnings.push('refresh_rate below 10 seconds may impact performance');
        }
    } else {
        raw.refresh_rate = 60; // Default 60 seconds
    }

    // Build validated config if no errors
    if (errors.length === 0) {
        const validConfig = {
            kpi_name: raw.kpi_name.trim(),
            metric: raw.metric,
            aggregation: raw.aggregation,
            time_range: raw.time_range,
            filters: raw.filters.map(f => ({
                field: f.field,
                operator: f.operator,
                value: f.value
            })),
            dimensions: [...raw.dimensions],
            visualization: raw.visualization,
            refresh_rate: raw.refresh_rate
        };

        // Freeze the config to ensure immutability
        Object.freeze(validConfig);
        validConfig.filters.forEach(f => Object.freeze(f));
        Object.freeze(validConfig.filters);
        Object.freeze(validConfig.dimensions);

        return {
            valid: true,
            config: validConfig,
            errors: [],
            warnings
        };
    }

    return {
        valid: false,
        config: null,
        errors,
        warnings
    };
}

/**
 * Parse JSON string and validate as KPIConfig
 * @param {string} jsonString - Raw JSON string from Mistral
 * @returns {ValidationResult}
 */
export function parseAndValidateKPIConfig(jsonString) {
    // Try to extract JSON from potential markdown code blocks
    let cleanJson = jsonString.trim();

    // Remove markdown code blocks if present
    const jsonMatch = cleanJson.match(/```(?:json)?\s*([\s\S]*?)```/);
    if (jsonMatch) {
        cleanJson = jsonMatch[1].trim();
    }

    // Try to find JSON object in response
    const objectMatch = cleanJson.match(/\{[\s\S]*\}/);
    if (objectMatch) {
        cleanJson = objectMatch[0];
    }

    try {
        const parsed = JSON.parse(cleanJson);
        return validateKPIConfig(parsed);
    } catch (e) {
        return {
            valid: false,
            config: null,
            errors: [`Failed to parse JSON: ${e.message}`],
            warnings: []
        };
    }
}

/**
 * Generate a default KPIConfig for fallback
 * @param {string} name - Display name
 * @returns {KPIConfig}
 */
export function createDefaultKPIConfig(name = 'Custom KPI') {
    const config = {
        kpi_name: name,
        metric: 'budget_total',
        aggregation: 'sum',
        time_range: 'this_month',
        filters: [],
        dimensions: [],
        visualization: 'number',
        refresh_rate: 60
    };

    Object.freeze(config);
    return config;
}

/**
 * Get schema documentation for Mistral prompt
 */
export function getSchemaDocumentation() {
    return {
        metrics: AVAILABLE_METRICS,
        aggregations: AGGREGATIONS,
        operators: OPERATORS,
        visualizations: VISUALIZATIONS,
        time_ranges: TIME_RANGES,
        dimensions: AVAILABLE_DIMENSIONS
    };
}
