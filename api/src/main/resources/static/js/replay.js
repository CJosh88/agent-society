import { CONDITION_LABELS, HttpError, POPULATION_LABELS, el, getJson, label, pct, showError } from './common.js';

const STEP_MS = 120; // one agent per step at 1x
const COLS = 6, CARD_W = 96, CARD_H = 60, GAP = 8, BOARD_X = 12, BOARD_Y = 12;
const STRIP = { y: 306, perRow: 50, dx: 12, dy: 15, x: 24 };
const SERIOUS = 0xc53030, ROUTINE = 0x2f855a, PLAIN = 0xb8b2a2;
const MODEL_COLORS = [0x2b6cb0, 0xdd6b20, 0x805ad5, 0x0f9d9d];
const SCRIPTED_COLOR = 0x8a94a0;

const params = new URLSearchParams(location.search);
const runId = params.get('run');
const status = document.getElementById('status');
const root = document.getElementById('replay');

let run, agents, events, names, personaOf, N, tickets, ticketIds;
let byPos, spawnModel, shownAt, ratingsAt, cum, truth, modelColor;
let game, scene, cardViews = {}, discs = [], ring, posText;
let pos = 0, speed = 1, timer = null, ready = false, selected = null;

// ---- Data ------------------------------------------------------------------------------------

async function load() {
  status.textContent = 'Loading…';
  root.hidden = true;
  if (!runId) { status.textContent = 'Run not found: no run id in the address.'; return; }
  if (typeof Phaser === 'undefined') {
    showError(status, new Error('The replay engine (Phaser) could not be loaded from the CDN'), () => location.reload());
    return;
  }
  try {
    const enc = encodeURIComponent(runId);
    const [detail, evs, tix] = await Promise.all([
      getJson(`/api/runs/${enc}`), getJson(`/api/runs/${enc}/events`), getJson('tickets.json')]);
    run = detail.run; agents = detail.agents; events = evs; tickets = Object.fromEntries(tix.map((t) => [t.id, t.text]));
  } catch (err) {
    if (err instanceof HttpError && err.status === 404) { status.textContent = 'Run not found.'; return; }
    showError(status, err, load);
    return;
  }
  prepare();
  status.textContent = '';
  root.hidden = false;
  fillHeader();
  fillLegend();
  startGame();
}

/** Index the events once, so any position can be drawn exactly (scrubbing never replays animation). */
function prepare() {
  N = agents.length;
  ticketIds = Object.keys(tickets).sort();
  names = Object.fromEntries(agents.map((a) => [a.agentId, a.name]));
  personaOf = Object.fromEntries(agents.map((a) => [a.agentId, a]));
  byPos = Array.from({ length: N + 1 }, () => []);
  spawnModel = {};
  shownAt = {};
  ratingsAt = Array.from({ length: N + 1 }, () => []);
  truth = {};
  for (const e of events) {
    if (e.type === 'PROBE_ANSWERED' || e.type === 'RUN_ENDED') continue;
    byPos[e.tick].push(e);
    if (e.type === 'AGENT_SPAWNED') spawnModel[e.tick] = e.payload.model;
    if (e.type === 'TICKETS_SHOWN') shownAt[e.tick] = e.payload;
    if (e.type === 'AGENT_RATED') {
      ratingsAt[e.tick].push(e.payload);
      truth[e.payload.ticket_id] = (e.payload.priority === 'HIGH') === e.payload.correct; // true = serious
    }
  }
  cum = [Object.fromEntries(ticketIds.map((t) => [t, { high: 0, total: 0 }]))];
  for (let t = 1; t <= N; t++) {
    const next = Object.fromEntries(Object.entries(cum[t - 1]).map(([k, v]) => [k, { ...v }]));
    for (const r of ratingsAt[t]) { next[r.ticket_id].total += 1; next[r.ticket_id].high += r.priority === 'HIGH' ? 1 : 0; }
    cum.push(next);
  }
  const models = [...new Set(Object.values(spawnModel).filter((m) => m !== 'scripted'))];
  modelColor = (m) => (m === 'scripted' ? SCRIPTED_COLOR : MODEL_COLORS[models.indexOf(m) % MODEL_COLORS.length]);
  document.getElementById('slider').max = N;
}

const colorCss = (c) => `#${c.toString(16).padStart(6, '0')}`;

