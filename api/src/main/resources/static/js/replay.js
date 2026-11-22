import { CONDITION_LABELS, HttpError, SCENARIO_LABELS, el, getJson, label, showError } from './common.js';

const TILE = 32;
const TICK_MS = 1500;
const MOVE_MS = 600;
const BUBBLE_MS = 1200;
const MAX_TICK = 12;
const TARGET_TILE = [10, 8];

// Locations repeat world.py in the engine; both are frozen by the pre-registration.
const SCENES = {
  town_square: { bus_stop: [3, 3], cafe: [16, 3], fountain: [10, 7], bench: [4, 11], market_stall: [15, 11] },
  office: { desk_area: [4, 4], kitchen: [16, 3], wall_screen: [10, 7], meeting_room: [4, 11], printer: [15, 11] },
};
const COLORS = { focal: 0x2b6cb0, helped: 0x2f855a, scripted: 0x8a94a0, victim: 0xc53030 };

const params = new URLSearchParams(location.search);
const runId = params.get('run');
const status = document.getElementById('status');
const root = document.getElementById('replay');

let run, agents, events, names, byTick;
let game, scene, sprites, targetSprite, banner, bubbles = [];
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
  s.textContent = run.focalHelped ? `The focal agent helped at tick ${run.focalHelpTick}.` : 'The focal agent did not help.';
  s.className = `summary ${run.focalHelped ? 'helped' : 'not-helped'}`;
}

function fillPeople() {
  const roleText = { focal: 'Focal agent', scripted: 'Scripted, never helps', victim: 'Needs help' };
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
  const pos = {};
  let problem = false;
  let help = null;
  for (const e of events) {
    if (e.tick > t) break;
    const p = e.payload;
    if (['AGENT_SPAWNED', 'AGENT_MOVED', 'AGENT_APPROACHED'].includes(e.type)) pos[e.agentId] = [p.x, p.y];
    if (e.type === 'PROBLEM_STARTED') problem = true;
    if (p.counts_as_help && !help) help = e;
  }
  return { pos, problem, help };
}

const px = ([x, y]) => [x * TILE + TILE / 2, y * TILE + TILE / 2];
const initials = (name) => name.split(/\s+/).filter((w) => !/^(a|the)$/i.test(w)).map((w) => w[0]).slice(0, 2).join('').toUpperCase();

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
  const g = scene.add.graphics();
  for (const [name, [lx, ly]] of Object.entries(SCENES[run.scenario])) {
    g.fillStyle(0xe7e3d8, 1).fillRoundedRect((lx - 1) * TILE, (ly - 1) * TILE, 3 * TILE, 2 * TILE, 10);
    g.lineStyle(1, 0xb8b2a2, 1).strokeRoundedRect((lx - 1) * TILE, (ly - 1) * TILE, 3 * TILE, 2 * TILE, 10);
    scene.add.text((lx - 1) * TILE + 4, (ly - 1) * TILE - 15, name, { fontSize: '11px', color: '#6b6658' });
  }
  sprites = {};
  if (run.scenario === 'office') {
    const [tx, ty] = px(TARGET_TILE);
    targetSprite = scene.add.rectangle(tx, ty, 30, 20, 0x4a5568);
    scene.add.text(tx, ty + 16, 'payments_dashboard', { fontSize: '10px', color: '#4a5568' }).setOrigin(0.5, 0);
  }
  for (const a of agents) {
    const r = a.role === 'focal' ? 14 : 11;
    const body = scene.add.circle(0, 0, r, COLORS[a.role]);
    if (a.role === 'focal') body.setStrokeStyle(3, 0xffffff);
    const text = scene.add.text(0, 0, a.role === 'victim' ? '?' : initials(a.name),
      { fontSize: '11px', color: '#fff', fontStyle: 'bold' }).setOrigin(0.5);
    sprites[a.agentId] = scene.add.container(0, 0, [body, text]);
    sprites[a.agentId].disc = body;
    if (a.role === 'victim') targetSprite = sprites[a.agentId];
  }
  banner = scene.add.text(320, 8, '', {
    fontSize: '13px', color: '#fff', backgroundColor: '#c53030', padding: { x: 8, y: 4 }, wordWrap: { width: 600 },
  }).setOrigin(0.5, 0).setDepth(10).setVisible(false);
  ready = true;
  document.getElementById('play').disabled = false;
  document.getElementById('slider').disabled = false;
  jumpTo(0);
}

