import { CONDITION_LABELS, POPULATION_LABELS, el, getJson, label, pct, showError } from './common.js';

// The GitHub repository. If this is emptied, the repo and write-up links are left out.
const REPO_URL = 'https://github.com/CJosh88/agent-society';
const WRITEUP_URL = REPO_URL && `${REPO_URL}/blob/main/docs/writeup.md`;

const SVG = 'http://www.w3.org/2000/svg';
const pp = (x) => `${x < 0 ? '−' : '+'}${Math.abs(x * 100).toFixed(1)}`;
const diffText = (d) => `${pp(d.diff)} pp (${pp(d.ciLow)} to ${pp(d.ciHigh)})`;
const comparisonText = (c) => c.split('-').map((x) => label(CONDITION_LABELS, x)).join(' − ');
const replayLink = (id, text = 'Replay') => el('a', { href: `replay.html?run=${encodeURIComponent(id)}` }, text);
const accuracyText = (a) => (a == null ? 'no ratings' : pct(a, 1));

// ---- Experiment tabs --------------------------------------------------------------------------
// One panel per experiment. The selected tab lives in the URL hash, so a link can point at a tab.

const tabButtons = [...document.querySelectorAll('[role="tab"]')];

function selectTab(name, focus = false) {
  const active = tabButtons.find((b) => b.dataset.tab === name) ?? tabButtons[0];
  for (const b of tabButtons) {
    const on = b === active;
    b.setAttribute('aria-selected', String(on));
    b.tabIndex = on ? 0 : -1;
    document.getElementById(b.getAttribute('aria-controls')).hidden = !on;
  }
  if (focus) active.focus();
}

for (const b of tabButtons) {
  b.addEventListener('click', () => { location.hash = b.dataset.tab; });
  b.addEventListener('keydown', (e) => {
    const step = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
    if (!step) return;
    e.preventDefault();
    const next = tabButtons[(tabButtons.indexOf(b) + step + tabButtons.length) % tabButtons.length];
    location.hash = next.dataset.tab;
    next.focus();
  });
}
window.addEventListener('hashchange', () => selectTab(location.hash.slice(1)));
selectTab(location.hash.slice(1));

// ---- Featured worlds --------------------------------------------------------------------------

async function loadFeatured() {
  const body = document.getElementById('featured-body');
  try {
    const runs = await getJson('/api/runs/featured');
    if (!runs.length) {
      body.replaceChildren(el('p', { class: 'muted' }, 'No featured worlds have been picked yet.'));
      return;
    }
    body.replaceChildren(...runs.map((r) => el('article', { class: 'card' },
      el('h3', {}, label(POPULATION_LABELS, r.population)),
      el('p', {}, `${label(CONDITION_LABELS, r.condition)} · world ${r.worldSeed}`),
      el('p', {}, `World accuracy ${accuracyText(r.accuracy)}`),
      replayLink(r.id, 'Watch the replay'))));
  } catch (err) {
    showError(body, err, loadFeatured);
  }
}

// ---- Results ----------------------------------------------------------------------------------

/** A plain SVG bar chart: one bar per condition, a whisker for the 95% interval, the axis from 0 to 100%. */
function chart(rows) {
  const W = 520, H = 190, L = 40, B = 34, T = 10, gap = 18;
  const bw = (W - L - 10 - gap * (rows.length - 1)) / rows.length;
  const y = (v) => T + (H - T - B) * (1 - v);
  const svg = document.createElementNS(SVG, 'svg');
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.setAttribute('class', 'chart');
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', 'Mean world accuracy by condition, with 95% intervals. The table below has the same numbers.');
  const add = (tag, attrs, text) => {
    const n = document.createElementNS(SVG, tag);
    Object.entries(attrs).forEach(([k, v]) => n.setAttribute(k, v));
    if (text != null) n.textContent = text;
    svg.append(n);
  };
  for (const v of [0, 0.5, 1]) {
    add('line', { x1: L, x2: W - 10, y1: y(v), y2: y(v), class: 'grid' });
    add('text', { x: L - 6, y: y(v) + 4, 'text-anchor': 'end', class: 'tick' }, `${v * 100}%`);
  }
  rows.forEach((r, i) => {
    const x = L + i * (bw + gap);
    const mid = x + bw / 2;
    add('rect', { x, y: y(r.meanAccuracy), width: bw, height: y(0) - y(r.meanAccuracy), class: `bar c-${r.condition}` });
    add('line', { x1: mid, x2: mid, y1: y(r.ciLow), y2: y(r.ciHigh), class: 'whisker' });
    add('line', { x1: mid - 5, x2: mid + 5, y1: y(r.ciLow), y2: y(r.ciLow), class: 'whisker' });
    add('line', { x1: mid - 5, x2: mid + 5, y1: y(r.ciHigh), y2: y(r.ciHigh), class: 'whisker' });
    add('text', { x: mid, y: H - 18, 'text-anchor': 'middle', class: 'tick' }, r.condition.replace('_', ' '));
    add('text', { x: mid, y: H - 5, 'text-anchor': 'middle', class: 'tick' }, pct(r.meanAccuracy));
  });
  return svg;
}

