/** Mounting helpers of the curation app tests: viewport, state, buttons and fields. */
import { vi } from "vitest";
import { DOMWrapper, flushPromises, type VueWrapper } from "@vue/test-utils";
import type { VAutocomplete, VCombobox, VSelect } from "vuetify/components";
import { isRecord, type Snapshot } from "../../src/curation-app/api/types";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { json } from "../unit/curation-fixtures";

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

/** The control that a `<label for>` with the text `label` names, inside `within`. */
function labelled(label: string, within: Element): HTMLElement | null {
  // Vuetify renders a field label twice; one of them names the input.
  const element = [...within.querySelectorAll("label")].find(
    (candidate) => candidate.htmlFor && candidate.textContent?.trim() === label,
  );
  return element?.htmlFor ? document.getElementById(element.htmlFor) : null;
}

/** The text field with the label `label`, inside `within` (the page by default). */
export function field(label: string, within: Element = document.body): DOMWrapper<HTMLInputElement> {
  const input = labelled(label, within);
  if (!(input instanceof HTMLInputElement)) throw new Error(`No field "${label}"`);
  return new DOMWrapper(input);
}

/** The text area with the label `label`, inside `within` (the page by default). */
export function textArea(label: string, within: Element = document.body): DOMWrapper<HTMLTextAreaElement> {
  const input = labelled(label, within);
  if (!(input instanceof HTMLTextAreaElement)) throw new Error(`No text area "${label}"`);
  return new DOMWrapper(input);
}

/** The radio button with the label `label`. */
export function radio(label: string): HTMLInputElement {
  const input = labelled(label, document.body);
  if (!(input instanceof HTMLInputElement) || input.type !== "radio") throw new Error(`No radio "${label}"`);
  return input;
}

/** The messages below the field, text area or radio group of `control`: its hint or errors. */
export function messagesOf(control: { element: Element } | Element): string {
  const element = control instanceof Element ? control : control.element;
  const input = element.closest(".v-input");
  return (input?.querySelector(":scope > .v-input__details .v-messages")?.textContent ?? "").replace(/\s+/g, " ").trim();
}

/** The Vuetify select, autocomplete or combobox with the label `label`. */
export function labeled<T extends typeof VSelect | typeof VAutocomplete | typeof VCombobox>(
  wrapper: VueWrapper,
  component: T,
  label: string,
) {
  const found = wrapper.findAllComponents(component).find((candidate) => candidate.props("label") === label);
  if (!found) throw new Error(`No field "${label}"`);
  return found;
}

/** Answers each request by its path from `routes`, as the local server would; other paths get 404. */
export function serve(routes: Record<string, unknown>): void {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = input instanceof Request ? input.url : String(input);
    const path = new URL(url, "http://127.0.0.1").pathname;
    return path in routes ? json(routes[path]) : json({ error: "Unknown resource" }, { status: 404 });
  });
}

/** A request that `serveApi` answered, with its JSON body. */
export interface ServedRequest {
  method: string;
  path: string;
  body: Record<string, unknown> | null;
}

/** An answer of `serveApi` that depends on the JSON body of the request. */
export type Handler = (body: Record<string, unknown> | null) => Response | Promise<Response>;

function isHandler(value: unknown): value is Handler {
  return typeof value === "function";
}

/**
 * Answers each request by `<METHOD> <path>` from `routes`, as the local server would, and
 * records the requests. A route is a JSON body, or a `Handler` of the request body; other
 * routes get 404.
 */
export function serveApi(routes: Record<string, unknown>): ServedRequest[] {
  const requests: ServedRequest[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = input instanceof Request ? input.url : String(input);
    const method = init?.method ?? "GET";
    const path = new URL(url, "http://127.0.0.1").pathname;
    const body: unknown = typeof init?.body === "string" ? JSON.parse(init.body) : null;
    const record = isRecord(body) ? body : null;
    requests.push({ method, path, body: record });
    const key = `${method} ${path}`;
    if (!(key in routes)) return json({ error: "Unknown resource" }, { status: 404 });
    const answer = routes[key];
    return isHandler(answer) ? answer(record) : json(answer);
  });
  return requests;
}
