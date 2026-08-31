const CARDS_BASE = '../cards/';
const IS_READONLY = window.location.hostname.endsWith('github.io');
let allCards = [];
let allStyles = {};
let selectedCard = null;

// --- Load cards from YAML via manifest ---
async function loadCards() {
  const cacheBust = '?t=' + Date.now();
  const manifestResp = await fetch(CARDS_BASE + 'manifest.yaml' + cacheBust);
  const manifestText = await manifestResp.text();
  const manifest = jsyaml.load(manifestText);

  const filePromises = manifest.files.map(async (file) => {
    const resp = await fetch(CARDS_BASE + file + cacheBust);
    const text = await resp.text();
    const cards = jsyaml.load(text);
    // Tag each card with its source file for reference
    return cards.map(card => ({ ...card, _source: file }));
  });

  const results = await Promise.all(filePromises);
  allCards = results.flat();

  // Assign stable IDs
  allCards.forEach((card, i) => { card._id = i; });

  // Load art styles
  try {
    const stylesResp = await fetch('../art.yaml' + cacheBust);
    const stylesText = await stylesResp.text();
    const styles = jsyaml.load(stylesText);
    if (Array.isArray(styles)) {
      styles.forEach(s => { allStyles[s.id] = s.name; });
    }
  } catch (e) { /* art.yaml is optional */ }

  document.getElementById('stats').textContent =
    `${allCards.length} cards loaded`;
}

// --- Filtering ---
function getActiveFilters() {
  const colors = new Set();
  document.querySelectorAll('#color-filters .active').forEach(btn => {
    colors.add(btn.dataset.color);
  });

  const types = new Set();
  document.querySelectorAll('#type-filters .active').forEach(btn => {
    types.add(btn.dataset.type);
  });

  const rarities = new Set();
  document.querySelectorAll('#rarity-filters .active').forEach(btn => {
    rarities.add(btn.dataset.rarity);
  });

  const cmcs = new Set();
  document.querySelectorAll('#cmc-filters .active').forEach(btn => {
    cmcs.add(btn.dataset.cmc);
  });

  const search = document.getElementById('search').value.toLowerCase().trim();

  return { colors, types, rarities, cmcs, search };
}

function cardMatchesFilters(card, filters) {
  // Color filter
  const cardColor = card.color || 'colorless';
  if (!filters.colors.has(cardColor)) return false;

  // Type filter — extract the primary type from type_line
  const primaryType = getPrimaryType(card.type_line);
  if (!filters.types.has(primaryType)) return false;

  // CMC filter
  const cmc = getConvertedManaCost(card.cost);
  const cmcKey = cmc >= 6 ? '6+' : String(cmc);
  if (!filters.cmcs.has(cmcKey)) return false;

  // Rarity filter
  if (!filters.rarities.has(card.rarity)) return false;

  // Search
  if (filters.search) {
    const haystack = [
      card.name,
      card.name_ru || '',
      card.name_en || '',
      card.type_line,
      card.text || '',
      card.flavor_text || '',
      card.notes || ''
    ].join(' ').toLowerCase();
    if (!haystack.includes(filters.search)) return false;
  }

  return true;
}

function getPrimaryType(typeLine) {
  const tl = typeLine.toLowerCase();
  // Check in order of specificity
  if (tl.includes('land')) return 'Land';
  if (tl.includes('creature')) return 'Creature';
  if (tl.includes('instant')) return 'Instant';
  if (tl.includes('sorcery')) return 'Sorcery';
  if (tl.includes('enchantment')) return 'Enchantment';
  if (tl.includes('artifact')) return 'Artifact';
  return 'Other';
}

