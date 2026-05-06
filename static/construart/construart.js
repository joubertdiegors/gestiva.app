/* ================================================================
   CONSTRUART · JS de comportamento global
   ----------------------------------------------------------------
   1. Toggle light / dark (persiste em localStorage)
   2. DataTable ca-table: filtro por coluna, multi-selecção,
      bulk-bar, contador de linhas visíveis.

   O SmartTable (smart-table.js) é independente e trata as suas
   próprias tabelas [data-smart-table]. Este ficheiro trata
   as tabelas [data-ca-table] com classe .ca-table.
   ================================================================ */

(function () {
  'use strict';

  /* ── 1. TEMA ─────────────────────────────────────────────────── */
  const THEME_KEY = 'construart-theme';
  const root = document.documentElement;

  function applyTheme(theme) {
    root.classList.add('ca-no-transition');
    root.setAttribute('data-theme', theme);
    void root.offsetWidth;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => root.classList.remove('ca-no-transition'));
    });
    try { localStorage.setItem(THEME_KEY, theme); } catch (_) {}
    document.querySelectorAll('.ca-theme-toggle button').forEach(btn => {
      btn.classList.toggle('is-active', btn.dataset.theme === theme);
    });
    document.dispatchEvent(new CustomEvent('ca:themechange', { detail: { theme } }));
  }

  function initTheme() {
    let theme = 'light';
    try { theme = localStorage.getItem(THEME_KEY) || 'light'; } catch (_) {}
    applyTheme(theme);
    document.addEventListener('click', e => {
      const btn = e.target.closest('.ca-theme-toggle button[data-theme]');
      if (btn) applyTheme(btn.dataset.theme);
    });
  }


  /* ── 2. CA-TABLE ─────────────────────────────────────────────── */
  function initTable(wrap) {
    const table   = wrap.querySelector('table.ca-table');
    if (!table) return;

    const tableId  = wrap.dataset.caTable || null;
    const COLS_KEY = tableId ? `ca-cols-${tableId}` : null;

    const tbody    = table.querySelector('tbody');
    const allRows  = Array.from(tbody ? tbody.querySelectorAll('tr') : []);
    const filters  = {};

    /* ── Filtros por coluna ── */
    wrap.querySelectorAll('.ca-th-search input[data-col]').forEach(inp => {
      filters[inp.dataset.col] = '';
      inp.addEventListener('input', () => {
        filters[inp.dataset.col] = inp.value.trim().toLowerCase();
        applyFilters();
      });
    });

    function applyFilters() {
      allRows.forEach(tr => {
        let visible = true;
        for (const col in filters) {
          const q = filters[col];
          if (!q) continue;
          const cell = tr.querySelector(`[data-col="${col}"]`);
          const txt  = cell ? cell.textContent.toLowerCase() : '';
          if (!txt.includes(q)) { visible = false; break; }
        }
        tr.style.display = visible ? '' : 'none';
      });
      updateCount();
      updateSelectAll();
      updateFilterBtn();
    }

    function updateFilterBtn() {
      const btn = wrap.querySelector('[data-ca-action="toggle-filters"]');
      if (!btn) return;
      const hasActive = Object.values(filters).some(v => v !== '');
      btn.classList.toggle('is-active', hasActive);
      btn.disabled = !hasActive;
    }

    /* ── Contador ── */
    const counterEl = wrap.querySelector('[data-ca-row-count]');
    function updateCount() {
      if (!counterEl) return;
      const total   = allRows.length;
      const visible = allRows.filter(r => r.style.display !== 'none').length;
      counterEl.textContent = visible === total ? total : `${visible} / ${total}`;
    }

    /* ── Multi-selecção ── */
    const selectAllCb = wrap.querySelector('input.ca-checkbox[data-ca-select-all]');
    const rowCbs = () => allRows
      .filter(tr => tr.style.display !== 'none')
      .map(tr => tr.querySelector('input.ca-checkbox[data-ca-row-select]'))
      .filter(Boolean);

    function selectedCbs() {
      return Array.from(wrap.querySelectorAll('input.ca-checkbox[data-ca-row-select]:checked'));
    }

    function updateBulkBar() {
      const n     = selectedCbs().length;
      const bulkBar  = wrap.querySelector('.ca-bulk-bar');
      const countEl  = wrap.querySelector('[data-ca-bulk-count]');
      if (bulkBar)  { if (n > 0) bulkBar.removeAttribute('hidden'); else bulkBar.setAttribute('hidden', ''); }
      if (countEl)  countEl.textContent = n;
    }

    function updateSelectAll() {
      if (!selectAllCb) return;
      const visible  = rowCbs();
      const checked  = visible.filter(cb => cb.checked).length;
      selectAllCb.checked       = checked > 0 && checked === visible.length;
      selectAllCb.indeterminate = checked > 0 && checked < visible.length;
      selectAllCb.classList.toggle('is-indeterminate', checked > 0 && checked < visible.length);
    }

    function updateRowHighlight() {
      allRows.forEach(tr => {
        const cb = tr.querySelector('input.ca-checkbox[data-ca-row-select]');
        tr.classList.toggle('is-selected', !!(cb && cb.checked));
      });
    }

    if (selectAllCb) {
      selectAllCb.addEventListener('change', () => {
        rowCbs().forEach(cb => { cb.checked = selectAllCb.checked; });
        updateBulkBar();
        updateRowHighlight();
      });
    }

    tbody && tbody.addEventListener('change', e => {
      if (e.target.matches('input.ca-checkbox[data-ca-row-select]')) {
        updateSelectAll();
        updateBulkBar();
        updateRowHighlight();
      }
    });

    /* ── Chips de filtro activos (botão × remove filtro) ── */
    wrap.querySelectorAll('[data-ca-filter-chip]').forEach(chip => {
      const x = chip.querySelector('.ca-chip-x');
      if (!x) return;
      x.addEventListener('click', () => {
        const col = chip.dataset.col;
        const inp = wrap.querySelector(`.ca-th-search input[data-col="${col}"]`);
        if (inp) { inp.value = ''; filters[col] = ''; applyFilters(); }
        chip.remove();
      });
    });

    /* ── Botões de acção ── */
    updateFilterBtn();

    wrap.addEventListener('click', e => {
      if (e.target.closest('.ca-col-panel')) return; // cliques dentro do painel não propagam
      const btn = e.target.closest('[data-ca-action]');
      if (!btn) return;
      const action = btn.dataset.caAction;

      if (action === 'toggle-filters' || action === 'clear-filters') {
        wrap.querySelectorAll('.ca-th-search input[data-col]').forEach(inp => {
          inp.value = '';
          filters[inp.dataset.col] = '';
        });
        applyFilters();

      } else if (action === 'refresh') {
        window.location.reload();

      } else if (action === 'export') {
        document.dispatchEvent(new CustomEvent('ca:export', { detail: { wrap } }));

      } else if (action === 'toggle-totals') {
        document.dispatchEvent(new CustomEvent('ca:toggle-totals', { detail: { wrap } }));

      } else if (action === 'columns') {
        toggleColPanel(btn);
      }
    });

    /* ── Painel de colunas ── */
    const allThs = Array.from(table.querySelectorAll('thead th'));

    function getColHeaders() {
      return allThs.filter(th => th.hasAttribute('data-col'));
    }

    function setColVisible(th, visible) {
      const pos = allThs.indexOf(th) + 1; // nth-child é 1-based
      table.querySelectorAll(
        `thead tr > th:nth-child(${pos}), tbody tr > td:nth-child(${pos})`
      ).forEach(el => { el.style.display = visible ? '' : 'none'; });
    }

    const PREF_URL = tableId
      ? `/api/prefs/table/${tableId}/`
      : null;

    function getCsrfToken() {
      const el = document.querySelector('[name=csrfmiddlewaretoken]');
      if (el) return el.value;
      const m = document.cookie.match(/csrftoken=([^;]+)/);
      return m ? m[1] : '';
    }

    function applyHiddenCols(hiddenCols) {
      getColHeaders().forEach(th => {
        const col      = th.dataset.col;
        const required = th.hasAttribute('data-col-required');
        const visible  = required ? true : !hiddenCols.includes(col);
        setColVisible(th, visible);
      });
    }

    function saveColState() {
      if (!PREF_URL) return;
      const hiddenCols = getColHeaders()
        .filter(th => {
          const pos = allThs.indexOf(th) + 1;
          const el  = table.querySelector(`thead tr > th:nth-child(${pos})`);
          return el && el.style.display === 'none';
        })
        .map(th => th.dataset.col);

      fetch(PREF_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({ hidden_cols: hiddenCols }),
      }).catch(() => {});
    }

    function loadColState() {
      // Aplica defaults imediatamente (sem flash de colunas erradas)
      applyHiddenCols(getColHeaders()
        .filter(th => th.hasAttribute('data-col-hidden'))
        .map(th => th.dataset.col)
      );

      if (!PREF_URL) return;

      fetch(PREF_URL)
        .then(r => r.ok ? r.json() : null)
        .then(data => {
          if (data && Array.isArray(data.hidden_cols)) {
            applyHiddenCols(data.hidden_cols);
          }
        })
        .catch(() => {});
    }

    function buildColPanel(anchorBtn) {
      const panel = document.createElement('div');
      panel.className = 'ca-col-panel';

      const header = document.createElement('div');
      header.className = 'ca-col-panel-header';
      header.innerHTML = '<strong>Colunas</strong>';
      const closeBtn = document.createElement('button');
      closeBtn.className = 'ca-col-panel-close';
      closeBtn.innerHTML = '&times;';
      closeBtn.addEventListener('click', () => panel.remove());
      header.appendChild(closeBtn);
      panel.appendChild(header);

      const list = document.createElement('ul');
      list.className = 'ca-col-panel-list';

      getColHeaders().forEach(th => {
        const col      = th.dataset.col;
        const label    = th.dataset.colLabel || col;
        const required = th.hasAttribute('data-col-required');
        const pos      = allThs.indexOf(th) + 1;
        const thEl     = table.querySelector(`thead tr > th:nth-child(${pos})`);
        const visible  = thEl ? thEl.style.display !== 'none' : true;

        const li = document.createElement('li');
        li.className = 'ca-col-panel-item';

        const lbl = document.createElement('label');
        const cb  = document.createElement('input');
        cb.type    = 'checkbox';
        cb.checked = visible;
        if (required) { cb.disabled = true; cb.title = 'Coluna obrigatória'; }

        cb.addEventListener('change', () => {
          setColVisible(th, cb.checked);
          saveColState();
        });

        lbl.appendChild(cb);
        lbl.appendChild(document.createTextNode(' ' + label));
        li.appendChild(lbl);
        list.appendChild(li);
      });

      panel.appendChild(list);

      const footer = document.createElement('div');
      footer.className = 'ca-col-panel-footer';
      const resetBtn = document.createElement('button');
      resetBtn.className = 'ca-col-panel-reset';
      resetBtn.textContent = 'Repor padrão';
      resetBtn.addEventListener('click', () => {
        if (COLS_KEY) { try { localStorage.removeItem(COLS_KEY); } catch (_) {} }
        panel.remove();
        loadColState();
        const newPanelBtn = wrap.querySelector('[data-ca-action="columns"]');
        if (newPanelBtn) toggleColPanel(newPanelBtn);
      });
      footer.appendChild(resetBtn);
      panel.appendChild(footer);

      anchorBtn.style.position = 'relative';
      anchorBtn.appendChild(panel);

      requestAnimationFrame(() => {
        document.addEventListener('click', function outsideClick(e) {
          if (!panel.contains(e.target) && e.target !== anchorBtn) {
            panel.remove();
            document.removeEventListener('click', outsideClick);
          }
        });
      });
    }

    function toggleColPanel(anchorBtn) {
      const existing = anchorBtn.querySelector('.ca-col-panel');
      if (existing) { existing.remove(); return; }
      buildColPanel(anchorBtn);
    }

    /* ── Arranque ── */
    loadColState();
    updateCount();
    updateBulkBar();
  }

  function initTables() {
    document.querySelectorAll('[data-ca-table]').forEach(initTable);
  }


  /* ── Boot ────────────────────────────────────────────────────── */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => { initTheme(); initTables(); });
  } else {
    initTheme();
    initTables();
  }

  window.Construart = { applyTheme, initTable, initTables };
})();
