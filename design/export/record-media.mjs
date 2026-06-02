// Renders the README media kit into docs/media/ (see "Media Kit Notes" in the handoff notes).
// Usage:
//   npx http-server design/export -p 4173 -s &          # serves the exported design pages
//   APP_URL=http://localhost:5173 node scripts/record-media.mjs [stills|hero|demo|all]
// Needs: playwright (npm i -D playwright && npx playwright install chromium) and ffmpeg on PATH.
import { chromium } from 'playwright';
import { execFileSync } from 'node:child_process';
import { mkdirSync, rmSync, statSync, writeFileSync, readdirSync, renameSync } from 'node:fs';
import path from 'node:path';

const DESIGN = process.env.DESIGN_URL || 'http://localhost:4173';
const APP = process.env.APP_URL || 'http://localhost:5173';
const OUT = 'docs/media', TMP = 'docs/media/.tmp';
const what = process.argv[2] || 'all';
const sh = (args) => execFileSync('ffmpeg', ['-y', '-loglevel', 'error', ...args], { stdio: 'inherit' });
const url = (p, q = '') => `${DESIGN}/${encodeURI(p)}${q}`;

try { execFileSync('ffmpeg', ['-version'], { stdio: 'ignore' }); } catch { console.error('ffmpeg not found. Install it (brew install ffmpeg / apt install ffmpeg) and run again.'); process.exit(1); }
mkdirSync(OUT, { recursive: true }); mkdirSync(TMP, { recursive: true });

const STILLS = [
  ['Media Architecture.dc.html', 'architecture.png', 1600, 1000],
  ['Media Lifecycle.dc.html', 'lifecycle.png', 1600, 1000],
  ['Media Hero Poster.dc.html', 'hero-poster.png', 1280, 720],
  ['Media Social Preview.dc.html', 'social-preview.png', 1280, 640],
  ['Media Feature Verdicts.dc.html', 'feature-verdicts.png', 1200, 675],
  ['Media Feature Evidence.dc.html', 'feature-evidence.png', 1200, 675],
  ['Media Feature Checks.dc.html', 'feature-checks.png', 1200, 675],
  ['Media Feature Approval.dc.html', 'feature-approval.png', 1200, 675]
];

async function settle(page) {
  await page.waitForLoadState('networkidle');
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(2500); // DC runtime, icons and nested iframes
}

async function shot(browser, file, out, w, h, q = '') {
  const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
  await page.goto(url(file, q)); await settle(page);
  await page.screenshot({ path: out, clip: { x: 0, y: 0, width: w, height: h } });
  await page.close();
}

async function stills(browser) {
  for (const [f, o, w, h] of STILLS) { await shot(browser, f, path.join(OUT, o), w, h); console.log('✓', o); }
}

async function hero(browser) {
  // Record the live loop at 1280×720, then cut exactly one 12 s cycle into a 960 px, 15 fps GIF.
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 }, recordVideo: { dir: TMP, size: { width: 1280, height: 720 } } });
  const page = await ctx.newPage();
  await page.goto(url('Media Hero.dc.html', '?record=1')); await settle(page);
  await page.waitForTimeout(26000); // two full cycles; we keep the second
  await ctx.close();
  const webm = path.join(TMP, readdirSync(TMP).find(n => n.endsWith('.webm')));
  // Find the loop start in the recording: the frame where the fade-in begins. Adjust SS if the cycle is off by a frame.
  const SS = process.env.HERO_SS || '14.5';
  let colors = 160;
  for (;;) {
    sh(['-ss', SS, '-t', '12', '-i', webm, '-vf', `fps=15,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=${colors}:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3`, path.join(OUT, 'hero.gif')]);
    const mb = statSync(path.join(OUT, 'hero.gif')).size / 1048576;
    if (mb < 8 || colors <= 48) { console.log(`✓ hero.gif ${mb.toFixed(1)} MB, ${colors} colours`); break; }
    colors -= 32;
  }
  await shot(browser, 'Media Hero Poster.dc.html', path.join(OUT, 'hero-poster.png'), 1280, 720);
}

