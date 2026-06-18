// --- FRONTEND LOGIC (API Connected) ---

let currentSelectedItem = null;
let currentView = 'pending'; // 'pending' or 'context'

// DOM Elements
const feedContainer = document.getElementById('approvalFeed');
const detailPanel = document.getElementById('detailPanel');
const panelContent = document.getElementById('panelContent');
const panelActions = document.getElementById('panelActions');
const simulateBtn = document.getElementById('simulateBtn');
const simulateReportBtn = document.getElementById('simulateReportBtn');
const hoursSavedDisplay = document.getElementById('hoursSaved');
const dollarsSavedDisplay = document.getElementById('dollarsSaved');
const navPending = document.getElementById('navPending');
const navContext = document.getElementById('navContext');
const navPlumbing = document.getElementById('navPlumbing');
const navSettings = document.getElementById('navSettings');
const navAnalytics = document.getElementById('navAnalytics');
const headerTitle = document.getElementById('headerTitle');
const headerSubtitle = document.getElementById('headerSubtitle');
const plumbingFeed = document.getElementById('plumbingFeed');
const settingsFeed = document.getElementById('settingsFeed');
const analyticsFeed = document.getElementById('analyticsFeed');

// Branding Elements
const mainLogoIcon = document.getElementById('mainLogoIcon');
const mainLogoText = document.getElementById('mainLogoText');
const brandNameInput = document.getElementById('brandNameInput');
const brandIconInput = document.getElementById('brandIconInput');
const btnSaveBrand = document.getElementById('btnSaveBrand');

// Gmail Elements
const gmailAddressInput = document.getElementById('gmailAddressInput');
const gmailAppPasswordInput = document.getElementById('gmailAppPasswordInput');
const btnSaveGmail = document.getElementById('btnSaveGmail');
const gmailStatusText = document.getElementById('gmailStatusText');

// UI Controls
const searchPending = document.getElementById('searchPending');
const btnClearPending = document.getElementById('btnClearPending');

// Modal Elements
const wizardModal = document.getElementById('wizardModal');
const btnFinishWizard = document.getElementById('btnFinishWizard');
const editModal = document.getElementById('editModal');
const editTextArea = document.getElementById('editTextArea');
const btnCancelEdit = document.getElementById('btnCancelEdit');
const btnSaveEdit = document.getElementById('btnSaveEdit');

function updateTimeSaved(hoursToAdd) {
    // This is now purely aesthetic if called directly, as loadTimeSaved() hits the backend
    loadTimeSaved();
}

async function loadTimeSaved() {
    try {
        const res = await fetch('/api/stats/roi');
        const data = await res.json();
        if (hoursSavedDisplay) hoursSavedDisplay.innerText = data.hours_saved + 'h';
        if (dollarsSavedDisplay) dollarsSavedDisplay.innerText = '$' + data.dollars_saved;
    } catch (e) {
        console.error("Error fetching ROI stats:", e);
    }
}

async function fetchPending() {
    const res = await fetch('/api/pending');
    const items = await res.json();
    return items;
}

async function fetchContext() {
    const res = await fetch('/api/context');
    const items = await res.json();
    return items;
}

