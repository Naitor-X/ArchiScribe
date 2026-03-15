/**
 * API-Client für ArchiScribe Backend
 */

const API_BASE_URL = '/api/v1';

// Development API-Key (aus backend/app/config.py)
const API_KEY = 'sk-tenant-00000000-0000-0000-0000-000000000001-a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6';

/**
 * Fetch-Wrapper mit Auth-Header
 */
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': API_KEY
        }
    };

    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers
        }
    };

    const response = await fetch(url, mergedOptions);

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Unbekannter Fehler' }));

        // Debug: Volle Fehlerantwort in Console
        console.error('API Error Response:', errorData);

        // Eigenes Fehlerformat mit details.errors
        if (errorData.details && Array.isArray(errorData.details.errors)) {
            const messages = errorData.details.errors.map(err => {
                return `${err.field || 'Feld'}: ${err.message || err}`;
            });
            throw new Error('Validierungsfehler: ' + messages.join(', '));
        }

        // Pydantic Validierungsfehler formatieren
        if (Array.isArray(errorData.detail)) {
            const messages = errorData.detail.map(err => {
                const field = err.loc ? err.loc.join('.') : 'Feld';
                return `${field}: ${err.msg}`;
            });
            throw new Error('Validierungsfehler: ' + messages.join(', '));
        }

        throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}`);
    }

    // Bei 204 No Content
    if (response.status === 204) {
        return null;
    }

    return response.json();
}

// API-Funktionen (global verfügbar für Nicht-Module)
const api = {
    // Projektliste abrufen
    async getProjects(status = null) {
        const params = new URLSearchParams();
        if (status && status !== 'all') {
            params.append('status_id', status);
        }
        const query = params.toString() ? `?${params.toString()}` : '';
        return apiRequest(`/projects${query}`);
    },

    // Einzelnes Projekt abrufen
    async getProject(id) {
        return apiRequest(`/projects/${id}`);
    },

    // Projekt aktualisieren
    async updateProject(id, data) {
        return apiRequest(`/projects/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    // Projektstatus ändern
    async updateProjectStatus(id, status) {
        return apiRequest(`/projects/${id}/status`, {
            method: 'PATCH',
            body: JSON.stringify({ new_status_id: status })
        });
    }
};

// Global verfügbar machen (für klassisches Script-Loading)
window.api = api;