// --- Rendering ---
function renderList() {
  const filters = getActiveFilters();
  const filtered = allCards.filter(c => cardMatchesFilters(c, filters));

  const listEl = document.getElementById('card-list');
  const countEl = document.getElementById('card-count');

  const pos = selectedCard ? filtered.findIndex(c => c._id === selectedCard._id) : -1;
  countEl.textContent = pos >= 0
    ? `#${pos + 1} of ${filtered.length} cards`
    : `${filtered.length} cards`;

  listEl.innerHTML = filtered.map(card => {
    const isSelected = selectedCard && selectedCard._id === card._id;
    return `
      <div class="card-item ${isSelected ? 'selected' : ''}"
           data-id="${card._id}"
           onclick="selectCard(${card._id})">
        <div class="color-pip" style="background:${getColorHex(card.color)}"></div>
        <div class="card-info">
          <div class="card-name">${escapeHtml(getCardName(card))}</div>
          <div class="card-meta">${escapeHtml(card.type_line)}</div>
        </div>
        <div class="card-cost">${formatManaCost(card.cost)}</div>
      </div>
    `;
  }).join('');
}

function selectCard(id) {
  selectedCard = allCards.find(c => c._id === id);
  document.getElementById('card-list').classList.remove('open');
  renderList();
  renderDetail();
  saveStateToHash();
}

function toggleCardList() {
  document.getElementById('card-list').classList.toggle('open');
}

function renderDetail() {
  const el = document.getElementById('card-detail');
  if (!selectedCard) {
    el.innerHTML = '<p class="placeholder-text">Select a card from the list</p>';
    return;
  }

  const card = selectedCard;
  const colorClass = 'color-' + (card.color || 'colorless');
  const hasPT = card.power !== undefined && card.toughness !== undefined;
  const artSymbol = getArtSymbol(card);

  const cardColumnHtml = card.dfc && card.back_face
    ? `<div class="dfc-pair">
        ${renderCardFace(card, colorClass, { rarity: true })}
        ${renderCardFace(card.back_face, colorClass, { rarity: false })}
      </div>`
    : renderCardFace(card, colorClass, { rarity: true });

  el.innerHTML = `
    ${IS_MOBILE() ? `<button id="mobile-back" onclick="mobileBack()">‹ Back</button>` : ''}
    <div class="card-column">
      ${cardColumnHtml}
    </div>

    ${IS_READONLY ? '' : `
    <div class="edit-column">
      <div class="edit-section">
        <div class="edit-header">
          <h3>Edit Card</h3>
          <span class="card-source"><code>${escapeHtml(card._source)}</code></span>
        </div>
        <div class="edit-form" id="edit-form">
          ${editField('name', 'Translit', card.name)}
          ${editField('name_ru', 'Кириллица', card.name_ru || '')}
          ${editField('name_en', 'English', card.name_en || '')}
          ${editField('cost', 'Cost', card.cost)}
          ${editField('type_line', 'Type', card.type_line)}
          <div class="edit-row-pair">
            ${editField('power', 'P', card.power ?? '', 'short')}
            ${editField('toughness', 'T', card.toughness ?? '', 'short')}
          </div>
          ${editField('text', 'Rules Text', card.text || '', 'textarea')}
          ${editField('flavor_text', 'Flavor', card.flavor_text || '', 'textarea')}
          ${editField('notes', 'Design Notes', card.notes || '', 'textarea')}
          <div class="edit-row-pair">
            ${editSelect('art_style', 'Art Style', card.art_style ?? '')}
            ${editField('art_file', 'Art File', card.art_file || '')}
          </div>
          ${editField('art_prompt', 'Art Prompt', card.art_prompt || '', 'textarea')}
          <div class="edit-actions">
            <button class="btn btn-save" onclick="saveCard()">Save</button>
            <button class="btn btn-generate" onclick="generateArt()">Generate Art</button>
          </div>
          <div id="save-status"></div>
          <div id="gen-status"></div>
          ${card.dfc && card.back_face ? `
          <div class="edit-subheader">Back Face</div>
          ${editField('back_face.name', 'Translit', card.back_face.name || '')}
          ${editField('back_face.name_ru', 'Кириллица', card.back_face.name_ru || '')}
          ${editField('back_face.name_en', 'English', card.back_face.name_en || '')}
          <div class="edit-row-pair">
            ${editSelect('back_face.art_style', 'Art Style', card.back_face.art_style ?? '')}
            ${editField('back_face.art_file', 'Art File', card.back_face.art_file || '')}
          </div>
          ${editField('back_face.art_prompt', 'Art Prompt', card.back_face.art_prompt || '', 'textarea')}
          <div class="edit-actions">
            <button class="btn btn-generate" onclick="generateArt(true)">Generate Back Art</button>
          </div>
          <div id="gen-status-back"></div>
          ` : ''}
        </div>

        <div id="previous-art"></div>
      </div>
    </div>
    `}
  `;

  if (!IS_READONLY) loadPreviousArt(card);

  // Auto-fit card text to the fixed-height text box (front and back face)
  el.querySelectorAll('.card-render').forEach(fitCardText);
}