async function fetchSettings() {
    const res = await fetch('/api/settings');
    const data = await res.json();
    
    if (data.has_key) {
        document.getElementById('keyStatusText').innerText = "✓ Active API Key Saved (" + data.openai_api_key + ")";
    }
    
    if (data.llm_provider) {
        document.getElementById('llmProviderInput').value = data.llm_provider;
    }
    
    // Apply Branding
    if (data.brand_name) {
        mainLogoText.innerText = data.brand_name;
        brandNameInput.value = data.brand_name;
    }
    if (data.brand_icon) {
        mainLogoIcon.innerText = data.brand_icon;
        mainLogoIcon.style.display = 'flex';
        mainLogoIcon.style.alignItems = 'center';
        mainLogoIcon.style.justifyContent = 'center';
        mainLogoIcon.style.fontSize = '1.2rem';
        brandIconInput.value = data.brand_icon;
    }
    
    // Apply Gmail
    if (data.has_gmail) {
        gmailStatusText.innerText = "✓ Gmail Connected";
        gmailAddressInput.value = data.gmail_address;
    }
    
    // Apply Enterprise Settings
    if (data.knowledge_base) {
        document.getElementById('knowledgeBaseInput').value = data.knowledge_base;
    }
    if (data.autonomy_threshold) {
        const slider = document.getElementById('autonomyThresholdInput');
        const display = document.getElementById('thresholdValueDisplay');
        if (slider && display) {
            slider.value = data.autonomy_threshold;
            display.innerText = data.autonomy_threshold + "%" + (data.autonomy_threshold == 100 ? " (Manual Mode)" : "");
        }
    }
    
    if (!data.wizard_completed) {
        wizardModal.classList.remove('hidden');
    }
    
    ['Gmail', 'DocuSign', 'LinkedIn', 'Stripe', 'Salesforce', 'Zendesk', 'WhatsApp', 'Slack'].forEach(name => {
        const toggle = document.getElementById('toggle' + name);
        if(toggle) toggle.checked = data['autopilot_' + name.toLowerCase()];
    });
    
    // Load RAG docs
    if (document.getElementById('kbDocumentList')) {
        renderKbDocuments();
    }
}

document.getElementById('btnSaveKey').addEventListener('click', async () => {
    const key = document.getElementById('apiKeyInput').value;
    const provider = document.getElementById('llmProviderInput').value;
    
    if (!key) return;
    const btn = document.getElementById('btnSaveKey');
    btn.innerHTML = 'Saving...';
    await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ openai_api_key: key, llm_provider: provider })
    });
    document.getElementById('apiKeyInput').value = '';
    await fetchSettings();
    btn.innerHTML = 'Save API';
});

btnSaveBrand.addEventListener('click', async () => {
    const brandName = brandNameInput.value;
    const brandIcon = brandIconInput.value;
    
    btnSaveBrand.innerHTML = 'Saving...';
    
    await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ brand_name: brandName, brand_icon: brandIcon })
    });
    
    await fetchSettings();
    btnSaveBrand.innerHTML = 'Save Branding';
});

btnSaveGmail.addEventListener('click', async () => {
    const email = gmailAddressInput.value;
    const pwd = gmailAppPasswordInput.value;
    if(!email) return;
    
    btnSaveGmail.innerHTML = 'Connecting...';
    await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gmail_address: email, gmail_app_password: pwd })
    });
    
    gmailAppPasswordInput.value = '';
    await fetchSettings();
    btnSaveGmail.innerHTML = 'Connect Gmail';
});

// RAG Document Manager logic
async function renderKbDocuments() {
    const res = await fetch('/api/documents');
    const docs = await res.json();
    const list = document.getElementById('kbDocumentList');
    if (!list) return;
    
    list.innerHTML = '';
    if (docs.length === 0) {
        list.innerHTML = '<div style="color: var(--text-secondary); font-size: 0.9rem;">No documents uploaded yet.</div>';
        return;
    }
    
    docs.forEach(doc => {
        const div = document.createElement('div');
        div.style.cssText = 'display: flex; justify-content: space-between; align-items: center; padding: 12px; background: var(--bg-dark); border: 1px solid var(--border-color); border-radius: 8px;';
        div.innerHTML = `
            <div>
                <strong style="color: var(--text-primary);">${doc.title}</strong>
                <div style="color: var(--text-secondary); font-size: 0.8rem; margin-top: 4px;">${doc.content.substring(0, 50)}...</div>
            </div>
            <button class="action-btn btn-reject" style="width: auto; padding: 6px 12px; font-size: 0.8rem;" onclick="deleteKbDoc(${doc.id})">Delete</button>
        `;
        list.appendChild(div);
    });
}

window.deleteKbDoc = async function(id) {
    await fetch('/api/documents/' + id, { method: 'DELETE' });
    renderKbDocuments();
};

const kbFileUpload = document.getElementById('kbFileUpload');
const kbFileName = document.getElementById('kbFileName');

