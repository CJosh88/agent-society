import { CONDITION_LABELS, HttpError, OUTCOME_TEXT, SCENARIO_LABELS, el, getJson, label, showError } from './common.js';

const TILE = 32;
const TICK_MS = 1500;
const BUBBLE_MS = 1200;
const MAX_TICK = 12;
const COLORS = { focal: 0x2b6cb0, helped: 0x2f855a, scripted: 0x8a94a0 };

// Where each person sits, by the `seat` number in their AGENT_SPAWNED event (pixels).
const SEATS = {
  alert_fatigue: [[320, 400]],
  triage_herding: [[320, 400], [96, 272], [232, 272], [408, 272], [544, 272]],
};
const TIMELINE = { x0: 60, x1: 580, y: 458 };

const params = new URLSearchParams(location.search);
const runId = params.get('run');
const status = document.getElementById('status');
const root = document.getElementById('replay');

let run, agents, events, names, byTick, seatOf;
let game, scene, sprites, bubbles = [], cards = [], chatBubbles = {}, priorityText, timeline;
let tick = 0, speed = 1, timer = null, ready = false;

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
    const detail = await getJson(`/api/runs/${encodeURIComponent(runId)}`);
    events = await getJson(`/api/runs/${encodeURIComponent(runId)}/events`);
    run = detail.run;
    agents = detail.agents;
  } catch (err) {
    if (err instanceof HttpError && err.status === 404) { status.textContent = 'Run not found.'; return; }
    showError(status, err, load);
    return;
  }
  names = Object.fromEntries(agents.map((a) => [a.agentId, a.name]));
  seatOf = Object.fromEntries(events.filter((e) => e.type === 'AGENT_SPAWNED').map((e) => [e.agentId, e.payload.seat]));
  byTick = Array.from({ length: MAX_TICK + 1 }, (_, t) => events.filter((e) => e.tick === t));
  status.textContent = '';
  root.hidden = false;
  fillHeader();
  fillPeople();
  startGame();
}

function fillHeader() {
  document.getElementById('title').textContent =
    `${label(SCENARIO_LABELS, run.scenario)} · ${label(CONDITION_LABELS, run.condition)}`;
  document.getElementById('subtitle').textContent = `${run.model} · seed ${run.seed}${run.pilot ? ' · pilot' : ''}`;
  const s = document.getElementById('summary');
  const o = OUTCOME_TEXT[run.scenario];
  s.textContent = run.focalHelped ? o.yes(run.focalHelpTick) : o.no;
  s.className = `summary ${run.focalHelped ? 'helped' : 'not-helped'}`;
}

function fillPeople() {
  const roleText = { focal: 'Focal agent', scripted: 'Colleague (scripted)' };
  document.getElementById('people').replaceChildren(...agents.map((a) => {
    const p = a.persona || {};
    return el('div', { class: `person ${a.role}` },
      el('strong', {}, a.name), roleText[a.role],
      p.age ? el('div', {}, `${p.age}, ${p.occupation}`) : null,
      a.role === 'focal' && p.bio ? el('div', { class: 'muted' }, p.bio) : null);
  }));
}

// ---- State at a tick (rebuilt from the event list, so scrubbing is exact) -----------------------

function frameAt(t) {
  const notices = [];
  const said = {};
  let help = null;
  let priority = null;
  for (const e of events) {
    if (e.tick > t) break;
    const p = e.payload;
    if (e.type === 'NOTICE_SHOWN') notices.push({ tick: e.tick, ...p });
    if (e.type === 'AGENT_SAID' && p.scripted) said[e.agentId] = p.text;
    if (e.type === 'AGENT_PRIORITY_SET') priority = p.priority;
    if (p.counts_as_help && !help) help = e;
  }
  return { notices, said, help, priority };
}

const initials = (name) => name.split(/\s+/).map((w) => w[0]).join('').slice(0, 2).toUpperCase();
const tickX = (t) => TIMELINE.x0 + (t * (TIMELINE.x1 - TIMELINE.x0)) / MAX_TICK;
const seatXY = (agentId) => SEATS[run.scenario][seatOf[agentId] ?? 0];

// ---- Phaser scene ---------------------------------------------------------------------------

function startGame() {
  game?.destroy(true);
  document.getElementById('game').replaceChildren();
  game = new Phaser.Game({
    type: Phaser.AUTO, width: 640, height: 480, parent: 'game', backgroundColor: '#f4f1ea',
    scene: {
      create() { scene = this; build(); },
    },
  });
}


