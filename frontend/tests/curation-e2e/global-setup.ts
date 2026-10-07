import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, realpathSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { builtApp, pythonProject, ROOT_VARIABLE } from "./paths.ts";

/**
 * Check that the app is built, prepare the Python environment once, and create the temporary
 * folder of the run, in which every spec file gets its workspace and server state.
 */
export default function globalSetup(): void {
  if (!existsSync(builtApp)) {
    throw new Error("The curation app is not built. Run npm run build:curation in frontend/ first.");
  }
  // The first `uv run` may install the environment; the servers of the spec files then start quickly.
  execFileSync("uv", ["run", "--project", pythonProject, "python", "-c", "import pkdb"], { stdio: "inherit" });
  process.env[ROOT_VARIABLE] = realpathSync(mkdtempSync(join(tmpdir(), "pkdb-curation-e2e-")));
}