if (kbFileUpload) {
    kbFileUpload.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            kbFileName.innerText = e.target.files[0].name;
            document.getElementById('kbDocTitle').value = e.target.files[0].name;
        } else {
            kbFileName.innerText = "No file selected";
        }
    });
}

const btnAddKbDoc = document.getElementById('btnAddKbDoc');
if (btnAddKbDoc) {
    btnAddKbDoc.addEventListener('click', async () => {
        const title = document.getElementById('kbDocTitle').value;
        const content = document.getElementById('kbDocContent').value;
        const fileInput = document.getElementById('kbFileUpload');
        
        if (!content && (!fileInput || fileInput.files.length === 0)) {
            alert('Please either upload a file or paste content.');
            return;
        }
        
        btnAddKbDoc.innerHTML = 'Embedding...';
        
        if (fileInput && fileInput.files.length > 0) {
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            
            const res = await fetch('/api/documents/upload', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (!data.success) {
                alert('Upload failed: ' + data.error);
                btnAddKbDoc.innerHTML = 'Embed & Save';
                return;
            }
        } else {
            const res = await fetch('/api/documents', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title, content })
            });
            const data = await res.json();
            if (!data.success) {
                alert('Save failed: ' + data.error);
                btnAddKbDoc.innerHTML = 'Embed & Save';
                return;
            }
        }
        
        document.getElementById('kbDocTitle').value = '';
        document.getElementById('kbDocContent').value = '';
        if (fileInput) {
            fileInput.value = '';
            kbFileName.innerText = 'No file selected';
        }
        
        btnAddKbDoc.innerHTML = 'Embed & Save';
        document.getElementById('kbStatusText').innerText = "✓ Embedded";
        setTimeout(() => document.getElementById('kbStatusText').innerText = "", 3000);
        
        renderKbDocuments();
    });
}

const thresholdSlider = document.getElementById('autonomyThresholdInput');
if (thresholdSlider) {
    thresholdSlider.addEventListener('input', (e) => {
        const val = e.target.value;
        document.getElementById('thresholdValueDisplay').innerText = val + "%" + (val == 100 ? " (Manual Mode)" : "");
    });
}

document.getElementById('btnSaveThreshold').addEventListener('click', async () => {
    const val = document.getElementById('autonomyThresholdInput').value;
    const btn = document.getElementById('btnSaveThreshold');
    btn.innerHTML = 'Saving...';
    await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ autonomy_threshold: val })
    });
    btn.innerHTML = 'Saved ✓';
    setTimeout(() => btn.innerHTML = 'Save Threshold', 2000);
});

if (searchPending) {
    searchPending.addEventListener('input', () => {
        if (currentView === 'pending') renderFeed();
    });
}

if (btnClearPending) {
    btnClearPending.addEventListener('click', async () => {
        if(confirm("Are you sure you want to clear all pending items?")) {
            await fetch('/api/clear_pending', { method: 'POST' });
            renderFeed();
        }
    });
}

