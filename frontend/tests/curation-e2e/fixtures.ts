import { execFile, spawn, type ChildProcess } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { promisify } from "node:util";
import { expect, test as base, type BrowserContext, type ConsoleMessage, type Cookie, type Page } from "@playwright/test";
import { pythonProject, ROOT_VARIABLE, testing } from "./paths.ts";

declare global {
  interface Window {
    /** The Content Security Policy violations of the page, collected from its first script on. */
    __cspViolations: string[];
    /** Reports a violation to the test also when the page goes away before the test reads them. */
    __reportCspViolation: (violation: string) => void;
  }
}

const run = promisify(execFile);
/** How long `pkdb curate` may take to print its launch URL. */
const START_MS = 60_000;
/** How long it may take to stop after Ctrl+C before it is killed. */
const STOP_MS = 10_000;

/** A running `pkdb curate` on a fresh copy of the fixture workspace. */
export interface CurationServer {
  /** The URL that `pkdb curate` prints, with its one-time launch token. */
  launchUrl: string;
  /** `http://127.0.0.1:<port>` */
  origin: string;
  /** The workspace folder: caffeine/Demo2020 (with its workbook), caffeine/Draft2021, caffeine/Legacy1990. */
  workspace: string;
  /** The file to which the recording opener appends every path that the server opens. */
  openLog: string;
}

/** The environment of the server: the user `curator`, no PK-DB account, and a recording opener. */
function serverEnvironment(cache: string, openLog: string): NodeJS.ProcessEnv {
  const environment: NodeJS.ProcessEnv = { ...process.env };
  for (const name of ["PKDB_API_KEY", "PKDB_ENDPOINT", "PKDB_AGENT"]) delete environment[name];
  const opener = join(testing, "record_open.py");
  return {
    ...environment,
    PKDB_USER: "curator",
    PKDB_NO_UPDATE: "1",
    // An empty cache: validation uses the vocabulary bundled with the client.
    XDG_CACHE_HOME: cache,
    // `uv run` puts the Python of the project first on the PATH; the server splits the command
    // like a shell, so the path is quoted.
    PKDB_OPEN_COMMAND: `python '${opener.replaceAll("'", "'\\''")}'`,
    PKDB_OPEN_LOG: openLog,
  };
}

/**
 * The launch URL from the output of `pkdb curate`, or an error with its output when it stops
 * first. The output is read to its end, so that a full pipe never blocks the server.
 */
