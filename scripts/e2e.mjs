// pnpm test:e2e: runs the Playwright smoke tests against the full stack in a separate
// Compose project. The development containers are stopped first (same ports) and the e2e
// stack is always removed afterwards, also when a test fails. The development database is
// never touched.
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const rootDir = fileURLToPath(new URL("../", import.meta.url));
const E2E_PROJECT = "eingang-e2e";

/** spawnSync that also runs .cmd shims on Windows, which needs the shell and one command line. */
function spawnCommand(command, args, options) {
  if (process.platform !== "win32") return spawnSync(command, args, options);
  return spawnSync([command, ...args].join(" "), { ...options, shell: true });
}

/** Runs a command with streamed output and returns its exit code. */
function run(title, command, args) {
  console.log(`\n=== ${title} ===\n`);
  const result = spawnCommand(command, args, { cwd: rootDir, stdio: "inherit" });
  if (result.error) {
    console.error(`e2e: could not start "${command}": ${result.error.message}`);
    return 1;
  }
  return result.status ?? 1;
}

const stopStatus = run("Stop development containers", "docker", ["compose", "stop"]);
if (stopStatus !== 0) {
  console.error("e2e: could not stop the development containers.");
  process.exit(stopStatus);
}

let status = 0;
try {
  status = run("Start the e2e stack", "docker", [
    "compose",
    "-p",
    E2E_PROJECT,
    "--profile",
    "e2e",
    "up",
    "-d",
    "--build",
    "--wait",
  ]);
  if (status !== 0) {
    console.error("e2e: the e2e stack did not become healthy.");
  } else {
    status = run("Run Playwright smoke tests", "pnpm", ["--filter", "frontend", "test:e2e"]);
  }
} finally {
  const downStatus = run("Remove the e2e stack", "docker", [
    "compose",
    "-p",
    E2E_PROJECT,
    "down",
    "-v",
  ]);
  if (downStatus !== 0) {
    console.error(`e2e: could not remove the e2e stack; run "docker compose -p ${E2E_PROJECT} down -v".`);
    if (status === 0) status = downStatus;
  }
}

process.exit(status);