// --- Edit helpers ---
function editField(key, label, value, type) {
  const id = `edit-${key}`;
  if (type === 'textarea') {
    return `<div class="edit-row">
      <label for="${id}">${label}</label>
      <textarea id="${id}" data-field="${key}" rows="3">${escapeHtml(String(value))}</textarea>
    </div>`;
  }
  const cls = type === 'short' ? 'edit-input-short' : '';
  return `<div class="edit-row ${type === 'short' ? 'edit-row-short' : ''}">
    <label for="${id}">${label}</label>
    <input id="${id}" data-field="${key}" value="${escapeHtml(String(value))}" class="${cls}">
  </div>`;
}

function editSelect(key, label, value) {
  const id = `edit-${key}`;
  const options = Object.entries(allStyles)
    .map(([sid, name]) => `<option value="${sid}" ${String(sid) === String(value) ? 'selected' : ''}>${sid}: ${escapeHtml(name)}</option>`)
    .join('');
  return `<div class="edit-row edit-row-short">
    <label for="${id}">${label}</label>
    <select id="${id}" data-field="${key}">
      <option value="">—</option>
      ${options}
    </select>
  </div>`;
}

async function saveCard() {
  const form = document.getElementById('edit-form');
  const updates = {};
  form.querySelectorAll('input, textarea, select').forEach(el => {
    updates[el.dataset.field] = el.value;
  });

  const statusEl = document.getElementById('save-status');
  statusEl.textContent = 'Saving...';
  statusEl.className = 'status-msg';

  try {
    const resp = await fetch('/api/save-card', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        source: selectedCard._source,
        original_name: selectedCard.name,
        updates
      })
    });
    const result = await resp.json();
    if (result.ok) {
      statusEl.textContent = 'Saved!';
      statusEl.className = 'status-msg status-ok';
      // Update in-memory card
      Object.assign(selectedCard, result.card);
      renderList();
      setTimeout(() => { statusEl.textContent = ''; }, 2000);
    } else {
      statusEl.textContent = 'Error: ' + result.error;
      statusEl.className = 'status-msg status-err';
    }
  } catch (e) {
    statusEl.textContent = 'Error: ' + e.message;
    statusEl.className = 'status-msg status-err';
  }
}

async function generateArt(backFace = false) {
  // Save first so the latest prompt/style changes are persisted before generating
  await saveCard();
  const saveStatus = document.getElementById('save-status');
  if (saveStatus && saveStatus.classList.contains('status-err')) return;

  const statusEl = document.getElementById(backFace ? 'gen-status-back' : 'gen-status');
  statusEl.textContent = 'Starting generation...';
  statusEl.className = 'status-msg';

  try {
    const resp = await fetch('/api/generate-art', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        source: selectedCard._source,
        card_name: selectedCard.name,
        back_face: backFace
      })
    });
    const result = await resp.json();
    if (result.ok) {
      if (backFace) {
        if (!selectedCard.back_face) selectedCard.back_face = {};
        if (result.art_file) selectedCard.back_face.art_file = result.art_file;
      } else {
        if (result.art_file) selectedCard.art_file = result.art_file;
      }
      statusEl.textContent = 'Generating... (this takes ~30s)';
      pollGenStatus(result.art_file, statusEl);
    } else {
      statusEl.textContent = 'Error: ' + result.error;
      statusEl.className = 'status-msg status-err';
    }
  } catch (e) {
    statusEl.textContent = 'Error: ' + e.message;
    statusEl.className = 'status-msg status-err';
  }
}

