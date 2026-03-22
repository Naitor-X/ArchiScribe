/**
 * Projektlisten-Logik mit Caching und Debouncing
 */

// Status-Labels für Anzeige
const STATUS_LABELS = {
    'raw_extracted': 'Rohdaten',
    'needs_review': 'Prüfung erforderlich',
    'verified_by_architect': 'Verifiziert'
};

// Cache für Projekte (Session-Storage)
const CACHE_KEY = 'archiscribe_projects_cache';
const CACHE_TTL = 30 * 1000; // 30 Sekunden

// Debounce-Timer
let debounceTimer = null;

// Status-Badge generieren
function statusBadge(status) {
    return `<span class="badge badge-${status}">${STATUS_LABELS[status] || status}</span>`;
}

// Datum formatieren
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('de-DE', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
}

// Cache lesen
function getCache(statusFilter) {
    try {
        const cached = sessionStorage.getItem(`${CACHE_KEY}_${statusFilter}`);
        if (!cached) return null;

        const { data, timestamp } = JSON.parse(cached);
        if (Date.now() - timestamp > CACHE_TTL) {
            sessionStorage.removeItem(`${CACHE_KEY}_${statusFilter}`);
            return null;
        }
        return data;
    } catch {
        return null;
    }
}

// Cache schreiben
function setCache(statusFilter, data) {
    try {
        sessionStorage.setItem(`${CACHE_KEY}_${statusFilter}`, JSON.stringify({
            data,
            timestamp: Date.now()
        }));
    } catch {
        // SessionStorage voll oder nicht verfügbar
    }
}

// Projektliste rendern
function renderProjects(projects) {
    const tbody = document.getElementById('project-list');

    if (!projects || projects.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="loading">Keine Projekte gefunden</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = projects.map(project => `
        <tr onclick="window.location.href='/app/project.html?id=${project.id}'">
            <td>${project.client_name || '-'}</td>
            <td>${project.address || '-'}</td>
            <td>${statusBadge(project.status_id)}</td>
            <td>${formatDate(project.created_at)}</td>
        </tr>
    `).join('');
}

// Fehler anzeigen
function showError(message) {
    const container = document.getElementById('error-container');
    container.innerHTML = `<div class="error">${message}</div>`;
    container.style.display = 'block';
}

// Projekte laden (mit Cache)
async function loadProjects(forceRefresh = false) {
    const statusFilter = document.getElementById('status-filter').value;

    // Cache prüfen
    if (!forceRefresh) {
        const cached = getCache(statusFilter);
        if (cached) {
            renderProjects(cached);
            return;
        }
    }

    try {
        document.getElementById('project-list').innerHTML = `
            <tr>
                <td colspan="4" class="loading">Lade Projekte...</td>
            </tr>
        `;

        const response = await window.api.getProjects(statusFilter);
        const projects = response.projects || [];

        // Cache aktualisieren
        setCache(statusFilter, projects);

        renderProjects(projects);
    } catch (error) {
        showError(`Fehler beim Laden: ${error.message}`);
        document.getElementById('project-list').innerHTML = '';
    }
}

// Debounced Load für Filter-Änderungen
function debouncedLoad() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => loadProjects(), 150);
}

// Event-Listener mit Debouncing
document.getElementById('status-filter').addEventListener('change', debouncedLoad);

// Initial laden
loadProjects();
