// Small helpers shared by both pages. Everything from the API goes in through textContent, never innerHTML.

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === false || v == null) continue;
    if (k === 'class') node.className = v;
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? '' : v);
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}

export class HttpError extends Error {
  constructor(status, url) {
    super(`${url} returned ${status}`);
    this.status = status;
  }
}

export async function getJson(url) {
  const res = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!res.ok) throw new HttpError(res.status, url);
  return res.json();
}

/** Show an error with a Retry button in `target`; `retry` is called when it is pressed. */
export function showError(target, err, retry) {
  target.replaceChildren(
    el('div', { class: 'error', role: 'alert' }, `Could not load this: ${err.message}`,
      el('button', { type: 'button', onclick: retry }, 'Retry')),
  );
}

export const CONDITION_LABELS = {
  independent: 'Independent (no counts)',
  weak: 'Weak influence (counts shown)',
  strong: 'Strong influence (counts, sorted)',
  seeded_wrong: 'Seeded wrong (first agents wrong)',
};
export const POPULATION_LABELS = {
  'llama-3.1-8b': 'Llama 3.1 8B',
  'gpt-oss-120b': 'gpt-oss-120b',
  'claude-haiku-5-5': 'Claude Haiku 5.5',
  mix_early: 'Mixed: stronger model first',
  mix_late: 'Mixed: stronger model last',
  fake: 'Fake model (tests)',
};
export const label = (map, key) => map[key] ?? key;
export const pct = (x, digits = 0) => `${(x * 100).toFixed(digits)}%`;