function populationBlock(p) {
  if (!p.rows.length) return [el('h3', {}, label(POPULATION_LABELS, p.population)), el('p', { class: 'muted' }, 'No study worlds yet.')];
  const head = ['Condition', 'Worlds', 'Mean accuracy (95% CI)', 'Parse failures', 'Truncations', 'Recognised'];
  const body = p.rows.map((r) => el('tr', {},
    el('td', { class: 'left' }, label(CONDITION_LABELS, r.condition)), el('td', {}, r.n),
    el('td', {}, `${pct(r.meanAccuracy, 1)} (${pct(r.ciLow, 1)} – ${pct(r.ciHigh, 1)})`),
    el('td', {}, pct(r.parseFailureRate, 1)), el('td', {}, pct(r.truncationRate, 1)),
    el('td', {}, r.recognitionRate == null ? '–' : pct(r.recognitionRate))));
  if (p.differences.length) {
    body.push(el('tr', { class: 'diff' }, el('th', { class: 'left', scope: 'row' }, 'Differences'),
      el('td', { class: 'left wrap', colspan: head.length - 1 },
        p.differences.map((d) => `${comparisonText(d.comparison)}: ${diffText(d)}`).join('  ·  '))));
  }
  return [el('h3', {}, label(POPULATION_LABELS, p.population)), chart(p.rows),
    el('div', { class: 'table-wrap' }, el('table', {},
      el('caption', { class: 'left note' }, 'World accuracy is the share of all ratings that match the truth. Differences are in percentage points.'),
      el('thead', {}, el('tr', {}, head.map((h) => el('th', { scope: 'col' }, h)))),
      el('tbody', {}, body)))];
}

async function loadResults() {
  const body = document.getElementById('results-body');
  try {
    const data = await getJson('/api/results');
    body.replaceChildren(...data.populations.flatMap(populationBlock), el('p', { class: 'note' },
      'Intervals are 95% bootstrap intervals over worlds. Populations are compared with themselves, never pooled.'));
    renderAboutLinks(data.traceLinks ?? []);
  } catch (err) {
    showError(body, err, loadResults);
  }
}

function renderAboutLinks(traceLinks) {
  const parts = [];
  if (WRITEUP_URL) parts.push(el('a', { href: WRITEUP_URL }, 'Write-up'));
  if (REPO_URL) parts.push(el('a', { href: REPO_URL }, 'Repository'));
  traceLinks.forEach((href, i) => parts.push(el('a', { href, rel: 'noopener' }, `LangSmith trace ${i + 1}`)));
  const target = document.getElementById('about-links');
  target.replaceChildren(...parts.flatMap((p, i) => (i ? [' · ', p] : [p])));
}

// ---- Worlds list ------------------------------------------------------------------------------

const form = document.getElementById('run-filters');
let page = 0;

async function loadRuns() {
  const body = document.getElementById('runs-body');
  const pager = document.getElementById('pager');
  const params = new URLSearchParams({ page, size: 20 });
  for (const [k, v] of new FormData(form)) if (v) params.set(k, v);
  try {
    const data = await getJson(`/api/runs?${params}`);
    if (!data.content.length) {
      body.replaceChildren(el('p', { class: 'muted' }, 'No worlds match.'));
      pager.replaceChildren();
      return;
    }
    body.replaceChildren(el('table', {},
      el('thead', {}, el('tr', {}, ['Population', 'Condition', 'World seed', 'Accuracy', ''].map((h) => el('th', { scope: 'col' }, h)))),
      el('tbody', {}, data.content.map((r) => el('tr', {},
        el('td', { class: 'left' }, label(POPULATION_LABELS, r.population) + (r.pilot ? ' (pilot)' : '')),
        el('td', { class: 'left' }, label(CONDITION_LABELS, r.condition)),
        el('td', {}, r.worldSeed), el('td', {}, accuracyText(r.accuracy)), el('td', {}, replayLink(r.id)))))));
    const { number, totalPages, totalElements } = data.page;
    pager.replaceChildren(
      el('button', { type: 'button', disabled: number === 0, onclick: () => { page = number - 1; loadRuns(); } }, 'Previous'),
      el('span', {}, `Page ${number + 1} of ${totalPages} · ${totalElements} worlds`),
      el('button', { type: 'button', disabled: number + 1 >= totalPages, onclick: () => { page = number + 1; loadRuns(); } }, 'Next'));
  } catch (err) {
    showError(body, err, loadRuns);
  }
}

form.addEventListener('change', () => { page = 0; loadRuns(); });
form.addEventListener('submit', (e) => e.preventDefault());

loadFeatured();
loadResults();
loadRuns();
