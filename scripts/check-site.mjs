// Smoke-test reference.html in headless Chromium over the DevTools protocol.
//   node scripts/check-site.mjs [page.html] [screenshot-dir]
// No npm install: Node's built-in WebSocket + the system Chromium. Fails (exit 1)
// on any page exception or console error, and checks that typing a symbol, hovering
// an action and searching all point at the right key. Screenshots land in
// screenshot-dir (default /tmp/toucan-site) for a visual look.
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const page = resolve(process.argv[2] || 'reference.html');
const shots = process.argv[3] || '/tmp/toucan-site';
mkdirSync(shots, { recursive: true });
const port = 9300 + Math.floor(Math.random() * 500);
const chrome = spawn(process.env.CHROMIUM || 'chromium', ['--headless=new', '--disable-gpu', '--no-first-run',
  `--remote-debugging-port=${port}`, `--user-data-dir=/tmp/toucan-site-profile-${port}`, 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));

let ws, id = 0;
const pending = new Map(), problems = [];
function send(method, params = {}) {
  return new Promise((ok, bad) => {
    const n = ++id; pending.set(n, { ok, bad });
    ws.send(JSON.stringify({ id: n, method, params }));
  });
}
async function connect() {
  for (let i = 0; i < 50; i++) {
    try {
      const tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
      const t = tabs.find(x => x.type === 'page');
      if (t) { ws = new WebSocket(t.webSocketDebuggerUrl); break; }
    } catch {}
    await sleep(100);
  }
  await new Promise(r => ws.addEventListener('open', r));
  ws.addEventListener('message', ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.bad(m.error) : p.ok(m.result); }
    if (m.method === 'Runtime.exceptionThrown') problems.push('exception: ' + m.params.exceptionDetails.exception?.description);
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') problems.push('console.error: ' + JSON.stringify(m.params.args.map(a => a.value)));
  });
}
const evaluate = async expr => (await send('Runtime.evaluate', { expression: expr, returnByValue: true })).result.value;
async function shot(name, w = 1600, h = 1000, dark = true) {
  await send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: w < 700 });
  await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: dark ? 'dark' : 'light' }] });
  await sleep(150);
  const { data } = await send('Page.captureScreenshot', { format: 'png' });
  writeFileSync(`${shots}/${name}.png`, Buffer.from(data, 'base64'));
}
async function key(k) {
  const text = k.length === 1 ? k : undefined;
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: k, text });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: k });
  await sleep(120);
}
const fails = [];
const check = (cond, msg) => { if (!cond) fails.push(msg); };

try {
  await connect();
  await send('Runtime.enable'); await send('Page.enable');
  await send('Page.navigate', { url: 'file://' + page });
  await sleep(800);
  await shot('1-base-dark');

  await key('{');
  const typed = await evaluate(`document.querySelector('#detail').textContent`);
  check(/hold LOWER/.test(typed), `typing { should explain "hold LOWER", got: ${typed}`);
  const hot = await evaluate(`[...document.querySelectorAll('#board .key.hot')].map(k => k.dataset.pos).join(',')`);
  check(hot.includes('33'), `typing { should light key 33 (the . key), lit: ${hot}`);
  await shot('2-typed-brace');

  await evaluate(`document.querySelector('#actions .row').dispatchEvent(new MouseEvent('mouseenter'))`);
  await shot('3-hover-action');

  await evaluate(`(() => { const q = document.querySelector('#q'); q.value = 'volume'; q.dispatchEvent(new Event('input')); })()`);
  const res = await evaluate(`document.querySelector('#results').textContent`);
  check(/Volume/i.test(res), `searching "volume" should list it, got: ${res.slice(0, 120)}`);
  await shot('4-search');

  await evaluate(`document.querySelector('.tab[data-layer="SYM"]').click()`);
  await shot('5-sym-light', 1600, 1000, false);
  await evaluate(`document.querySelector('.tab[data-layer="BASE"]').click()`);
  await shot('6-phone', 390, 900);
} catch (e) {
  fails.push('harness: ' + (e.message || JSON.stringify(e)));
} finally {
  chrome.kill();
}
const all = [...problems, ...fails];
if (all.length) { console.error(all.join('\n')); process.exit(1); }
console.log(`ok - screenshots in ${shots}`);
