import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import { defineComponent, h, type PropType } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";
import { useTheme } from "vuetify";
import { VApp } from "vuetify/components";
import App from "../../src/curation-app/App.vue";
import AppHeader from "../../src/curation-app/components/AppHeader.vue";
import StatusBanner from "../../src/curation-app/components/StatusBanner.vue";
import { useColorTheme } from "../../src/curation-app/composables/useColorTheme";
import type { ConnectionStatus } from "../../src/curation-app/api/types";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import {
  afterMenuClosed,
  button,
  buttons,
  click,
  json,
  loadSnapshot,
  page,
  setViewport,
  snapshot,
  studyRow,
} from "./curation-fixtures";

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

/** An app that calls `use` in its setup, for code that needs the Vuetify instance. */
const Probe = defineComponent({
  props: { use: { type: Function as PropType<() => void>, required: true } },
  setup(props) {
    props.use();
    return () => h(VApp, () => h("div"));
  },
});

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
  it("shows the logo, the app name and the workspace path", async () => {
    await loadSnapshot(snapshot());
    const wrapper = mountHeader();
    await flushPromises();
    expect(wrapper.get("img").attributes("alt")).toBe("PK-DB");
    expect(wrapper.text()).toContain("Local curation");
    expect(wrapper.text()).toContain("/work/pkdb_data");
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
    expect(menu.get("code").text()).toBe("pkdb update");
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

  it("pauses the automatic actions", async () => {
    await loadSnapshot(snapshot());
    const pause = vi.spyOn(useOverviewStore(), "pause").mockResolvedValue(snapshot({ paused: true }));
    mountHeader();
    await flushPromises();
    await click("File watching: Active");
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
    expect(buttons("Open /work/pkdb_data")).toHaveLength(0);
    await click("Open /work/other");
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
    expect(menu.text()).toContain("/work/pkdb_data");
    expect(menu.text()).toContain("Active");
    expect(menu.text()).toContain("Connected");
    expect(menu.text()).toContain("curator");
    setViewport(960);
    await flushPromises();
    expect(wrapper.find('[aria-label="Header menu"]').exists()).toBe(false);
    expect(button("Settings").exists()).toBe(true);
  });

  it("switches the theme and keeps the choice", async () => {
    await loadSnapshot(snapshot());
    const wrapper = mountHeader();
    await flushPromises();
    expect(themeOf(wrapper)).toBe("v-theme--light");
    await click("Toggle color theme");
    expect(themeOf(wrapper)).toBe("v-theme--dark");
    expect(localStorage.getItem(THEME_KEY)).toBe("dark");
    await click("Toggle color theme");
    expect(themeOf(wrapper)).toBe("v-theme--light");
    expect(localStorage.getItem(THEME_KEY)).toBe("light");
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
    vi.spyOn(globalThis, "fetch").mockImplementation(async () => json({ error: "No session" }, 401));
    const wrapper = mountBanner();
    await useOverviewStore().refresh();
    await flushPromises();
    expect(wrapper.text()).toContain("This page has no session. Open the link that pkdb curate printed.");
  });

  it("shows other failures of the state", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
      json({ error: "The local action failed. Review workspace activity and retry." }, 500),
    );
    const wrapper = mountBanner();
    await useOverviewStore().refresh();
    await flushPromises();
    expect(wrapper.text()).toContain("The local action failed. Review workspace activity and retry.");
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