async function renderFeed() {
    feedContainer.classList.add('hidden');
    plumbingFeed.classList.add('hidden');
    settingsFeed.classList.add('hidden');
    analyticsFeed.classList.add('hidden');
    
    if (currentView === 'plumbing') {
        searchPending.style.display = 'none';
        btnClearPending.style.display = 'none';
        plumbingFeed.classList.remove('hidden');
        clearSelection();
        return;
    }
    
    if (currentView === 'settings') {
        searchPending.style.display = 'none';
        btnClearPending.style.display = 'none';
        settingsFeed.classList.remove('hidden');
        clearSelection();
        return;
    }

    if (currentView === 'analytics') {
        analyticsFeed.classList.remove('hidden');
        clearSelection();
        initCharts();
        return;
    }
    
    if (currentView === 'pending') {
        searchPending.style.display = 'block';
        btnClearPending.style.display = 'block';
        feedContainer.classList.remove('hidden');
        const items = await fetchPending();
        let filteredItems = items;
        if (searchPending.value) {
            const q = searchPending.value.toLowerCase();
            filteredItems = items.filter(i => 
                (i.title && i.title.toLowerCase().includes(q)) || 
                (i.sourceText && i.sourceText.toLowerCase().includes(q))
            );
        }
        
        // Auto-refresh logic: only completely redraw if length changed or top item changed to avoid scroll jumping
        const currentCount = feedContainer.children.length;
        const newTopId = filteredItems.length > 0 ? filteredItems[0].id : null;
        
        if (window._lastRenderedCount === filteredItems.length && window._lastRenderedTopId === newTopId) {
            return; // No structural changes needed
        }
        
        window._lastRenderedCount = filteredItems.length;
        window._lastRenderedTopId = newTopId;
        
        feedContainer.innerHTML = '';
        if (filteredItems.length === 0) {
            feedContainer.innerHTML = `
                <div style="text-align:center; padding: 40px; color: var(--text-secondary);">
                    <h3>Inbox Zero! 🎉</h3>
                    <p style="margin-top: 10px;">The AI has handled all pending tasks.</p>
                </div>
            `;
            clearSelection();
            return;
        }

        filteredItems.forEach(item => {
            const isEscalated = item.is_escalated === 1;
            const card = document.createElement('div');
            card.className = `card ${currentSelectedItem && currentSelectedItem.id === item.id ? 'selected' : ''} ${isEscalated ? 'escalated' : ''}`;
            card.onclick = () => selectItem(item);
            
            let badges = `<span class="badge badge-pending">Needs Approval</span>`;
            if (isEscalated) {
                badges += `<span class="badge badge-escalated">MANAGER ESCALATION</span>`;
            }
            
            card.innerHTML = `
                <div class="card-icon ${item.iconClass}">${item.icon}</div>
                <div class="card-content">
                    <div class="card-header">
                        <span class="card-title">${item.title}</span>
                        <span class="card-time">${item.timestamp}</span>
                    </div>
                    <div class="card-preview">${item.sourceText.substring(0, 80)}...</div>
                    ${badges}
                </div>
            `;
            feedContainer.appendChild(card);
        });
    } else if (currentView === 'context') {
        searchPending.style.display = 'none';
        btnClearPending.style.display = 'none';
        feedContainer.classList.remove('hidden');
        const items = await fetchContext();
        feedContainer.innerHTML = '';
        
        if (items.length === 0) {
            feedContainer.innerHTML = `
                <div style="text-align:center; padding: 40px; color: var(--text-secondary);">
                    <h3>The Brain is Empty</h3>
                    <p style="margin-top: 10px;">Approve tasks to teach the AI your business logic.</p>
                </div>
            `;
            clearSelection();
            return;
        }

        items.forEach(item => {
            const card = document.createElement('div');
            card.className = 'card';
            card.style.cursor = 'default';
            
            card.innerHTML = `
                <div class="card-icon" style="background: rgba(99, 102, 241, 0.1); color: #818cf8;">🧠</div>
                <div class="card-content">
                    <div class="card-header">
                        <span class="card-title">Learned Context Rule #${item.id}</span>
                        <span class="card-time">${item.created_at}</span>
                    </div>
                    <div class="card-preview" style="color: var(--success);">Approved Action Logged</div>
                </div>
            `;
            feedContainer.appendChild(card);
        });
    }
}

