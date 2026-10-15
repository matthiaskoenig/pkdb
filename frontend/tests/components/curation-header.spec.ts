import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import { defineComponent, h, type PropType } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";
import { useTheme } from "vuetify";
import { VApp } from "vuetify/components";
import App from "../../src/curation-app/App.vue";
import AppHeader from "../../src/curation-app/components/AppHeader.vue";
import StatusBanner from "../../src/curation-app/components/StatusBanner.vue";
import { initialTheme, servedTheme, useColorTheme } from "../../src/curation-app/composables/useColorTheme";
import type { ConnectionStatus, Snapshot } from "../../src/curation-app/api/types";
import { ApiError } from "../../src/study-views/errors";
import { formatTime } from "../../src/study-views/overview";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { json, snapshot, studyRow } from "../unit/curation-fixtures";
import { afterMenuClosed, button, buttons, click, focusDialog, loadSnapshot, page, setViewport } from "./curation-dom";

const FAILED = { request_id: "3f9c2a71", time: "2026-10-12T14:03:11+02:00" };

enableAutoUnmount(afterEach);

const THEME_KEY = "pkdb.curation.theme";
let pinia: Pinia;

function router() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/:pathMatch(.*)*", component: { render: () => null } }],
  });
}

/** The header inside an app, as on every page. */
function mountHeader() {
  return mount(() => h(VApp, () => h(AppHeader)), {
    attachTo: document.body,
    global: { plugins: [pinia, router()] },
  });
}

/** Focuses the button `name` and clicks it, as a keyboard does. */
async function focusAndClick(name: string): Promise<void> {
  button(name).element.focus();
  await click(name);
}

/** An app that calls `use` in its setup, for code that needs the Vuetify instance. */
const Probe = defineComponent({
  props: { use: { type: Function as PropType<() => void>, required: true } },
  setup(props) {
    props.use();
    return () => h(VApp, () => h("div"));
  },
});

/** A media query list of a browser whose system theme matches `matches`. */
function mediaQuery(media: string, matches: boolean): MediaQueryList {
  return {
    matches,
    media,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(() => false),
  };
}

/** Whether the shared Vuetify theme follows the system. */
function followsSystem(): boolean {
  let system = false;
  mount(Probe, { props: { use: () => (system = useTheme().isSystem.value) } }).unmount();
  return system;
}

/** The theme class of the app: `v-theme--light` or `v-theme--dark`. */
function themeOf(wrapper: ReturnType<typeof mountHeader>): string | undefined {
  return wrapper.get(".v-application").classes().find((name) => name.startsWith("v-theme--"));
}

beforeEach(() => {
  pinia = createPinia();
  setActivePinia(pinia);
  localStorage.clear();
  setViewport(1280);
});

afterEach(() => {
  disposePinia(pinia);
  localStorage.clear();
  // The tests of this file share the Vuetify instance of tests/setup.ts.
  mount(Probe, { props: { use: () => void useTheme().change("light") } }).unmount();
});

