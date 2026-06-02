(function () {
  if (window.__egUI) return; window.__egUI = true;
  var P = {
    inbox: '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
    check: '<path d="M20 6 9 17l-5-5"/>',
    'circle-check': '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    'check-check': '<path d="M18 6 7 17l-5-5"/><path d="m22 10-7.5 7.5L13 16"/>',
    hourglass: '<path d="M5 22h14"/><path d="M5 2h14"/><path d="M17 22v-4.172a2 2 0 0 0-.586-1.414L12 12l-4.414 4.414A2 2 0 0 0 7 17.828V22"/><path d="M7 2v4.172a2 2 0 0 0 .586 1.414L12 12l4.414-4.414A2 2 0 0 0 17 6.172V2"/>',
    loader: '<path d="M21 12a9 9 0 1 1-6.219-8.56"/>',
    triangle: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    octagon: '<path d="M12 16h.01"/><path d="M12 8v4"/><path d="M15.312 2a2 2 0 0 1 1.414.586l4.688 4.688A2 2 0 0 1 22 8.688v6.624a2 2 0 0 1-.586 1.414l-4.688 4.688a2 2 0 0 1-1.414.586H8.688a2 2 0 0 1-1.414-.586l-4.688-4.688A2 2 0 0 1 2 15.312V8.688a2 2 0 0 1 .586-1.414l4.688-4.688A2 2 0 0 1 8.688 2z"/>',
    info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M17 8l-5-5-5 5"/><path d="M12 3v12"/>',
    download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/>',
    'file-text': '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    'file-code': '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="m10 13-2 2 2 2"/><path d="m14 17 2-2-2-2"/>',
    pencil: '<path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/><path d="m15 5 4 4"/>',
    'chevron-down': '<path d="m6 9 6 6 6-6"/>',
    'chevron-right': '<path d="m9 18 6-6-6-6"/>',
    'chevron-left': '<path d="m15 18-6-6 6-6"/>',
    user: '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    building: '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/><path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/><path d="M10 18h4"/>',
    archive: '<rect width="20" height="5" x="2" y="3" rx="1"/><path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/><path d="M10 12h4"/>',
    gauge: '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
    sliders: '<path d="M21 4h-7"/><path d="M10 4H3"/><path d="M21 12h-9"/><path d="M8 12H3"/><path d="M21 20h-5"/><path d="M12 20H3"/><path d="M14 2v4"/><path d="M8 10v4"/><path d="M16 18v4"/>',
    more: '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>',
    plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
    landmark: '<path d="M3 22h18"/><path d="M6 18v-7"/><path d="M10 18v-7"/><path d="M14 18v-7"/><path d="M18 18v-7"/><path d="M12 2 20 7H4z"/>',
    copy: '<rect width="14" height="14" x="8" y="8" rx="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
    eye: '<path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/>',
    clock: '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    ban: '<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>',
    message: '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    lock: '<rect width="18" height="11" x="3" y="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    refresh: '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
    external: '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    circle: '<circle cx="12" cy="12" r="9"/>',
    minus: '<path d="M5 12h14"/>',
    'circle-alert': '<circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/>',
    'zoom-in': '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/><path d="M11 8v6"/><path d="M8 11h6"/>',
    'zoom-out': '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/><path d="M8 11h6"/>',
    paperclip: '<path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"/>'
  };
  var st = document.createElement('style');
  st.textContent = '@keyframes eg-spin{to{transform:rotate(360deg)}}e-icon,e-bars{display:inline-flex;flex:none;line-height:0}';
  document.head.appendChild(st);
  class EIcon extends HTMLElement {
    static get observedAttributes() { return ['name', 'size', 'spin']; }
    connectedCallback() { this.r(); }
    attributeChangedCallback() { if (this.isConnected) this.r(); }
    r() {
      var s = +(this.getAttribute('size') || 16);
      var sw = (1.5 * 24 / s).toFixed(3); // 1.5 px rendered stroke at any size
      var spin = this.getAttribute('spin') === 'true';
      var root = this.shadowRoot || this.attachShadow({ mode: 'open' });
      root.innerHTML = '<style>:host{display:inline-flex;flex:none;line-height:0}@keyframes eg-spin{to{transform:rotate(360deg)}}</style><svg xmlns="http://www.w3.org/2000/svg" width="' + s + '" height="' + s + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="' + sw + '" stroke-linecap="round" stroke-linejoin="round" focusable="false"' + (spin ? ' style="animation:eg-spin .9s linear infinite"' : '') + '>' + (P[this.getAttribute('name')] || '') + '</svg>';
      if (!this.hasAttribute('aria-label')) this.setAttribute('aria-hidden', 'true');
      else this.setAttribute('role', 'img');
    }
  }
  if (!customElements.get('e-icon')) customElements.define('e-icon', EIcon);
  window.EG_ICON_NAMES = Object.keys(P);
  window.EG_ICON_PATHS = P;
  class EBars extends HTMLElement {
    static get observedAttributes() { return ['level']; }
    connectedCallback() { this.r(); }
    attributeChangedCallback() { if (this.isConnected) this.r(); }
    r() {
      var l = +(this.getAttribute('level') || 0), h = [5, 8, 11], s = '';
      for (var i = 0; i < 3; i++) s += '<rect x="' + (i * 4.5 + 0.5) + '" y="' + (12 - h[i]) + '" width="3" height="' + h[i] + '" rx="1" fill="' + (i < l ? 'currentColor' : '#d6cbbb') + '"/>';
      var root = this.shadowRoot || this.attachShadow({ mode: 'open' });
      root.innerHTML = '<style>:host{display:inline-flex;flex:none;line-height:0}</style><svg width="14" height="12" viewBox="0 0 14 12" focusable="false">' + s + '</svg>';
      this.setAttribute('aria-hidden', 'true');
    }
  }
  if (!customElements.get('e-bars')) customElements.define('e-bars', EBars);

  function addFilter() {
    if (document.getElementById('eg-ink')) return;
    var d = document.createElement('div');
    d.setAttribute('aria-hidden', 'true');
    d.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden';
    d.innerHTML = '<svg width="0" height="0"><filter id="eg-ink" x="-6%" y="-10%" width="112%" height="120%">' +
      '<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="4" result="warp"/>' +
      '<feDisplacementMap id="eg-ink-disp" in="SourceGraphic" in2="warp" scale="3" xChannelSelector="R" yChannelSelector="G" result="rough"/>' +
      '<feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="1" seed="9" result="grain"/>' +
      '<feColorMatrix id="eg-ink-mask" in="grain" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -4 2.9" result="mask"/>' +
      '<feComposite in="rough" in2="mask" operator="in"/></filter></svg>';
    document.body.appendChild(d);
  }
  if (document.body) addFilter(); else document.addEventListener('DOMContentLoaded', addFilter);
  window.egInk = function (on) {
    addFilter();
    var disp = document.getElementById('eg-ink-disp'), m = document.getElementById('eg-ink-mask');
    if (disp) disp.setAttribute('scale', on ? '3' : '0');
    if (m) m.setAttribute('values', on ? '0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -4 2.9' : '0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0 1');
  };
})();
