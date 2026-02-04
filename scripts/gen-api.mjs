// pnpm gen:api: exports the OpenAPI schema (backend/openapi.json) and regenerates the
// frontend types (frontend/src/api/schema.d.ts).
// With --check it generates both into a temporary directory and fails if either differs from
// the committed file. Nothing is overwritten in check mode.
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = fileURLToPath(new URL("../", import.meta.url));
const backendDir = join(rootDir, "backend");

const committedSchema = join(backendDir, "openapi.json");
const committedTypes = join(rootDir, "frontend", "src", "api", "schema.d.ts");

/** Raised when a step fails; carries the exit code to finish with. */
class StepFailed extends Error {
  /** @param {string} message @param {number} exitCode */
  constructor(message, exitCode) {
    super(message);
    this.exitCode = exitCode;
  }
}

/** Quotes an argument for a Windows command line. */
function quote(arg) {
  return /[\s"]/.test(arg) ? `"${arg.replaceAll('"', '\\"')}"` : arg;
}

/** spawnSync that also runs .cmd shims on Windows, which needs the shell and one command line. */
function spawnCommand(command, args, options) {
  if (process.platform !== "win32") return spawnSync(command, args, options);
  return spawnSync([command, ...args.map(quote)].join(" "), { ...options, shell: true });
}

/** Runs a command with streamed output and throws StepFailed if it fails. */
function run(title, command, args, cwd) {
  console.log(`=== ${title} ===`);
  const result = spawnCommand(command, args, { cwd, stdio: "inherit" });
  if (result.error) {
    throw new StepFailed(`could not start "${command}": ${result.error.message}`, 1);
  }
  if (result.status !== 0) {
    throw new StepFailed(`"${title}" failed.`, result.status ?? 1);
  }
}

/** Exports the OpenAPI schema. `output` overrides the default backend/openapi.json. */
function exportSchema(output) {
  const args = ["run", "poe", "openapi"];
  if (output !== undefined) args.push("--file", output);
  run("Export OpenAPI schema", "uv", args, backendDir);
}

function generateTypes(schemaPath, output) {
  mkdirSync(dirname(output), { recursive: true });
  run(
    "Generate frontend API types",
    "pnpm",
    ["--filter", "frontend", "exec", "openapi-typescript", schemaPath, "-o", output],
    rootDir,
  );
}

/** Reads a file with line endings normalised, so a CRLF checkout compares equal. */
function readNormalised(path) {
  return readFileSync(path, "utf8").replace(/\r\n/g, "\n");
}

function generate() {
  exportSchema(undefined);
  generateTypes(committedSchema, committedTypes);
  console.log("gen-api: wrote backend/openapi.json and frontend/src/api/schema.d.ts.");
}

/** @returns {string[]} the committed files that are missing or differ from a fresh export */
function findStale() {
  const tempDir = mkdtempSync(join(tmpdir(), "eingang-gen-api-"));
  try {
    const freshSchema = join(tempDir, "openapi.json");
    const freshTypes = join(tempDir, "schema.d.ts");
    exportSchema(freshSchema);
    generateTypes(freshSchema, freshTypes);

    const pairs = [
      ["backend/openapi.json", committedSchema, freshSchema],
      ["frontend/src/api/schema.d.ts", committedTypes, freshTypes],
    ];
    return pairs
      .filter(
        ([, committed, fresh]) =>
          !existsSync(committed) || readNormalised(committed) !== readNormalised(fresh),
      )
      .map(([label]) => label);
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
}

try {
  if (!process.argv.includes("--check")) {
    generate();
  } else {
    const stale = findStale();
    if (stale.length > 0) {
      console.error("gen-api --check: these generated files are missing or out of date:");
      for (const label of stale) console.error(`  ${label}`);
      console.error("Run `pnpm gen:api` and commit the result.");
      process.exit(1);
    }
    console.log(
      "gen-api --check: backend/openapi.json and frontend/src/api/schema.d.ts are up to date.",
    );
  }
} catch (error) {
  if (error instanceof StepFailed) {
    console.error(`gen-api: ${error.message}`);
    process.exit(error.exitCode);
  }
  throw error;
}