describe("AppHeader", () => {
  it("shows the logo, the app name Curation and the workspace folder", async () => {
    await loadSnapshot(snapshot());
    const wrapper = mountHeader();
    await flushPromises();
    expect(wrapper.get("img").attributes("alt")).toBe("PK-DB");
    // The link home is named by the logo and the app name: "PK-DB Curation".
    expect(wrapper.get("a.brand").text()).toBe("Curation");
    // The header shows the folder name; the title, the accessible name and the menu the path.
    const workspace = button("Workspace: /work/pkdb_data");
    expect(workspace.text()).toBe("pkdb_data");
    expect(workspace.attributes("title")).toBe("/work/pkdb_data");
    await click("Workspace: /work/pkdb_data");
    expect(page().get(".workspace-panel").text()).toContain("/work/pkdb_data");
  });

  it.each<[ConnectionStatus, string]>([
    ["connected", "Connected"],
    ["offline", "Offline"],
    ["connecting", "Connecting"],
    ["not_configured", "Not configured"],
    ["unauthorized", "Rejected API key"],
    ["incompatible", "Update pkdb"],
    ["error", "Error"],
  ])("shows the connection state %s as %s", async (connection, label) => {
    await loadSnapshot(snapshot({ connection }));
    mountHeader();
    await flushPromises();
    expect(button(`Connection: ${label}`).text()).toContain(label);
  });

  it("colors the app bar teal, with the white text of the bar", async () => {
    await loadSnapshot(snapshot());
    const wrapper = mountHeader();
    await flushPromises();
    expect(wrapper.get(".app-header").classes()).toContain("bg-app-bar");
  });

  it("shows a warning or an error on the bar in the light amber or red of the bar, and in the colors of the surface in its menu", async () => {
    await loadSnapshot(snapshot({ paused: true, connection: "unauthorized" }));
    mountHeader();
    await flushPromises();
    const paused = button("File watching: Paused").get(".v-chip");
    expect(paused.classes()).toEqual(expect.arrayContaining(["bar-chip", "v-chip--variant-flat", "bg-app-bar-warning"]));
    expect(paused.classes()).not.toContain("status-chip");
    expect(button("Connection: Rejected API key").get(".v-chip").classes()).toEqual(
      expect.arrayContaining(["bar-chip", "v-chip--variant-flat", "bg-app-bar-error"]),
    );
    await click("File watching: Paused");
    expect(page().get(".watching-panel .panel-heading .v-chip").classes()).toEqual(
      expect.arrayContaining(["status-chip", "v-chip--variant-tonal", "text-warning"]),
    );
  });

  it("shows every other state on the bar as a translucent white chip in the white text of the bar", async () => {
    await loadSnapshot(snapshot({ connection: "connected" }));
    mountHeader();
    await flushPromises();
    for (const name of ["File watching: Active", "Connection: Connected"]) {
      const classes = button(name).get(".v-chip").classes();
      expect(classes).toEqual(expect.arrayContaining(["bar-chip", "v-chip--variant-tonal"]));
      expect(classes.filter((value) => value.startsWith("text-") || value.startsWith("bg-"))).toEqual([]);
    }
  });

  it("keeps the colors of the surface for the states in the collapsed menu", async () => {
    await loadSnapshot(snapshot({ paused: true, connection: "connected" }));
    setViewport(800);
    mountHeader();
    await flushPromises();
    await click("Header menu");
    expect(button("File watching: Paused").get(".v-chip").classes()).toEqual(
      expect.arrayContaining(["status-chip", "text-warning"]),
    );
    expect(button("Connection: Connected").get(".v-chip").classes()).toEqual(
      expect.arrayContaining(["status-chip", "text-success"]),
    );
  });

  it("shows the warning without a user and Set user in the colors of the bar, and of the surface in the collapsed menu", async () => {
    await loadSnapshot(snapshot({ user: "", author: { user: null, reason: "Set a user" } }));
    const wrapper = mountHeader();
    await flushPromises();
    expect(wrapper.get(".author-warning .v-icon").classes()).toContain("text-app-bar-warning");
    expect(button("Set user").classes().filter((value) => value.startsWith("text-"))).toEqual([]);
    setViewport(800);
    await flushPromises();
    await click("Header menu");
    expect(page().get(".header-panel .author-warning .v-icon").classes()).toContain("text-warning");
    expect(button("Set user").classes()).toContain("text-primary");
  });

  it("shows the connection details with the pkdb update hint", async () => {
    await loadSnapshot(
      snapshot({
        connection: "incompatible",
        connection_error: "The server needs pkdb 0.12.0 or newer",
        checked_at: "2026-10-07T10:15:00Z",
        endpoint: "https://pk-db.com",
        account: "curator",
        offline: false,
        vocabulary: { status: "current" },
        server_version: "0.12.0",
        update_required: true,
      }),
    );
    mountHeader();
    await flushPromises();
    await click("Connection: Update pkdb");
    const menu = page().get(".connection-panel");
    expect(menu.text()).toContain("The server needs pkdb 0.12.0 or newer");
    expect(menu.text()).toContain("Last checked");
    expect(menu.text()).toContain("https://pk-db.com");
    expect(menu.text()).toContain("curator");
    expect(menu.text()).toContain("Current");
    expect(menu.text()).toContain("Client 0.11.1 · server 0.12.0");
    expect(menu.get(".v-alert").text()).toContain("The server needs pkdb 0.12.0 or newer");
    expect(menu.get("code").text()).toBe("pkdb update");
    expect(menu.text()).toContain("The server runs pkdb 0.12.0. Stop pkdb curate, run pkdb update");
  });

  it("asks for pkdb update without naming an unknown server version", async () => {
    await loadSnapshot(snapshot({ connection: "incompatible", server_version: null, update_required: true }));
    mountHeader();
    await flushPromises();
    await click("Connection: Update pkdb");
    const menu = page().get(".connection-panel");
    expect(menu.text()).toContain("Stop pkdb curate, run pkdb update and start pkdb curate again.");
    expect(menu.text()).not.toContain("The server runs pkdb");
    expect(menu.find(".v-alert").exists()).toBe(false);
  });

  it("opens the settings from the connection menu", async () => {
    await loadSnapshot(snapshot());
    mountHeader();
    await flushPromises();
    await click("Connection: Offline");
    await click("Connection settings");
    expect(page().get('[role="dialog"]').text()).toContain("Connection settings");
    // The menu closes, so that it is not open behind the dialog nor after it.
    expect(button("Connection: Offline").attributes("aria-expanded")).toBe("false");
  });

  it("shows the user who writes the study files", async () => {
    await loadSnapshot(snapshot());
    const wrapper = mountHeader();
    await flushPromises();
    expect(wrapper.get(".author").text()).toContain("curator");
  });

  it("warns without a user and opens the settings from Set user", async () => {
    const reason = "A PK-DB user name is required: set it in Connection settings";
    await loadSnapshot(snapshot({ user: "", author: { user: null, reason } }));
    const wrapper = mountHeader();
    await flushPromises();
    expect(wrapper.get(".author").text()).toContain(reason);
    expect(page().find('[role="dialog"]').exists()).toBe(false);
    await click("Set user");
    expect(page().get('[role="dialog"]').text()).toContain("Connection settings");
  });

  it("opens the settings from the gear button", async () => {
    await loadSnapshot(snapshot());
    mountHeader();
    await flushPromises();
    await click("Settings");
    expect(page().get('[role="dialog"]').text()).toContain("Connection settings");
  });

  it("returns the focus to the gear button when the settings close", async () => {
    await loadSnapshot(snapshot());
    mountHeader();
    await flushPromises();
    await focusAndClick("Settings");
    focusDialog();
    await click("Cancel");
    expect(document.activeElement).toBe(button("Settings").element);
  });

  it("returns the focus to the menu button after a dialog that a menu item opened", async () => {
    await loadSnapshot(snapshot());
    mountHeader();
    await flushPromises();
    await focusAndClick("Connection: Offline");
    await focusAndClick("Connection settings");
    focusDialog();
    await click("Cancel");
    // The item went with the menu; its button stays.
    expect(document.activeElement).toBe(button("Connection: Offline").element);
  });

  it("returns the focus to the header menu in a narrow window", async () => {
    await loadSnapshot(snapshot());
    setViewport(800);
    mountHeader();
    await flushPromises();
    await focusAndClick("Header menu");
    await focusAndClick("Settings");
    focusDialog();
    await click("Cancel");
    expect(document.activeElement).toBe(button("Header menu").element);
  });

  it("focuses the gear button when the control that opened the settings is gone", async () => {
    await loadSnapshot(snapshot({ user: "", author: { user: null, reason: "Set a user" } }));
    const wrapper = mountHeader();
    await flushPromises();
    await focusAndClick("Set user");
    // Saving a user removes Set user.
    await loadSnapshot(snapshot());
    expect(wrapper.text()).not.toContain("Set user");
    focusDialog();
    await click("Cancel");
    expect(document.activeElement).toBe(button("Settings").element);
  });

  it("pauses the automatic actions", async () => {
    await loadSnapshot(snapshot());
    const pause = vi.spyOn(useOverviewStore(), "pause").mockResolvedValue(snapshot({ paused: true }));
    mountHeader();
    await flushPromises();
    await click("File watching: Active");
    expect(page().get(".watching-panel").text()).toContain("Saving a file starts the On save action.");
    await click("Pause automatic actions");
    expect(pause).toHaveBeenCalledWith(true);
  });

  it("resumes the automatic actions", async () => {
    await loadSnapshot(snapshot({ paused: true }));
    const resume = vi.spyOn(useOverviewStore(), "resume").mockResolvedValue(snapshot());
    mountHeader();
    await flushPromises();
    await click("File watching: Paused");
    await click("Resume automatic actions");
    expect(resume).toHaveBeenCalledWith();
  });

  it("shows why the server refused to resume", async () => {
    const reason = "The upload of caffeine/Example has an unknown outcome. Turn off offline mode.";
    await loadSnapshot(snapshot({ paused: true }));
    vi.spyOn(useOverviewStore(), "resume").mockRejectedValue(new ApiError(400, { error: reason }));
    mountHeader();
    await flushPromises();
    await click("File watching: Paused");
    await click("Resume automatic actions");
    expect(page().get(".watching-panel .v-alert").text()).toBe(reason);
    // It goes with the next attempt and when the menu opens again: no close button, which would drop the focus.
    expect(page().get(".watching-panel .v-alert").find(".v-alert__close").exists()).toBe(false);
  });

  it("tells that Resume first checks uploads with an unknown outcome", async () => {
    await loadSnapshot(snapshot({ paused: true, studies: [studyRow({ status: "unknown" })] }));
    mountHeader();
    await flushPromises();
    await click("File watching: Paused");
    expect(page().get(".watching-panel").text()).toContain(
      "Resume first checks the uploads with an unknown outcome on the server.",
    );
  });

  it("shows why pausing failed", async () => {
    await loadSnapshot(snapshot());
    vi.spyOn(useOverviewStore(), "pause").mockRejectedValue(new Error("Wait for the running job"));
    mountHeader();
    await flushPromises();
    await click("File watching: Active");
    await click("Pause automatic actions");
    expect(page().get(".watching-panel").text()).toContain("Wait for the running job");
    await click("File watching: Active");
    await afterMenuClosed();
    await click("File watching: Active");
    expect(button("File watching: Active").attributes("aria-expanded")).toBe("true");
    expect(page().get(".watching-panel").text()).not.toContain("Wait for the running job");
  });

  it("lists the recent workspaces and removes one", async () => {
    await loadSnapshot(
      snapshot({
        recent_workspaces: [
          { path: "/work/pkdb_data", exists: true },
          { path: "/work/other", exists: true },
        ],
      }),
    );
    const store = useOverviewStore();
    const forget = vi.spyOn(store, "forgetWorkspace").mockResolvedValue(snapshot());
    const select = vi.spyOn(store, "selectWorkspace").mockResolvedValue(snapshot());
    mountHeader();
    await flushPromises();
    await click("Workspace: /work/pkdb_data");
    // The current workspace is not listed again.
    expect(buttons("Open pkdb_data in /work")).toHaveLength(0);
    await click("Open other in /work");
    expect(select).toHaveBeenCalledWith("/work/other");
    expect(button("Workspace: /work/pkdb_data").attributes("aria-expanded")).toBe("false");
    await afterMenuClosed();
    await click("Workspace: /work/pkdb_data");
    expect(button("Workspace: /work/pkdb_data").attributes("aria-expanded")).toBe("true");
    await click("Remove /work/other from recent workspaces");
    expect(forget).toHaveBeenCalledWith("/work/other");
  });

  it("opens the folder browser from Choose workspace", async () => {
    await loadSnapshot(snapshot());
    vi.spyOn(useOverviewStore(), "listDirectories").mockResolvedValue({
      path: "/work/pkdb_data",
      parent: "/work",
      home: "/home/curator",
      kind: "repository",
      truncated: false,
      entries: [],
    });
    mountHeader();
    await flushPromises();
    await click("Workspace: /work/pkdb_data");
    await click("Choose workspace");
    expect(page().get('[role="dialog"]').text()).toContain("Choose workspace");
  });

  it("collapses into a menu below 960 px", async () => {
    await loadSnapshot(snapshot({ connection: "connected" }));
    setViewport(959);
    const wrapper = mountHeader();
    await flushPromises();
    expect(buttons(/^Workspace: /)).toHaveLength(0);
    expect(buttons("Settings")).toHaveLength(0);
    await click("Header menu");
    const menu = page().get(".header-panel");
    expect(menu.text()).toContain("pkdb_data");
    expect(menu.text()).toContain("Active");
    expect(buttons("On save: Validate")).toHaveLength(1);
    expect(menu.text()).toContain("Connected");
    expect(menu.text()).toContain("curator");
    setViewport(960);
    await flushPromises();
    expect(wrapper.find('[aria-label="Header menu"]').exists()).toBe(false);
    expect(button("Settings").exists()).toBe(true);
  });

  it("does not reopen the collapsed menu by itself after the window was wide", async () => {
    await loadSnapshot(snapshot());
    setViewport(800);
    mountHeader();
    await flushPromises();
    await click("Header menu");
    setViewport(1280);
    await flushPromises();
    setViewport(800);
    await flushPromises();
    expect(button("Header menu").attributes("aria-expanded")).toBe("false");
  });

  it("shows the last known state and offers no actions while the server is stopped", async () => {
    await loadSnapshot(snapshot({ connection: "unauthorized", recent_workspaces: [{ path: "/work/other", exists: true }] }));
    mountHeader();
    await flushPromises();
    expect(button("Connection: Rejected API key").get(".v-chip").classes()).toContain("bg-app-bar-error");
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    await useOverviewStore().refresh();
    await flushPromises();
    // The chips lose their status color: on the bar they are translucent white.
    for (const name of ["File watching: Active", "Connection: Rejected API key"])
      expect(button(name).get(".v-chip").classes().some((value) => value.startsWith("text-") || value.startsWith("bg-"))).toBe(false);
    await click("File watching: Active");
    expect(page().get(".watching-panel").text()).toContain("This is the last known state.");
    expect(button("Pause automatic actions").attributes("disabled")).toBeDefined();
    await click("Workspace: /work/pkdb_data");
    expect(button("Choose workspace").attributes("disabled")).toBeDefined();
    expect(button("Open other in /work").attributes("disabled")).toBeDefined();
    expect(button("Remove /work/other from recent workspaces").attributes("disabled")).toBeDefined();
    // The next good poll brings the actions back.
    vi.spyOn(globalThis, "fetch").mockImplementation(async () => json(snapshot({ connection: "unauthorized" })));
    await useOverviewStore().refresh();
    await flushPromises();
    expect(button("Choose workspace").attributes("disabled")).toBeUndefined();
    expect(button("Connection: Rejected API key").get(".v-chip").classes()).toContain("bg-app-bar-error");
  });

  it("switches the theme and keeps the choice", async () => {
    await loadSnapshot(snapshot());
    const wrapper = mountHeader();
    await flushPromises();
    expect(themeOf(wrapper)).toBe("v-theme--light");
    await click("Toggle color theme");
    expect(themeOf(wrapper)).toBe("v-theme--dark");
    expect(localStorage.getItem(THEME_KEY)).toBe("dark");
    // Back to the light system theme, the app follows the system again.
    await click("Toggle color theme");
    expect(themeOf(wrapper)).toBe("v-theme--light");
    expect(localStorage.getItem(THEME_KEY)).toBeNull();
    expect(followsSystem()).toBe(true);
  });

  it("keeps the choice in the local server, as the next start has another origin", async () => {
    await loadSnapshot(snapshot());
    const configure = vi.spyOn(useOverviewStore(), "configure").mockResolvedValue(snapshot({ theme: "dark" }));
    mountHeader();
    await flushPromises();
    await click("Toggle color theme");
    expect(configure).toHaveBeenLastCalledWith({ theme: "dark" });
    await click("Toggle color theme");
    expect(configure).toHaveBeenLastCalledWith({ theme: "system" });
  });

  it("switches the theme when the local server cannot keep it", async () => {
    await loadSnapshot(snapshot());
    vi.spyOn(useOverviewStore(), "configure").mockRejectedValue(new Error("The local server stopped."));
    const wrapper = mountHeader();
    await flushPromises();
    await click("Toggle color theme");
    expect(themeOf(wrapper)).toBe("v-theme--dark");
  });

  it("follows a dark system again when the curator switches to dark", async () => {
    // tests/setup-media.ts mocks matchMedia for all tests: this test replaces it and puts it back.
    const original = window.matchMedia;
    onTestFinished(() => {
      window.matchMedia = original;
    });
    window.matchMedia = (query) => mediaQuery(query, query.includes("dark"));
    localStorage.setItem(THEME_KEY, "light");
    await loadSnapshot(snapshot());
    mountHeader();
    await flushPromises();
    await click("Toggle color theme");
    expect(localStorage.getItem(THEME_KEY)).toBeNull();
    expect(followsSystem()).toBe(true);
  });

  it("switches the theme when the browser refuses storage", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("Storage is disabled", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("Storage is disabled", "SecurityError");
    });
    await loadSnapshot(snapshot());
    const wrapper = mountHeader();
    await flushPromises();
    await click("Toggle color theme");
    expect(themeOf(wrapper)).toBe("v-theme--dark");
  });

  it("shows that file watching fails, with the error and the log", async () => {
    const time = "2026-10-12T14:03:11+02:00";
    await loadSnapshot(snapshot({ watcher_error: { time, detail: "OSError: [Errno 5] Input/output error", recovered: false } }));
    mountHeader();
    await flushPromises();
    expect(button("File watching: Error").get(".v-chip").classes()).toContain("bg-app-bar-error");
    await click("File watching: Error");
    const panel = page().get(".watching-panel");
    expect(panel.get(".panel-heading .v-chip").classes()).toContain("text-error");
    expect(panel.get(".watcher-error-text").text()).toBe(`File watching failed at ${formatTime(time)}. It tries again every second.`);
    expect(panel.get(".watcher-error-detail").text()).toBe("OSError: [Errno 5] Input/output error");
    // At most 6 lines, as in the alert of an action; the rest scrolls, with the keyboard too.
    expect(panel.get(".watcher-error-detail").classes()).toContain("failure-detail");
    expect(panel.get(".watcher-error-detail").attributes("tabindex")).toBe("0");
    expect(panel.get(".watcher-error-log").text()).toBe(`The log has the traceback: ${snapshot().log_file}`);
  });

  it("tells that file watching works again after an error", async () => {
    const time = "2026-10-12T14:03:11+02:00";
    await loadSnapshot(snapshot({ watcher_error: { time, detail: "OSError: x", recovered: true } }));
    mountHeader();
    await flushPromises();
    await click("File watching: Active");
    expect(page().get(".watcher-recovered").text()).toBe(`File watching works again after an error at ${formatTime(time)}.`);
    expect(page().find(".watcher-error").exists()).toBe(false);
  });

  it("shows what failed when a recent workspace cannot be opened", async () => {
    await loadSnapshot(
      snapshot({
        recent_workspaces: [
          { path: "/work/pkdb_data", exists: true },
          { path: "/work/other", exists: true },
        ],
      }),
    );
    vi.spyOn(useOverviewStore(), "selectWorkspace").mockRejectedValue(
      new ApiError(400, {
        error: "Could not open the workspace.",
        code: "file_error",
        detail: "PermissionError: [Errno 13] Permission denied: '/work/other'",
        action: "Choose the workspace (POST /local/workspace)",
        ...FAILED,
      }),
    );
    mountHeader();
    await flushPromises();
    await click("Workspace: /work/pkdb_data");
    await click("Open other in /work");
    const alert = page().get(".workspace-panel .action-failure");
    expect(alert.get(".action-failure-text").text()).toBe("Could not open the workspace.");
    expect(alert.get(".action-failure-detail").text()).toBe("PermissionError: [Errno 13] Permission denied: '/work/other'");
    // It goes with the next attempt and when the menu opens again: no close button, which would drop the focus.
    expect(alert.find(".v-alert__close").exists()).toBe(false);
  });
});

