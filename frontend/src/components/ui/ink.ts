// The shared ink filter that gives every stamp impression and the mark their uneven edge.
// It is added to the document once, the first time a stamp or mark mounts.
export const INK_FILTER_ID = "eg-ink";

const FILTER_MARKUP =
  `<svg width="0" height="0"><filter id="${INK_FILTER_ID}" x="-6%" y="-10%" width="112%" height="120%">` +
  '<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="4" result="warp"/>' +
  '<feDisplacementMap in="SourceGraphic" in2="warp" scale="3" xChannelSelector="R" yChannelSelector="G" result="rough"/>' +
  '<feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="1" seed="9" result="grain"/>' +
  '<feColorMatrix in="grain" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -4 2.9" result="mask"/>' +
  '<feComposite in="rough" in2="mask" operator="in"/></filter></svg>';

export function ensureInkFilter(): void {
  if (typeof document === "undefined" || document.getElementById(INK_FILTER_ID))
    return;
  const holder = document.createElement("div");
  holder.setAttribute("aria-hidden", "true");
  holder.style.cssText = "position:absolute;width:0;height:0;overflow:hidden";
  holder.innerHTML = FILTER_MARKUP;
  document.body.appendChild(holder);
}
