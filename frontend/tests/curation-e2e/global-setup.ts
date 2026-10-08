import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, realpathSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { builtApp, pythonProject, PYTHON_VARIABLE, ROOT_VARIABLE } from "./paths.ts";

/**
 * Check that the app is built, prepare the Python environment once, and create the temporary
 * folder of the run, in which every spec file gets its workspace and server state.
 */
export default function globalSetup(): void {
  if (!existsSync(builtApp)) {
    throw new Error("The curation app is not built. Run npm run build:curation in frontend/ first.");
  }
  // `uv run` installs the environment when needed. The specs then run its interpreter
  // directly, so that a signal to a server reaches `pkdb curate` itself.
  const python = execFileSync(
    "uv",
    ["run", "--project", pythonProject, "python", "-c", "import sys, pkdb; print(sys.executable)"],
    { encoding: "utf8", stdio: ["ignore", "pipe", "inherit"] },
  ).trim();
  process.env[PYTHON_VARIABLE] = python;
  process.env[ROOT_VARIABLE] = realpathSync(mkdtempSync(join(tmpdir(), "pkdb-curation-e2e-")));
}
