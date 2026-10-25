(function () {
  'use strict';
  if (window.__steamControlInitialized) return;
  window.__steamControlInitialized = true;

  const API_BASE = window.location.hostname.includes('pindaroli.org')
    ? '/api/steam'
    : 'https://home-internal.pindaroli.org/api/steam';
  let isTransitioning = false;
  let currentStatus = 'unknown';
  let pollInterval = null;

  async function fetchSteamStatus() {
    try {
      const res = await fetch(`${API_BASE}/status/current`, {
        method: 'GET',
        headers: { 'Accept': 'application/json' }
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return data.data ? data.data.status : 'unknown';
    } catch (err) {
      console.warn('[SteamControl] Status error:', err);
      return 'error';
    }
  }

  async function startSteam() {
    isTransitioning = true;
    updatePillUI('starting');
    try {
      const res = await fetch(`${API_BASE}/status/start`, {
        method: 'POST',
        headers: { 'Accept': 'application/json' }
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      startPolling();
    } catch (err) {
      console.error('[SteamControl] Start error:', err);
      alert('Errore avvio Steam: ' + err.message);
      isTransitioning = false;
      refreshStatus();
    }
  }

  async function stopSteam() {
    if (!confirm('Vuoi arrestare lxc-steam? Ollama verra riavviato automaticamente.')) {
      return;
    }
    isTransitioning = true;
    updatePillUI('stopping');
    try {
      const res = await fetch(`${API_BASE}/status/shutdown`, {
        method: 'POST',
        headers: { 'Accept': 'application/json' }
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      startPolling();
    } catch (err) {
      console.error('[SteamControl] Stop error:', err);
      alert('Errore arresto Steam: ' + err.message);
      isTransitioning = false;
      refreshStatus();
    }
  }

  function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    let attempts = 0;
    pollInterval = setInterval(async () => {
      attempts++;
      const status = await fetchSteamStatus();
      if (isTransitioning) {
        if (status === 'running' || status === 'stopped') {
          isTransitioning = false;
          clearInterval(pollInterval);
          pollInterval = setInterval(refreshStatus, 15000);
        }
      }
      currentStatus = status;
      updatePillUI(status);
      if (attempts > 30) {
        clearInterval(pollInterval);
        isTransitioning = false;
        pollInterval = setInterval(refreshStatus, 15000);
      }
    }, 3000);
  }

  async function refreshStatus() {
    if (isTransitioning) return;
    const status = await fetchSteamStatus();
    currentStatus = status;
    updatePillUI(status);
  }

  function findSteamCard() {
    // 1. Cerca il link con l'IP/porta di Steam e risali alla .service-card
    const link = document.querySelector('a[href*="10.10.20.34:6080"]');
    if (link) {
      const card = link.closest('.service-card') || link.closest('[class*="service-card"]');
      if (card) return card;
    }

    // 2. Cerca per testo del servizio e risali alla .service-card
    const allText = document.querySelectorAll('.service-name, .service-title, div, a');
    for (const el of allText) {
      if (el.children.length <= 2 && (el.textContent.includes('Steam Host') || el.textContent.includes('Steam Gaming Host'))) {
        const card = el.closest('.service-card') || el.closest('[class*="service-card"]');
        if (card) return card;
      }
    }
    return null;
  }

  function updatePillUI(status) {
    const pill = document.getElementById('steam-control-pill');
    if (!pill) return;

    pill.className = 'steam-pill-btn';
    pill.disabled = false;

    if (status === 'running') {
      pill.classList.add('running');
      pill.title = 'Steam e ONLINE. Clicca per arrestare.';
      pill.innerHTML = '<span class="steam-pill-dot"></span><span class="steam-pill-label">Spegni</span>';
      pill.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        stopSteam();
      };
    } else if (status === 'stopped') {
      pill.classList.add('stopped');
      pill.title = 'Steam e SPENTO. Clicca per avviare.';
      pill.innerHTML = '<span class="steam-pill-dot"></span><span class="steam-pill-label">Avvia</span>';
      pill.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        startSteam();
      };
    } else if (status === 'starting') {
      pill.classList.add('loading');
      pill.disabled = true;
      pill.innerHTML = '<span class="steam-pill-spinner"></span><span class="steam-pill-label">Avvio...</span>';
    } else if (status === 'stopping') {
      pill.classList.add('loading');
      pill.disabled = true;
      pill.innerHTML = '<span class="steam-pill-spinner"></span><span class="steam-pill-label">Stop...</span>';
    } else {
      pill.classList.add('stopped');
      pill.disabled = true;
      pill.innerHTML = '<span class="steam-pill-dot"></span><span class="steam-pill-label">N/D</span>';
    }
  }

  function injectWidget() {
    if (document.getElementById('steam-control-pill')) return;
    const card = findSteamCard();
    if (!card) return;

    // Assicura position relative sul container intero della casella (.service-card)
    card.style.position = 'relative';

    // Riserva spazio a destra per la pillola in basso a destra
    const nameContainer = card.querySelector('.service-name') || card.querySelector('.service-title-text');
    if (nameContainer) {
      nameContainer.style.paddingRight = '75px';
    }

    const pill = document.createElement('button');
    pill.type = 'button';
    pill.id = 'steam-control-pill';
    pill.className = 'steam-pill-btn loading';
    pill.disabled = true;
    pill.innerHTML = '<span class="steam-pill-spinner"></span><span class="steam-pill-label">...</span>';

    pill.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
    });

    // Appende al container intero della casella .service-card
    card.appendChild(pill);
    refreshStatus();
  }

  const observer = new MutationObserver(() => {
    if (!document.getElementById('steam-control-pill')) {
      injectWidget();
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectWidget);
  } else {
    injectWidget();
  }

  pollInterval = setInterval(refreshStatus, 15000);
})();