function selectItem(item) {
    if (currentView !== 'pending') return;
    
    currentSelectedItem = item;
    renderFeed(); // Re-render to show selected state
    
    let badgeColor = '#ef4444'; // red
    if (currentSelectedItem.confidence >= 80) badgeColor = '#22c55e'; // green
    else if (currentSelectedItem.confidence >= 50) badgeColor = '#eab308'; // yellow
    
    let confidenceHtml = currentSelectedItem.confidence !== undefined 
        ? `<div style="display:inline-block; margin-left:12px; background:${badgeColor}; color:#fff; padding:4px 8px; border-radius:12px; font-size:0.8rem; font-weight:bold;">Confidence: ${currentSelectedItem.confidence}%</div>`
        : '';
        
    let reasoningHtml = currentSelectedItem.reasoning 
        ? `<div style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:12px; font-style:italic;">Reasoning: ${currentSelectedItem.reasoning}</div>` 
        : '';

    let badges = confidenceHtml;
    if (currentSelectedItem.is_escalated === 1) {
        badges += `<div style="display:inline-block; margin-left:12px; background:#ef4444; color:#fff; padding:4px 8px; border-radius:12px; font-size:0.8rem; font-weight:bold;">🚨 MANAGER ESCALATION REQUIRED</div>`;
    }

    // Update Detail Panel
    panelContent.innerHTML = `
        <div class="detail-source">
            <h4>Original Context</h4>
            <p>${currentSelectedItem.sourceText.replace(/\\n/g, '<br>').replace(/\n/g, '<br>')}</p>
        </div>
        <div class="detail-draft">
            <h4 style="display:flex; align-items:center;">
                <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" style="margin-right:8px;"><path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg> 
                AI Suggested Action
                ${badges}
            </h4>
            ${reasoningHtml}
            <div class="draft-content">${currentSelectedItem.draftText.replace(/\\n/g, '<br>').replace(/\n/g, '<br>')}</div>
        </div>
    `;
    
    panelActions.classList.remove('hidden');
}

function clearSelection() {
    currentSelectedItem = null;
    let msg = "Select an item to review the AI's drafted response.";
    if (currentView === 'context') msg = "The Brain records your approvals here to learn your specific business logic.";
    if (currentView === 'plumbing') msg = "Visual representation of external data flowing into the Nexus AI Brain via secure webhooks.";
    if (currentView === 'settings') msg = "Manage your API integrations and live webhook endpoints.";
    
    panelContent.innerHTML = `
        <div class="empty-state">
            <svg width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path></svg>
            <p>${msg}</p>
        </div>
    `;
    panelActions.classList.add('hidden');
}

// Action Button Listeners
document.getElementById('btnApprove').addEventListener('click', async () => {
    if (!currentSelectedItem) return;
    
    const btn = document.getElementById('btnApprove');
    btn.innerHTML = 'Sending...';
    
    await fetch('/api/approve/' + currentSelectedItem.id, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ draftText: currentSelectedItem.draftText })
    });
    
    updateTimeSaved(0.25);
    clearSelection();
    await renderFeed();
    btn.innerHTML = 'Approve & Send';
});

document.getElementById('btnReject').addEventListener('click', async () => {
    if (!currentSelectedItem) return;
    
    await fetch('/api/reject/' + currentSelectedItem.id, { method: 'POST' });
    clearSelection();
    await renderFeed();
});

document.getElementById('btnEdit').addEventListener('click', () => {
    if (!currentSelectedItem) return;
    editTextArea.value = currentSelectedItem.draftText;
    editModal.classList.remove('hidden');
});

// Modal Listeners
btnCancelEdit.addEventListener('click', () => editModal.classList.add('hidden'));

btnSaveEdit.addEventListener('click', async () => {
    if (!currentSelectedItem) return;
    
    const editedText = editTextArea.value;
    
    await fetch('/api/approve/' + currentSelectedItem.id, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ draftText: editedText })
    });
    
    updateTimeSaved(0.15); // Saved less time due to manual editing
    editModal.classList.add('hidden');
    clearSelection();
    await renderFeed();
});

// Simulate Buttons
simulateBtn.addEventListener('click', async () => {
    await fetch('/api/simulate', { method: 'POST' });
    if(currentView === 'pending') await renderFeed();
});

simulateReportBtn.addEventListener('click', async () => {
    await fetch('/api/simulate-report', { method: 'POST' });
    if(currentView === 'pending') await renderFeed();
});

// Autopilot Toggles
['Gmail', 'DocuSign', 'LinkedIn', 'Stripe', 'Salesforce', 'Zendesk', 'WhatsApp', 'Slack'].forEach(name => {
    const toggle = document.getElementById('toggle' + name);
    if(toggle) {
        toggle.addEventListener('change', async (e) => {
            const payload = {};
            payload['autopilot_' + name.toLowerCase()] = e.target.checked;
            await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        });
    }
});

