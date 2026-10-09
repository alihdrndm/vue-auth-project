// The evidence highlight in the Text tab: the selected field's evidence string is marked where it
// occurs in the PDF text (design: --hl with a --stamp ring), and its lines are the current lines.

export interface Segment {
  text: string;
  mark: boolean;
}

export interface TextLine {
  number: number;
  segments: Segment[];
  /** The line holds part of the marked evidence. */
  hit: boolean;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Where `evidence` occurs in `text` as [start, end), or null. Tries the exact string first, then
 * ignores case and differences in white space (the PDF text may wrap or double spaces).
 */
export function findEvidence(
  text: string,
  evidence: string | null | undefined,
): [number, number] | null {
  const needle = evidence?.trim();
  if (!needle) return null;
  const exact = text.indexOf(needle);
  if (exact !== -1) return [exact, exact + needle.length];
  const pattern = needle.split(/\s+/).map(escapeRegExp).join("\\s+");
  const match = new RegExp(pattern, "i").exec(text);
  return match ? [match.index, match.index + match[0].length] : null;
}

/** The text as numbered lines, with the evidence range cut out as marked segments. */
export function markLines(
  text: string,
  range: [number, number] | null,
): TextLine[] {
  const lines = text.replace(/\r\n?/g, "\n").split("\n");
  if (lines.length > 1 && lines[lines.length - 1] === "") lines.pop();
  let offset = 0;
  return lines.map((line, index) => {
    const start = offset;
    const end = start + line.length;
    offset = end + 1;
    if (!range || range[1] <= start || range[0] > end) {
      return {
        number: index + 1,
        segments: [{ text: line, mark: false }],
        hit: false,
      };
    }
    const from = Math.max(range[0], start) - start;
    const to = Math.min(range[1], end) - start;
    const segments: Segment[] = [
      { text: line.slice(0, from), mark: false },
      { text: line.slice(from, to), mark: true },
      { text: line.slice(to), mark: false },
    ].filter((segment) => segment.text !== "");
    return { number: index + 1, segments, hit: to > from };
  });
}
