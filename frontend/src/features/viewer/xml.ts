// A small XML highlighter for the CodeView: splits the source into lines of coloured tokens.
// Tokens are rendered as text (Vue escapes them), so nothing from the file is ever parsed as HTML.
// Design colours: element names --stamp, attributes --warn-text, values --ok, brackets --muted,
// text --ink.

export type TokenKind =
  "bracket" | "name" | "attr" | "value" | "text" | "comment";

export interface Token {
  kind: TokenKind;
  text: string;
}

export type Line = Token[];

const ATTRIBUTE = /(\s+)([^\s=/>?]+)(\s*=\s*)?("[^"]*"|'[^']*')?/y;

function tagTokens(tag: string): Token[] {
  const tokens: Token[] = [];
  const open = /^<[/?!]?/.exec(tag)?.[0] ?? "<";
  const close = /[/?]?>$/.exec(tag)?.[0] ?? "";
  const inner = tag.slice(open.length, tag.length - close.length);
  tokens.push({ kind: "bracket", text: open });
  const name = /^[^\s/>?]*/.exec(inner)?.[0] ?? "";
  if (name) tokens.push({ kind: "name", text: name });
  let index = name.length;
  while (index < inner.length) {
    ATTRIBUTE.lastIndex = index;
    const match = ATTRIBUTE.exec(inner);
    if (!match || match[0] === "") {
      tokens.push({ kind: "text", text: inner.slice(index) });
      break;
    }
    const [, space = "", attr = "", equals, value] = match;
    tokens.push({ kind: "bracket", text: space });
    tokens.push({ kind: "attr", text: attr });
    if (equals) tokens.push({ kind: "bracket", text: equals });
    if (value) tokens.push({ kind: "value", text: value });
    index = ATTRIBUTE.lastIndex;
  }
  if (close) tokens.push({ kind: "bracket", text: close });
  return tokens;
}

/** Index of the `>` closing the tag at `start`, skipping `>` inside quoted values; −1 if none. */
function tagEnd(source: string, start: number): number {
  let quote: string | null = null;
  for (let index = start + 1; index < source.length; index += 1) {
    const char = source[index];
    if (quote) {
      if (char === quote) quote = null;
    } else if (char === '"' || char === "'") {
      quote = char;
    } else if (char === ">") {
      return index;
    }
  }
  return -1;
}

/** The whole source as one token stream. */
export function tokenize(source: string): Token[] {
  const tokens: Token[] = [];
  let index = 0;
  while (index < source.length) {
    const start = source.indexOf("<", index);
    if (start === -1) {
      tokens.push({ kind: "text", text: source.slice(index) });
      break;
    }
    if (start > index)
      tokens.push({ kind: "text", text: source.slice(index, start) });
    if (source.startsWith("<!--", start)) {
      const end = source.indexOf("-->", start);
      const stop = end === -1 ? source.length : end + 3;
      tokens.push({ kind: "comment", text: source.slice(start, stop) });
      index = stop;
    } else if (source.startsWith("<![CDATA[", start)) {
      const end = source.indexOf("]]>", start);
      const stop = end === -1 ? source.length : end + 3;
      tokens.push({ kind: "text", text: source.slice(start, stop) });
      index = stop;
    } else {
      const end = tagEnd(source, start);
      const stop = end === -1 ? source.length : end + 1;
      tokens.push(...tagTokens(source.slice(start, stop)));
      index = stop;
    }
  }
  return tokens.filter((token) => token.text !== "");
}

/** The source as numbered lines of tokens; tokens that span lines are split at each newline. */
export function highlightXml(source: string): Line[] {
  const lines: Line[] = [[]];
  for (const token of tokenize(source.replace(/\r\n?/g, "\n"))) {
    const parts = token.text.split("\n");
    parts.forEach((part, index) => {
      if (index > 0) lines.push([]);
      if (part !== "")
        lines[lines.length - 1]?.push({ kind: token.kind, text: part });
    });
  }
  // A final newline does not start another numbered line.
  if (lines.length > 1 && lines[lines.length - 1]?.length === 0) lines.pop();
  return lines;
}