describe("OnSaveMenu", () => {
  /** The account `curator` may upload to beta.pk-db.com. */
  const ONLINE: Partial<Snapshot> = {
    offline: false,
    endpoint: "https://beta.pk-db.com",
    authenticated: true,
    account: "curator",
    can_upload: true,
    connection: "connected",
  };

  function dialog() {
    return page().get('.v-overlay--active[role="dialog"]');
  }

  it("shows On save after File watching, with the icon and the label of the action", async () => {
    await loadSnapshot(snapshot({ mode: "off" }));
    mountHeader();
    await flushPromises();
    const onSave = button("On save: Off");
    expect(onSave.find("i.fa-pause").exists()).toBe(true);
    expect(onSave.get(".header-control-label").text()).toBe("On save");
    expect(onSave.get(".v-chip").text()).toBe("Off");
    // On the teal bar, a warning chip takes the warning color of the bar, as the other badges do.
    expect(onSave.get(".v-chip").classes()).toEqual(
      expect.arrayContaining(["bar-chip", "v-chip--variant-flat", "bg-app-bar-warning"]),
    );
    const names = page()
      .findAll(".header-controls button")
      .map((item) => item.attributes("aria-label"));
    expect(names.indexOf("On save: Off")).toBe(names.indexOf("File watching: Active") + 1);
  });

  it("lists the three actions, each with what a save does, and marks the one that is set", async () => {
    await loadSnapshot(snapshot());
    mountHeader();
    await flushPromises();
    await click("On save: Validate");
    const panel = page().get(".on-save-panel");
    expect(panel.get('[role="group"]').attributes("aria-label")).toBe("On save action");
    expect(["Validate", "Upload", "Off"].map((name) => button(name).attributes("aria-pressed"))).toEqual([
      "true",
      "false",
      "false",
    ]);
    expect(panel.text()).toContain("It applies to every study of this workspace, with this server and PK-DB account.");
    const line = (name: string) => document.getElementById(button(name).attributes("aria-describedby") ?? "")?.textContent?.trim();
    expect(line("Validate")).toBe("A save syncs, formats and validates the study.");
    expect(line("Off")).toBe("A save marks the study as changed. Validate or upload it yourself.");
  });

  it("sets Off for every study at once, and the action that is set sends nothing", async () => {
    await loadSnapshot(snapshot());
    const setMode = vi.spyOn(useOverviewStore(), "setMode").mockResolvedValue(snapshot({ mode: "off" }));
    mountHeader();
    await flushPromises();
    await click("On save: Validate");
    await click("Off");
    expect(setMode).toHaveBeenCalledWith("off");
    await click("Validate");
    expect(setMode).toHaveBeenCalledTimes(1);
  });

  it("offers no upload on save offline and says why", async () => {
    await loadSnapshot(snapshot());
    mountHeader();
    await flushPromises();
    await click("On save: Validate");
    const upload = button("Upload");
    expect(upload.attributes("disabled")).toBeDefined();
    expect(document.getElementById(upload.attributes("aria-describedby") ?? "")?.textContent).toContain(
      "Work offline is on. Turn it off in the settings to upload.",
    );
  });

  it("asks before it turns on upload on save for every study of the workspace", async () => {
    await loadSnapshot(snapshot(ONLINE));
    const setMode = vi.spyOn(useOverviewStore(), "setMode").mockResolvedValue(snapshot({ ...ONLINE, mode: "upload" }));
    mountHeader();
    await flushPromises();
    await click("On save: Validate");
    await click("Upload");
    expect(setMode).not.toHaveBeenCalled();
    expect(dialog().get("h2").text()).toBe("Turn on upload on save");
    expect(dialog().text()).toContain("https://beta.pk-db.com");
    expect(dialog().text()).toContain("/work/pkdb_data");
    expect(dialog().text()).toContain("saving a file of any study in this workspace");
    expect(dialog().find(".upload-studies").exists()).toBe(false);
    await click("Turn on upload on save");
    expect(setMode).toHaveBeenCalledWith("upload");
    expect(page().find('.v-overlay--active[role="dialog"]').exists()).toBe(false);
  });

  it("keeps the dialog open with the refusal of the server", async () => {
    await loadSnapshot(snapshot(ONLINE));
    vi.spyOn(useOverviewStore(), "setMode").mockRejectedValue(
      new ApiError(400, {
        error: "Could not set the On save action.",
        detail: "ValueError: Connect an authorized PK-DB account before enabling uploads on save",
      }),
    );
    mountHeader();
    await flushPromises();
    await click("On save: Validate");
    await click("Upload");
    await click("Turn on upload on save");
    expect(dialog().get(".v-alert").text()).toContain("Could not set the On save action.");
  });

  it("returns the focus to On save after the dialog that its Upload opened", async () => {
    await loadSnapshot(snapshot(ONLINE));
    mountHeader();
    await flushPromises();
    await focusAndClick("On save: Validate");
    await focusAndClick("Upload");
    focusDialog();
    await click("Cancel");
    expect(document.activeElement).toBe(button("On save: Validate").element);
  });

  it("is one more entry of the collapsed header, whose Upload opens the dialog of the header", async () => {
    await loadSnapshot(snapshot(ONLINE));
    setViewport(800);
    mountHeader();
    await flushPromises();
    await click("Header menu");
    await click("On save: Validate");
    await click("Upload");
    expect(button("Header menu").attributes("aria-expanded")).toBe("false");
    expect(dialog().get("h2").text()).toBe("Turn on upload on save");
  });

  it("shows why setting On save failed, until the menu opens again", async () => {
    await loadSnapshot(snapshot());
    vi.spyOn(useOverviewStore(), "setMode").mockRejectedValue(
      new ApiError(400, { error: "Could not set the On save action." }),
    );
    mountHeader();
    await flushPromises();
    await click("On save: Validate");
    await click("Off");
    expect(page().get(".on-save-panel .v-alert").text()).toContain("Could not set the On save action.");
    await click("On save: Validate");
    await afterMenuClosed();
    await click("On save: Validate");
    expect(button("On save: Validate").attributes("aria-expanded")).toBe("true");
    expect(page().find(".on-save-panel .v-alert").exists()).toBe(false);
  });

  it("shows the last known On save and offers no change while the server is stopped", async () => {
    await loadSnapshot(snapshot({ mode: "off" }));
    mountHeader();
    await flushPromises();
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    await useOverviewStore().refresh();
    await flushPromises();
    expect(button("On save: Off").get(".v-chip").classes().some((value) => value.startsWith("text-"))).toBe(false);
    await click("On save: Off");
    expect(page().get(".on-save-panel").text()).toContain("This is the last known state.");
    for (const name of ["Validate", "Upload", "Off"]) expect(button(name).attributes("disabled")).toBeDefined();
  });
});

