import { vi } from "vitest";
import { DOMWrapper, flushPromises } from "@vue/test-utils";
import type { Snapshot, StudyRow } from "../../src/curation-app/api/types";
import { useOverviewStore } from "../../src/curation-app/stores/overview";

/**
 * A window of `width` pixels with the visual viewport that Vuetify places menus in; jsdom has
 * none. Vuetify reads the width from `resize` events.
 */
export function setViewport(width = 1280, height = 800): void {
  vi.stubGlobal(
    "visualViewport",
    Object.assign(new EventTarget(), { width, height, offsetTop: 0, offsetLeft: 0, scale: 1 }),
  );
  Object.defineProperty(window, "innerWidth", { configurable: true, value: width });
  Object.defineProperty(window, "innerHeight", { configurable: true, value: height });
  window.dispatchEvent(new Event("resize"));
}

/** The overview row of the valid study `caffeine/Example`. */
export function studyRow(changes: Partial<StudyRow> = {}): StudyRow {
  return {
    id: "caffeine/Example",
    name: "Example",
    path: "caffeine/Example",
    duplicate: false,
    substance: "caffeine",
    mode: "validate",
    status: "valid",
    stale: false,
    files: [{ id: "study.json", path: "study.json" }],
    problems: [],
    last_upload: null,
    progress: null,
    report_id: null,
    summary: { title: "Caffeine pharmacokinetics", review_status: "draft", open_items: 0 },
    reference: null,
    sync: { status: "in_sync", changes: 0, conflicts: 0 },
    counts: { errors: 0, warnings: 0 },
    issue: null,
    ...changes,
  };
}

/** The state of `GET /local/state` for a workspace with the user `curator`, offline. */
export function snapshot(changes: Partial<Snapshot> = {}): Snapshot {
  return {
    workspace: "/work/pkdb_data",
    endpoint: "https://beta.pk-db.com",
    user: "curator",
    author: { user: "curator", reason: null },
    authenticated: false,
    account: null,
    can_upload: false,
    connection: "offline",
    connection_error: null,
    checked_at: null,
    client_version: "0.11.1",
    server_version: null,
    update_required: false,
    offline: true,
    paused: false,
    vocabulary: { status: "offline" },
    github: { users: [], issues: [], status: "not_loaded", user: "", repository: "matthiaskoenig/pkdb_data" },
    studies: [],
    format1_folders: 0,
    jobs: [],
    recent_workspaces: [{ path: "/work/pkdb_data", exists: true }],
    ...changes,
  };
}

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

/** Loads `value` into the overview store as the next `GET /local/state` would. */
export async function loadSnapshot(value: Snapshot): Promise<void> {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => json(value));
  await useOverviewStore().refresh();
  await flushPromises();
}

/** The document body; menus and dialogs render there. */
export function page(): DOMWrapper<HTMLElement> {
  return new DOMWrapper(document.body);
}

/** The accessible name of a button: its `aria-label`, else its text. */
function nameOf(element: Element): string {
  return (element.getAttribute("aria-label") ?? element.textContent ?? "").replace(/\s+/g, " ").trim();
}

/** The buttons of the page, menus and dialogs included, with the accessible name `name`. */
export function buttons(name: string | RegExp): DOMWrapper<HTMLButtonElement>[] {
  return page()
    .findAll("button")
    .filter((button) =>
      typeof name === "string" ? nameOf(button.element) === name : name.test(nameOf(button.element)),
    );
}

/** The one button with the accessible name `name`. */
export function button(name: string | RegExp): DOMWrapper<HTMLButtonElement> {
  const found = buttons(name);
  if (found.length !== 1) throw new Error(`Expected one button "${String(name)}", found ${found.length}`);
  return found[0]!;
}

/** Clicks the button `name` and waits for the updates and promises that follow. */
export async function click(name: string | RegExp): Promise<void> {
  await button(name).trigger("click");
  await flushPromises();
}

/** Waits until a closed menu opens again: Vuetify ignores clicks on its activator for 50 ms. */
export function afterMenuClosed(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 60));
}

/** The text field with the label `label`. */
export function field(label: string): DOMWrapper<HTMLInputElement> {
  // Vuetify renders a field label twice; one of them names the input.
  const element = [...document.body.querySelectorAll("label")].find(
    (candidate) => candidate.htmlFor && candidate.textContent?.trim() === label,
  );
  const input = element?.htmlFor ? document.getElementById(element.htmlFor) : null;
  if (!(input instanceof HTMLInputElement)) throw new Error(`No field "${label}"`);
  return new DOMWrapper(input);
}
