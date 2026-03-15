/**
 * Projektlisten-Logik
 */

// Status-Labels für Anzeige
const STATUS_LABELS = {
    'raw_extracted': 'Rohdaten',
    'needs_review': 'Prüfung erforderlich',
    'verified_by_architect': 'Verifiziert'
};

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

// Projekte laden
async function loadProjects() {
    const statusFilter = document.getElementById('status-filter').value;

    try {
        document.getElementById('project-list').innerHTML = `
            <tr>
                <td colspan="4" class="loading">Lade Projekte...</td>
            </tr>
        `;

        const response = await window.api.getProjects(statusFilter);
        // API gibt {projects: [...], total: n, ...} zurück
        const projects = response.projects || [];
        renderProjects(projects);
    } catch (error) {
        showError(`Fehler beim Laden: ${error.message}`);
        document.getElementById('project-list').innerHTML = '';
    }
}

// Event-Listener
document.getElementById('status-filter').addEventListener('change', loadProjects);

// Initial laden
loadProjects();
