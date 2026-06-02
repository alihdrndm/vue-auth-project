const { CompositionStage, useComposition } = window;
const css = str => { const o = {}; str.split(';').forEach(d => { const i = d.indexOf(':'); if (i < 0) return; const k = d.slice(0, i).trim(), v = d.slice(i + 1).trim(); if (!k) return; o[k.replace(/-([a-z])/g, (m, c) => c.toUpperCase())] = v; }); return o; };
const Icon = ({ name, size = 16, color }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={(1.5 * 24 / size).toFixed(3)} strokeLinecap="round" strokeLinejoin="round" style={{ flex: 'none', color }} aria-hidden="true" dangerouslySetInnerHTML={{ __html: (window.EG_ICON_PATHS || {})[name] || '' }} />;
const DOCS = [['RE-2026-0412.xml', 'Elektro Kessler GmbH', 'RE-2026-0412', 'XRechnung · UBL', 'file-code', 'valid'], ['SA-26-1187.pdf', 'Spedition Albers GmbH', 'SA/26/1187', 'ZUGFeRD · EN 16931', 'paperclip', 'valid'], ['2026-1043.pdf', 'Druckerei Sommer GmbH', '2026-1043', 'Plain PDF', 'file-text', 'ai'], ['F-2026-118.pdf', 'Atelier Moreau SARL', 'F-2026-118', 'ZUGFeRD · BASIC WL', 'paperclip', 'bwl']];
const V = { valid: ['Valid e-invoice', 'circle-check', '#e4f1ed', '#0f6e62', '', '#746c61'], ai: ['Not an e-invoice', 'info', '#f6f0e6', '#746c61', 'AI-read, 1 field to check', '#8a4a06'], bwl: ['Not an e-invoice', 'info', '#f6f0e6', '#746c61', '(profile BASIC WL)', '#746c61'], wait: ['Processing', 'loader', '#e6eef7', '#2f5d8a', '', '#746c61'] };
const NOTE = 'Called on the number we already had; the change is real.';
const cl = (x, a, b) => Math.max(0, Math.min(1, (x - a) / (b - a)));
const ez = p => p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
const SH = '0 30px 60px -34px #3a2a1480, 0 2px 8px -3px #3a2a1433', SHS = '0 1px 0 #3a2a140f, 0 30px 60px -34px #3a2a1470, 0 2px 6px -2px #3a2a1426';
const Chip = ({ label, icon, bg, fg, ic, sq }) => <span style={css('display:inline-flex;align-items:center;gap:4px;height:24px;padding:0 8px;font-size:12px;font-weight:500;white-space:nowrap;border-radius:' + (sq ? '6px;border:1px solid #d6cbbb' : '999px') + ';background:' + bg + ';color:' + fg)}><Icon name={icon} size={14} color={ic} />{label}</span>;
const Btn = ({ label, icon, on, press, h = 32 }) => <span style={css('display:inline-flex;align-items:center;justify-content:center;gap:4px;white-space:nowrap;padding:0 12px;border-radius:6px;font-weight:500;height:' + h + 'px;font-size:' + (h > 40 ? 15 : 13) + 'px;' + (on ? 'background:' + (press ? '#3f3a33' : '#1f1c18') + ';color:#fffdf9;border:1px solid #1f1c18;transform:' + (press ? 'translateY(1px)' : 'none') : 'background:#f6f0e6;color:#746c61;border:1px solid #ebe3d6'))}>{icon ? <Icon name={icon} size={14} /> : null}{label}</span>;

function HeroScene({ T, C, poster }) {
  const c = C || { Stamp: 0, Open: 3, Resolve: 6, Approve: 9 }, end = c.Approve + 3;
  const at = i => c.Stamp + 0.3 + i * 0.65;
  const typed = Math.round(cl(T, c.Resolve, c.Resolve + 1.3) * NOTE.length), resolved = T >= c.Resolve + 1.7, reviewed = T >= c.Resolve + 2.5, approved = T >= c.Approve + 0.8;
  const pressR = T >= c.Resolve + 1.45 && T < c.Resolve + 1.65, pressM = T >= c.Resolve + 2.25 && T < c.Resolve + 2.45, pressA = T >= c.Approve + 0.55 && T < c.Approve + 0.8;
  const cardP = ez(cl(T, c.Resolve + 2.9, c.Approve + 0.3)), rowP = ez(cl(T, c.Approve + 1.0, c.Approve + 1.6));
  const fade = poster ? 1 : (T < 0.3 ? cl(T, 0, 0.3) : 1 - cl(T, end - 0.5, end));
  const act = T < c.Open ? 'A' : T < c.Resolve + 2.8 ? 'B' : 'C', dim = k => (poster || act === k ? 1 : 0.45);
  const st = approved ? ['Approved', 'circle-check', '#e4f1ed', '#0f6e62'] : reviewed ? ['Awaiting approval', 'hourglass', '#e8edf7', '#2c4a8a'] : ['Needs review', 'eye', '#fcefd8', '#8a4a06'];
  const rows = DOCS.map((d, i) => ({ d, i })).filter(({ i }) => T >= at(i) + 0.1).reverse();
  return (
    <div style={css('position:absolute;inset:0;font-family:Instrument Sans,sans-serif;font-size:14px;line-height:1.45;color:#3f3a33;background-color:#ebe4d6;background-image:linear-gradient(#3a2a140b 1px,transparent 1px),linear-gradient(90deg,#3a2a140b 1px,transparent 1px);background-size:32px 32px')}>
      <div style={{ position: 'absolute', inset: 0, opacity: fade }}>
        <div style={css('position:absolute;left:40px;top:28px;display:flex;align-items:center;gap:12px')}><span style={css('width:28px;height:28px;display:grid;place-items:center;border:1.75px solid #2c4a8a;border-radius:4px;outline:0.7px solid #2c4a8a;outline-offset:-4.9px;background:#fffdf9;color:#2c4a8a;font:700 15px/1 Barlow Condensed,sans-serif')}>E</span><span style={css('font:700 21px/1 Familjen Grotesk,sans-serif;letter-spacing:-0.025em;color:#1f1c18')}>Eingang</span></div>
        <span style={css('position:absolute;right:40px;top:32px;display:inline-flex;align-items:center;height:24px;padding:0 12px;border-radius:999px;font-size:13px;font-weight:500;color:#5f574d;border:1px dashed #5f574d;background:#fdfaf4')}>Sample data</span>

        <div style={{ ...css('position:absolute;left:40px;top:84px;width:380px;height:600px'), opacity: dim('A') }}>
          <div style={css('display:grid;grid-template-columns:repeat(4,1fr);gap:12px')}>
            {DOCS.map((d, i) => { const s = cl(T, at(i), at(i) + 0.14); return (
              <div key={i} style={{ ...css('position:relative;height:72px;padding:8px;background:#fdfaf4;border-radius:8px;display:grid;align-content:start;gap:4px'), boxShadow: SHS, transform: s > 0 && s < 1 ? 'translateY(2px)' : 'none' }}>
                <Icon name={d[4]} size={16} color="#746c61" /><span style={css('font:12px/1.2 JetBrains Mono,monospace;color:#1f1c18;overflow:hidden;text-overflow:ellipsis;white-space:nowrap')}>{d[0]}</span>
                <span style={{ position: 'absolute', right: 4, bottom: 4, opacity: s, transform: 'rotate(-8deg) scale(' + (1.25 - 0.25 * s).toFixed(3) + ')' }}><span style={css('display:inline-grid;padding:3px 5px;border:1px solid #2c4a8a;border-radius:2px;color:#2c4a8a;font:700 14px/1 Barlow Condensed,sans-serif;text-transform:uppercase;letter-spacing:0.08em;background:#fdfaf4')}>Eingang</span></span>
              </div>); })}
          </div>
          <div style={{ ...css('margin-top:20px;height:508px;background:#fffdf9;border:1px solid #ebe3d6;border-radius:12px;overflow:hidden'), boxShadow: SH }}>
            <div style={css('display:flex;align-items:center;gap:8px;height:40px;padding:0 16px;background:#f7f2ea;border-bottom:1px solid #ebe3d6')}><Icon name="inbox" size={16} color="#1f1c18" /><span style={css('font:700 16px/1 Familjen Grotesk,sans-serif;color:#1f1c18')}>Inbox</span><span style={{ flex: 1 }} /><span style={css('font:500 12px JetBrains Mono,monospace;color:#3f3a33')}>{rows.length} invoices</span></div>
            {rows.map(({ d, i }) => { const p = ez(cl(T, at(i) + 0.1, at(i) + 0.34)), v = V[T >= at(i) + 0.5 ? d[5] : 'wait']; return (
              <div key={i} style={{ ...css('display:grid;gap:8px;padding:12px 16px;border-bottom:1px solid #ebe3d6'), opacity: p, transform: 'translateY(' + ((1 - p) * -8).toFixed(1) + 'px)' }}>
                <div style={css('display:flex;justify-content:space-between;gap:8px')}><span style={css('font-size:14px;font-weight:500;color:#1f1c18')}>{d[1]}</span><span style={css('font:12px JetBrains Mono,monospace;color:#746c61')}>{d[2]}</span></div>
                <div style={css('display:flex;flex-wrap:wrap;gap:8px;align-items:center')}><Chip label={d[3]} icon={d[4]} bg="#fffdf9" fg="#3f3a33" sq /><Chip label={v[0]} icon={v[1]} bg={v[2]} fg={v[3]} />{v[4] ? <span style={{ fontSize: 12, color: v[5] }}>{v[4]}</span> : null}</div>
              </div>); })}
          </div>
        </div>

        <div style={{ ...css('position:absolute;left:450px;top:84px;width:380px;height:600px'), opacity: dim('B') }}>
          <div style={{ ...css('height:600px;background:#fffdf9;border:1px solid #ebe3d6;border-radius:12px;display:grid;grid-template-rows:auto 1fr auto'), boxShadow: SH }}>
            <div style={css('display:grid;gap:8px;padding:16px;background:#f7f2ea;border-bottom:1px solid #ebe3d6;border-radius:12px 12px 0 0')}>
              <div style={css('display:flex;justify-content:space-between;align-items:center;gap:8px')}><span style={css('font:700 18px/1.2 Familjen Grotesk,sans-serif;letter-spacing:-0.025em;color:#1f1c18')}>Bürobedarf Nord KG</span><Chip label={st[0]} icon={st[1]} bg={st[2]} fg={st[3]} /></div>
              <span style={css('font:13px JetBrains Mono,monospace;color:#746c61')}>BN-88290, 97,58 €</span>
            </div>
            <div style={{ padding: 16 }}>
              <div style={css('position:relative;display:grid;gap:12px;padding:16px;border:1px solid #ebe3d6;border-radius:8px')}>
                <div style={css('display:grid;gap:4px')}><span style={{ ...css('display:inline-flex;align-items:center;gap:4px;font-size:13px;font-weight:500'), color: resolved ? '#0f6e62' : '#b42318' }}><Icon name={resolved ? 'circle-check' : 'octagon'} size={16} />{resolved ? 'Resolved by Anna Weber' : 'Block'}</span><span style={css('font-size:15px;font-weight:600;color:#1f1c18')}>Bank account differs from earlier invoices</span></div>
                <div style={css('display:grid;gap:4px;font-size:13px')}><span style={css('font-size:12px;color:#746c61')}>Before</span><span style={css('font-family:JetBrains Mono,monospace;color:#1f1c18')}>DE89 3704 0044 0532 0130 00</span><span style={css('font-size:12px;color:#746c61;padding-top:4px')}>Now</span><span style={css('display:flex;flex-wrap:wrap;gap:8px;align-items:center')}><span style={css('font-family:JetBrains Mono,monospace;color:#1f1c18')}>DE02 1203 0000 0000 2020 51</span>{resolved ? <Chip label="Confirmed change" icon="circle-check" bg="#e4f1ed" fg="#0f6e62" /> : <Chip label="New account" icon="circle-alert" bg="#fbe9e6" fg="#b42318" />}</span></div>
                <div style={css('display:grid;gap:4px')}><span style={css('font-size:13px;font-weight:500;color:#1f1c18')}>How did you check this?</span><div style={{ ...css('min-height:64px;padding:8px 12px;border-radius:6px;background:#fffdf9;font-size:14px;color:#1f1c18'), border: '1px solid ' + (T >= c.Resolve - 0.2 && !resolved ? '#1f1c18' : '#d6cbbb') }}>{NOTE.slice(0, typed)}<span style={{ display: 'inline-block', width: 1, height: 16, verticalAlign: -3, background: '#1f1c18', opacity: !resolved && T >= c.Resolve - 0.2 && Math.floor(T * 2) % 2 === 0 ? 1 : 0 }} /></div></div>
                <div>{resolved ? <span style={css('display:inline-flex;align-items:center;gap:4px;height:28px;padding:0 12px;border-radius:6px;font-size:13px;font-weight:500;background:#e4f1ed;color:#0f6e62')}><Icon name="check" size={14} />Check resolved</span> : <Btn label="Resolve check" on press={pressR} h={28} />}</div>
                <svg aria-hidden="true" width="380" height="372" viewBox="0 0 380 372" style={{ position: 'absolute', left: -16, top: -12, overflow: 'visible', pointerEvents: 'none' }}><path d="M 200 6 C 320 4, 372 60, 372 186 C 372 330, 300 368, 180 366 C 60 365, 6 320, 6 190 C 6 60, 70 8, 230 10" fill="none" stroke="#d3241b" strokeWidth="2.4" strokeLinecap="round" strokeDasharray="1300" strokeDashoffset={(1300 * (1 - ez(cl(T, c.Open + 0.3, c.Open + 1.2)))).toFixed(0)} /></svg>
              </div>
            </div>
            <div style={css('display:flex;justify-content:flex-end;padding:12px 16px;background:#f7f2ea;border-top:1px solid #ebe3d6;border-radius:0 0 12px 12px')}><Btn label={reviewed ? 'Marked reviewed' : 'Mark reviewed'} on={resolved && !reviewed} press={pressM} /></div>
          </div>
        </div>

        <div style={{ ...css('position:absolute;left:860px;top:84px;width:380px;height:600px'), opacity: dim('C') }}>
          <div style={{ ...css('margin:0 auto;width:300px;height:372px;border:8px solid #1f1c18;border-radius:40px;background:#fffdf9;overflow:hidden;display:grid;grid-template-rows:44px 1fr'), boxShadow: SH }}>
            <div style={css('display:flex;align-items:center;gap:8px;padding:0 16px;background:#f7f2ea;border-bottom:1px solid #ebe3d6')}><span style={css('font:700 16px/1 Familjen Grotesk,sans-serif;color:#1f1c18')}>Approvals</span><span style={{ flex: 1 }} /><span style={css('width:28px;height:28px;border-radius:999px;background:#e8edf7;color:#2c4a8a;display:grid;place-items:center;font-size:12px;font-weight:600')}>JB</span></div>
            <div style={{ padding: 12 }}>
              <div style={{ ...css('display:grid;gap:12px;padding:12px;border:1px solid #ebe3d6;border-radius:8px'), opacity: cardP, transform: 'translateY(' + ((1 - cardP) * 24).toFixed(1) + 'px)' }}>
                <div style={{ display: 'grid' }}><span style={css('font-size:14px;font-weight:600;color:#1f1c18')}>Bürobedarf Nord KG</span><span style={css('font:12px JetBrains Mono,monospace;color:#746c61')}>BN-88290</span></div>
                <span style={css('font:500 21px JetBrains Mono,monospace;color:#1f1c18')}>97,58 €</span>
                <span style={css('font-size:12px;color:#746c61')}>Reviewed by Anna Weber, just now</span>
                {approved ? <div style={css('display:flex;gap:8px;align-items:center;min-height:44px;padding:8px 12px;border-radius:6px;background:#e4f1ed;color:#0f6e62;font-size:13px;font-weight:500')}><Icon name="circle-check" size={16} />You approved this on 09 Oct 2026.</div>
                  : <div style={css('display:grid;grid-template-columns:1fr 1fr;gap:8px')}><span style={css('display:grid;place-items:center;height:44px;border-radius:6px;font-size:15px;font-weight:500;background:#fbe9e6;color:#b42318;border:1px solid #b42318')}>Reject…</span><Btn label="Approve" icon="check" on press={pressA} h={44} /></div>}
              </div>
            </div>
          </div>
          <div style={css('position:relative;width:340px;height:200px;margin:24px auto 0')}>
            <svg aria-hidden="true" width="340" height="200" viewBox="0 0 340 200" style={{ position: 'absolute', inset: 0, overflow: 'visible' }}><path d="M 16 54 C 16 44, 22 38, 32 38 L 116 36 C 124 36, 127 40, 131 46 L 140 58 L 316 56 C 324 56, 326 62, 326 70 L 324 188 L 20 190 Z" fill="#fdfaf4" stroke="#d3241b" strokeWidth="2.2" strokeLinejoin="round" /></svg>
            <div style={{ ...css('position:absolute;left:24px;top:30px;width:292px;height:40px;display:flex;align-items:center;gap:8px;padding:0 12px;background:#fffdf9;border:1px solid #ebe3d6;border-radius:6px;font-size:12px;color:#1f1c18'), opacity: T >= c.Approve + 1.0 ? 1 : 0, transform: 'translateY(' + (-48 + 74 * rowP).toFixed(1) + 'px)' }}><span style={{ fontFamily: 'JetBrains Mono,monospace' }}>BN-88290</span><span style={{ flex: 1 }} /><span style={{ fontFamily: 'JetBrains Mono,monospace' }}>97,58 €</span><Chip label="Exported" icon="check" bg="#f6f0e6" fg="#746c61" /></div>
            <svg aria-hidden="true" width="340" height="200" viewBox="0 0 340 200" style={{ position: 'absolute', inset: 0, overflow: 'visible' }}><path d="M 8 88 C 96 82, 236 80, 334 84 L 328 192 L 14 194 Z" fill="#fdfaf4" stroke="#d3241b" strokeWidth="2.2" strokeLinejoin="round" /></svg>
            <span lang="de" style={css('position:absolute;left:0;right:0;top:124px;text-align:center;font:600 28px/1 Caveat,cursive;color:#d3241b')}>Für den Steuerberater</span>
          </div>
        </div>
      </div>
    </div>);
}
function Live() { const { T, CUES } = useComposition(); return <HeroScene T={T} C={CUES} />; }
function RecordLoop() {
  const [T, setT] = React.useState(0);
  React.useEffect(() => {
    const fix = 'margin:0;width:1280px;height:720px;overflow:hidden;background:#ebe4d6';
    document.documentElement.style.cssText = fix; document.body.style.cssText = fix;
    const start = performance.now(); let raf;
    const tick = now => { setT(((now - start) / 1000) % 12); raf = requestAnimationFrame(tick); };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);
  return <div style={{ position: 'fixed', left: 0, top: 0, width: 1280, height: 720, overflow: 'hidden', zIndex: 2147483000 }}><HeroScene T={T} /></div>;
}
window.HeroStage = function HeroStage() { if (new URLSearchParams(window.location.search).get('record') === '1') return <RecordLoop />; return <CompositionStage width={1280} height={720} scenes={window.OM_SCENES} playback={window.OM_PLAYBACK} bg="#ebe4d6"><Live /></CompositionStage>; };
window.HeroPoster = function HeroPoster() { return <div style={{ position: 'relative', width: 1280, height: 720, overflow: 'hidden' }}><HeroScene T={10.8} poster /></div>; };