function pollGenStatus(artFile, statusEl) {
  const poll = setInterval(async () => {
    try {
      const resp = await fetch(`/api/gen-status?file=${encodeURIComponent(artFile)}`);
      const status = await resp.json();
      if (status.status === 'done') {
        clearInterval(poll);
        statusEl.textContent = 'Done! Refreshing...';
        statusEl.className = 'status-msg status-ok';
        // Refresh the card art
        renderDetail();
        loadPreviousArt(selectedCard);
      } else if (status.status === 'error') {
        clearInterval(poll);
        statusEl.textContent = 'Error: ' + status.message;
        statusEl.className = 'status-msg status-err';
      } else if (status.status === 'queued') {
        statusEl.textContent = 'Queued — waiting for previous generation...';
      } else {
        statusEl.textContent = 'Generating... (this takes ~30s)';
      }
    } catch (e) { /* keep polling */ }
  }, 3000);
}

async function loadPreviousArt(card) {
  if (!card.art_file) return;
  const el = document.getElementById('previous-art');
  if (!el) return;

  try {
    const resp = await fetch(`/api/previous-art?file=${encodeURIComponent(card.art_file)}`);
    const versions = await resp.json();
    if (versions.length === 0) {
      el.innerHTML = '';
      return;
    }
    el.innerHTML = `
      <div class="prev-art-section">
        <h3>Previous Versions</h3>
        <div class="prev-art-grid">
          ${versions.map(v => `
            <div class="prev-art-item" onclick="restoreArt('${escapeHtml(v.filename)}')">
              <img src="/${v.path}?t=${Date.now()}" alt="${v.filename}">
              <span>${v.filename.replace(/.*_(\d{8}_\d{6})\.png/, '$1')}</span>
            </div>
          `).join('')}
        </div>
      </div>`;
  } catch (e) { /* ignore */ }
}

async function restoreArt(previousFile) {
  if (!selectedCard.art_file) return;
  if (!confirm(`Restore ${previousFile}?`)) return;

  try {
    const resp = await fetch('/api/restore-art', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        previous_file: previousFile,
        art_file: selectedCard.art_file
      })
    });
    const result = await resp.json();
    if (result.ok) {
      renderDetail();
    }
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

// --- Mobile helpers ---
const IS_MOBILE = () => window.innerWidth <= 700;

function toggleFilters() {
  const filters = document.getElementById('filters');
  const icon = document.getElementById('filter-toggle-icon');
  const open = filters.classList.toggle('open');
  icon.textContent = open ? '▲' : '▼';
}

// --- Language switch ---
function getCurrentLang() {
  return localStorage.getItem('cardLang') || 'translit';
}

function getCardName(face) {
  const lang = getCurrentLang();
  if (lang === 'ru') return face.name_ru || face.name;
  if (lang === 'en') return face.name_en || face.name;
  return face.name;
}

function switchLang(lang) {
  localStorage.setItem('cardLang', lang);
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === lang);
  });
  renderList();
  renderDetail();
}

// --- Helpers ---
function getColorHex(color) {
  const map = {
    white: '#f9faf4',
    blue: '#0e68ab',
    black: '#3d3229',
    red: '#d3202a',
    green: '#00733e',
    colorless: '#9ea2a5',
    multicolor: '#c9a44a'
  };
  return map[color] || '#888';
}