// Wizard Button
btnFinishWizard.addEventListener('click', async () => {
    const q1 = document.getElementById('wizardQ1').value;
    const q2 = document.getElementById('wizardQ2').value;
    const q3 = document.getElementById('wizardQ3').value;
    
    btnFinishWizard.innerHTML = "Booting up...";
    
    await fetch('/api/wizard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ q1, q2, q3 })
    });
    
    wizardModal.classList.add('hidden');
    await fetchContext();
    if(currentView === 'context') await renderFeed();
});

// Chart.js Init (Only once)
let chartsInitialized = false;
function initCharts() {
    if (chartsInitialized) return;
    chartsInitialized = true;
    
    const ctxHours = document.getElementById('hoursChart').getContext('2d');
    new Chart(ctxHours, {
        type: 'line',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [{
                label: 'Cumulative Hours Saved',
                data: [1.2, 2.5, 4.1, 5.8, 8.2, 9.5, 12.4],
                borderColor: '#10b981',
                backgroundColor: 'rgba(16, 185, 129, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: {
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
                x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
            }
        }
    });

    const ctxTasks = document.getElementById('tasksChart').getContext('2d');
    new Chart(ctxTasks, {
        type: 'doughnut',
        data: {
            labels: ['Gmail Support', 'CRM Entry', 'DocuSign', 'Stripe Resolves'],
            datasets: [{
                data: [45, 25, 15, 15],
                backgroundColor: ['#ef4444', '#10b981', '#f59e0b', '#6366f1'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'right', labels: { color: '#94a3b8' } }
            }
        }
    });
}

// Navigation Listeners
function updateNav(view) {
    navPending.classList.remove('active');
    navContext.classList.remove('active');
    navPlumbing.classList.remove('active');
    navSettings.classList.remove('active');
    navAnalytics.classList.remove('active');
    
    if (view === 'pending') navPending.classList.add('active');
    if (view === 'context') navContext.classList.add('active');
    if (view === 'plumbing') navPlumbing.classList.add('active');
    if (view === 'settings') navSettings.classList.add('active');
    if (view === 'analytics') navAnalytics.classList.add('active');
    
    window._lastRenderedCount = -1;
    window._lastRenderedTopId = null;
}

navPending.addEventListener('click', () => {
    currentView = 'pending';
    updateNav('pending');
    headerTitle.innerText = "Pending Approvals";
    headerSubtitle.innerText = "Review AI drafts to teach it your business logic.";
    document.getElementById('statsCard').style.display = 'flex';
    clearSelection();
    renderFeed();
});

navContext.addEventListener('click', () => {
    currentView = 'context';
    updateNav('context');
    headerTitle.innerText = "The Brain (Context Memory)";
    headerSubtitle.innerText = "The AI's accumulated knowledge based on your past approvals.";
    document.getElementById('statsCard').style.display = 'none';
    clearSelection();
    renderFeed();
});

navPlumbing.addEventListener('click', () => {
    currentView = 'plumbing';
    updateNav('plumbing');
    headerTitle.innerText = "Data Integrations";
    headerSubtitle.innerText = "Monitoring live webhook streams into the central Brain.";
    document.getElementById('statsCard').style.display = 'none';
    clearSelection();
    renderFeed();
});

navSettings.addEventListener('click', () => {
    currentView = 'settings';
    updateNav('settings');
    headerTitle.innerText = "App Settings";
    headerSubtitle.innerText = "Configure live AI keys and webhook endpoints.";
    document.getElementById('statsCard').style.display = 'none';
    clearSelection();
    renderFeed();
});

navAnalytics.addEventListener('click', () => {
    currentView = 'analytics';
    updateNav('analytics');
    headerTitle.innerText = "ROI Analytics Dashboard";
    headerSubtitle.innerText = "Real-time metrics on how much time and money your AI is saving you.";
    document.getElementById('statsCard').style.display = 'none';
    clearSelection();
    renderFeed();
});

// Initialize App
loadTimeSaved();
fetchSettings();
renderFeed();

// Auto-refresh the pending feed every 10 seconds
setInterval(() => {
    if (currentView === 'pending') {
        renderFeed();
    }
}, 10000);
