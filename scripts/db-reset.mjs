// pnpm db:reset: drops and recreates the local database, runs the migrations and loads the
// seed data. The LLM ledger (llm_calls) and the response cache (llm_cache) protect real money,
// so their rows are dumped first and restored after the migrations.
import { spawnSync } from "node:child_process";
import { closeSync, openSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const rootDir = fileURLToPath(new URL("../", import.meta.url));
const backendDir = fileURLToPath(new URL("../backend/", import.meta.url));
const DB_NAME = "eingang";
const DB_USER = "eingang";
const PRESERVED_TABLES = ["llm_calls", "llm_cache"];

/** Quotes an argument for a Windows command line. */
function quote(arg) {
  return /[\s"]/.test(arg) ? `"${arg.replaceAll('"', '\\"')}"` : arg;
}

/** spawnSync that also runs .cmd shims on Windows, which needs the shell and one command line. */
function spawnCommand(command, args, options) {
  if (process.platform !== "win32") return spawnSync(command, args, options);
  return spawnSync([command, ...args.map(quote)].join(" "), { ...options, shell: true });
}

/**
 * Runs a command and exits with its code if it fails.
 * @param {string} title
 * @param {string} command
 * @param {string[]} args
 * @param {{ cwd?: string, stdin?: number, stdout?: number | "pipe" }} [options]
 * @returns {string} captured stdout when `stdout` is "pipe", otherwise ""
 */
function run(title, command, args, options = {}) {
  console.log(`\n=== ${title} ===\n`);
  const result = spawnCommand(command, args, {
    cwd: options.cwd ?? rootDir,
    stdio: [options.stdin ?? "inherit", options.stdout ?? "inherit", "inherit"],
    encoding: "utf8",
  });
  if (result.error) {
    fail(`could not start "${command}": ${result.error.message}`, 1);
  }
  if (result.status !== 0) {
    fail(`"${title}" failed.`, result.status ?? 1);
  }
  return typeof result.stdout === "string" ? result.stdout : "";
}

let dumpFile = "";

/** @param {string} message @param {number} exitCode @returns {never} */
function fail(message, exitCode) {
  console.error(`\ndb:reset: ${message}`);
  if (dumpFile !== "") {
    console.error(`db:reset: the dump of ${PRESERVED_TABLES.join(" and ")} is kept at ${dumpFile}`);
    console.error(
      `db:reset: restore it with: docker compose exec -T db psql -v ON_ERROR_STOP=1 -U ${DB_USER} -d ${DB_NAME} < "${dumpFile}"`,
    );
  }
  process.exit(exitCode);
}

/** Runs one SQL statement through psql in the db container and returns its unaligned output. */
function psql(title, database, sql) {
  return run(
    title,
    "docker",
    ["compose", "exec", "-T", "db", "psql", "-v", "ON_ERROR_STOP=1", "-U", DB_USER, "-d", database, "-tA", "-c", sql],
    { stdout: "pipe" },
  ).trim();
}

function manage(command, ...args) {
  run(`manage.py ${command}`, "uv", ["run", "python", "manage.py", command, ...args], {
    cwd: backendDir,
  });
}

run("Start db", "docker", ["compose", "up", "-d", "--wait", "db"]);

// 1. Dump the preserved tables, if the database and the tables exist yet.
const databaseExists =
  psql("Check for the database", "postgres", `SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}'`) === "1";
const existingTables = databaseExists
  ? PRESERVED_TABLES.filter(
      (table) =>
        psql(`Check for table ${table}`, DB_NAME, `SELECT to_regclass('public.${table}') IS NOT NULL`) === "t",
    )
  : [];

if (existingTables.length > 0) {
  const file = join(tmpdir(), `eingang-db-reset-${Date.now()}.sql`);
  const fd = openSync(file, "w");
  try {
    run(
      `Dump ${existingTables.join(", ")}`,
      "docker",
      [
        "compose",
        "exec",
        "-T",
        "db",
        "pg_dump",
        "--data-only",
        "--disable-triggers",
        "-U",
        DB_USER,
        ...existingTables.flatMap((table) => ["-t", `public.${table}`]),
        DB_NAME,
      ],
      { stdout: fd },
    );
  } finally {
    closeSync(fd);
  }
  dumpFile = file;
  console.log(`Dumped ${statSync(dumpFile).size} bytes to ${dumpFile}`);
} else {
  console.log(`\nNo ${PRESERVED_TABLES.join(" or ")} table yet; nothing to preserve.`);
}

// 2. Drop and recreate the database.
psql("Drop the database", "postgres", `DROP DATABASE IF EXISTS ${DB_NAME} WITH (FORCE)`);
psql("Create the database", "postgres", `CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}`);

// 3. Migrate.
manage("migrate", "--noinput");

// 4. Restore the preserved rows.
if (dumpFile !== "") {
  const fd = openSync(dumpFile, "r");
  try {
    run(
      `Restore ${existingTables.join(", ")}`,
      "docker",
      ["compose", "exec", "-T", "db", "psql", "-v", "ON_ERROR_STOP=1", "-q", "-U", DB_USER, "-d", DB_NAME],
      { stdin: fd },
    );
  } finally {
    closeSync(fd);
  }
  rmSync(dumpFile, { force: true });
  dumpFile = "";
}

// 5. Seed.
manage("seed_rules");
manage("seed_dev");

console.log("\ndb:reset: done.");
