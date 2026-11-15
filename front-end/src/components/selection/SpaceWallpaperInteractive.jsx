import { useEffect, useRef } from "react";

const TAU = Math.PI * 2;
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));

function mulberry32(a) {
  return () => {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function makeFbm(rand) {
  const p = new Uint8Array(512);
  const a = [...Array(256).keys()];
  for (let i = 255; i > 0; i--) { const j = (rand() * (i + 1)) | 0; [a[i], a[j]] = [a[j], a[i]]; }
  for (let i = 0; i < 512; i++) p[i] = a[i & 255];
  const sm = (t) => t * t * (3 - 2 * t);
  const noise = (x, y) => {
    const xi = Math.floor(x), yi = Math.floor(y), X = xi & 255, Y = yi & 255;
    const u = sm(x - xi), v = sm(y - yi);
    const a0 = p[p[X] + Y], b0 = p[p[X + 1] + Y], a1 = p[p[X] + Y + 1], b1 = p[p[X + 1] + Y + 1];
    const top = a0 + (b0 - a0) * u, bot = a1 + (b1 - a1) * u;
    return (top + (bot - top) * v) / 255;
  };
  return (x, y, oct = 4) => {
    let s = 0, amp = 0.5, f = 1, tot = 0;
    for (let i = 0; i < oct; i++) { s += noise(x * f, y * f) * amp; tot += amp; amp *= 0.5; f *= 2.03; }
    return s / tot;
  };
}

const TILT = -0.62, CORE = 0.02;
const CA = Math.cos(TILT), SA = Math.sin(TILT);

function bandDensity(px, py) {
  const u = px * CA + py * SA, v = -px * SA + py * CA;
  const band = Math.exp(-(v * v) / (2 * 0.17 * 0.17));
  const core = Math.exp(-((u - CORE) ** 2) / (2 * 0.5 * 0.5));
  return 0.24 + 0.76 * band * (0.55 + 0.45 * core);
}

function buildSky(seed, w, h) {
  const fbm = makeFbm(mulberry32(seed));
  const rnd = mulberry32(seed + 99);
  const c = document.createElement("canvas");
  c.width = w; c.height = h;
  const ctx = c.getContext("2d");
  const img = ctx.createImageData(w, h), d = img.data;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const px = (x - w / 2) / h, py = (y - h / 2) / h;
      const u = px * CA + py * SA, v = -px * SA + py * CA;
      const warp = (fbm(u * 1.6 + 10, v * 1.6, 4) - 0.5) * 0.36 + 0.07 * Math.sin(u * 2.4);
      const vv = v + warp;
      const band = Math.exp(-(vv * vv) / (2 * 0.14 * 0.14));
      const wide = Math.exp(-(vv * vv) / (2 * 0.45 * 0.45));
      const core = Math.exp(-((u - CORE) ** 2) / (2 * 0.46 * 0.46));
      const clouds = fbm(u * 5 + 3, vv * 5, 5);
      const fine = fbm(u * 22 + 7, v * 22, 3);
      const ridge = 1 - Math.abs(2 * fbm(u * 3.6 + 40, vv * 3.6, 5) - 1);
      const dust = Math.pow(ridge, 3) * Math.exp(-(vv * vv) / (2 * 0.075 * 0.075));
      let lum = band * (0.3 + 0.7 * core) * (0.4 + clouds) * (0.65 + 0.7 * fine);
      lum *= 1 - 0.9 * dust * (0.35 + 0.65 * core);
      lum += 0.035 * wide * (0.6 + 0.8 * clouds);
      const t = Math.min(1, band * core * 1.2);
      const cr = 105 + 125 * t, cg = 90 + 90 * t, cb = 185 - 10 * t;
      const m = 1 - Math.exp(-lum * 1.5), gain = 175;
      const glow = fbm(px * 2.2 + 70, py * 2.2 + 20, 3);
      const n = (rnd() - 0.5) * 2.5;
      const i = (y * w + x) * 4;
      d[i] = 5 + 5 * glow + (cr / 255) * m * gain + n;
      d[i + 1] = 2 + 2 * glow + (cg / 255) * m * gain + n;
      d[i + 2] = 12 + 9 * glow + (cb / 255) * m * gain + n;
      d[i + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  return c;
}

const PALETTE = [[170, 190, 255], [210, 220, 255], [255, 248, 245], [255, 232, 200], [255, 195, 150]];
const PW = [0.18, 0.22, 0.28, 0.2, 0.12];

function buildStars(rand, count) {
  const px = [], py = [], br = [], ph = [], ci = [];
  PALETTE.forEach((_, k) => {
    const n = Math.floor(count * PW[k]);
    let made = 0;
    while (made < n) {
      const x = (rand() * 2 - 1) * 1.1, y = (rand() * 2 - 1) * 0.85;
      if (rand() > bandDensity(x, y)) continue;
      px.push(x); py.push(y); br.push(0.1 + Math.pow(rand(), 4.5) * 0.7);
      ph.push(rand() * TAU); ci.push(k); made++;
    }
  });
  const bright = [];
  for (let i = 0; i < 70; i++) {
    bright.push({
      x: (rand() * 2 - 1) * 1.1, y: (rand() * 2 - 1) * 0.85,
      b: 0.75 + rand() * 0.25, ph: rand() * TAU, c: PALETTE[(rand() * 5) | 0],
    });
  }
  return {
    px: Float32Array.from(px), py: Float32Array.from(py), br: Float32Array.from(br),
    ph: Float32Array.from(ph), ci: Uint8Array.from(ci), bright,
  };
}

function makeGrain(rand) {
  const c = document.createElement("canvas");
  c.width = c.height = 256;
  const g = c.getContext("2d");
  const img = g.createImageData(256, 256);
  for (let i = 0; i < img.data.length; i += 4) {
    const v = rand() * 255;
    img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 255;
  }
  g.putImageData(img, 0, 0);
  return c;
}

const TINTS = [[255, 255, 255], [205, 215, 255], [200, 255, 220], [255, 215, 175]];

function spawnMeteor(W, H, rand, big) {
  const ang = ((20 + rand() * 32) * Math.PI) / 180;
  const flip = rand() < 0.22 ? 1 : -1;
  return {
    x: flip < 0 ? W * (0.35 + rand() * 0.75) : W * (-0.1 + rand() * 0.65),
    y: -20 + rand() * H * 0.5,
    dx: flip * Math.cos(ang), dy: Math.sin(ang),
    speed: (big ? 650 : 1000) + rand() * 1100,
    life: big ? 1.7 + rand() : 0.55 + rand() * 0.9,
    len: big ? 460 : 130 + rand() * 280,
    w: big ? 2.8 : 0.9 + rand() * 1.1,
    tint: TINTS[(rand() * 4) | 0], age: 0, big,
  };
}

const INTERACTIVE_EL = 'a,button,input,textarea,select,summary,label,video,iframe,[role="button"],[contenteditable="true"]';

export default function SpaceWallpaperInteractive({
  className = "", interactive = true, fullControl = false, fixed = true,
  meteors = true, satellites = true, density = 1, seed = 7,
}) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const rand = mulberry32(seed * 17 + 3);
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const sky = buildSky(seed, 720, 405);
    const stars = buildStars(rand, Math.round((window.innerWidth < 700 ? 9000 : 16000) * density));
    const grainPat = ctx.createPattern(makeGrain(rand), "repeat");

    let W = 0, H = 0, dpr = 1, raf = 0, last = performance.now(), t = 0, flash = 0;
    let nextMeteor = 2, nextSat = 3, lastTap = 0, trailAcc = 0, lastMx = 0, lastMy = 0, pinchD = 0;
    const shooting = [], sparks = [], sats = [], dust = [], ripples = [], cand = [];
    const view = { panX: 0, panY: 0, vx: 0, vy: 0, zoom: 1, zoomT: 1, scroll: 0 };
    const ptr = { x: -999, y: -999, nx: 0, ny: 0, sx: 0, sy: 0, a: 0, in: false };
    const drag = { down: false, on: false, can: false, id: null, lx: 0, ly: 0, lt: 0, t0: 0, moved: 0 };
    const pts = new Map();

    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      W = canvas.clientWidth; H = canvas.clientHeight;
      canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
      if (reduce) draw(0);
    };

    const local = (e) => {
      const r = canvas.getBoundingClientRect();
      return [e.clientX - r.left, e.clientY - r.top];
    };
    const ignore = (e) => !fullControl && e.target instanceof Element && e.target.closest(INTERACTIVE_EL);

    const shootAt = (x, y, big) => {
      const m = spawnMeteor(W, H, rand, big);
      m.x = x - m.dx * m.speed * m.life * 0.5;
      m.y = y - m.dy * m.speed * m.life * 0.5;
      shooting.push(m);
      ripples.push({ x, y, age: 0 });
    };

    const onMove = (e) => {
      const [x, y] = local(e);
      ptr.x = x; ptr.y = y; ptr.nx = (x / W - 0.5) * 2; ptr.ny = (y / H - 0.5) * 2; ptr.in = true;
      if (pts.has(e.pointerId)) pts.set(e.pointerId, { x, y });
      if (fullControl && pts.size === 2) {
        const [a, b] = [...pts.values()];
        const d = Math.hypot(a.x - b.x, a.y - b.y);
        if (pinchD) view.zoomT = clamp(view.zoomT * (d / pinchD), 1, 2.6);
        pinchD = d; return;
      }
      if (drag.down && drag.id === e.pointerId) {
        const dx = x - drag.lx, dy = y - drag.ly, now = performance.now();
        drag.moved += Math.hypot(dx, dy);
        if (!drag.on && drag.can && drag.moved > 5) {
          drag.on = true;
          document.body.style.userSelect = "none";
          window.getSelection()?.removeAllRanges();
        }
        if (drag.on) {
          const s = Math.max(1, now - drag.lt) / 1000;
          view.panX += dx; view.panY += dy;
          view.vx = view.vx * 0.6 + (dx / s) * 0.4; view.vy = view.vy * 0.6 + (dy / s) * 0.4;
        }
        drag.lx = x; drag.ly = y; drag.lt = now;
      } else {
        trailAcc += Math.hypot(x - lastMx, y - lastMy);
        while (trailAcc > 14 && dust.length < 80) {
          trailAcc -= 14;
          dust.push({ x: x + (rand() - 0.5) * 8, y: y + (rand() - 0.5) * 8, vx: (rand() - 0.5) * 18, vy: (rand() - 0.5) * 18 + 6, life: 0.8 + rand() * 0.9, age: 0 });
        }
      }
      lastMx = x; lastMy = y;
    };

    const onDown = (e) => {
      if (ignore(e) || e.button > 0) return;
      const [x, y] = local(e);
      pts.set(e.pointerId, { x, y });
      if (pts.size === 2) { const [a, b] = [...pts.values()]; pinchD = Math.hypot(a.x - b.x, a.y - b.y); return; }
      Object.assign(drag, { down: true, on: false, can: e.pointerType !== "touch" || fullControl, id: e.pointerId, lx: x, ly: y, lt: performance.now(), t0: performance.now(), moved: 0 });
      view.vx = view.vy = 0;
      ptr.x = x; ptr.y = y; ptr.in = true;
      if (fullControl) canvas.setPointerCapture?.(e.pointerId);
    };

    const endDrag = () => { drag.down = false; drag.on = false; document.body.style.userSelect = ""; };

    const onUp = (e) => {
      pts.delete(e.pointerId); pinchD = 0;
      if (!drag.down || drag.id !== e.pointerId) return;
      const wasTap = !drag.on && drag.moved < 6 && performance.now() - drag.t0 < 500;
      endDrag();
      if (wasTap) {
        const [x, y] = local(e), now = performance.now(), dbl = now - lastTap < 350;
        lastTap = dbl ? 0 : now;
        shootAt(x, y, dbl);
      }
      if (e.pointerType === "touch") ptr.in = false;
    };

    const onCancel = (e) => { pts.delete(e.pointerId); pinchD = 0; endDrag(); ptr.in = false; };
    const onOut = (e) => { if (!e.relatedTarget) ptr.in = false; };
    const onWheel = (e) => { e.preventDefault(); view.zoomT = clamp(view.zoomT * Math.exp(-e.deltaY * 0.0015), 1, 2.6); };
    const onScroll = () => { view.scroll = window.scrollY; };

    function draw(dt) {
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.globalCompositeOperation = "source-over";
      ctx.globalAlpha = 1;
      ctx.fillStyle = "#05020c";
      ctx.fillRect(0, 0, W, H);

      if (!reduce) ctx.translate(0.16 * (Math.sin(t * 7.3) + Math.sin(t * 11.1 + 2)), 0.16 * (Math.sin(t * 6.1 + 1) + Math.sin(t * 13.7)));

      view.zoom += (view.zoomT - view.zoom) * Math.min(1, dt * 8);
      if (!drag.on) {
        view.panX += view.vx * dt; view.panY += view.vy * dt;
        const f = Math.exp(-3 * dt); view.vx *= f; view.vy *= f;
      }
      const zoom = view.zoom;
      const k = Math.max(W / sky.width, H / sky.height) * 1.6;
      const S = sky.height * k, Sz = S * zoom, cx = W / 2, cy = H / 2;
      const maxX = Math.max(0, (sky.width * k * zoom) / 2 - W / 2 - 70);
      const maxY = Math.max(0, (sky.height * k * zoom) / 2 - H / 2 - 70);
      view.panX = clamp(view.panX, -maxX, maxX); view.panY = clamp(view.panY, -maxY, maxY);
      const ox = view.panX;
      const oy = clamp(view.panY - clamp(view.scroll * 0.05, 0, maxY * 0.8), -maxY, maxY);
      ptr.sx += ((ptr.in ? ptr.nx : 0) - ptr.sx) * Math.min(1, dt * 3);
      ptr.sy += ((ptr.in ? ptr.ny : 0) - ptr.sy) * Math.min(1, dt * 3);
      ptr.a += ((ptr.in ? 1 : 0) - ptr.a) * Math.min(1, dt * 6);

      const rot = reduce ? 0 : 0.06 * Math.sin(t * 0.03);
      const cr = Math.cos(rot), sr = Math.sin(rot);
      ctx.save();
      ctx.translate(cx + ox + ptr.sx * 5, cy + oy + ptr.sy * 3);
      ctx.rotate(rot);
      ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = "high";
      ctx.drawImage(sky, (-sky.width * k * zoom) / 2, (-sky.height * k * zoom) / 2, sky.width * k * zoom, sky.height * k * zoom);
      ctx.restore();

      const RAD = Math.max(140, Math.min(W, H) * 0.2), RAD2 = RAD * RAD;
      const near = ptr.a > 0.02;
      cand.length = 0;
      ctx.globalCompositeOperation = "lighter";
      let lastCi = -1;
      for (let i = 0; i < stars.px.length; i++) {
        const sx = stars.px[i], sy = stars.py[i], b = stars.br[i];
        const dep = 0.4 + b;
        const x = cx + ox + ptr.sx * 9 * dep + (sx * cr - sy * sr) * Sz;
        const y = cy + oy + ptr.sy * 6 * dep + (sx * sr + sy * cr) * Sz;
        if (x < -4 || x > W + 4 || y < -4 || y > H + 4) continue;
        if (stars.ci[i] !== lastCi) {
          lastCi = stars.ci[i];
          const c = PALETTE[lastCi];
          ctx.fillStyle = `rgb(${c[0]},${c[1]},${c[2]})`;
        }
        let tw = 1 - 0.3 * (0.5 + 0.5 * Math.sin(t * (1.1 + stars.ph[i] * 0.35) + stars.ph[i] * 40));
        let boost = 1;
        if (near) {
          const dx = x - ptr.x, dy = y - ptr.y, d2 = dx * dx + dy * dy;
          if (d2 < RAD2) {
            const f = 1 - Math.sqrt(d2) / RAD;
            boost = 1 + 1.6 * f * ptr.a;
            if (b > 0.32 && cand.length < 28) cand.push({ x, y, f });
          }
        }
        ctx.globalAlpha = Math.min(1, b * 1.15 * tw * boost);
        const s = (b > 0.55 ? 1.7 : b > 0.3 ? 1.2 : 0.9) * (1 + 0.25 * (zoom - 1)) * (boost > 1.3 ? 1.35 : 1);
        ctx.fillRect(x - s / 2, y - s / 2, s, s);
      }
      for (const s of stars.bright) {
        const dep = 0.4 + s.b;
        const x = cx + ox + ptr.sx * 9 * dep + (s.x * cr - s.y * sr) * Sz;
        const y = cy + oy + ptr.sy * 6 * dep + (s.x * sr + s.y * cr) * Sz;
        if (x < -30 || x > W + 30 || y < -30 || y > H + 30) continue;
        let f = 0;
        if (near) {
          const d = Math.hypot(x - ptr.x, y - ptr.y);
          if (d < RAD) { f = (1 - d / RAD) * ptr.a; if (cand.length < 28) cand.push({ x, y, f }); }
        }
        const tw = (0.82 + 0.18 * Math.sin(t * 1.7 + s.ph * 9)) * (1 + 0.6 * f);
        const [r, g, b] = s.c, Rg = (6 + s.b * 13) * (1 + 0.8 * f);
        const gr = ctx.createRadialGradient(x, y, 0, x, y, Rg);
        gr.addColorStop(0, `rgba(${r},${g},${b},${Math.min(1, 0.5 * tw)})`);
        gr.addColorStop(0.25, `rgba(${r},${g},${b},${0.12 * tw})`);
        gr.addColorStop(1, `rgba(${r},${g},${b},0)`);
        ctx.globalAlpha = 1; ctx.fillStyle = gr;
        ctx.fillRect(x - Rg, y - Rg, Rg * 2, Rg * 2);
        ctx.fillStyle = `rgba(255,255,255,${Math.min(1, tw)})`;
        ctx.beginPath(); ctx.arc(x, y, 0.9 + s.b * 0.8, 0, TAU); ctx.fill();
        if (s.b > 0.9 || f > 0.15) {
          const L = (12 + s.b * 12) * (1 + 1.4 * f);
          ctx.strokeStyle = `rgba(${r},${g},${b},${Math.min(0.6, 0.22 * tw)})`; ctx.lineWidth = 0.6;
          ctx.beginPath();
          ctx.moveTo(x - L, y); ctx.lineTo(x + L, y); ctx.moveTo(x, y - L); ctx.lineTo(x, y + L);
          ctx.stroke();
        }
      }

      if (near && cand.length > 1) {
        ctx.lineWidth = 0.8;
        for (let i = 0; i < cand.length; i++) {
          const a = cand[i];
          let n1 = -1, n2 = -1, d1 = 130 * 130, d2 = d1;
          for (let j = 0; j < cand.length; j++) {
            if (j === i) continue;
            const dd = (a.x - cand[j].x) ** 2 + (a.y - cand[j].y) ** 2;
            if (dd < d1) { d2 = d1; n2 = n1; d1 = dd; n1 = j; }
            else if (dd < d2) { d2 = dd; n2 = j; }
          }
          for (const n of [n1, n2]) {
            if (n < 0) continue;
            const c = cand[n];
            ctx.strokeStyle = `rgba(190,175,255,${0.3 * Math.min(a.f, c.f) * ptr.a})`;
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(c.x, c.y); ctx.stroke();
          }
          ctx.strokeStyle = `rgba(215,205,255,${0.5 * a.f * ptr.a})`;
          ctx.beginPath(); ctx.arc(a.x, a.y, 3.5 + a.f * 3, 0, TAU); ctx.stroke();
        }
      }
      ctx.globalAlpha = 1;

      for (let i = dust.length - 1; i >= 0; i--) {
        const p = dust[i];
        p.age += dt;
        if (p.age > p.life) { dust.splice(i, 1); continue; }
        p.x += p.vx * dt; p.y += p.vy * dt;
        const a = 1 - p.age / p.life;
        ctx.globalAlpha = a * 0.16; ctx.fillStyle = "rgb(190,170,255)";
        ctx.fillRect(p.x - 2.5, p.y - 2.5, 5, 5);
        ctx.globalAlpha = a * 0.9; ctx.fillStyle = "rgb(235,228,255)";
        ctx.fillRect(p.x - 0.7, p.y - 0.7, 1.4, 1.4);
      }
      for (let i = ripples.length - 1; i >= 0; i--) {
        const r = ripples[i];
        r.age += dt;
        const kk = r.age / 0.9;
        if (kk > 1) { ripples.splice(i, 1); continue; }
        ctx.globalAlpha = 0.4 * Math.pow(1 - kk, 1.5);
        ctx.strokeStyle = "rgb(190,170,255)"; ctx.lineWidth = 1.2;
        ctx.beginPath(); ctx.arc(r.x, r.y, 6 + kk * 130, 0, TAU); ctx.stroke();
      }
      ctx.globalAlpha = 1;

      if (!reduce) {
        if (satellites) {
          nextSat -= dt;
          if (nextSat <= 0) {
            const kind = rand();
            sats.push({
              x: -30, y: H * (0.05 + rand() * 0.8), vx: 26 + rand() * 40, vy: (rand() - 0.5) * 8,
              b: 0.6 + rand() * 0.4, iss: kind < 0.2, train: kind > 0.8 ? 8 + ((rand() * 5) | 0) : 1, ph: rand() * TAU,
            });
            nextSat = 8 + rand() * 14;
          }
          for (let i = sats.length - 1; i >= 0; i--) {
            const s = sats[i];
            s.x += s.vx * dt; s.y += s.vy * dt;
            if (s.x - s.train * 16 > W + 30) { sats.splice(i, 1); continue; }
            for (let j = 0; j < s.train; j++) {
              const px = s.x - j * 16 * (s.vx / 40), py = s.y - j * 16 * (s.vy / 40);
              const fade = clamp(px / (W * 0.08)) * clamp((W - px) / (W * 0.12));
              const al = fade * s.b * (s.iss ? 1 : 0.55) * (0.8 + 0.2 * Math.sin(t * 3 + s.ph + j));
              if (al < 0.02) continue;
              const sz = s.iss ? 2 : 1.3;
              ctx.globalAlpha = al * 0.22; ctx.fillStyle = "rgb(210,215,255)";
              ctx.fillRect(px - sz * 2, py - sz * 2, sz * 4, sz * 4);
              ctx.globalAlpha = al; ctx.fillStyle = "rgb(255,255,255)";
              ctx.fillRect(px - sz / 2, py - sz / 2, sz, sz);
            }
          }
          ctx.globalAlpha = 1;
        }

        for (let i = shooting.length - 1; i >= 0; i--) {
          const m = shooting[i];
          m.age += dt;
          if (m.age > m.life) { shooting.splice(i, 1); continue; }
          m.x += m.dx * m.speed * dt; m.y += m.dy * m.speed * dt;
          const env = Math.pow(Math.sin(Math.PI * Math.min(1, m.age / m.life)), 0.6);
          const L = m.len * (0.35 + 0.65 * env);
          const tx = m.x - m.dx * L, ty = m.y - m.dy * L, [r, g, b] = m.tint;
          const gr = ctx.createLinearGradient(tx, ty, m.x, m.y);
          gr.addColorStop(0, `rgba(${r},${g},${b},0)`);
          gr.addColorStop(0.7, `rgba(${r},${g},${b},${0.35 * env})`);
          gr.addColorStop(1, `rgba(255,255,255,${env})`);
          ctx.lineCap = "round"; ctx.strokeStyle = gr;
          ctx.globalAlpha = 0.2; ctx.lineWidth = m.w * 4.5;
          ctx.beginPath(); ctx.moveTo(tx, ty); ctx.lineTo(m.x, m.y); ctx.stroke();
          ctx.globalAlpha = 1; ctx.lineWidth = m.w;
          ctx.beginPath(); ctx.moveTo(tx, ty); ctx.lineTo(m.x, m.y); ctx.stroke();
          const hr = m.w * 7;
          const hg = ctx.createRadialGradient(m.x, m.y, 0, m.x, m.y, hr);
          hg.addColorStop(0, `rgba(255,255,255,${env})`);
          hg.addColorStop(0.3, `rgba(${r},${g},${b},${0.4 * env})`);
          hg.addColorStop(1, `rgba(${r},${g},${b},0)`);
          ctx.fillStyle = hg; ctx.fillRect(m.x - hr, m.y - hr, hr * 2, hr * 2);
          if (m.big) {
            flash = Math.max(flash, 0.045 * env);
            for (let n = 0; n < 2; n++) {
              const a = rand() * TAU, sp = 20 + rand() * 90;
              sparks.push({ x: m.x, y: m.y, vx: Math.cos(a) * sp - m.dx * 60, vy: Math.sin(a) * sp - m.dy * 60 + 20, life: 0.4 + rand() * 0.6, age: 0 });
            }
          }
        }
        for (let i = sparks.length - 1; i >= 0; i--) {
          const p = sparks[i];
          p.age += dt;
          if (p.age > p.life) { sparks.splice(i, 1); continue; }
          p.x += p.vx * dt; p.y += p.vy * dt; p.vy += 40 * dt;
          const a = 1 - p.age / p.life;
          ctx.globalAlpha = a * 0.9;
          ctx.fillStyle = a > 0.5 ? "rgb(255,230,190)" : "rgb(255,150,80)";
          ctx.fillRect(p.x, p.y, 1.3, 1.3);
        }
        ctx.globalAlpha = 1;
        if (flash > 0.002) {
          ctx.globalAlpha = flash; ctx.fillStyle = "rgb(150,130,255)";
          ctx.fillRect(0, 0, W, H);
          ctx.globalAlpha = 1; flash *= 0.9;
        }
        if (meteors) {
          nextMeteor -= dt;
          if (nextMeteor <= 0) {
            const big = rand() < 0.09;
            shooting.push(spawnMeteor(W, H, rand, big));
            if (!big && rand() < 0.25) shooting.push(spawnMeteor(W, H, rand, false));
            nextMeteor = 1.8 + rand() * 5;
          }
        }
      }

      ctx.globalCompositeOperation = "lighter";
      ctx.globalAlpha = 0.045;
      const gx = reduce ? 0 : (rand() * 256) | 0, gy = reduce ? 0 : (rand() * 256) | 0;
      ctx.translate(-gx, -gy);
      ctx.fillStyle = grainPat;
      ctx.fillRect(gx, gy, W + 4, H + 4);
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = "source-over";
    }

    const loop = (now) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now; t += dt;
      draw(dt);
      raf = requestAnimationFrame(loop);
    };

    resize();
    window.addEventListener("resize", resize);

    const target = fullControl ? canvas : window;
    const wantsEvents = interactive && !reduce;
    if (wantsEvents) {
      target.addEventListener("pointermove", onMove, { passive: true });
      target.addEventListener("pointerdown", onDown);
      target.addEventListener("pointerup", onUp);
      target.addEventListener("pointercancel", onCancel);
      window.addEventListener("mouseout", onOut);
      window.addEventListener("blur", onCancel);
      window.addEventListener("scroll", onScroll, { passive: true });
      if (fullControl) canvas.addEventListener("wheel", onWheel, { passive: false });
      onScroll();
    }

    if (reduce) draw(0);
    else raf = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      if (wantsEvents) {
        target.removeEventListener("pointermove", onMove);
        target.removeEventListener("pointerdown", onDown);
        target.removeEventListener("pointerup", onUp);
        target.removeEventListener("pointercancel", onCancel);
        window.removeEventListener("mouseout", onOut);
        window.removeEventListener("blur", onCancel);
        window.removeEventListener("scroll", onScroll);
        if (fullControl) canvas.removeEventListener("wheel", onWheel);
        document.body.style.userSelect = "";
      }
    };
  }, [interactive, fullControl, meteors, satellites, density, seed]);

  const pos = fixed ? "fixed inset-0 -z-10" : "absolute inset-0 z-0";
  const events = fullControl && interactive ? "pointer-events-auto" : "pointer-events-none";

  return (
    <div aria-hidden="true" className={`${pos} ${events} overflow-hidden bg-[#05020c] ${className}`}>
      <canvas
        ref={canvasRef}
        className={`block h-full w-full ${fullControl && interactive ? "cursor-grab touch-none active:cursor-grabbing" : ""}`}
      />
      <div
        className="pointer-events-none absolute inset-0"
        style={{ background: "radial-gradient(ellipse at center, transparent 45%, rgba(3,0,10,0.7) 100%)" }}
      />
    </div>
  );
}