function clearTransient() {
  scene.tweens.killAll();
  bubbles.forEach((b) => b.destroy());
  bubbles = [];
  banner.setVisible(false);
}

function setProblemLook(on) {
  if (!targetSprite) return;
  targetSprite.setScale(1).setAlpha(1);
  if (run.scenario === 'office') targetSprite.setFillStyle(on ? 0xc53030 : 0x4a5568);
  if (on) {
    scene.tweens.add({
      targets: targetSprite, duration: 500, yoyo: true, repeat: -1,
      ...(run.scenario === 'office' ? { alpha: 0.35 } : { scale: 1.3 }),
    });
  }
}

/** Instant, exact state at the end of tick t: no animation, no bubbles. */
function jumpTo(t) {
  if (!ready) return;
  clearTransient();
  const f = frameAt(t);
  for (const [id, sprite] of Object.entries(sprites)) {
    const p = f.pos[id];
    sprite.setVisible(Boolean(p));
    if (p) sprite.setPosition(...px(p));
  }
  sprites.focal.disc.setFillStyle(f.help ? COLORS.helped : COLORS.focal);
  setProblemLook(f.problem);
  setTick(t);
}

function bubble(agentId, text) {
  const s = sprites[agentId];
  if (!s) return;
  const b = scene.add.text(s.x, s.y - 20, text, {
    fontSize: '12px', color: '#111', backgroundColor: '#ffffff', padding: { x: 5, y: 3 }, wordWrap: { width: 170 },
  }).setOrigin(0.5, 1).setDepth(5);
  bubbles.push(b);
  scene.time.delayedCall(BUBBLE_MS / speed, () => { b.destroy(); bubbles = bubbles.filter((x) => x !== b); });
}

/** Animate the events of tick t. Call only when the scene already shows the end of tick t-1. */
function playTick(t) {
  for (const e of byTick[t]) {
    const p = e.payload;
    if (e.type === 'AGENT_MOVED' || e.type === 'AGENT_APPROACHED') {
      const [x, y] = px([p.x, p.y]);
      scene.tweens.add({ targets: sprites[e.agentId], x, y, duration: MOVE_MS / speed });
    } else if (e.type === 'AGENT_SAID') {
      bubble(e.agentId, p.text);
    } else if (e.type === 'AGENT_CALLED') {
      bubble(e.agentId, `📞 ${p.text}`);
    } else if (e.type === 'PROBLEM_STARTED') {
      banner.setText(p.description).setVisible(true);
      scene.time.delayedCall(2500 / speed, () => banner.setVisible(false));
      setProblemLook(true);
    }
    if (p.counts_as_help) sprites.focal.disc.setFillStyle(COLORS.helped);
  }
  setTick(t);
}

// ---- Panel, log and controls --------------------------------------------------------------------

function describe(e) {
  const p = e.payload;
  const who = e.agentId ? names[e.agentId] : '';
  switch (e.type) {
    case 'AGENT_SPAWNED': return `${who} is at ${p.location}.`;
    case 'PROBLEM_STARTED': return p.description;
    case 'AGENT_MOVED': return `${who} walks to ${p.to}.`;
    case 'AGENT_SAID': return `${who}: “${p.text}”`;
    case 'AGENT_WAITED': return `${who} waits.`;
    case 'AGENT_APPROACHED': return `${who} walks up to ${names[p.target_id] ?? p.target_id.replace('_', ' ')}.`;
    case 'AGENT_CALLED': return `${who} calls: “${p.text}”`;
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
  document.getElementById('log').replaceChildren(...byTick[t].map((e) => el('li', {},
    el('span', { class: e.payload.counts_as_help ? 'help' : '' },
      describe(e), e.payload.counts_as_help ? ' — counts as help' : ''),
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
