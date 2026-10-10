// pnpm verify: the quality gate. Runs every check in order and stops at the first failure.
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const rootDir = fileURLToPath(new URL("../", import.meta.url));
const backendDir = fileURLToPath(new URL("../backend/", import.meta.url));

/** spawnSync that also runs .cmd shims on Windows, which needs the shell and one command line. */
function spawnCommand(command, args, options) {
  if (process.platform !== "win32") return spawnSync(command, args, options);
  return spawnSync([command, ...args].join(" "), { ...options, shell: true });
}

/** @type {{ title: string, command: string, args: string[], cwd: string }[]} */
const steps = [
  { title: "backend: lint", command: "uv", args: ["run", "poe", "lint"], cwd: backendDir },
  { title: "backend: typecheck", command: "uv", args: ["run", "poe", "typecheck"], cwd: backendDir },
  // The corpus tests fail when the pinned corpus is missing, so a fresh clone downloads it
  // here once (about 150 MB); later runs find it and skip the download.
  {
    title: "backend: ZUGFeRD corpus",
    command: "uv",
    args: ["run", "poe", "fetch-corpus"],
    cwd: backendDir,
  },
  { title: "backend: test", command: "uv", args: ["run", "poe", "test"], cwd: backendDir },
  {
    title: "backend: OpenAPI freshness",
    command: "uv",
    args: ["run", "poe", "openapi-check"],
    cwd: backendDir,
  },
  { title: "frontend: lint", command: "pnpm", args: ["--filter", "frontend", "lint"], cwd: rootDir },
  {
    title: "frontend: typecheck",
    command: "pnpm",
    args: ["--filter", "frontend", "typecheck"],
    cwd: rootDir,
  },
  { title: "frontend: test", command: "pnpm", args: ["--filter", "frontend", "test"], cwd: rootDir },
  {
    title: "frontend: generated API types freshness",
    command: "node",
    args: ["scripts/gen-api.mjs", "--check"],
    cwd: rootDir,
  },
  { title: "frontend: build", command: "pnpm", args: ["--filter", "frontend", "build"], cwd: rootDir },
];

for (const [index, step] of steps.entries()) {
  console.log(`\n=== [${index + 1}/${steps.length}] ${step.title} ===\n`);
  const result = spawnCommand(step.command, step.args, { cwd: step.cwd, stdio: "inherit" });
  if (result.error) {
    console.error(`\nverify: could not start "${step.command}": ${result.error.message}`);
    process.exit(1);
  }
  if (result.status !== 0) {
    console.error(`\nverify: "${step.title}" failed.`);
    process.exit(result.status ?? 1);
  }
}

console.log("\nverify: all checks passed.");
