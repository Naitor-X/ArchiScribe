/**
 * Projektdetail-Logik mit Caching
 */

// Projekt-ID aus URL
const projectId = new URLSearchParams(window.location.search).get('id');

if (!projectId) {
    window.location.href = '/app/';
}

// Cache-Konfiguration
const CACHE_KEY = 'archiscribe_project_cache';
const CACHE_TTL = 60 * 1000; // 60 Sekunden

// Status-Labels
const STATUS_LABELS = {
    'raw_extracted': 'Rohdaten',
    'needs_review': 'Prüfung erforderlich',
    'verified_by_architect': 'Verifiziert'
};

// Enum-Optionen (aus Backend-Schema - exakt wie in database/schema.sql)
const ENUM_OPTIONS = {
    // Grundstück
    topography: ['eben', 'leichte Hanglage', 'starke Hanglage', 'Sonstiges'],
    access_status: ['voll erschlossen', 'teilerschlossen', 'nicht erschlossen'],

    // Vorstellungen / Ziele
    project_type: ['Neubau', 'Bauen im Bestand', 'Umbau im Inneren', 'Sanierung/Modernis.', 'Zubau/Anbau', 'Aufstockung', 'noch unklar', 'Sonstiges'],
    building_type: ['EFH', 'Doppelhaus', 'Reihenhaus', 'Mehrfamilienhaus', 'Sonstige'],
    construction_method: ['Massivbau', 'Holzbau', 'noch offen'],
    heating_type: ['Wärmepumpe', 'Gasheizung', 'Fernwärme', 'Holz/Pellets', 'Sonstige'],

    // Besondere Hinweise
    own_contribution: ['ja', 'nein', 'teilweise'],
    accessibility: ['wichtig', 'optional', 'nicht relevant'],
};

// Cache lesen
function getProjectCache() {
    try {
        const cached = sessionStorage.getItem(`${CACHE_KEY}_${projectId}`);
        if (!cached) return null;

        const { data, timestamp } = JSON.parse(cached);
        if (Date.now() - timestamp > CACHE_TTL) {
            sessionStorage.removeItem(`${CACHE_KEY}_${projectId}`);
            return null;
        }
        return data;
    } catch {
        return null;
    }
}

// Cache schreiben
function setProjectCache(data) {
    try {
        sessionStorage.setItem(`${CACHE_KEY}_${projectId}`, JSON.stringify({
            data,
            timestamp: Date.now()
        }));
    } catch {
        // SessionStorage voll oder nicht verfügbar
    }
}

// Cache invalidieren
function invalidateProjectCache() {
    try {
        sessionStorage.removeItem(`${CACHE_KEY}_${projectId}`);
        // Auch Listen-Cache invalidieren
        sessionStorage.removeItem('archiscribe_projects_cache_all');
        sessionStorage.removeItem('archiscribe_projects_cache_raw_extracted');
        sessionStorage.removeItem('archiscribe_projects_cache_needs_review');
        sessionStorage.removeItem('archiscribe_projects_cache_verified_by_architect');
    } catch {}
}

// Formular-Daten sammeln (nur editierbare Felder)
function collectFormData() {
    const form = document.getElementById('project-form');
    const formData = new FormData(form);
    const data = {};

    for (const [key, value] of formData.entries()) {
        if (key === 'development_plan') {
            data[key] = value === 'on';
        } else if (['budget', 'plot_size_m2'].includes(key)) {
            data[key] = value ? parseFloat(value) : null;
        } else {
            data[key] = value || null;
        }
    }

    const checkbox = document.getElementById('development_plan');
    if (checkbox && !checkbox.checked) {
        data['development_plan'] = false;
    }

    return data;
}

