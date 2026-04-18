const tg = window.Telegram.WebApp;
tg.expand(); // Expand to full screen

// Colors for Telegram Theme Integration (Optional, using fallback)
const bgColor = tg.themeParams.bg_color || '#0f111a';
const textColor = tg.themeParams.text_color || '#ffffff';

const API_BASE = window.location.origin;

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    loadStats();
    loadDrafts();
    loadSettings();
    
    document.getElementById('save-settings').addEventListener('click', saveSettings);
});

function initNavigation() {
    const navBtns = document.querySelectorAll('.nav-btn');
    const views = document.querySelectorAll('.view');

    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.getAttribute('data-target');
            
            navBtns.forEach(b => b.classList.remove('active'));
            views.forEach(v => v.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(target).classList.add('active');
            
            if(target === 'dashboard') loadStats();
            if(target === 'drafts') loadDrafts();
        });
    });
}

async function loadStats() {
    try {
        const res = await fetch(`${API_BASE}/api/stats`);
        const data = await res.json();
        
        animateValue('stat-processed', data.totalProcesssed);
        animateValue('stat-pending', data.pendingDrafts);
        animateValue('stat-published', data.published);
        animateValue('stat-rejected', data.rejected);
        
        updateBadge(data.pendingDrafts);
    } catch (e) {
        console.error("Stats Error:", e);
    }
}

async function loadDrafts() {
    const container = document.getElementById('draft-container');
    try {
        const res = await fetch(`${API_BASE}/api/drafts/pending`);
        const drafts = await res.json();
        
        updateBadge(drafts.length);
        
        if (drafts.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <span>🎉</span>
                    <p>No pending drafts!</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = drafts.map(renderDraftCard).join('');
    } catch (e) {
        console.error("Drafts Error:", e);
    }
}

function renderDraftCard(draft) {
    return `
        <div class="draft-card" id="draft-${draft.id}">
            <div class="draft-score">Score: ${draft.relevance_score.toFixed(2)}</div>
            <h3 class="draft-title">${draft.suggested_headline}</h3>
            <p class="draft-body">${draft.rewritten_text}</p>
            <div class="action-row">
                <button class="btn-approve" onclick="handleAction(${draft.id}, 'approve')">Approve & Queue</button>
                <button class="btn-reject" onclick="handleAction(${draft.id}, 'reject')">Reject</button>
            </div>
        </div>
    `;
}

async function handleAction(id, action) {
    try {
        await fetch(`${API_BASE}/api/drafts/${id}/action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        });
        
        // Remove card with animation
        const card = document.getElementById(`draft-${id}`);
        card.style.transform = 'translateX(100px)';
        card.style.opacity = '0';
        setTimeout(() => {
            card.remove();
            loadDrafts(); // sync badge and empty state
        }, 300);
        
        tg.HapticFeedback.notificationOccurred('success');
    } catch (e) {
        console.error("Action Error:", e);
        tg.HapticFeedback.notificationOccurred('error');
    }
}

async function loadSettings() {
    try {
        const res = await fetch(`${API_BASE}/api/settings`);
        const data = await res.json();
        
        document.getElementById('set-target').value = data.target_channel_id;
        document.getElementById('set-tone').value = data.tone_style;
        document.getElementById('set-mode').value = data.post_mode;
    } catch (e) {
        console.error("Settings Error:", e);
    }
}

async function saveSettings() {
    const btn = document.getElementById('save-settings');
    btn.textContent = 'Saving...';
    btn.disabled = true;
    
    try {
        await fetch(`${API_BASE}/api/settings`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                target_channel_id: document.getElementById('set-target').value,
                tone_style: document.getElementById('set-tone').value,
                post_mode: document.getElementById('set-mode').value,
                bot_language: "English",
                target_language: "English",
                auto_publish_threshold: 0.8
            })
        });
        
        tg.HapticFeedback.notificationOccurred('success');
        btn.textContent = 'Saved!';
        setTimeout(() => {
            btn.textContent = 'Save Configuration';
            btn.disabled = false;
        }, 2000);
    } catch (e) {
        console.error("Settings Update Error:", e);
        btn.textContent = 'Error';
    }
}

function updateBadge(count) {
    const badge = document.getElementById('draft-badge');
    if (count > 0) {
        badge.textContent = count;
        badge.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
    }
}

function animateValue(id, target) {
    const obj = document.getElementById(id);
    const start = parseInt(obj.innerText) || 0;
    const duration = 500;
    
    if(start === target) return;
    
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = Math.floor(progress * (target - start) + start);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        } else {
            obj.innerHTML = target;
        }
    };
    window.requestAnimationFrame(step);
}
