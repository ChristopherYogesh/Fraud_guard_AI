/**
 * FRAUD GUARD AI — BLUEPRINT CLIENT APPLICATION
 * Telemetry, Audio Synthesizer, Real-time Alerts, Theme Switcher
 */

// 1. Audio Alarm Synthesizer (Zero-dependency Web Audio API)
class SecuritySoundEngine {
    constructor() {
        this.ctx = null;
        this.enabled = localStorage.getItem('fraudguard_audio') !== 'false';
    }

    init() {
        if (!this.ctx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                this.ctx = new AudioContext();
            }
        }
    }

    playAlertChime(priority = 'HIGH') {
        if (!this.enabled) return;
        this.init();
        if (!this.ctx) return;

        if (this.ctx.state === 'suspended') {
            this.ctx.resume();
        }

        const now = this.ctx.currentTime;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        if (priority === 'CRITICAL') {
            // Urgent two-tone siren
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(880, now);
            osc.frequency.exponentialRampToValueAtTime(440, now + 0.18);
            osc.frequency.exponentialRampToValueAtTime(880, now + 0.36);
            gain.gain.setValueAtTime(0.3, now);
            gain.gain.exponentialRampToValueAtTime(0.01, now + 0.45);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(now);
            osc.stop(now + 0.45);
        } else {
            // Subtle crisp chime
            osc.type = 'sine';
            osc.frequency.setValueAtTime(587.33, now); // D5
            osc.frequency.exponentialRampToValueAtTime(880, now + 0.12); // A5
            gain.gain.setValueAtTime(0.2, now);
            gain.gain.exponentialRampToValueAtTime(0.01, now + 0.35);
            osc.connect(gain);
            gain.connect(this.ctx.destination);
            osc.start(now);
            osc.stop(now + 0.35);
        }
    }

    toggle() {
        this.enabled = !this.enabled;
        localStorage.setItem('fraudguard_audio', this.enabled ? 'true' : 'false');
        return this.enabled;
    }
}

const soundEngine = new SecuritySoundEngine();

// 2. Real-time Clock
function initClock() {
    const clockEl = document.getElementById('topbar-clock');
    if (!clockEl) return;
    function update() {
        const now = new Date();
        const utc = now.toISOString().slice(11, 19) + ' UTC';
        const local = now.toLocaleTimeString([], { hour12: false });
        clockEl.textContent = `${local} [${utc}]`;
    }
    update();
    setInterval(update, 1000);
}

// 3. Theme Toggle (Drafting Paper vs Cyanotype)
function initTheme() {
    const toggleBtn = document.getElementById('btn-theme-toggle');
    const savedTheme = localStorage.getItem('fraudguard_theme') || document.documentElement.getAttribute('data-theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);

    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('fraudguard_theme', next);
            
            // Sync with server settings
            fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ theme: next })
            }).catch(() => {});
        });
    }
}

// 4. Audio Alert Toggle
function initAudioToggle() {
    const btn = document.getElementById('btn-audio-toggle');
    if (!btn) return;
    
    function updateIcon() {
        const enabled = soundEngine.enabled;
        btn.innerHTML = enabled 
            ? `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path></svg>`
            : `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><line x1="23" y1="9" x2="17" y2="15"></line><line x1="17" y1="9" x2="23" y2="15"></line></svg>`;
        btn.title = enabled ? "Audio Alerts: Enabled" : "Audio Alerts: Muted";
    }
    updateIcon();
    
    btn.addEventListener('click', () => {
        soundEngine.toggle();
        updateIcon();
        soundEngine.playAlertChime('LOW');
    });
}

// 5. Unread Alerts Poller & Notification Badging
let lastKnownAlertCount = 0;
function initAlertPoller() {
    const badge = document.getElementById('topbar-alert-badge');
    const sidebarBadge = document.getElementById('sidebar-alert-badge');
    
    async function checkAlerts() {
        try {
            const res = await fetch('/api/alerts/unread');
            if (!res.ok) return;
            const data = await res.json();
            
            if (data.count > lastKnownAlertCount) {
                // New alert arrived! Play audio
                soundEngine.playAlertChime(data.has_critical ? 'CRITICAL' : 'HIGH');
            }
            lastKnownAlertCount = data.count;
            
            if (badge) {
                badge.textContent = data.count;
                badge.style.display = data.count > 0 ? 'inline-flex' : 'none';
            }
            if (sidebarBadge) {
                sidebarBadge.textContent = data.count;
                sidebarBadge.style.display = data.count > 0 ? 'inline-block' : 'none';
            }
        } catch (e) {}
    }

    checkAlerts();
    setInterval(checkAlerts, 5000);
}

// Global modal helpers
function openModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.add('open');
}

function closeModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.remove('open');
}

// Init when DOM ready
document.addEventListener('DOMContentLoaded', () => {
    initClock();
    initTheme();
    initAudioToggle();
    initAlertPoller();
});