// Formular befüllen
function populateForm(project) {
    document.getElementById('page-title').textContent = project.client_name || 'Projekt';

    const fields = [
        'client_name', 'address', 'phone', 'email',
        'plot_location', 'plot_size_m2', 'landowner',
        'topography', 'topography_other',
        'development_plan', 'access_status',
        'project_type', 'project_type_other',
        'building_type', 'building_type_other',
        'construction_method',
        'heating_type', 'heating_type_other',
        'budget', 'planned_start',
        'own_contribution', 'own_contribution_details',
        'accessibility', 'outdoor_area', 'materiality',
        'notes'
    ];

    fields.forEach(field => {
        const element = document.getElementById(field);
        if (element) {
            if (element.type === 'checkbox') {
                element.checked = project[field] === true;
            } else {
                element.value = project[field] || '';
            }
        }
    });

    if (project.form_date) {
        const dateInput = document.getElementById('form_date');
        if (dateInput) {
            dateInput.value = project.form_date;
        }
    }

    const statusEl = document.getElementById('project-status');
    statusEl.innerHTML = `<span class="badge badge-${project.status_id}">${STATUS_LABELS[project.status_id] || project.status_id}</span>`;

    const verifyBtn = document.getElementById('verify-btn');
    verifyBtn.style.display = project.status_id === 'needs_review' ? 'inline-flex' : 'none';

    renderRooms(project.rooms || []);
}

// Enum-Selects befüllen
function populateEnumSelects() {
    for (const [field, options] of Object.entries(ENUM_OPTIONS)) {
        const select = document.getElementById(field);
        if (select) {
            select.innerHTML = `
                <option value="">Bitte wählen</option>
                ${options.map(opt => `<option value="${opt}">${opt}</option>`).join('')}
            `;
        }
    }
}

// Raumprogramm rendern
function renderRooms(rooms) {
    const container = document.getElementById('rooms-container');

    if (!rooms || rooms.length === 0) {
        container.innerHTML = '<p class="loading">Keine Räume vorhanden</p>';
        return;
    }

    container.innerHTML = `
        <table class="room-table">
            <thead>
                <tr>
                    <th>Raumtyp</th>
                    <th>Fläche (m²)</th>
                    <th>Anzahl</th>
                    <th>Besondere Anforderungen</th>
                </tr>
            </thead>
            <tbody>
                ${rooms.map(room => `
                    <tr>
                        <td>${room.room_type || '-'}</td>
                        <td>${room.size_m2 || '-'}</td>
                        <td>${room.quantity || 1}</td>
                        <td>${room.special_requirements || '-'}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

// Fehler/Success anzeigen
function showMessage(message, isError = false) {
    const container = document.getElementById('message-container');
    container.innerHTML = `<div class="${isError ? 'error' : 'success'}">${message}</div>`;
    container.style.display = 'block';

    setTimeout(() => {
        container.style.display = 'none';
    }, 3000);
}

// Projekt laden (mit Cache)
async function loadProject(forceRefresh = false) {
    // Cache prüfen
    if (!forceRefresh) {
        const cached = getProjectCache();
        if (cached) {
            populateForm(cached);
            return;
        }
    }

    try {
        const project = await window.api.getProject(projectId);
        setProjectCache(project);
        populateForm(project);
    } catch (error) {
        showMessage(`Fehler beim Laden: ${error.message}`, true);
    }
}

// Speichern
async function saveProject() {
    try {
        const data = collectFormData();
        const updated = await window.api.updateProject(projectId, data);

        // Cache aktualisieren
        setProjectCache(updated);
        invalidateProjectCache(); // Listen-Cache invalidieren

        showMessage('Projekt erfolgreich gespeichert');
    } catch (error) {
        showMessage(`Fehler beim Speichern: ${error.message}`, true);
    }
}

// Verifizieren
async function verifyProject() {
    try {
        await window.api.updateProjectStatus(projectId, 'verified_by_architect');

        // Cache invalidieren
        invalidateProjectCache();

        showMessage('Projekt als verifiziert markiert');
        loadProject(true); // Neu laden für UI-Update
    } catch (error) {
        showMessage(`Fehler: ${error.message}`, true);
    }
}

// Event-Listener
document.getElementById('save-btn').addEventListener('click', saveProject);
document.getElementById('verify-btn').addEventListener('click', verifyProject);

// Initialisierung
populateEnumSelects();
loadProject();