function drawBackground() {
  const g = scene.add.graphics().setDepth(1);
  for (const a of agents) { // a desk zone around each person
    const [sx, sy] = seatXY(a.agentId);
    g.fillStyle(0xe7e3d8, 1).fillRoundedRect(sx - 1.5 * TILE, sy - 1.2 * TILE, 3 * TILE, 2.4 * TILE, 10);
    g.lineStyle(1, 0xb8b2a2, 1).strokeRoundedRect(sx - 1.5 * TILE, sy - 1.2 * TILE, 3 * TILE, 2.4 * TILE, 10);
  }
  // The feed panel: alerts for alert_fatigue, the ticket for triage_herding.
  const triage = run.scenario === 'triage_herding';
  scene.add.rectangle(40, 44, 560, triage ? 104 : 286, 0x1a202c).setOrigin(0).setStrokeStyle(3, 0x4a5568).setDepth(2);
  scene.add.text(52, 50, triage ? 'TICKET QUEUE' : 'ALERT FEED', { fontSize: '11px', color: '#a0aec0' }).setDepth(3);
  if (triage) {
    priorityText = scene.add.text(588, 50, '', { fontSize: '12px', color: '#fff', fontStyle: 'bold' }).setOrigin(1, 0).setDepth(3);
  }
}

function drawTimeline() {
  scene.add.rectangle(TIMELINE.x0, TIMELINE.y, TIMELINE.x1 - TIMELINE.x0, 2, 0x718096).setOrigin(0, 0.5).setDepth(2);
  for (let t = 0; t <= MAX_TICK; t++) {
    scene.add.text(tickX(t), TIMELINE.y + 10, String(t), { fontSize: '9px', color: '#4a5568' }).setOrigin(0.5, 0).setDepth(2);
  }
  scene.add.text(TIMELINE.x0, TIMELINE.y - 24, 'what reached the focal agent, by tick', { fontSize: '10px', color: '#4a5568' }).setDepth(2);
  timeline = scene.add.graphics().setDepth(3);
}

function renderTimeline(t, notices) {
  if (!timeline) return;
  timeline.clear();
  for (const n of notices) {
    timeline.fillStyle(n.real ? 0xc53030 : 0x718096, 1);
    timeline.fillCircle(tickX(n.tick), TIMELINE.y, n.real ? 8 : 6);
  }
  timeline.fillStyle(0x2b6cb0, 1);
  timeline.fillTriangle(tickX(t) - 5, TIMELINE.y + 28, tickX(t) + 5, TIMELINE.y + 28, tickX(t), TIMELINE.y + 20);
}

function build() {
  drawBackground();
  drawTimeline();
  sprites = {};
  for (const a of agents) {
    const [sx, sy] = seatXY(a.agentId);
    const body = scene.add.circle(0, 0, a.role === 'focal' ? 14 : 11, COLORS[a.role]);
    if (a.role === 'focal') body.setStrokeStyle(3, 0xffffff);
    const text = scene.add.text(0, 0, initials(a.name), { fontSize: '11px', color: '#fff', fontStyle: 'bold' }).setOrigin(0.5);
    sprites[a.agentId] = scene.add.container(sx, sy, [body, text]).setDepth(4);
    sprites[a.agentId].disc = body;
  }
  ready = true;
  document.getElementById('play').disabled = false;
  document.getElementById('slider').disabled = false;
  jumpTo(0);
}

function clearTransient() {
  scene.tweens.killAll();
  bubbles.forEach((b) => b.destroy());
  bubbles = [];
  cards.forEach((c) => c.destroy());
  cards = [];
  Object.values(chatBubbles).forEach((b) => b.destroy());
  chatBubbles = {};
  priorityText?.setText('Priority: not set').setColor('#a0aec0');
}

// A card in the feed: one row per alert, or the ticket.
function addCard(n, animate) {
  const triage = run.scenario === 'triage_herding';
  const row = cards.length;
  const w = 536;
  const h = triage ? 70 : 32;
  const y = triage ? 66 : 70 + row * 36;
  const fill = n.real ? 0xc53030 : 0x4a5568;
  const box = scene.add.rectangle(0, 0, w, h, triage ? 0x2d3748 : fill).setOrigin(0);
  const text = scene.add.text(8, triage ? 6 : 6, triage ? n.text : `[turn ${n.tick}] ${n.text}`, {
    fontSize: triage ? '12px' : '11px', color: n.real || triage ? '#fff' : '#cbd5e0', wordWrap: { width: w - 16 },
  });
  const card = scene.add.container(52, y, [box, text]).setDepth(3);
  cards.push(card);
  if (animate) {
    card.setAlpha(0);
    scene.tweens.add({ targets: card, alpha: 1, duration: 300 / speed, onComplete: () => pulse(card, n) });
  } else {
    pulse(card, n);
  }
}

function pulse(card, n) {
  if (n.real && run.scenario === 'alert_fatigue') {
    scene.tweens.add({ targets: card, alpha: 0.6, duration: 500, yoyo: true, repeat: -1 });
  }
}

function showChat(agentId, text) {
  const [sx, sy] = seatXY(agentId);
  chatBubbles[agentId]?.destroy();
  chatBubbles[agentId] = scene.add.text(sx, sy - 56, text, {
    fontSize: '10px', color: '#111', backgroundColor: '#ffffff', padding: { x: 4, y: 3 }, wordWrap: { width: 128 },
  }).setOrigin(0.5, 1).setDepth(5);
}

function showPriority(priority) {
  if (!priorityText) return;
  priorityText.setText(`Priority: ${priority}`).setColor(priority === 'HIGH' ? '#68d391' : '#f6ad55');
}

