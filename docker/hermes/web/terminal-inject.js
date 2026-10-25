(() => {
  'use strict';

  const BTN_ID = 'hermes-terminal-nav-btn';
  const FAB_ID = 'hermes-terminal-fab';
  const OVERLAY_ID = 'hermes-terminal-overlay';

  function getTerminalUrl() {
    return '/terminal';
  }

  function ensureTerminalOverlay() {
    let overlay = document.getElementById(OVERLAY_ID);
    if (overlay) return overlay;

    overlay = document.createElement('div');
    overlay.id = OVERLAY_ID;
    overlay.style.cssText = [
      'position:fixed', 'inset:0', 'z-index:9998',
      'background:rgba(15,17,23,0.92)', 'display:none',
      'flex-direction:column', 'backdrop-filter:blur(4px)'
    ].join(';');

    const header = document.createElement('div');
    header.style.cssText = [
      'display:flex', 'align-items:center', 'justify-content:space-between',
      'padding:8px 16px', 'background:#161922', 'border-bottom:1px solid #2d3343',
      'color:#e2e8f0', 'font-family:system-ui,sans-serif', 'font-size:13px'
    ].join(';');

    const title = document.createElement('span');
    title.textContent = 'Hermes Web Terminal (ttyd — /opt/data)';

    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.textContent = 'Chiudi (ESC)';
    closeBtn.style.cssText = [
      'background:#2d3343', 'color:#fff', 'border:none',
      'padding:4px 10px', 'border-radius:6px', 'cursor:pointer'
    ].join(';');
    closeBtn.onclick = () => toggleTerminal(false);

    header.appendChild(title);
    header.appendChild(closeBtn);

    const iframe = document.createElement('iframe');
    iframe.id = 'hermes-terminal-iframe';
    iframe.style.cssText = 'flex:1;width:100%;border:none;background:#041c1c;';
    iframe.dataset.loaded = 'false';

    overlay.appendChild(header);
    overlay.appendChild(iframe);
    document.body.appendChild(overlay);

    window.addEventListener('keydown', (ev) => {
      if (ev.key === 'Escape' && overlay.style.display === 'flex') {
        toggleTerminal(false);
      }
    });

    return overlay;
  }

  function toggleTerminal(forceState) {
    const overlay = ensureTerminalOverlay();
    const iframe = document.getElementById('hermes-terminal-iframe');
    const isHidden = overlay.style.display === 'none';
    const nextState = typeof forceState === 'boolean' ? forceState : isHidden;

    if (nextState) {
      if (iframe && iframe.dataset.loaded !== 'true') {
        iframe.src = getTerminalUrl();
        iframe.dataset.loaded = 'true';
      }
      overlay.style.display = 'flex';
    } else {
      overlay.style.display = 'none';
    }
  }

  const TERMINAL_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5 shrink-0"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" x2="20" y1="19" y2="19"></line></svg>';

  function createNavItem(referenceLink) {
    const li = document.createElement('li');
    li.id = 'hermes-terminal-nav-item';

    const btn = document.createElement('a');
    btn.id = BTN_ID;
    btn.href = '#terminal';

    const baseClasses = 'group/nav relative flex items-center gap-3 px-5 py-2.5 font-sans text-display uppercase text-sm tracking-[0.12em] whitespace-nowrap transition-colors cursor-pointer text-text-secondary hover:text-midground';
    if (referenceLink && referenceLink.className) {
      let refClasses = referenceLink.className.replace(/\btext-midground\b/g, '').trim();
      btn.className = refClasses + ' text-text-secondary hover:text-midground';
    } else {
      btn.className = baseClasses;
    }
    btn.style.clipPath = 'var(--component-tab-clip-path)';

    btn.innerHTML = [
      TERMINAL_SVG,
      '<span class="truncate transition-opacity duration-300 lg:opacity-100">Terminale</span>',
      '<span aria-hidden="true" class="absolute inset-y-0.5 left-1.5 right-1.5 bg-midground opacity-0 pointer-events-none transition-opacity duration-200 group-hover/nav:opacity-5"></span>'
    ].join('');

    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      toggleTerminal();
    });

    li.appendChild(btn);
    return li;
  }

  function ensureFloatingFallback(showFallback) {
    let fab = document.getElementById(FAB_ID);
    if (!showFallback) {
      if (fab) fab.style.display = 'none';
      return;
    }
    if (!fab) {
      fab = document.createElement('button');
      fab.id = FAB_ID;
      fab.type = 'button';
      fab.title = 'Apri Web Terminal';
      fab.textContent = '>_ Terminal';
      fab.style.cssText = [
        'position:fixed', 'bottom:16px', 'left:16px', 'z-index:9990',
        'background:#1e293b', 'color:#f8fafc', 'border:1px solid #475569',
        'border-radius:999px', 'padding:6px 12px', 'font-size:12px',
        'font-family:monospace', 'cursor:pointer', 'box-shadow:0 4px 12px rgba(0,0,0,0.4)'
      ].join(';');
      fab.onclick = () => toggleTerminal();
      document.body.appendChild(fab);
    }
    fab.style.display = 'block';
  }

  function mountTerminalTrigger() {
    const existingBtn = document.getElementById(BTN_ID);
    if (existingBtn && document.body.contains(existingBtn)) {
      const isVisible = existingBtn.offsetParent !== null;
      ensureFloatingFallback(!isVisible);
      return;
    }

    const chatLink = document.querySelector('a[href*="/chat"], nav a, aside a');
    if (chatLink) {
      const navItem = createNavItem(chatLink);
      const parentLi = chatLink.closest('li');
      if (parentLi && parentLi.parentElement) {
        parentLi.insertAdjacentElement('afterend', navItem);
      } else if (chatLink.parentElement) {
        chatLink.insertAdjacentElement('afterend', navItem);
      }
      ensureFloatingFallback(false);
    } else {
      ensureFloatingFallback(true);
    }
  }

  let scheduled = false;
  const observer = new MutationObserver(() => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      mountTerminalTrigger();
    });
  });

  function init() {
    mountTerminalTrigger();
    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