describe("useColorTheme", () => {
  function mountRestored() {
    let system = false;
    const wrapper = mount(Probe, {
      props: {
        use: () => {
          useColorTheme().restore();
          system = useTheme().isSystem.value;
        },
      },
    });
    return { wrapper, system: () => system };
  }

  it("restores the theme that the curator chose", async () => {
    localStorage.setItem(THEME_KEY, "dark");
    const { wrapper, system } = mountRestored();
    await flushPromises();
    expect(wrapper.get(".v-application").classes()).toContain("v-theme--dark");
    expect(system()).toBe(false);
  });

  it("follows the system without a choice", () => {
    expect(mountRestored().system()).toBe(true);
  });

  it("starts with the theme that pkdb curate put into the page, over the one of this browser", () => {
    const meta = Object.assign(document.createElement("meta"), { name: "pkdb-theme", content: "dark" });
    document.head.append(meta);
    try {
      localStorage.setItem(THEME_KEY, "light");
      expect(initialTheme()).toBe("dark");
      meta.content = "system";
      expect(initialTheme()).toBe("system");
      // The development server leaves the placeholder: the browser's choice counts then.
      meta.content = "__PKDB_THEME__";
      expect(servedTheme()).toBeNull();
      expect(initialTheme()).toBe("light");
      localStorage.clear();
      expect(initialTheme()).toBe("system");
    } finally {
      meta.remove();
    }
  });

  it("applies the theme that the local server keeps over the one of this browser", async () => {
    localStorage.setItem(THEME_KEY, "light");
    await loadSnapshot(snapshot({ theme: "dark" }));
    const { wrapper } = mountRestored();
    await flushPromises();
    expect(wrapper.get(".v-application").classes()).toContain("v-theme--dark");
    expect(localStorage.getItem(THEME_KEY)).toBe("dark");
    // A choice made in another tab arrives with the next state.
    vi.spyOn(globalThis, "fetch").mockImplementation(async () => json(snapshot({ theme: "system" })));
    await useOverviewStore().refresh();
    await flushPromises();
    expect(followsSystem()).toBe(true);
    expect(localStorage.getItem(THEME_KEY)).toBeNull();
  });

  it("follows the system when the browser refuses storage", () => {
    localStorage.setItem(THEME_KEY, "dark");
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("Storage is disabled", "SecurityError");
    });
    expect(mountRestored().system()).toBe(true);
  });
});