function getArtSymbol(card) {
  const tl = card.type_line.toLowerCase();
  if (tl.includes('land')) return '&#x26F0;';
  if (tl.includes('dragon')) return '&#x1F409;';
  if (tl.includes('cat')) return '&#x1F408;';
  if (tl.includes('bird') || tl.includes('swan') || tl.includes('raven')) return '&#x1F426;';
  if (tl.includes('wolf')) return '&#x1F43A;';
  if (tl.includes('bear')) return '&#x1F43B;';
  if (tl.includes('fox')) return '&#x1F98A;';
  if (tl.includes('rabbit')) return '&#x1F407;';
  if (tl.includes('fish')) return '&#x1F41F;';
  if (tl.includes('horse') || tl.includes('mount')) return '&#x1F40E;';
  if (tl.includes('treefolk')) return '&#x1F333;';
  if (tl.includes('spirit') || tl.includes('zombie')) return '&#x1F480;';
  if (tl.includes('demon')) return '&#x1F525;';
  if (tl.includes('equipment')) return '&#x2694;';
  if (tl.includes('artifact')) return '&#x2699;';
  if (tl.includes('ship')) return '&#x26F5;';
  if (tl.includes('enchantment')) return '&#x2728;';
  if (tl.includes('instant')) return '&#x26A1;';
  if (tl.includes('sorcery')) return '&#x1F320;';
  if (tl.includes('construct')) return '&#x2699;';
  if (tl.includes('human')) return '&#x1F9D1;';
  if (tl.includes('creature')) return '&#x1F9D1;';
  return '&#x2726;';
}

function getArtHtml(card, fallbackSymbol) {
  if (!card.art_file) {
    return `<div class="card-art-placeholder">${fallbackSymbol}</div>`;
  }
  const artUrl = '../art/' + card.art_file + '?t=' + Date.now();
  const idAttr = card._id !== undefined ? ` id="art-${card._id}"` : '';
  const errTarget = card._id !== undefined
    ? `document.getElementById('art-${card._id}').innerHTML='${fallbackSymbol}'`
    : `this.parentElement.innerHTML='${fallbackSymbol}'`;
  return `<div class="card-art-placeholder"${idAttr}>
    <img src="${artUrl}" alt="" class="card-art-img"
         onerror="this.remove(); ${errTarget}">
  </div>`;
}

function renderCardFace(face, colorClass, opts = {}) {
  const hasPT = face.power !== undefined && face.toughness !== undefined;
  const artSymbol = getArtSymbol(face);
  const costHtml = face.cost ? `<span class="card-cost-display">${formatManaCostHtml(face.cost)}</span>` : '';
  const footerLeft = opts.rarity ? `<span class="card-rarity">${face.rarity}</span>` : '<span></span>';
  const displayName = getCardName(face);
  return `
    <div class="card-render ${colorClass}">
      <div class="card-header">
        <span class="card-title">${escapeHtml(displayName)}</span>
        ${costHtml}
      </div>
      ${getArtHtml(face, artSymbol)}
      <div class="card-type-bar">${escapeHtml(face.type_line)}</div>
      <div class="card-text-box">
        ${face.text ? `<div class="card-rules">${formatRulesText(face.text, displayName)}</div>` : ''}
        ${face.flavor_text ? `<div class="card-flavor">${escapeHtml(face.flavor_text.replace(/<this>/g, displayName))}</div>` : ''}
      </div>
      <div class="card-footer">
        ${footerLeft}
        ${hasPT ? `<span class="card-pt">${face.power}/${face.toughness}</span>` : ''}
      </div>
    </div>`;
}

