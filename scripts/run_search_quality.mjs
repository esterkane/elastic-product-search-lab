import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";

const scriptArgs = ["scripts/search_quality_program.py", ...process.argv.slice(2)];
const bundledPython = process.env.USERPROFILE
  ? join(
      process.env.USERPROFILE,
      ".cache",
      "codex-runtimes",
      "codex-primary-runtime",
      "dependencies",
      "python",
      "python.exe",
    )
  : "";

const candidates = [
  process.env.PYTHON ? [process.env.PYTHON] : null,
  ["python"],
  ["python3"],
  ["py", "-3"],
  bundledPython && existsSync(bundledPython) ? [bundledPython] : null,
].filter(Boolean);

for (const command of candidates) {
  const [executable, ...prefixArgs] = command;
  const version = spawnSync(executable, [...prefixArgs, "--version"], { encoding: "utf8", shell: false });
  if (version.error || version.status !== 0) {
    continue;
  }
  const result = spawnSync(executable, [...prefixArgs, ...scriptArgs], { stdio: "inherit", shell: false });
  process.exit(result.status ?? 1);
}

console.error("Could not find Python. Set PYTHON to a Python 3.12+ executable and rerun the quality gate.");
process.exit(1);