function fillHeader() {
  document.getElementById('title').textContent = `${label(POPULATION_LABELS, run.population)} · ${label(CONDITION_LABELS, run.condition)}`;
  document.getElementById('subtitle').textContent =
    `World ${run.worldSeed} · ${N} agents${run.pilot ? ' · pilot' : ''} · prompt ${run.promptVersion}`;
  updateSummary();
}

function updateSummary() {
  const s = document.getElementById('summary');
  const reveal = document.getElementById('reveal').checked;
  s.textContent = reveal
    ? `World accuracy ${run.accuracy == null ? 'unavailable' : pct(run.accuracy, 1)} (${run.ratedCount} ratings).`
    : 'World accuracy is hidden. Tick “Reveal truth” to see it and which tickets are serious.';
}

function fillLegend() {
  const models = [...new Set(Object.values(spawnModel))];
  document.getElementById('legend').replaceChildren(...models.map((m) => el('span', { class: 'key' },
    el('i', { style: `background:${colorCss(modelColor(m))}` }), m === 'scripted' ? 'scripted (wrong on purpose)' : m)));
}

// ---- Phaser scene ---------------------------------------------------------------------------

function startGame() {
  game?.destroy(true);
  document.getElementById('game').replaceChildren();
  game = new Phaser.Game({
    type: Phaser.AUTO, width: 640, height: 480, parent: 'game', backgroundColor: '#f4f1ea',
    scene: { create() { scene = this; build(); } },
  });
}

function build() {
  cardViews = {};
  discs = [];
  ticketIds.forEach((id, i) => {
    const x = BOARD_X + (i % COLS) * (CARD_W + GAP), y = BOARD_Y + Math.floor(i / COLS) * (CARD_H + GAP);
    const box = scene.add.rectangle(x, y, CARD_W, CARD_H, 0xffffff).setOrigin(0).setStrokeStyle(2, PLAIN)
      .setInteractive({ useHandCursor: true });
    box.on('pointerdown', () => select(id));
    const idText = scene.add.text(x + 6, y + 4, id, { fontSize: '13px', color: '#1f2933', fontStyle: 'bold' });
    const count = scene.add.text(x + CARD_W - 6, y + 5, '0 / 0', { fontSize: '11px', color: '#5f6c7b' }).setOrigin(1, 0);
    scene.add.rectangle(x + 6, y + CARD_H - 16, CARD_W - 12, 8, 0xe2e8f0).setOrigin(0);
    const bar = scene.add.rectangle(x + 6, y + CARD_H - 16, 0, 8, 0x2b6cb0).setOrigin(0);
    const share = scene.add.text(x + 6, y + 24, '', { fontSize: '11px', color: '#2b6cb0' });
    cardViews[id] = { box, count, bar, share };
  });
  scene.add.text(BOARD_X, STRIP.y - 20, 'Agents in order. Filled discs have acted.', { fontSize: '11px', color: '#4a5568' });
  for (let p = 1; p <= N; p++) {
    const i = p - 1;
    const d = scene.add.circle(STRIP.x + (i % STRIP.perRow) * STRIP.dx, STRIP.y + Math.floor(i / STRIP.perRow) * STRIP.dy,
      4.5, modelColor(spawnModel[p]));
    discs.push(d);
  }
  ring = scene.add.circle(0, 0, 8).setStrokeStyle(2, 0x1f2933).setVisible(false);
  posText = scene.add.text(BOARD_X, 400, '', { fontSize: '12px', color: '#1f2933' });
  ready = true;
  document.getElementById('play').disabled = false;
  document.getElementById('slider').disabled = false;
  jumpTo(0);
}

function drawBoard() {
  const reveal = document.getElementById('reveal').checked;
  const c = cum[pos];
  for (const id of ticketIds) {
    const v = cardViews[id], { high, total } = c[id];
    const s = total ? high / total : 0;
    v.bar.width = (CARD_W - 12) * s;
    v.count.setText(`${high} / ${total}`);
    v.share.setText(total ? `${Math.round(s * 100)}% HIGH` : '');
    const known = reveal && id in truth;
    const color = known ? (truth[id] ? SERIOUS : ROUTINE) : PLAIN;
    v.box.setStrokeStyle(id === selected ? 4 : 2, id === selected && !known ? 0x2b6cb0 : color);
  }
  discs.forEach((d, i) => d.setAlpha(i < pos ? 1 : 0.2));
  if (pos >= 1) {
    const i = pos - 1;
    ring.setPosition(discs[i].x, discs[i].y).setVisible(true);
  } else {
    ring.setVisible(false);
  }
  posText.setText(pos ? `Agent ${pos} of ${N}: ${names[`a${pos}`]}` : 'Nobody has acted yet.');
}