// Storyboard: Media Demo Storyboard.dc.html. Card shots are rendered frames; app shots are recorded live.
const SHOTS = [
  { card: ['Media Demo Title.dc.html', ''], s: 4 },
  { app: async p => { await p.goto(APP); await p.getByRole('link', { name: 'Open the sandbox' }).first().click(); }, s: 5, cap: 'No sign-up: open the sandbox' },
  { card: ['Media Demo Chapters.dc.html', '?ch=1'], s: 3 },
  { app: async p => { await p.getByRole('tab', { name: /All/ }).click(); await p.mouse.move(1500, 300); await p.mouse.move(1500, 800, { steps: 40 }); }, s: 8, cap: 'Twelve invoices, each with a verdict' },
  { app: async p => { await p.getByRole('button', { name: 'Upload invoices' }).click(); await p.setInputFiles('input[type=file]', 'e2e/fixtures/sample-plain.pdf'); await p.waitForTimeout(8000); }, s: 10, cap: 'Watch it detect, validate, extract, check' },
  { card: ['Media Demo Chapters.dc.html', '?ch=2'], s: 3 },
  { app: async p => { await p.getByText('2026-1043').first().click(); await p.getByRole('button', { name: /Show where IBAN came from/ }).click(); await p.waitForTimeout(3000); await p.getByRole('button', { name: 'Show in document' }).click(); }, s: 9, cap: 'Every AI value shows its source' },
  { app: async p => { await p.getByRole('button', { name: 'Edit VAT ID' }).first().click(); await p.keyboard.type('DE 812 345 678', { delay: 90 }); await p.getByRole('button', { name: 'Save' }).click(); }, s: 5, cap: 'Low confidence? Type it from paper' },
  { card: ['Media Demo Chapters.dc.html', '?ch=3'], s: 3 },
  { app: async p => { await p.goto(APP + '/inbox'); await p.getByText('RE-2026-0413').first().click(); await p.getByRole('button', { name: 'Show official message' }).click(); await p.waitForTimeout(2500); await p.getByRole('button', { name: 'Show in XML' }).click(); }, s: 7, cap: 'Rule BR-DE-15, explained in plain English' },
  { app: async p => { await p.goto(APP + '/inbox'); await p.getByText('BN-88290').first().click(); await p.getByRole('button', { name: 'Resolve check' }).first().click(); await p.getByRole('textbox').last().type('Checked with the supplier on the number in our files.', { delay: 40 }); await p.getByRole('button', { name: 'Resolve check' }).last().click(); await p.getByRole('button', { name: 'Mark reviewed' }).click(); }, s: 10, cap: 'New bank account? Check before paying' },
  { card: ['Media Demo Chapters.dc.html', '?ch=4'], s: 3 },
  { app: async p => { /* switch to Jonas Brandt the way the sandbox offers it */ await p.goto(APP + '/approvals'); await p.getByRole('button', { name: /Approve BN-88290/ }).click(); }, s: 6, cap: 'A second person approves' },
  { app: async p => { await p.goto(APP + '/exports'); await p.getByRole('radio', { name: /one row per invoice/ }).click(); await p.getByRole('button', { name: /Export/ }).click(); await p.getByRole('link', { name: 'Download' }).first().click(); }, s: 6, cap: 'One CSV for the tax advisor' },
  { card: ['Media Demo End.dc.html', ''], s: 4 }
];

async function captionPng(browser, text, out) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.setContent(`<html><head><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@600&display=swap"></head><body style="margin:0;background:transparent"><div style="position:absolute;left:0;right:0;bottom:96px;display:grid;justify-items:center"><div style="padding:20px 40px;background:#1f1c18;border-radius:12px;font:600 44px/1.2 'Instrument Sans',sans-serif;color:#fffdf9">${text}</div></div></body></html>`);
  await page.evaluate(() => document.fonts.ready); await page.waitForTimeout(500);
  await page.screenshot({ path: out, omitBackground: true }); await page.close();
}

async function demo(browser) {
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, recordVideo: { dir: path.join(TMP, 'app'), size: { width: 1920, height: 1080 } } });
  const app = await ctx.newPage();
  const parts = [];
  let i = 0;
  for (const s of SHOTS) {
    i++; const seg = path.join(TMP, `seg-${String(i).padStart(2, '0')}.mp4`);
    if (s.card) {
      const png = path.join(TMP, `card-${i}.png`);
      await shot(browser, s.card[0], png, 1920, 1080, s.card[1]);
      sh(['-loop', '1', '-t', String(s.s), '-i', png, '-r', '30', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', seg]);
    } else {
      const t0 = Date.now(); await s.app(app); const used = (Date.now() - t0) / 1000;
      if (used < s.s) await app.waitForTimeout((s.s - used) * 1000);
      s.span = [t0, Date.now()];
    }
    parts.push({ s, seg });
  }
  const startAll = SHOTS.find(x => x.span).span[0];
  await ctx.close();
  const raw = path.join(TMP, 'app', readdirSync(path.join(TMP, 'app')).find(n => n.endsWith('.webm')));
  for (const { s, seg } of parts) {
    if (!s.span) continue;
    const cap = seg.replace('.mp4', '-cap.png'); await captionPng(browser, s.cap, cap);
    const ss = ((s.span[1] - startAll) / 1000 - s.s).toFixed(2); // last s seconds of the shot
    sh(['-ss', ss, '-t', String(s.s), '-i', raw, '-i', cap, '-filter_complex', '[0:v]fps=30,scale=1920:1080[v];[v][1:v]overlay=0:0', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-an', seg]);
  }
  const list = path.join(TMP, 'list.txt');
  writeFileSync(list, parts.map(p => `file '${path.resolve(p.seg)}'`).join('\n'));
  sh(['-f', 'concat', '-safe', '0', '-i', list, '-r', '30', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', path.join(OUT, 'demo.mp4')]);
  console.log('✓ demo.mp4');
}

const browser = await chromium.launch();
if (what === 'stills' || what === 'all') await stills(browser);
if (what === 'hero' || what === 'all') await hero(browser);
if (what === 'demo' || what === 'all') await demo(browser);
await browser.close();
rmSync(TMP, { recursive: true, force: true });
