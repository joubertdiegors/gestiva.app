/**
 * SmartTable — tabela ERP com colunas configuráveis, filtro integrado no header,
 * ordenação com setas, seleção de linhas e persistência em localStorage.
 *
 * Atributos dos <th>:
 *   data-col="chave"              — identificador único (obrigatório)
 *   data-label="Texto"            — label visível no header/filtro
 *   data-type="text|num|date"     — tipo para ordenação (default: text)
 *   data-filter-type="select"     — usa <select> no filtro (requer data-filter-options)
 *   data-filter-options="a,b,c"   — opções para o select, separadas por vírgula
 *   data-default-hidden           — coluna oculta por padrão
 *   data-nosort                   — desabilita ordenação
 *   data-nofilter                 — sem campo de filtro
 *   data-nohide                   — não pode ser ocultada pelo painel
 *
 * Atributos do wrapper [data-smart-table]:
 *   data-selectable               — checkboxes de linha
 *   data-result-count="N"         — total server-side (para o contador)
 */
(function () {
  'use strict';

  /* ── utils ─────────────────────────────────────────────────── */
  function save(id, k, v) { try { localStorage.setItem('st_'+id+'_'+k, JSON.stringify(v)); } catch(_){} }
  function load(id, k, fb) {
    try { const r = localStorage.getItem('st_'+id+'_'+k); return r !== null ? JSON.parse(r) : fb; }
    catch(_){ return fb; }
  }

  function cellText(td) {
    const s = td.querySelector('.st-sort-val');
    return (s ? s.textContent : td.textContent).trim();
  }

  function parseVal(text, type) {
    const t = text.trim();
    if (type === 'num') {
      const n = parseFloat(t.replace(/[^\d.,-]/g,'').replace(',','.'));
      return isNaN(n) ? -Infinity : n;
    }
    if (type === 'date') {
      const m = t.match(/(\d{2})\/(\d{2})\/(\d{4})/);
      return m ? m[3]+'-'+m[2]+'-'+m[1] : t;
    }
    return t.toLowerCase();
  }

  /* ══════════════════════════════════════════════════════════════
     INIT
  ══════════════════════════════════════════════════════════════ */
  function init(wrapper) {
    const tableId    = wrapper.dataset.smartTable;
    const selectable = wrapper.hasAttribute('data-selectable');
    const table      = wrapper.querySelector('table');
    if (!table) return;
    const thead = table.tHead;
    const tbody = table.tBodies[0];
    if (!thead || !tbody) return;

    const origRow = thead.rows[0]; // linha original do HTML com os <th> de definição

    /* ── 1. Lê definição das colunas ──────────────────────────── */
    const colDefs = [];
    Array.from(origRow.cells).forEach((th, idx) => {
      const key = th.dataset.col;
      if (!key) return;
      colDefs.push({
        key,
        idx,
        label:         th.dataset.label || th.textContent.trim(),
        type:          th.dataset.type  || 'text',
        filterType:    th.dataset.filterType || 'text',   // 'text' | 'select'
        filterOptions: th.dataset.filterOptions ? th.dataset.filterOptions.split(',').map(o => {
          const p = o.trim().split(':');
          return { label: p[0].trim(), value: p.length > 1 ? p[1].trim() : p[0].trim() };
        }) : [],
        nosort:        th.hasAttribute('data-nosort'),
        nofilter:      th.hasAttribute('data-nofilter'),
        nohide:        th.hasAttribute('data-nohide'),
        defHidden:     th.hasAttribute('data-default-hidden'),
        minWidth:      th.dataset.width || '',
      });
    });
    origRow.remove(); // remove a linha de definição — vamos gerar a nova

    /* ── 2. Estado ────────────────────────────────────────────── */
    const defaultOrder   = colDefs.map(c => c.key);
    const defaultVisible = colDefs.filter(c => !c.defHidden).map(c => c.key);

    let colOrder   = load(tableId, 'order',   defaultOrder);
    let colVisible = load(tableId, 'visible', defaultVisible);
    let sortState  = load(tableId, 'sort',    { col: null, dir: null });

    colOrder   = [...defaultOrder.filter(k => !colOrder.includes(k)), ...colOrder.filter(k => defaultOrder.includes(k))];
    colVisible = colVisible.filter(k => defaultOrder.includes(k));

    const filterVals = {};
    const allRows    = Array.from(tbody.rows);

    /* ── 3. Checkboxes de seleção nas linhas ──────────────────── */
    if (selectable) {
      allRows.forEach(row => {
        const td = document.createElement('td');
        td.className = 'st-chk-td';
        td.innerHTML = '<input type="checkbox" class="st-chk st-row-chk">';
        row.insertBefore(td, row.firstChild);
      });
    }

    /* ── 4. Marca tds das linhas com data-st-col ──────────────── */
    allRows.forEach(row => {
      const offset = selectable ? 1 : 0;
      colDefs.forEach(col => {
        const td = row.cells[col.idx + offset];
        if (td) td.dataset.stCol = col.key;
      });
    });

    /* ── 5. Cria a linha de header+filtro unificada ───────────── */
    const headerRow = document.createElement('tr');
    headerRow.className = 'st-header-row';
    thead.appendChild(headerRow);

    function buildHeaderCell(col) {
      const isSort = sortState.col === col.key;
      const dir    = isSort ? sortState.dir : null;

      const th = document.createElement('th');
      th.dataset.col = col.key;
      if (col.minWidth) th.style.minWidth = col.minWidth;
      if (!colVisible.includes(col.key)) th.classList.add('st-col-hidden');

      const inner = document.createElement('div');
      inner.className = 'st-th-inner';

      /* ── coluna com label + filtro (estrutura vertical) ── */
      const cell = document.createElement('div');
      cell.className = 'st-th-cell';

      /* label sempre visível */
      if (col.label) {
        const lbl = document.createElement('span');
        lbl.className = 'st-th-label';
        lbl.textContent = col.label;
        cell.appendChild(lbl);
      }

      /* input/select encaixotado abaixo do label */
      if (!col.nofilter) {
        const wrap = document.createElement('div');
        wrap.className = 'st-filter-wrap';

        if (col.filterType === 'select') {
          const sel = document.createElement('select');
          sel.className = 'st-filter-select';
          sel.dataset.filterCol = col.key;
          const blank = document.createElement('option');
          blank.value = ''; blank.textContent = '—';
          sel.appendChild(blank);
          col.filterOptions.forEach(opt => {
            const o = document.createElement('option');
            o.value = opt.value; o.textContent = opt.label;
            if (filterVals[col.key] === opt.value) o.selected = true;
            sel.appendChild(o);
          });
          wrap.appendChild(sel);
        } else {
          const icon = document.createElement('span');
          icon.className = 'st-filter-icon';
          icon.innerHTML = '<svg viewBox="0 0 12 12" width="11" height="11" fill="none"><circle cx="5" cy="5" r="3.5" stroke="currentColor" stroke-width="1.3"/><line x1="7.8" y1="7.8" x2="11" y2="11" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>';

          const inp = document.createElement('input');
          inp.type = 'text';
          inp.className = 'st-filter-input';
          inp.dataset.filterCol = col.key;
          inp.autocomplete = 'off';
          inp.spellcheck   = false;
          inp.value        = filterVals[col.key] || '';

          const clearBtn = document.createElement('button');
          clearBtn.type = 'button';
          clearBtn.className = 'st-filter-clear';
          clearBtn.textContent = '×';
          clearBtn.dataset.filterCol = col.key;
          clearBtn.style.display = inp.value ? '' : 'none';

          wrap.appendChild(icon);
          wrap.appendChild(inp);
          wrap.appendChild(clearBtn);
        }
        cell.appendChild(wrap);
      }

      inner.appendChild(cell);

      /* ── setas sort ── */
      if (!col.nosort) {
        const sortWrap = document.createElement('div');
        sortWrap.className = 'st-sort-wrap';

        const up = document.createElement('button');
        up.type = 'button';
        up.className = 'st-sort-btn st-sort-up' + (isSort && dir === 'asc' ? ' active' : '');
        up.dataset.sortCol = col.key;
        up.dataset.sortDir = 'asc';
        up.innerHTML = '<svg viewBox="0 0 10 6" width="9" height="6"><path d="M1 5L5 1L9 5" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg>';

        const dn = document.createElement('button');
        dn.type = 'button';
        dn.className = 'st-sort-btn st-sort-dn' + (isSort && dir === 'desc' ? ' active' : '');
        dn.dataset.sortCol = col.key;
        dn.dataset.sortDir = 'desc';
        dn.innerHTML = '<svg viewBox="0 0 10 6" width="9" height="6"><path d="M1 1L5 5L9 1" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg>';

        sortWrap.appendChild(up);
        sortWrap.appendChild(dn);
        inner.appendChild(sortWrap);
      }

      th.appendChild(inner);

      /* checkbox "selecionar tudo" na coluna de checkbox */
      if (col.nohide && selectable && col.key === colDefs.find(c => c.nohide)?.key) {
        // será tratado à parte
      }

      return th;
    }

    /* ── 6. Rebuild header (reordenar + visibilidade) ────────── */
    function rebuildHeader() {
      // Guarda valores dos filtros actuais antes de recriar
      headerRow.querySelectorAll('.st-filter-input').forEach(el => {
        if (el.value) filterVals[el.dataset.filterCol] = el.value;
      });
      headerRow.querySelectorAll('.st-filter-select').forEach(el => {
        filterVals[el.dataset.filterCol] = el.value;
      });

      headerRow.innerHTML = '';

      // Checkbox "all" se selectable
      if (selectable) {
        const th = document.createElement('th');
        th.className = 'st-chk-th';
        th.innerHTML = `<input type="checkbox" class="st-chk" id="st-chk-all-${tableId}">`;
        headerRow.appendChild(th);
      }

      colOrder.forEach(key => {
        const col = colDefs.find(c => c.key === key);
        if (col) headerRow.appendChild(buildHeaderCell(col));
      });

      bindFilterInputs();
      bindSortBtns();
      if (selectable) bindCheckboxes();
    }

    /* ── 7. Visibilidade e ordem das linhas ───────────────────── */
    function applyToRows() {
      allRows.forEach(row => {
        colOrder.forEach(key => {
          const td = row.querySelector(`td[data-st-col="${key}"]`);
          if (!td) return;
          td.classList.toggle('st-col-hidden', !colVisible.includes(key));
        });
        // reordena tds
        const chkTd = selectable ? row.querySelector('.st-chk-td') : null;
        colOrder.forEach(key => {
          const td = row.querySelector(`td[data-st-col="${key}"]`);
          if (td) row.appendChild(td);
        });
        if (chkTd) row.insertBefore(chkTd, row.firstChild);
      });
    }

    /* ── 8. Sort ─────────────────────────────────────────────── */
    function applySort() {
      if (!sortState.col) return;
      const col = colDefs.find(c => c.key === sortState.col);
      if (!col) return;
      const dir = sortState.dir === 'asc' ? 1 : -1;
      [...allRows].sort((a, b) => {
        const vA = parseVal(cellText(a.querySelector(`td[data-st-col="${col.key}"]`) || document.createElement('td')), col.type);
        const vB = parseVal(cellText(b.querySelector(`td[data-st-col="${col.key}"]`) || document.createElement('td')), col.type);
        return vA < vB ? -dir : vA > vB ? dir : 0;
      }).forEach(r => tbody.appendChild(r));
    }

    /* ── 9. Filter ───────────────────────────────────────────── */
    function applyFilter() {
      const active = Object.entries(filterVals).filter(([,v]) => v && v.trim());
      allRows.forEach(row => {
        if (!active.length) { row.style.display = ''; return; }
        const ok = active.every(([key, val]) => {
          const td = row.querySelector(`td[data-st-col="${key}"]`);
          if (!td) return false;
          return cellText(td).toLowerCase().includes(val.toLowerCase());
        });
        row.style.display = ok ? '' : 'none';
      });
      updateResultCount();
    }

    /* ── 10. Contador ────────────────────────────────────────── */
    const resultEl      = wrapper.querySelector('.st-result-count');
    const totalFromAttr = parseInt(wrapper.dataset.resultCount || '0', 10);
    function updateResultCount() {
      if (!resultEl) return;
      const vis = allRows.filter(r => r.style.display !== 'none').length;
      const has = Object.values(filterVals).some(v => v && v.trim());
      resultEl.textContent = has
        ? vis + ' resultado' + (vis !== 1 ? 's' : '') + ' filtrado' + (vis !== 1 ? 's' : '')
        : (totalFromAttr || allRows.length) + ' resultado' + ((totalFromAttr || allRows.length) !== 1 ? 's' : '');
    }

    /* ── 11. Render completo ─────────────────────────────────── */
    function render() {
      rebuildHeader();
      applyToRows();
      applySort();
      applyFilter();
    }

    /* ── 12. Events: sort ────────────────────────────────────── */
    function bindSortBtns() {
      headerRow.querySelectorAll('.st-sort-btn').forEach(btn => {
        btn.addEventListener('click', e => {
          e.stopPropagation();
          const key = btn.dataset.sortCol;
          const dir = btn.dataset.sortDir;
          // toggle: clica na mesma direcção → remove sort
          if (sortState.col === key && sortState.dir === dir) {
            sortState = { col: null, dir: null };
          } else {
            sortState = { col: key, dir };
          }
          save(tableId, 'sort', sortState);
          // atualiza classes active nas setas sem recriar header
          headerRow.querySelectorAll('.st-sort-btn').forEach(b => {
            b.classList.toggle('active',
              b.dataset.sortCol === sortState.col && b.dataset.sortDir === sortState.dir);
          });
          applySort();
        });
      });
    }

    /* ── 13. Events: filtros ─────────────────────────────────── */
    function bindFilterInputs() {
      headerRow.querySelectorAll('.st-filter-input').forEach(inp => {
        inp.addEventListener('input', () => {
          filterVals[inp.dataset.filterCol] = inp.value;
          const clr = inp.nextElementSibling;
          if (clr && clr.classList.contains('st-filter-clear'))
            clr.style.display = inp.value ? '' : 'none';
          applyFilter();
        });
      });

      headerRow.querySelectorAll('.st-filter-clear').forEach(btn => {
        btn.addEventListener('click', e => {
          e.stopPropagation();
          const key = btn.dataset.filterCol;
          const inp = btn.previousElementSibling;
          if (inp) inp.value = '';
          filterVals[key] = '';
          btn.style.display = 'none';
          applyFilter();
        });
      });

      headerRow.querySelectorAll('.st-filter-select').forEach(sel => {
        sel.addEventListener('change', () => {
          filterVals[sel.dataset.filterCol] = sel.value;
          applyFilter();
        });
      });
    }

    /* ── 14. Events: checkboxes ──────────────────────────────── */
    function bindCheckboxes() {
      const chkAll = wrapper.querySelector('#st-chk-all-' + tableId);
      if (!chkAll) return;
      chkAll.addEventListener('change', () => {
        wrapper.querySelectorAll('.st-row-chk').forEach(c => {
          if (c.closest('tr').style.display !== 'none') c.checked = chkAll.checked;
        });
        updateBulkBar();
      });
      wrapper.querySelectorAll('.st-row-chk').forEach(c => {
        c.addEventListener('change', () => {
          const all     = wrapper.querySelectorAll('.st-row-chk').length;
          const checked = wrapper.querySelectorAll('.st-row-chk:checked').length;
          chkAll.indeterminate = checked > 0 && checked < all;
          chkAll.checked       = checked === all;
          updateBulkBar();
        });
      });
    }

    function updateBulkBar() {
      const bar   = wrapper.querySelector('.st-bulk-bar');
      const count = wrapper.querySelectorAll('.st-row-chk:checked').length;
      if (!bar) return;
      bar.querySelector('.st-bulk-count').textContent = count + ' seleccionado' + (count !== 1 ? 's' : '');
      bar.style.display = count > 0 ? 'flex' : 'none';
    }

    /* ── 15. Painel de colunas ───────────────────────────────── */
    function buildColumnPanel() {
      const panel = wrapper.querySelector('.st-col-panel');
      if (!panel) return;
      panel.innerHTML = '';

      const title = document.createElement('div');
      title.className   = 'st-col-panel-title';
      title.textContent = 'Colunas visíveis';
      panel.appendChild(title);

      const list = document.createElement('ul');
      list.className = 'st-col-list';

      colOrder.forEach((key, pos) => {
        const col = colDefs.find(c => c.key === key);
        if (!col || col.nohide) return;
        const movable = colOrder.filter(k => !colDefs.find(c => c.key === k)?.nohide);
        const posInMovable = movable.indexOf(key);

        const li = document.createElement('li');
        li.className  = 'st-col-item';
        li.dataset.key = key;
        li.draggable   = true;
        li.innerHTML   = `
          <span class="st-col-drag" title="Arrastar">⠿</span>
          <label class="st-col-chk-label">
            <input type="checkbox" class="st-col-chk" data-key="${key}" ${colVisible.includes(key) ? 'checked' : ''}>
            <span>${col.label}</span>
          </label>
          <span class="st-col-move">
            <button class="st-col-up" data-key="${key}" ${posInMovable === 0 ? 'disabled' : ''}>↑</button>
            <button class="st-col-dn" data-key="${key}" ${posInMovable === movable.length-1 ? 'disabled' : ''}>↓</button>
          </span>`;
        list.appendChild(li);
      });
      panel.appendChild(list);

      list.querySelectorAll('.st-col-chk').forEach(chk => {
        chk.addEventListener('change', () => {
          if (chk.checked) { if (!colVisible.includes(chk.dataset.key)) colVisible.push(chk.dataset.key); }
          else colVisible = colVisible.filter(k => k !== chk.dataset.key);
          save(tableId, 'visible', colVisible);
          render(); buildColumnPanel();
        });
      });

      list.querySelectorAll('.st-col-up, .st-col-dn').forEach(btn => {
        btn.addEventListener('click', () => {
          const key = btn.dataset.key;
          const idx = colOrder.indexOf(key);
          const dir = btn.classList.contains('st-col-up') ? -1 : 1;
          const swp = idx + dir;
          if (swp < 0 || swp >= colOrder.length) return;
          [colOrder[idx], colOrder[swp]] = [colOrder[swp], colOrder[idx]];
          save(tableId, 'order', colOrder);
          render(); buildColumnPanel();
        });
      });

      initDrag(list);
    }

    /* ── 16. Drag-and-drop ───────────────────────────────────── */
    function initDrag(list) {
      let drag = null;
      list.querySelectorAll('.st-col-item').forEach(item => {
        item.addEventListener('dragstart', e => { drag = item; item.classList.add('st-dragging'); e.dataTransfer.effectAllowed = 'move'; });
        item.addEventListener('dragend',   () => {
          item.classList.remove('st-dragging');
          list.querySelectorAll('.st-col-item').forEach(i => i.classList.remove('st-drag-over'));
          drag = null;
          colOrder = Array.from(list.querySelectorAll('.st-col-item')).map(i => i.dataset.key);
          colDefs.filter(c => c.nohide).forEach(c => { if (!colOrder.includes(c.key)) colOrder.push(c.key); });
          save(tableId, 'order', colOrder);
          render(); buildColumnPanel();
        });
        item.addEventListener('dragover', e => {
          e.preventDefault();
          if (!drag || drag === item) return;
          list.querySelectorAll('.st-col-item').forEach(i => i.classList.remove('st-drag-over'));
          item.classList.add('st-drag-over');
          const mid = item.getBoundingClientRect().top + item.getBoundingClientRect().height / 2;
          list.insertBefore(drag, e.clientY < mid ? item : item.nextSibling);
        });
      });
    }

    /* ── 17. Botão config + reset ────────────────────────────── */
    // Procura dentro do wrapper OU no grupo externo [data-st-controls="tableId"]
    const ctrlRoot  = document.querySelector(`[data-st-controls="${tableId}"]`) || wrapper;
    const configBtn = ctrlRoot.querySelector('.st-config-btn');
    const colPanel  = ctrlRoot.querySelector('.st-col-panel') || wrapper.querySelector('.st-col-panel');

    // Sincroniza o contador externo se existir
    const extCount = document.querySelector(`[data-st-count="${tableId}"]`);
    if (extCount) {
      const origUpdate = updateResultCount;
      updateResultCount = function() {
        origUpdate();
        if (resultEl) extCount.textContent = resultEl.textContent;
        else {
          const vis = allRows.filter(r => r.style.display !== 'none').length;
          const has = Object.values(filterVals).some(v => v && v.trim());
          extCount.textContent = has
            ? vis + ' resultado' + (vis !== 1 ? 's' : '') + ' filtrado' + (vis !== 1 ? 's' : '')
            : (totalFromAttr || allRows.length) + ' resultado' + ((totalFromAttr || allRows.length) !== 1 ? 's' : '');
        }
      };
    }

    if (configBtn && colPanel) {
      configBtn.addEventListener('click', e => {
        e.stopPropagation();
        const open = colPanel.classList.toggle('st-panel-open');
        if (open) buildColumnPanel();
      });
      document.addEventListener('click', e => {
        if (!colPanel.contains(e.target) && e.target !== configBtn)
          colPanel.classList.remove('st-panel-open');
      });
    }

    const resetBtn = ctrlRoot.querySelector('.st-reset-btn');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        colOrder   = [...defaultOrder];
        colVisible = [...defaultVisible];
        sortState  = { col: null, dir: null };
        Object.keys(filterVals).forEach(k => { filterVals[k] = ''; });
        save(tableId, 'order',   colOrder);
        save(tableId, 'visible', colVisible);
        save(tableId, 'sort',    sortState);
        render();
        if (colPanel) buildColumnPanel();
      });
    }

    /* ── 18. Pesquisa global ─────────────────────────────────── */
    const globalSearch = wrapper.querySelector('.st-global-search');
    if (globalSearch) {
      globalSearch.addEventListener('input', () => {
        const q = globalSearch.value.toLowerCase();
        allRows.forEach(row => {
          if (!q) { row.style.display = ''; return; }
          row.style.display = Array.from(row.cells).map(td => cellText(td)).join(' ').toLowerCase().includes(q) ? '' : 'none';
        });
        updateResultCount();
      });
    }

    /* ── 19. Arranque ────────────────────────────────────────── */
    render();
    updateResultCount();
    if (colPanel) buildColumnPanel();
  }

  function initAll() { document.querySelectorAll('[data-smart-table]').forEach(init); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initAll);
  else initAll();
  window.SmartTable = { init, initAll };
})();
