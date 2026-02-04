// Fails when a raw hex colour appears in frontend source outside the design tokens.
// Colours belong in src/styles/tokens.css; everything else uses its custom properties.
import { readdirSync, readFileSync } from "node:fs";
import { extname, join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

const frontendDir = fileURLToPath(new URL("../frontend/", import.meta.url));
const srcDir = join(frontendDir, "src");

const EXTENSIONS = new Set([".vue", ".css", ".ts"]);
const EXCLUDED = new Set(["src/styles/tokens.css", "src/api/schema.d.ts"]);
// #rgb, #rrggbb or #rrggbbaa, not part of a longer word and not an HTML entity such as &#123;
const HEX_COLOUR = /(?<![&\w])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-zA-Z_-])/g;

/** @param {string} dir @returns {string[]} */
function listFiles(dir) {
  /** @type {string[]} */
  const files = [];
  let entries;
  try {
    entries = readdirSync(dir, { withFileTypes: true });
  } catch {
    return files;
  }
  for (const entry of entries) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...listFiles(path));
    } else if (entry.isFile() && EXTENSIONS.has(extname(entry.name))) {
      files.push(path);
    }
  }
  return files;
}

const findings = [];
for (const file of listFiles(srcDir)) {
  const rel = relative(frontendDir, file).split(sep).join("/");
  if (EXCLUDED.has(rel)) continue;
  const lines = readFileSync(file, "utf8").split(/\r?\n/);
  lines.forEach((line, index) => {
    for (const match of line.matchAll(HEX_COLOUR)) {
      findings.push(`frontend/${rel}:${index + 1}: ${match[0]}`);
    }
  });
}

if (findings.length > 0) {
  console.error("Raw hex colours found. Use the design tokens from src/styles/tokens.css instead:");
  for (const finding of findings) console.error(`  ${finding}`);
  process.exit(1);
}
console.log("check-hex: no raw hex colours outside the design tokens.");
