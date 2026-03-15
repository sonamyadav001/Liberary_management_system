// ═══════════════════════════════════════════
// SHABD SANGRAH - Main JavaScript
// ═══════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    initDarkMode();
    initClock();
    initFlashMessages();
    initHamburger();
    initSearchAutocomplete();
    initAnimations();
    initActiveNav();
});

// ─── DARK MODE ──────────────────────────────────────
function initDarkMode() {
    const toggle = document.getElementById('darkModeToggle');
    const saved = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);
    if (toggle) {
        toggle.textContent = saved === 'dark' ? '☀️' : '🌙';
        toggle.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
            toggle.textContent = next === 'dark' ? '☀️' : '🌙';
        });
    }
}

// ─── LIVE CLOCK ─────────────────────────────────────
function initClock() {
    const timeEl = document.getElementById('liveTime');
    const dateEl = document.getElementById('liveDate');
    const dayEl = document.getElementById('liveDay');

    if (!timeEl) return;

    const days = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
    const months = ['January','February','March','April','May','June','July','August','September','October','November','December'];

    function update() {
        const now = new Date();
        const h = String(now.getHours()).padStart(2,'0');
        const m = String(now.getMinutes()).padStart(2,'0');
        const s = String(now.getSeconds()).padStart(2,'0');
        timeEl.textContent = `${h}:${m}:${s}`;
        if (dateEl) dateEl.textContent = `${now.getDate()} ${months[now.getMonth()]} ${now.getFullYear()}`;
        if (dayEl) dayEl.textContent = days[now.getDay()];
    }
    update();
    setInterval(update, 1000);
}

// ─── FLASH MESSAGES ──────────────────────────────────
function initFlashMessages() {
    const flashes = document.querySelectorAll('.flash');
    flashes.forEach(flash => {
        setTimeout(() => {
            flash.style.animation = 'slideOut 0.4s ease forwards';
            setTimeout(() => flash.remove(), 400);
        }, 5000);
        flash.addEventListener('click', () => flash.remove());
    });
}

// ─── HAMBURGER ──────────────────────────────────────
function initHamburger() {
    const btn = document.getElementById('hamburger');
    const nav = document.getElementById('navbarNav');
    if (btn && nav) {
        btn.addEventListener('click', () => nav.classList.toggle('open'));
    }
}

// ─── SEARCH AUTOCOMPLETE ─────────────────────────────
function initSearchAutocomplete() {
    const searchInput = document.getElementById('searchInput');
    const resultsBox = document.getElementById('searchResults');
    if (!searchInput || !resultsBox) return;

    let timer;
    searchInput.addEventListener('input', () => {
        clearTimeout(timer);
        const q = searchInput.value.trim();
        if (q.length < 2) { resultsBox.style.display = 'none'; return; }
        timer = setTimeout(async () => {
            try {
                const res = await fetch(`/api/books/search?q=${encodeURIComponent(q)}`);
                const data = await res.json();
                if (data.length === 0) { resultsBox.style.display = 'none'; return; }
                resultsBox.innerHTML = data.map(b => `
                    <a href="/book/${b.id}" class="autocomplete-item">
                        <span class="ac-title">${b.title}</span>
                        <span class="ac-author">${b.author} · ${b.category}</span>
                        <span class="ac-avail ${b.available > 0 ? 'ac-available' : 'ac-unavailable'}">
                            ${b.available > 0 ? '✅ Available' : '❌ Unavailable'}
                        </span>
                    </a>
                `).join('');
                resultsBox.style.display = 'block';
            } catch(e) { console.error(e); }
        }, 300);
    });

    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target)) resultsBox.style.display = 'none';
    });
}

// ─── SCROLL ANIMATIONS ──────────────────────────────
function initAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.book-card, .stat-card, .chart-container, .card').forEach(el => {
        observer.observe(el);
    });
}

// ─── ACTIVE NAV ─────────────────────────────────────
function initActiveNav() {
    const path = window.location.pathname;
    document.querySelectorAll('.nav-link, .sidebar-nav a').forEach(link => {
        if (link.getAttribute('href') === path) link.classList.add('active');
    });
}

// ─── DELIVERY DISTANCE CALCULATOR ─────────────────
function calcDelivery() {
    const dist = parseFloat(document.getElementById('distInput')?.value || 0);
    const maxKm = 5, chargePerKm = 5;
    const chargeEl = document.getElementById('deliveryCharge');
    const warningEl = document.getElementById('distWarning');
    if (!chargeEl) return;
    if (dist > maxKm) {
        if (warningEl) warningEl.style.display = 'block';
        chargeEl.textContent = 'Out of range';
        chargeEl.style.color = '#dc3545';
    } else {
        if (warningEl) warningEl.style.display = 'none';
        const charge = (dist * chargePerKm).toFixed(2);
        chargeEl.textContent = `₹${charge}`;
        chargeEl.style.color = 'var(--brown-dark)';
    }
}

// ─── CONFIRM DELETE ──────────────────────────────────
function confirmDelete(msg) {
    return confirm(msg || 'Are you sure you want to delete this?');
}

// ─── FILTER BOOKS ────────────────────────────────────
function applyFilter() {
    const form = document.getElementById('filterForm');
    if (form) form.submit();
}

// ─── SORT CHANGE ─────────────────────────────────────
function sortChange(val) {
    const url = new URL(window.location.href);
    url.searchParams.set('sort', val);
    window.location.href = url.toString();
}

// ─── AUTOCOMPLETE STYLES (injected) ─────────────────
const acStyles = document.createElement('style');
acStyles.textContent = `
.search-wrapper { position: relative; }
#searchResults {
    position: absolute; top: 100%; left: 0; right: 0;
    background: white; border-radius: 12px;
    box-shadow: 0 8px 40px rgba(109,59,7,0.2);
    z-index: 500; max-height: 320px; overflow-y: auto;
    display: none; margin-top: 4px;
}
.autocomplete-item {
    display: flex; flex-direction: column; gap: 2px;
    padding: 12px 16px; text-decoration: none; color: #2C1810;
    transition: background 0.2s; border-bottom: 1px solid #f0ebe0;
}
.autocomplete-item:hover { background: #f5f0e8; }
.ac-title { font-weight: 700; font-size: 14px; }
.ac-author { font-size: 12px; color: #8B6355; }
.ac-avail { font-size: 11px; font-weight: 600; }
.ac-available { color: #155724; }
.ac-unavailable { color: #721c24; }
`;
document.head.appendChild(acStyles);
