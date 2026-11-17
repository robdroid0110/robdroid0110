/* RBD/0110: original canvas field renderer. Zero dependencies, no analytics. */
(() => {
  'use strict';
  const canvas = document.getElementById('field');
  if (!canvas) return;
  const ctx = canvas.getContext('2d', { alpha: false });
  const log = document.getElementById('log');
  const cmdInput = document.getElementById('commandInput');
  const form = document.getElementById('commandForm');
  const frameEl = document.getElementById('fpsLabel');
  const seedEl = document.getElementById('seedLabel');
  const coordEl = document.getElementById('coordinate');
  const modeEl = document.getElementById('topMode');
  const eventEl = document.getElementById('eventCount');
  const sampleEl = document.getElementById('sampledAt');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const TWO_PI = Math.PI * 2;
  const TAU = TWO_PI;
  let width = 600, height = 520, pixelRatio = 1, frame = 0, lastTime = 0;
  let seed = 110, inverted = false, frozen = reducedMotion, pulse = 0, transient = 0, animationId = 0;
  let angleClock = 0, dirty = true;
  let target = { x: .5, y: .5, active: false }, mouse = { x: .5, y: .5 };
  let points = [], coils = [];
  let currentState = { sample_size: null, push_count: null, sampled_at: null, activity_days: null };

  function hash(n) {
    let x = n | 0;
    x = Math.imul(x ^ (x >>> 16), 0x7feb352d);
    x = Math.imul(x ^ (x >>> 15), 0x846ca68b);
    return ((x ^ (x >>> 16)) >>> 0) / 4294967295;
  }
  function setSeed(next) {
    seed = Math.abs(next | 0) % 999999;
    const n = window.matchMedia('(max-width:600px)').matches ? 76 : 128;
    points = Array.from({length: n}, (_, i) => ({
      phi: i * 2.399963229728653 + hash(seed + i * 101) * .7,
      speed: .28 + hash(seed + i * 15) * .55,
      offset: hash(seed + i * 29) * TAU,
      wave: .18 + hash(seed + i * 47) * .72,
      shade: hash(seed + i * 23),
    }));
    coils = Array.from({length: 44}, (_, i) => ({angle: i * TAU / 44, hue: hash(seed + i * 17)}));
    seedEl.textContent = 'SEED / ' + String(seed).padStart(6, '0');
    dirty = true;
  }
  function resize() {
    const r = canvas.getBoundingClientRect();
    width = Math.max(300, r.width);
    height = Math.max(300, r.height);
    pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(width * pixelRatio);
    canvas.height = Math.round(height * pixelRatio);
    ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    setSeed(seed);
  }
  function addLog(message, cls = '') {
    const line = document.createElement('div');
    line.className = 'log-line' + (cls ? ' ' + cls : '');
    line.textContent = message;
    log.append(line);
    while (log.childElementCount > 45) log.firstElementChild.remove();
    log.scrollTop = log.scrollHeight;
  }
  function notify(message, cls='signal') { addLog('[ ' + new Date().toLocaleTimeString('en-GB', {hour12:false}) + ' ] ' + message, cls); }
  function toggleFreeze() {
    frozen = !frozen;
    modeEl.textContent = frozen ? 'SIMULATION PAUSED' : 'LOCAL INSTANCE';
    notify(frozen ? 'State suspended.' : 'Simulation resumed.');
    dirty = true;
  }
  function execute(input) {
    const command = input.trim().toLowerCase().replace(/^\//, '');
    if (!command) return;
    addLog('rbd@0110:~$ ' + input, 'command');
    const [cmd, ...args] = command.split(/\s+/);
    switch(cmd) {
      case 'help':
      case '?':
        addLog('COMMANDS : help / pulse / invert / mutate / freeze');
        addLog('           scan / whoami / clear / seed <integer>');
        addLog('KEYBOARD : SPACE  I  R  F');
        break;
      case 'pulse':
        pulse = 1.4; notify('Pressure wave injected into field.'); dirty = true; break;
      case 'invert':
        inverted = !inverted;
        document.documentElement.style.setProperty('--acid', inverted ? '#ff725d' : '#d6fa65');
        document.documentElement.style.setProperty('--orange', inverted ? '#d6fa65' : '#ed7253');
        notify('Topology inverted. Reference frame unstable.'); dirty = true; break;
      case 'mutate':
      case 'reseed':
        setSeed(Math.floor(Math.random() * 899999) + 100000);
        notify('Origin seed discarded. New structure synthesized.'); break;
      case 'freeze': toggleFreeze(); break;
      case 'scan':
        addLog('SENSOR: public event metadata only.');
        addLog('SAMPLE: ' + (currentState.sample_size ?? 'UNOBSERVED') + ' events / ' + (currentState.push_count ?? 'UNKNOWN') + ' push events.');
        addLog('NO DEVICE OR VISITOR DATA IS TRANSMITTED.');
        break;
      case 'whoami':
        addLog('UNKNOWN. A person is not a configuration file.', 'alert'); break;
      case 'seed':
        if (args[0] && /^\d{1,8}$/.test(args[0])) { setSeed(Number(args[0])); notify('Seed assigned / ' + seed); }
        else addLog('USAGE: seed <integer 0..99999999>', 'alert');
        break;
      case 'clear': log.replaceChildren(); break;
      default: addLog('UNRECOGNIZED INSTRUCTION. TYPE "help".', 'alert');
    }
  }
  function draw(t) {
    ctx.fillStyle = inverted ? '#110b0b' : '#070b09';
    ctx.fillRect(0, 0, width, height);
    const size = Math.min(width, height);
    const x0 = width * .5, y0 = height * .5;
    const minR = size * .092;
    const maxR = size * (width < 500 ? .405 : .44);
    const moveX = (mouse.x - .5) * size * .16;
    const moveY = (mouse.y - .5) * size * .16;
    const dir = inverted ? -1 : 1;
    const primary = inverted ? '255,114,93' : '214,250,101';
    const accent = inverted ? '214,250,101' : '237,114,83';

    // Calibration circles are guides, not assets.
    ctx.lineWidth = 1;
    for (let r = 0; r < 5; r++) {
      const rad = minR + (maxR - minR) * (r + 1) / 5;
      ctx.strokeStyle = `rgba(${primary},${r % 2 ? .13 : .08})`;
      ctx.beginPath(); ctx.ellipse(x0, y0, rad, rad * .88, 0, 0, TAU); ctx.stroke();
    }

    // The field is made of deformable filaments; every frame redraws the geometry.
    const segments = width < 500 ? 32 : 44;
    ctx.lineCap = 'round';
    for (let i = 0; i < points.length; i++) {
      const p = points[i];
      const phase = p.phi + dir * t * .08 * p.speed;
      const dx = Math.cos(phase), dy = Math.sin(phase);
      ctx.beginPath();
      for (let j = 0; j <= segments; j++) {
        const k = j / segments;
        const r = minR + Math.pow(k, .84) * (maxR - minR) * (.78 + p.wave * .23);
        const curl = Math.sin(k * 15 + phase * 4 + p.offset + t * .14) * (.11 + .28 * k);
        const bend = Math.sin(k * 7 + p.offset + t * .1) * .26;
        const angle = phase + k * (1.9 + p.wave) + curl + bend * dir + pulse * k * .18;
        const wave = Math.sin(k * 21 + t * .8 * p.speed + p.offset) * (4 + 17 * k);
        const ax = x0 + Math.cos(angle) * (r + wave) + moveX * k * k + dx * pulse * 8 * k;
        const ay = y0 + Math.sin(angle) * (r * .88 + wave * .7) + moveY * k * k + dy * pulse * 8 * k;
        if (j === 0) ctx.moveTo(ax, ay); else ctx.lineTo(ax, ay);
      }
      ctx.lineWidth = p.shade > .7 ? 1.35 : .75;
      ctx.strokeStyle = `rgba(${p.shade < .07 ? accent : primary}, ${.09 + p.shade * .25})`;
      ctx.stroke();
    }
    ctx.lineWidth = 1;
    // Materialization marks: synchronized, individually generated orbiting nodes.
    for (const c of coils) {
      const a = c.angle + t * (.075 + c.hue * .04) * dir;
      const radius = maxR * (.46 + c.hue * .6);
      const x = x0 + Math.cos(a) * radius + moveX * .3;
      const y = y0 + Math.sin(a) * radius * .88 + moveY * .3;
      ctx.fillStyle = `rgba(${primary},${.3 + .5 * c.hue})`;
      ctx.fillRect(x - .9, y - .9, 1.8 + c.hue * 1.2, 1.8 + c.hue * 1.2);
    }
    // Nucleus + reticle.
    ctx.fillStyle = inverted ? '#1e1110' : '#0b100c';
    ctx.beginPath(); ctx.arc(x0, y0, minR * 1.19, 0, TAU); ctx.fill();
    ctx.strokeStyle = `rgba(${primary},.88)`;
    ctx.lineWidth = 1.2;
    ctx.beginPath();ctx.arc(x0,y0,minR*1.19,0,TAU);ctx.stroke();
    ctx.strokeStyle = `rgba(${primary},.35)`;
    ctx.beginPath();ctx.arc(x0,y0,minR*1.34,Math.PI*.24,Math.PI*.87);ctx.stroke();
    ctx.beginPath();ctx.arc(x0,y0,minR*1.34,Math.PI*1.17,Math.PI*1.78);ctx.stroke();
    if (pulse > .001) {
      ctx.lineWidth = 1.5; ctx.strokeStyle = `rgba(${accent},${Math.min(1,pulse*.65)})`;
      ctx.beginPath();ctx.arc(x0,y0,minR+(1.4-pulse)*(maxR-minR)*1.14,0,TAU);ctx.stroke();
    }
    dirty = false;
  }
  function loop(now) {
    animationId = requestAnimationFrame(loop);
    const dt = Math.min(.05, (now - (lastTime || now)) / 1000);
    lastTime = now;
    if (document.hidden) return;
    if (!frozen) { angleClock += dt; pulse = Math.max(0, pulse - dt * .65); }
    mouse.x += (target.x - mouse.x) * Math.min(1, dt * 3.3);
    mouse.y += (target.y - mouse.y) * Math.min(1, dt * 3.3);
    if (!frozen || dirty) draw(angleClock);
    if (++frame % 50 === 0) frameEl.textContent = frozen ? 'FRAME: HOLD' : 'FRAME: ACTIVE';
  }
  canvas.addEventListener('pointermove', e => {
    const rect = canvas.getBoundingClientRect();
    target.x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    target.y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
    target.active = true;
    coordEl.textContent = `X:${String(Math.round(target.x*999)).padStart(3,'0')} Y:${String(Math.round(target.y*999)).padStart(3,'0')}`;
    dirty = true;
  });
  canvas.addEventListener('pointerleave', () => { target.x = .5; target.y = .5; target.active = false; });
  canvas.addEventListener('pointerdown', () => execute('pulse'));
  document.querySelectorAll('[data-action]').forEach(button => button.addEventListener('click', () => execute(button.dataset.action)));
  document.addEventListener('keydown', event => {
    if (event.target === cmdInput || event.ctrlKey || event.metaKey || event.altKey) return;
    const map = {' ': 'pulse', i:'invert', r:'mutate', f:'freeze'};
    const action = map[event.key.toLowerCase()];
    if (action) { event.preventDefault(); execute(action); }
    if (event.key === '/') { event.preventDefault(); cmdInput.focus(); }
  });
  form.addEventListener('submit', e => { e.preventDefault(); execute(cmdInput.value); cmdInput.value = ''; });
  window.addEventListener('resize', resize, {passive:true});
  function sample(signal) {
    if (!signal || typeof signal !== 'object') return;
    currentState = signal;
    if (Number.isInteger(signal.sample_size)) {
      eventEl.textContent = String(signal.sample_size).padStart(2,'0') + ' PUBLIC EVENTS';
    }
    if (typeof signal.sampled_at === 'string') {
      const d = new Date(signal.sampled_at);
      if (!Number.isNaN(d.getTime())) sampleEl.textContent = 'SAMPLED ' + d.toISOString().slice(0,16).replace('T',' ') + ' UTC';
    }
    if (Number.isInteger(signal.seed)) { setSeed(signal.seed); notify('Public signal integrated (historical sample).'); }
  }
  addLog('RBD/0110  /  NOT AN IMAGE.  NOT A BIOGRAPHY.');
  addLog('ENGINE: local canvas; all graphics calculated in your browser.');
  addLog('INTERACT: move pointer / tap the field / type "help".', 'signal');
  setSeed(110);
  resize();
  if (ctx) { draw(0); animationId = requestAnimationFrame(loop); }
  fetch('./state.json', {cache:'no-store'}).then(r => { if (!r.ok) throw new Error('not available'); return r.json(); }).then(sample).catch(() => notify('No public sample; local simulation retained.', 'alert'));
})();
