// pnpm seed: loads the local development seed data (idempotent).
// Runs `manage.py seed_rules` and then `manage.py seed_dev` in backend/.
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const backendDir = fileURLToPath(new URL("../backend/", import.meta.url));

/** spawnSync that also runs .cmd shims on Windows, which needs the shell and one command line. */
function spawnCommand(command, args, options) {
  if (process.platform !== "win32") return spawnSync(command, args, options);
  return spawnSync([command, ...args].join(" "), { ...options, shell: true });
}

for (const command of ["seed_rules", "seed_dev"]) {
  console.log(`\n=== manage.py ${command} ===\n`);
  const result = spawnCommand("uv", ["run", "python", "manage.py", command], {
    cwd: backendDir,
    stdio: "inherit",
  });
  if (result.error) {
    console.error(`seed: could not start "uv": ${result.error.message}`);
    process.exit(1);
  }
  if (result.status !== 0) {
    console.error(`seed: "manage.py ${command}" failed.`);
    process.exit(result.status ?? 1);
  }
}

console.log("\nseed: done.");