/** Instant, exact state at the end of tick t: no animation. */
function jumpTo(t) {
  if (!ready) return;
  clearTransient();
  const f = frameAt(t);
  f.notices.forEach((n) => addCard(n, false));
  Object.entries(f.said).forEach(([id, text]) => showChat(id, text));
  if (f.priority) showPriority(f.priority);
  sprites.focal.disc.setFillStyle(f.help ? COLORS.helped : COLORS.focal);
  setTick(t);
}

function bubble(agentId, text) {
  const s = sprites[agentId];
  if (!s) return;
  const b = scene.add.text(s.x, s.y - 56, text, {
    fontSize: '12px', color: '#111', backgroundColor: '#ffffff', padding: { x: 5, y: 3 }, wordWrap: { width: 190 },
  }).setOrigin(0.5, 1).setDepth(6);
  bubbles.push(b);
  scene.time.delayedCall(BUBBLE_MS / speed, () => { b.destroy(); bubbles = bubbles.filter((x) => x !== b); });
}

/** Animate the events of tick t. Call only when the scene already shows the end of tick t-1. */
function playTick(t) {
  for (const e of byTick[t]) {
    const p = e.payload;
    if (e.type === 'NOTICE_SHOWN') addCard({ tick: t, ...p }, true);
    else if (e.type === 'AGENT_SAID') (p.scripted ? showChat(e.agentId, p.text) : bubble(e.agentId, p.text));
    else if (e.type === 'AGENT_CALLED') bubble(e.agentId, `📞 ${p.text}`);
    else if (e.type === 'AGENT_PRIORITY_SET') showPriority(p.priority);
    if (p.counts_as_help) sprites.focal.disc.setFillStyle(COLORS.helped);
  }
  setTick(t);
}

// ---- Panel, log and controls --------------------------------------------------------------------

function describe(e) {
  const p = e.payload;
  const who = e.agentId ? names[e.agentId] : '';
  switch (e.type) {
    case 'AGENT_SPAWNED': return `${who} sits at desk ${p.seat + 1}.`;
    case 'NOTICE_SHOWN':
      return p.kind === 'ticket' ? p.text : `${p.text} (${p.real ? 'the real alert' : 'a false alarm'})`;
    case 'AGENT_SAID': return `${who}: “${p.text}”`;
    case 'AGENT_WAITED': return `${who} waits.`;
    case 'AGENT_CALLED': return `${who} calls: “${p.text}”`;
    case 'AGENT_PRIORITY_SET': return `${who} sets the priority to ${p.priority}.`;
    case 'ACTION_PARSE_FAILED': return `${who}'s reply could not be used${p.truncated ? ' (cut off)' : ''}.`;
    case 'PROBE_ANSWERED': return `${who} answers the recognition question: “${p.text}”`;
    case 'RUN_ENDED': return 'The run ends.';
    default: return e.type;
  }
}

function setTick(t) {
  tick = t;
  document.getElementById('slider').value = t;
  document.getElementById('tick-label').textContent = `Tick ${t} / ${MAX_TICK}`;
  document.getElementById('log-title').textContent = `Events at tick ${t}`;
  renderTimeline(t, frameAt(t).notices);
  document.getElementById('log').replaceChildren(...byTick[t].map((e) => el('li', {},
    el('span', { class: e.payload.counts_as_help ? 'help' : '' },
      describe(e), e.payload.counts_as_help ? ' — counts as the outcome' : ''),
    e.payload.thought ? el('span', { class: 'thought' }, `Thought: ${e.payload.thought}`) : null)));
  const probe = events.find((e) => e.type === 'PROBE_ANSWERED');
  const box = document.getElementById('probe');
  box.hidden = !(probe && t >= MAX_TICK);
  if (!box.hidden) {
    box.replaceChildren(el('strong', {}, 'Recognition probe, asked after the run: '), `“${probe.payload.text}” `,
      el('em', {}, probe.payload.recognized ? '(counted as recognised)' : '(not counted as recognised)'));
  }
}

function pause() {
  clearTimeout(timer);
  timer = null;
  document.getElementById('play').textContent = tick >= MAX_TICK ? 'Replay' : 'Play';
}

function step() {
  if (tick >= MAX_TICK) { pause(); return; }
  playTick(tick + 1);
  timer = setTimeout(step, TICK_MS / speed);
}

function play() {
  if (tick >= MAX_TICK) jumpTo(0);
  document.getElementById('play').textContent = 'Pause';
  timer = setTimeout(step, 300 / speed);
}

document.getElementById('play').addEventListener('click', () => (timer ? pause() : play()));
document.getElementById('slider').addEventListener('input', (e) => { pause(); jumpTo(Number(e.target.value)); });
document.getElementById('thoughts').addEventListener('change', (e) => {
  document.getElementById('log').classList.toggle('hide-thoughts', !e.target.checked);
});
document.querySelectorAll('.speed').forEach((b) => b.addEventListener('click', () => {
  speed = Number(b.dataset.speed);
  document.querySelectorAll('.speed').forEach((x) => x.classList.toggle('active', x === b));
}));

load();