function launchUrlOf(child: ChildProcess): Promise<string> {
  return new Promise((resolve, reject) => {
    let output = "";
    let started = false;
    const timer = setTimeout(() => fail(new Error(`pkdb curate printed no launch URL:\n${output}`)), START_MS);
    function fail(error: Error): void {
      clearTimeout(timer);
      reject(error);
    }
    function read(chunk: Buffer): void {
      if (started) return;
      output += chunk.toString();
      const match = /PK-DB curation: (http:\/\/127\.0\.0\.1:\d+\/#token=\S+)/.exec(output);
      if (match?.[1]) {
        started = true;
        clearTimeout(timer);
        resolve(match[1]);
      }
    }
    child.stdout?.on("data", read);
    child.stderr?.on("data", read);
    child.once("exit", (code) => fail(new Error(`pkdb curate stopped with code ${code}:\n${output}`)));
  });
}

class RunningServer {
  constructor(
    readonly info: CurationServer,
    private readonly child: ChildProcess,
    private readonly folder: string,
  ) {}

  /** Start `pkdb curate` on a new copy of the fixture in a new folder below `root`. */
  static async start(root: string): Promise<RunningServer> {
    const folder = mkdtempSync(join(root, "server-"));
    const workspace = join(folder, "workspace");
    const openLog = join(folder, "open.log");
    await run("uv", ["run", "--project", pythonProject, "python", join(testing, "workspace.py"), workspace]);
    const child = spawn(
      "uv",
      [
        ...["run", "--project", pythonProject, "pkdb", "curate", workspace],
        ...["--offline", "--no-browser", "--port", "0", "--state-dir", join(folder, "state")],
      ],
      { env: serverEnvironment(join(folder, "cache"), openLog), stdio: ["ignore", "pipe", "pipe"] },
    );
    try {
      const launchUrl = await launchUrlOf(child);
      return new RunningServer({ launchUrl, origin: new URL(launchUrl).origin, workspace, openLog }, child, folder);
    } catch (error) {
      child.kill("SIGKILL");
      rmSync(folder, { recursive: true, force: true });
      throw error;
    }
  }

  /** Stop the server as Ctrl+C does, then remove its workspace and state. */
  async stop(): Promise<void> {
    const child = this.child;
    if (child.exitCode === null && child.signalCode === null) {
      const exited = new Promise((resolve) => child.once("exit", resolve));
      // uv passes the interrupt on to pkdb curate, which closes its engine.
      child.kill("SIGINT");
      const timer = setTimeout(() => child.kill("SIGKILL"), STOP_MS);
      await exited;
      clearTimeout(timer);
    }
    rmSync(this.folder, { recursive: true, force: true });
  }
}

/**
 * The server of the spec file that runs. Playwright keeps a worker for many files, so the
 * worker-scoped pool starts a new server when the file changes: spec files never share a
 * workspace, while the tests of one file share its server and session.
 */
class ServerPool {
  private current: { file: string; server: RunningServer; cookies: Cookie[] } | null = null;

  async forFile(file: string): Promise<CurationServer> {
    if (this.current?.file !== file) {
      await this.close();
      const root = process.env[ROOT_VARIABLE];
      if (!root) throw new Error(`${ROOT_VARIABLE} is not set: run the suite with playwright.curation.config.ts`);
      this.current = { file, server: await RunningServer.start(root), cookies: [] };
    }
    return this.current.server.info;
  }

  /** The session cookie of the file, once a test opened the launch URL. */
  get cookies(): Cookie[] {
    return this.current?.cookies ?? [];
  }

  set cookies(cookies: Cookie[]) {
    if (this.current) this.current.cookies = cookies;
  }

  async close(): Promise<void> {
    const server = this.current?.server;
    this.current = null;
    await server?.stop();
  }
}

/** A console error that a test causes on purpose: a request that the server answers with `status`. */
interface ExpectedError {
  path: string;
  status: number;
}

/** The app of the spec file's server in the page of the test. */
export interface CurationApp {
  server: CurationServer;
  /**
   * Open the app: the launch URL in the first test of a file, which creates the session; later
   * tests reuse its cookie, as the token works once. Then show `hash`, by default the overview.
   */
  open(hash?: string): Promise<void>;
  /**
   * Accept the console error of a request to `path` that the server answers with `status`.
   * Browsers log every 4xx answer; any other console error fails the test.
   */
  allowFailedRequest(path: string, status: number): void;
}

/** Whether `message` is the browser's log of a request to `path` answered with `status`. */
function isFailedRequest(message: ConsoleMessage, { path, status }: ExpectedError): boolean {
  const location = message.location().url;
  return (
    message.text().includes(`the server responded with a status of ${status}`) &&
    location !== "" &&
    new URL(location).pathname === path
  );
}

async function openApp(page: Page, context: BrowserContext, servers: ServerPool, server: CurationServer, hash: string) {
  const header = page.getByRole("link", { name: "PK-DB Local curation" });
  if (servers.cookies.length) {
    await context.addCookies(servers.cookies);
    await page.goto(`${server.origin}/${hash}`);
    await expect(header).toBeVisible();
    return;
  }
  const session = page.waitForResponse((response) => new URL(response.url()).pathname === "/local/session");
  await page.goto(server.launchUrl);
  expect((await session).status()).toBe(200);
  servers.cookies = await context.cookies(server.origin);
  // The app creates its router after the session; a route changed before would be missed.
  await expect(header).toBeVisible();
  if (hash !== "#/") await showRoute(page, hash);
}

/** Show the route `hash` of the open app, as a link in the app does. */
async function showRoute(page: Page, hash: string): Promise<void> {
  await page.evaluate((target) => (window.location.hash = target), hash);
  await expect.poll(() => new URL(page.url()).hash).toBe(hash);
}

/**
 * Pause or resume the automatic actions of the local server from the File watching menu of the
 * header. While they are paused, saved files and queued jobs wait.
 */
export async function setAutomaticActions(page: Page, paused: boolean): Promise<void> {
  const [from, action, to] = paused
    ? ["Active", "Pause automatic actions", "Paused"]
    : ["Paused", "Resume automatic actions", "Active"];
  await page.getByRole("button", { name: `File watching: ${from}` }).click();
  await page.getByRole("button", { name: action }).click();
  await expect(page.getByRole("button", { name: `File watching: ${to}` })).toBeVisible();
  await page.keyboard.press("Escape");
}

export const test = base.extend<{ curation: CurationServer; app: CurationApp }, { servers: ServerPool }>({
  servers: [
    // eslint-disable-next-line no-empty-pattern
    async ({}, use) => {
      const pool = new ServerPool();
      await use(pool);
      await pool.close();
    },
    { scope: "worker", timeout: START_MS + STOP_MS },
  ],
  curation: async ({ servers }, use, testInfo) => {
    await use(await servers.forFile(testInfo.file));
  },
  app: async ({ page, context, servers, curation }, use) => {
    const violations: string[] = [];
    const errors: string[] = [];
    const expected: ExpectedError[] = [];
    await page.exposeFunction("__reportCspViolation", (violation: string) => violations.push(violation));
    await page.addInitScript(() => {
      window.__cspViolations = [];
      document.addEventListener("securitypolicyviolation", (event) => {
        const violation = `${event.violatedDirective} ${event.blockedURI} ${event.sourceFile}:${event.lineNumber}`;
        window.__cspViolations.push(violation);
        window.__reportCspViolation(violation);
      });
    });
    page.on("console", (message) => {
      if (message.type() !== "error") return;
      if (expected.some((allowed) => isFailedRequest(message, allowed))) return;
      errors.push(`${message.text()} (${message.location().url})`);
    });
    page.on("pageerror", (error) => errors.push(error.message));

    await use({
      server: curation,
      open: (hash = "#/") => openApp(page, context, servers, curation, hash),
      allowFailedRequest: (path, status) => expected.push({ path, status }),
    });

    // The page's own list holds also the violations whose report is still on its way.
    const inPage = page.isClosed() ? [] : await page.evaluate(() => window.__cspViolations ?? []);
    expect([...new Set([...violations, ...inPage])], "Content Security Policy violations").toEqual([]);
    expect(errors, "console errors").toEqual([]);
  },
});

export { expect };