function select(id) {
  selected = id;
  document.getElementById('ticket-title').textContent = `Ticket ${id}`;
  document.getElementById('ticket-text').textContent = tickets[id];
  if (ready) drawBoard();
}

// ---- Panel, log and controls --------------------------------------------------------------------

function describe(e) {
  const p = e.payload;
  const reveal = document.getElementById('reveal').checked;
  switch (e.type) {
    case 'AGENT_SPAWNED': return `Takes position ${p.position} (${p.model}).`;
    case 'TICKETS_SHOWN': {
      const shown = p.counts == null ? 'no counts shown' : 'counts shown';
      return `Sees the list in this order, ${shown}: ${p.order.join(' ')}`;
    }
    case 'AGENT_PICKED': return `Picks ${p.ticket_ids.join(', ')}${p.scripted ? ' (scripted)' : ''}.`;
    case 'AGENT_RATED':
      return `Rates ${p.ticket_id} ${p.priority}${reveal ? (p.correct ? ' — correct' : ' — wrong') : ''}.`;
    case 'ACTION_PARSE_FAILED': return `A reply could not be used${p.truncated ? ' (cut off)' : ''}: “${p.raw_excerpt}”`;
    default: return e.type;
  }
}

function setPos(p) {
  pos = p;
  document.getElementById('slider').value = p;
  document.getElementById('pos-label').textContent = `Agent ${p} / ${N}`;
  const a = personaOf[`a${p}`];
  document.getElementById('agent-title').textContent = p ? `Agent ${p}: ${a.name}` : 'Agent';
  const card = document.getElementById('agent-card');
  if (!p) {
    card.replaceChildren('Press Play or drag the slider.');
  } else {
    const per = a.persona || {};
    card.replaceChildren(el('strong', {}, a.name),
      a.role === 'scripted' ? 'Scripted (always wrong)' : spawnModel[p],
      per.age ? el('div', {}, `${per.age}, ${per.occupation}`) : null,
      per.bio ? el('div', { class: 'muted' }, per.bio) : null);
  }
  document.getElementById('log-title').textContent = p ? `Agent ${p}` : 'This agent';
  document.getElementById('log').replaceChildren(...(byPos[p] ?? []).map((e) => el('li', {},
    describe(e), e.payload.thought ? el('span', { class: 'thought' }, `Thought: ${e.payload.thought}`) : null)));
  const probes = events.filter((e) => e.type === 'PROBE_ANSWERED');
  const box = document.getElementById('probe');
  box.hidden = !(probes.length && p >= N);
  if (!box.hidden) {
    box.replaceChildren(el('strong', {}, `Recognition probe, asked after the world (${probes.length} agents): `),
      el('em', {}, `${probes.filter((e) => e.payload.recognized).length} counted as recognised.`),
      el('ul', {}, probes.map((e) => el('li', {}, `${names[e.agentId]}: “${e.payload.text}”`))));
  }
  if (ready) drawBoard();
}

function jumpTo(p) { if (ready) setPos(p); }

function pause() {
  clearTimeout(timer);
  timer = null;
  document.getElementById('play').textContent = pos >= N ? 'Replay' : 'Play';
}

function step() {
  if (pos >= N) { pause(); return; }
  setPos(pos + 1);
  timer = setTimeout(step, STEP_MS / speed);
}

function play() {
  if (pos >= N) jumpTo(0);
  document.getElementById('play').textContent = 'Pause';
  timer = setTimeout(step, 200 / speed);
}

document.getElementById('play').addEventListener('click', () => (timer ? pause() : play()));
document.getElementById('slider').addEventListener('input', (e) => { pause(); jumpTo(Number(e.target.value)); });
document.getElementById('thoughts').addEventListener('change', (e) => {
  document.getElementById('log').classList.toggle('hide-thoughts', !e.target.checked);
});
document.getElementById('reveal').addEventListener('change', () => { updateSummary(); if (ready) setPos(pos); });
document.querySelectorAll('.speed').forEach((b) => b.addEventListener('click', () => {
  speed = Number(b.dataset.speed);
  document.querySelectorAll('.speed').forEach((x) => x.classList.toggle('active', x === b));
}));

load();
