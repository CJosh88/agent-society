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

export const CONDITION_LABELS = { alone: 'Alone', group5: 'Group of 5', group5_owner: 'Group of 5 + owner' };
export const SCENARIO_LABELS = { town_square: 'Town square', office: 'Office' };
export const label = (map, key) => map[key] ?? key;
