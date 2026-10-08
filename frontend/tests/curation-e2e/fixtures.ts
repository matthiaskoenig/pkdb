import { execFile, spawn, type ChildProcess } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { promisify } from "node:util";
import { expect, test as base, type BrowserContext, type ConsoleMessage, type Cookie, type Page } from "@playwright/test";
import { PYTHON_VARIABLE, ROOT_VARIABLE, testing } from "./paths.ts";

declare global {
  interface Window {
    /** The Content Security Policy violations of the page, collected from its first script on. */
    __cspViolations: string[];
    /** Reports a violation to the test also when the page goes away before the test reads them. */
    __reportCspViolation: (violation: string) => void;
  }
}

const execute = promisify(execFile);
/** How long `pkdb curate` may take to print its launch URL. */
const START_MS = 60_000;
/** How long it may take to stop after Ctrl+C before it is killed. */
const STOP_MS = 10_000;
/** How much of the latest output of a server a failed test reports. */
const TAIL_CHARACTERS = 20_000;
/** The line in which `pkdb curate` prints its launch URL. */
const LAUNCH_LINE = /^PK-DB curation: (http:\/\/127\.0\.0\.1:\d+\/#token=\S+)\r?\n/m;
/** The name of the session cookie that the launch token creates. */
const SESSION_COOKIE = "pkdb_curation";
/** A launch token in a URL that `pkdb curate` printed. */
const LAUNCH_TOKEN = /#token=[^\s&]+/g;

/** `text` without launch tokens, as tools/curation_docs/render.mjs reports errors. */
function redact(text: string): string {
  return text.replace(LAUNCH_TOKEN, "#token=<launch token>");
}

/** The interpreter of the python/ project, which the global setup found. */
function python(): string {
  const interpreter = process.env[PYTHON_VARIABLE];
  if (!interpreter) throw new Error(`${PYTHON_VARIABLE} is not set: run the suite with playwright.curation.config.ts`);
  return interpreter;
}

/** Run a script of tools/curation_testing with the interpreter of the python/ project. */
export async function runTool(script: string, ...args: string[]): Promise<void> {
  await execute(python(), [join(testing, script), ...args]);
}

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

/**
 * The environment of the server: the user `curator`, no PK-DB account, a cache of its own in the
 * folder of the server, which `stop` removes, and a recording opener.
 */
function serverEnvironment(cache: string, openLog: string): NodeJS.ProcessEnv {
  const environment: NodeJS.ProcessEnv = { ...process.env };
  for (const name of ["PKDB_API_KEY", "PKDB_ENDPOINT", "PKDB_AGENT", "PKDB_CACHE_DIR"]) delete environment[name];
  // The server splits the command like a shell, so the paths are quoted.
  const quoted = (path: string) => `'${path.replaceAll("'", "'\\''")}'`;
  return {
    ...environment,
    PKDB_USER: "curator",
    PKDB_NO_UPDATE: "1",
    // An empty cache: validation uses the vocabulary bundled with the client. PKDB_CACHE_DIR
    // comes first in pkdb, on every platform.
    PKDB_CACHE_DIR: cache,
    XDG_CACHE_HOME: cache,
    PKDB_OPEN_COMMAND: `${quoted(python())} ${quoted(join(testing, "record_open.py"))}`,
    PKDB_OPEN_LOG: openLog,
  };
}

/** `pkdb curate` on a copy of the fixture in its own folder, with the latest part of its output. */
class RunningServer {
  /** The launch URL once the server printed it; rejected when it stops or takes too long. */
  readonly launchUrl: Promise<string>;
  private tail = "";

  private constructor(
    private readonly folder: string,
    readonly workspace: string,
    readonly openLog: string,
    private readonly child: ChildProcess,
  ) {
    this.launchUrl = this.readLaunchUrl();
  }

  /** Copy the fixture into a new folder below `root` and start `pkdb curate` on it. */
  static async start(root: string): Promise<RunningServer> {
    const folder = mkdtempSync(join(root, "server-"));
    const workspace = join(folder, "workspace");
    const openLog = join(folder, "open.log");
    try {
      await runTool("workspace.py", workspace);
    } catch (error) {
      rmSync(folder, { recursive: true, force: true });
      throw error;
    }
    // The interpreter itself, not `uv run`, so that signals reach the server.
    const child = spawn(
      python(),
      [
        ...["-m", "pkdb", "curate", workspace],
        ...["--offline", "--no-browser", "--port", "0", "--state-dir", join(folder, "state")],
      ],
      { env: serverEnvironment(join(folder, "cache"), openLog), stdio: ["ignore", "pipe", "pipe"] },
    );
    return new RunningServer(folder, workspace, openLog, child);
  }

  /** The latest output of the server, for the report of a failed test, without the launch token. */
  get log(): string {
    return redact(this.tail);
  }

  async info(): Promise<CurationServer> {
    const launchUrl = await this.launchUrl;
    return { launchUrl, origin: new URL(launchUrl).origin, workspace: this.workspace, openLog: this.openLog };
  }

  /**
   * Read both output streams to their end, so that a full pipe never blocks the server, keep
   * their latest part, and resolve with the launch URL once a stream printed its whole line.
   */
  private readLaunchUrl(): Promise<string> {
    const child = this.child;
    return new Promise((resolve, reject) => {
      let settled = false;
      const settle = (result: string | Error) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        if (typeof result === "string") resolve(result);
        else reject(result);
      };
      const timer = setTimeout(
        () => settle(new Error(`pkdb curate printed no launch URL within ${START_MS} ms:\n${this.log}`)),
        START_MS,
      );
      for (const stream of [child.stdout, child.stderr]) {
        let line = "";
        stream?.setEncoding("utf8");
        stream?.on("data", (text: string) => {
          this.tail = (this.tail + text).slice(-TAIL_CHARACTERS);
          if (settled) return;
          line += text;
          const match = LAUNCH_LINE.exec(line);
          if (match?.[1]) settle(match[1]);
        });
      }
      child.once("error", (error) => settle(error));
      child.once("exit", (code, signal) =>
        settle(new Error(`pkdb curate stopped (${signal ?? `code ${code}`}) before its launch URL:\n${this.log}`)),
      );
    });
  }

  /** Stop the server as Ctrl+C does, kill it when it does not stop, and remove its folder. */
  async stop(): Promise<void> {
    const child = this.child;
    // A launch URL that never came is reported by the test that waited for it.
    this.launchUrl.catch(() => undefined);
    if (child.exitCode === null && child.signalCode === null) {
      const exited = new Promise((resolve) => child.once("exit", resolve));
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
      // Kept before its launch URL comes, so that closing the pool stops it in any case.
      this.current = { file, server: await RunningServer.start(root), cookies: [] };
    }
    return this.current.server.info();
  }

  /** The latest output of the server of the file. */
  get log(): string {
    return this.current?.server.log ?? "";
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
   * Accept one console error of a request to `path` that the server answers with `status`.
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
  try {
    await page.goto(server.launchUrl);
  } catch (error) {
    // The error of Playwright repeats the URL, so it is not attached as the cause.
    // eslint-disable-next-line preserve-caught-error
    throw new Error(redact(error instanceof Error ? error.message : String(error)));
  }
  expect((await session).status()).toBe(200);
  // The app creates its router after the session; a route changed before would be missed.
  await expect(header).toBeVisible();
  const cookies = await context.cookies(server.origin);
  expect(cookies.map((cookie) => cookie.name)).toContain(SESSION_COOKIE);
  servers.cookies = cookies;
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
  // Its own timeout, so that a server without a launch URL reports its output.
  curation: [
    async ({ servers }, use, testInfo) => {
      await use(await servers.forFile(testInfo.file));
    },
    { timeout: START_MS + STOP_MS },
  ],
  app: async ({ page, context, servers, curation }, use, testInfo) => {
    const violations: string[] = [];
    const errors: string[] = [];
    const allowed: ExpectedError[] = [];
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
      // Each allowance accepts one error.
      const index = allowed.findIndex((expected) => isFailedRequest(message, expected));
      if (index >= 0) allowed.splice(index, 1);
      else errors.push(`${message.text()} (${message.location().url})`);
    });
    page.on("pageerror", (error) => errors.push(error.message));

    await use({
      server: curation,
      open: (hash = "#/") => openApp(page, context, servers, curation, hash),
      allowFailedRequest: (path, status) => allowed.push({ path, status }),
    });

    // The page's own list holds also the violations whose report is still on its way.
    const inPage = page.isClosed() ? [] : await page.evaluate(() => window.__cspViolations ?? []);
    const found = [...new Set([...violations, ...inPage])];
    if (testInfo.status !== testInfo.expectedStatus || found.length || errors.length) {
      await testInfo.attach("pkdb-curate.log", { body: servers.log, contentType: "text/plain" });
    }
    expect(found, "Content Security Policy violations").toEqual([]);
    expect(errors, "console errors").toEqual([]);
  },
});

export { expect };