function fitCardText(cardEl) {
  const box = cardEl.querySelector('.card-text-box');
  if (!box) return;
  const rules = box.querySelector('.card-rules');
  const flavor = box.querySelector('.card-flavor');
  if (!rules) return;

  const maxSize = 13;
  const minSize = 7;
  let size = maxSize;
  rules.style.fontSize = size + 'px';
  if (flavor) flavor.style.fontSize = (size - 1) + 'px';

  while (box.scrollHeight > box.clientHeight && size > minSize) {
    size -= 0.5;
    rules.style.fontSize = size + 'px';
    if (flavor) flavor.style.fontSize = Math.max(size - 1, minSize) + 'px';
  }
}

function getConvertedManaCost(cost) {
  if (!cost) return 0;
  const symbols = cost.match(/\{[^}]+\}/g) || [];
  let total = 0;
  for (const sym of symbols) {
    const s = sym.replace(/[{}]/g, '');
    const n = parseInt(s, 10);
    if (!isNaN(n)) {
      total += n;
    } else {
      // Each colored or special symbol counts as 1
      total += 1;
    }
  }
  return total;
}

function formatManaCost(cost) {
  if (!cost) return '';
  return cost.replace(/\{|\}/g, '');
}

function formatManaCostHtml(cost) {
  if (!cost) return '';
  const symbols = cost.match(/\{[^}]+\}/g) || [];
  return symbols.map(sym => {
    const s = sym.replace(/[{}]/g, '');
    let cls = 'mana ';
    if ('WUBRGC'.includes(s)) {
      cls += 'mana-' + s;
    } else {
      cls += 'mana-num';
    }
    return `<span class="${cls}">${s}</span>`;
  }).join('');
}

