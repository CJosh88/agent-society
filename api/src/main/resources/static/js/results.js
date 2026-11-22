import { CONDITION_LABELS, OUTCOME_TEXT, SCENARIO_LABELS, el, getJson, label, showError } from './common.js';

// The GitHub repository. If this is emptied, the repo and write-up links are left out.
const REPO_URL = 'https://github.com/CJosh88/agent-society';
const WRITEUP_URL = REPO_URL && `${REPO_URL}/blob/main/docs/writeup.md`;

const pct = (x) => `${Math.round(x * 100)}%`;
const rate = (r, lo, hi) => `${pct(r)} (${Math.round(lo * 100)}–${Math.round(hi * 100)})`;
const pp = (x) => `${x < 0 ? '−' : '+'}${Math.abs(Math.round(x * 100))}`;
const diffText = (d) => `${pp(d.diff)} pp (${pp(d.ciLow)} to ${pp(d.ciHigh)})`;
const comparisonText = (c) => c.split('-').map((x) => label(CONDITION_LABELS, x)).join(' − ');

const replayLink = (id, text = 'Replay') => el('a', { href: `replay.html?run=${encodeURIComponent(id)}` }, text);

// ---- Featured runs ----------------------------------------------------------------------------

async function loadFeatured() {
  const body = document.getElementById('featured-body');
  try {
    const runs = await getJson('/api/runs/featured');
    if (!runs.length) {
      body.replaceChildren(el('p', { class: 'muted' }, 'No featured runs have been picked yet.'));
      return;
    }
    body.replaceChildren(...runs.map((r) => el('article', { class: 'card' },
      el('h3', {}, label(SCENARIO_LABELS, r.scenario)),
      el('p', {}, `${label(CONDITION_LABELS, r.condition)} · ${r.model}`),
      el('p', {}, r.focalHelped ? OUTCOME_TEXT[r.scenario].yes(r.focalHelpTick) : OUTCOME_TEXT[r.scenario].no),
      replayLink(r.id, 'Watch the replay'))));
  } catch (err) {
    showError(body, err, loadFeatured);
  }
}

// ---- Results ----------------------------------------------------------------------------------

function resultsTable(sc) {
  const head = ['Model', 'Condition', 'n', OUTCOME_TEXT[sc.scenario].column, 'Within 2 ticks of onset', 'Median outcome tick',
    'Parse failures', 'Truncations', 'Recognised'];
  const dash = (v, f) => (v == null ? '–' : f(v));
  const body = [];
  const models = [...new Set(sc.rows.map((r) => r.model))];
  for (const model of models) {
    for (const r of sc.rows.filter((x) => x.model === model)) {
      body.push(el('tr', {},
        el('td', { class: 'left' }, r.model), el('td', { class: 'left' }, label(CONDITION_LABELS, r.condition)),
        el('td', {}, r.n), el('td', {}, rate(r.rate, r.ciLow, r.ciHigh)), el('td', {}, pct(r.earlyRate)),
        el('td', {}, dash(r.medianHelpTick, (v) => v)), el('td', {}, pct(r.parseFailureRate)),
        el('td', {}, pct(r.truncationRate)), el('td', {}, dash(r.recognitionRate, pct))));
    }
    const diffs = sc.differences.filter((d) => d.model === model);
    if (diffs.length) {
      body.push(el('tr', { class: 'diff' },
        el('th', { class: 'left', colspan: 2, scope: 'row' }, `${model}: differences`),
        el('td', { class: 'left', colspan: head.length - 2 },
          diffs.map((d) => `${comparisonText(d.comparison)}: ${diffText(d)}`).join('  ·  '))));
    }
  }
  return el('div', { class: 'table-wrap' }, el('table', {},
    el('caption', { class: 'left note' }, 'Outcome rate by tick 12. Differences are in percentage points.'),
    el('thead', {}, el('tr', {}, head.map((h) => el('th', { scope: 'col' }, h)))),
    el('tbody', {}, body)));
}

async function loadResults() {
  const body = document.getElementById('results-body');
  try {
    const data = await getJson('/api/results');
    body.replaceChildren(...data.scenarios.flatMap((sc) => [
      el('h3', {}, label(SCENARIO_LABELS, sc.scenario)),
      ...(sc.rows.length ? [] : [el('p', { class: 'muted' }, 'No study runs yet.')]),
      ...(sc.rows.length ? [resultsTable(sc)] : []),
    ]), el('p', { class: 'note' },
      'Rates carry 95% Wilson intervals and differences 95% Newcombe intervals. Models are compared with themselves, never pooled.'));
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

// ---- Runs list --------------------------------------------------------------------------------

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
      body.replaceChildren(el('p', { class: 'muted' }, 'No runs match.'));
      pager.replaceChildren();
      return;
    }
    body.replaceChildren(el('table', {},
      el('thead', {}, el('tr', {}, ['Scenario', 'Condition', 'Model', 'Seed', 'Outcome', ''].map((h) => el('th', { scope: 'col' }, h)))),
      el('tbody', {}, data.content.map((r) => el('tr', {},
        el('td', { class: 'left' }, label(SCENARIO_LABELS, r.scenario)),
        el('td', { class: 'left' }, label(CONDITION_LABELS, r.condition)),
        el('td', { class: 'left' }, r.model + (r.pilot ? ' (pilot)' : '')),
        el('td', {}, r.seed),
        el('td', { class: 'left' }, r.focalHelped ? `outcome at tick ${r.focalHelpTick}` : 'no outcome'),
        el('td', {}, replayLink(r.id)))))));
    const { number, totalPages, totalElements } = data.page;
    pager.replaceChildren(
      el('button', { type: 'button', disabled: number === 0, onclick: () => { page = number - 1; loadRuns(); } }, 'Previous'),
      el('span', {}, `Page ${number + 1} of ${totalPages} · ${totalElements} runs`),
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
