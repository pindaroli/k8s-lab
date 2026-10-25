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

  function createNavButton(referenceNode) {
    const btn = document.createElement('a');
    btn.id = BTN_ID;
    btn.href = '#terminal';
    btn.className = referenceNode ? referenceNode.className : '';
    btn.style.cssText = [
      'display:flex', 'align-items:center', 'gap:10px',
      'padding:8px 12px', 'border-radius:8px', 'cursor:pointer',
      'text-decoration:none', 'color:inherit', 'font-weight:500'
    ].join(';');
    btn.innerHTML = '<span>&gt;_</span><span>Terminale</span>';
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      toggleTerminal();
    });
    return btn;
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
    if (chatLink && chatLink.parentElement) {
      const navBtn = createNavButton(chatLink);
      chatLink.insertAdjacentElement('afterend', navBtn);
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