function formatRulesText(text, thisName = null) {
  const t = thisName ? text.replace(/<this>/g, thisName) : text;
  return escapeHtml(t).replace(/\{([^}]+)\}/g, (_, s) => {
    let cls = 'mana ';
    if ('WUBRGC'.includes(s)) {
      cls += 'mana-' + s;
    } else if (s === 'T') {
      return '<span class="mana mana-num">T</span>';
    } else {
      cls += 'mana-num';
    }
    return `<span class="${cls}">${s}</span>`;
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// --- Event listeners ---
document.querySelectorAll('.filter-buttons button').forEach(btn => {
  btn.addEventListener('click', (e) => {
    const group = btn.closest('.filter-buttons');
    const siblings = group.querySelectorAll('button');
    if (e.metaKey || e.ctrlKey) {
      // Cmd/Ctrl+click: toggle this one button
      btn.classList.toggle('active');
    } else {
      const activeButtons = Array.from(siblings).filter(b => b.classList.contains('active'));
      const onlyThisActive = activeButtons.length === 1 && btn.classList.contains('active');
      if (onlyThisActive) {
        // Clicking the sole active button: reset — select all
        siblings.forEach(b => b.classList.add('active'));
      } else {
        // Otherwise: exclusive select this one
        siblings.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
      }
    }
    renderList();
    saveStateToHash();
  });
});

document.getElementById('search').removeEventListener('input', renderList);
document.getElementById('search').addEventListener('input', () => {
  renderList();
  saveStateToHash();
});

// Keyboard navigation
document.addEventListener('keydown', (e) => {
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;

  const filters = getActiveFilters();
  const filtered = allCards.filter(c => cardMatchesFilters(c, filters));
  if (filtered.length === 0) return;

  const currentIdx = selectedCard
    ? filtered.findIndex(c => c._id === selectedCard._id)
    : -1;

  if (e.key === 'ArrowDown' || e.key === 'j') {
    e.preventDefault();
    const next = Math.min(currentIdx + 1, filtered.length - 1);
    selectCard(filtered[next]._id);
    scrollToSelected();
  } else if (e.key === 'ArrowUp' || e.key === 'k') {
    e.preventDefault();
    const prev = Math.max(currentIdx - 1, 0);
    selectCard(filtered[prev]._id);
    scrollToSelected();
  }
});

function mobileBack() {
  selectedCard = null;
  renderList();
  renderDetail();
  document.getElementById('sidebar').scrollIntoView({ behavior: 'smooth' });
}

function scrollToSelected() {
  const el = document.querySelector('.card-item.selected');
  if (el) el.scrollIntoView({ block: 'nearest' });
}

// --- URL hash state ---
function saveStateToHash() {
  const state = {};

  // Only save filters that differ from "all active" (to keep URLs short)
  const filterGroups = [
    { id: 'color-filters', key: 'c', attr: 'color' },
    { id: 'type-filters', key: 't', attr: 'type' },
    { id: 'rarity-filters', key: 'r', attr: 'rarity' },
    { id: 'cmc-filters', key: 'm', attr: 'cmc' },
  ];

  for (const { id, key, attr } of filterGroups) {
    const all = document.querySelectorAll(`#${id} button`);
    const active = document.querySelectorAll(`#${id} .active`);
    if (active.length < all.length) {
      state[key] = Array.from(active).map(b => b.dataset[attr]).join(',');
    }
  }

  const search = document.getElementById('search').value.trim();
  if (search) state.q = search;

  if (selectedCard) state.card = selectedCard._id;

  const hash = Object.entries(state)
    .map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
    .join('&');

  history.replaceState(null, '', hash ? '#' + hash : window.location.pathname);
}

function restoreStateFromHash() {
  const hash = window.location.hash.slice(1);
  if (!hash) return;

  const params = {};
  for (const part of hash.split('&')) {
    const [k, v] = part.split('=');
    if (k && v !== undefined) params[k] = decodeURIComponent(v);
  }

  const filterGroups = [
    { id: 'color-filters', key: 'c', attr: 'color' },
    { id: 'type-filters', key: 't', attr: 'type' },
    { id: 'rarity-filters', key: 'r', attr: 'rarity' },
    { id: 'cmc-filters', key: 'm', attr: 'cmc' },
  ];

  for (const { id, key, attr } of filterGroups) {
    if (params[key] !== undefined) {
      const activeValues = new Set(params[key].split(','));
      document.querySelectorAll(`#${id} button`).forEach(btn => {
        btn.classList.toggle('active', activeValues.has(btn.dataset[attr]));
      });
    }
  }

  if (params.q) {
    document.getElementById('search').value = params.q;
  }

  if (params.card !== undefined) {
    const id = parseInt(params.card, 10);
    if (!isNaN(id)) {
      selectedCard = allCards.find(c => c._id === id) || null;
    }
  }
}

// --- Close card-list dropdown when tapping outside ---
document.addEventListener('click', e => {
  const list = document.getElementById('card-list');
  const count = document.getElementById('card-count');
  if (list.classList.contains('open') && !list.contains(e.target) && !count.contains(e.target)) {
    list.classList.remove('open');
  }
});

// --- Swipe navigation ---
(function setupSwipe() {
  let startX = 0, startY = 0;
  const detail = document.getElementById('detail');

  detail.addEventListener('touchstart', e => {
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
  }, { passive: true });

  detail.addEventListener('touchend', e => {
    if (!selectedCard) return;
    const dx = e.changedTouches[0].clientX - startX;
    const dy = e.changedTouches[0].clientY - startY;
    if (Math.abs(dx) < 50 || Math.abs(dx) < Math.abs(dy)) return;

    const filters = getActiveFilters();
    const filtered = allCards.filter(c => cardMatchesFilters(c, filters));
    const idx = filtered.findIndex(c => c._id === selectedCard._id);

    if (dx < 0 && idx < filtered.length - 1) {
      selectCard(filtered[idx + 1]._id);
      scrollToSelected();
    } else if (dx > 0 && idx > 0) {
      selectCard(filtered[idx - 1]._id);
      scrollToSelected();
    }
  }, { passive: true });
})();

// --- Init ---
loadCards().then(() => {
  // Restore sticky lang switch state
  const lang = getCurrentLang();
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === lang);
  });
  restoreStateFromHash();
  renderList();
  renderDetail();
  scrollToSelected();
});