describe("StatusBanner", () => {
  function mountBanner() {
    return mount(StatusBanner, { attachTo: document.body, global: { plugins: [pinia] } });
  }

  it("tells to start pkdb curate again while the server is stopped, until a poll succeeds", async () => {
    const fetch = vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    const wrapper = mountBanner();
    await useOverviewStore().refresh();
    await flushPromises();
    expect(wrapper.text()).toContain("The local server stopped. Start pkdb curate again.");
    fetch.mockImplementation(async () => json(snapshot()));
    await useOverviewStore().refresh();
    await flushPromises();
    expect(wrapper.text()).toBe("");
  });

  it("tells to open the printed link without a session", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async () => json({ error: "No session" }, { status: 401 }));
    const wrapper = mountBanner();
    await useOverviewStore().refresh();
    await flushPromises();
    expect(wrapper.text()).toContain("This page has no session. Open the link that pkdb curate printed.");
  });

  it("says once why the state could not be read, with what went wrong and Details", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
      json(
        {
          error: "Could not read the workspace state.",
          code: "unexpected",
          detail: "RuntimeError: boom",
          action: "Read the workspace state (GET /local/state)",
          ...FAILED,
        },
        { status: 500 },
      ),
    );
    const wrapper = mountBanner();
    await useOverviewStore().refresh();
    await flushPromises();
    const banner = wrapper.get(".status-banner");
    expect(banner.get(".action-failure-text").text()).toBe("Could not read the workspace state.");
    expect(banner.get(".action-failure-detail").text()).toBe("RuntimeError: boom");
    expect(banner.findAll(".failure-summary").map((summary) => summary.text())).toEqual(["Details"]);
    expect(wrapper.text().split("Could not read the workspace state.")).toHaveLength(2);
    expect(wrapper.text()).not.toContain("could not be loaded");
    expect(banner.find(".v-alert__close").exists()).toBe(false);
  });
});

describe("App", () => {
  it("polls the state of the local server while it is mounted", async () => {
    const store = useOverviewStore();
    const start = vi.spyOn(store, "start").mockResolvedValue();
    const stop = vi.spyOn(store, "stop").mockReturnValue();
    const wrapper = mount(App, { attachTo: document.body, global: { plugins: [pinia, router()] } });
    await flushPromises();
    expect(start).toHaveBeenCalledOnce();
    expect(stop).not.toHaveBeenCalled();
    wrapper.unmount();
    expect(stop).toHaveBeenCalledOnce();
  });
});
