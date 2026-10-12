import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  onTestFinished,
  vi,
} from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import { ApiError, ServerStopped } from "../../src/curation-app/api/client";
import ActionFailureAlert from "../../src/curation-app/components/ActionFailureAlert.vue";
import { makeRouter } from "../../src/curation-app/router";
import {
  actionFailure,
  failureOf,
  type ActionFailure,
} from "../../src/curation-app/study";
import { snapshot } from "../unit/curation-fixtures";
import { button, click, loadSnapshot, page } from "./curation-dom";

enableAutoUnmount(afterEach);

const LOG = "/home/curator/.cache/pkdb/curation/logs/curation.log";
const OPEN_FAILED = {
  error: "Could not open the tables of caffeine/Example.",
  code: "open_failed",
  detail:
    "CalledProcessError: xdg-open exited with status 4\nno method available for opening",
  action: "Open tables (POST /local/studies/tables)",
  request_id: "3f9c2a71",
  time: "2026-10-12T14:03:11+02:00",
  activity_id: "0123456789abcdef0123456789abcdef",
};
const TRACEBACK = Array.from(
  { length: 30 },
  (_, line) => `  line ${line}`,
).join("\n");

let pinia: Pinia;

/** A clipboard with `writeText`, removed again after the test; jsdom has none. */
function stubClipboard(writeText: (text: string) => Promise<void>) {
  const spy = vi.fn(writeText);
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText: spy },
  });
  onTestFinished(() => {
    Reflect.deleteProperty(navigator, "clipboard");
  });
  return spy;
}

async function mountAlert(failure: ActionFailure, study: string | null = null) {
  const router = makeRouter();
  await router.push("/");
  await router.isReady();
  const wrapper = mount(ActionFailureAlert, {
    attachTo: document.body,
    props: { failure, study },
    global: { plugins: [pinia, router] },
  });
  await flushPromises();
  return wrapper;
}

beforeEach(async () => {
  pinia = createPinia();
  setActivePinia(pinia);
  await loadSnapshot(snapshot({ log_file: LOG }));
});

afterEach(() => {
  disposePinia(pinia);
});

describe("ActionFailureAlert", () => {
  it("shows the message alone for a failure that the app explains", async () => {
    await mountAlert(actionFailure("The path could not be copied: /work/x"));
    const alert = page().get(".action-failure");
    expect(alert.get(".action-failure-text").text()).toBe(
      "The path could not be copied: /work/x",
    );
    expect(alert.find(".action-failure-detail").exists()).toBe(false);
    expect(alert.find("summary").exists()).toBe(false);
    expect(alert.text()).not.toContain("Copy details");
  });

  it("shows the detail, the details and Show in Activity of a failure of the local server", async () => {
    await mountAlert(
      failureOf(new ApiError(500, OPEN_FAILED)),
      "caffeine/Example",
    );
    const alert = page().get(".action-failure");
    expect(alert.get(".action-failure-text").text()).toBe(OPEN_FAILED.error);
    expect(alert.get(".action-failure-detail").text()).toBe(OPEN_FAILED.detail);
    expect(alert.get(".failure-disclosure summary").text()).toBe("Details");
    const facts = alert.findAll(".failure-facts dt").map((term) => term.text());
    expect(facts).toEqual([
      "Action",
      "Status",
      "Code",
      "Error type",
      "Request",
      "Time",
      "Log",
    ]);
    expect(alert.get(".failure-facts").text()).toContain(LOG);
    expect(alert.get(".action-failure-activity").text()).toBe(
      "Show in Activity",
    );
    expect(alert.get(".action-failure-activity").attributes("href")).toBe(
      `#/studies/caffeine/Example/activity?entry=${OPEN_FAILED.activity_id}`,
    );
  });

  it("offers no link without the study of the page", async () => {
    await mountAlert(failureOf(new ApiError(500, OPEN_FAILED)));
    expect(page().get(".action-failure").findAll("a")).toHaveLength(0);
  });

  it("shows the traceback of an unexpected error in a block that the keyboard can scroll", async () => {
    await mountAlert(
      failureOf(
        new ApiError(500, {
          ...OPEN_FAILED,
          code: "unexpected",
          traceback: TRACEBACK,
        }),
      ),
    );
    const traceback = page().get(".failure-traceback");
    expect(traceback.text()).toBe(TRACEBACK.trim());
    expect(traceback.attributes("tabindex")).toBe("0");
  });

  it("copies the details as Markdown for an issue", async () => {
    const writeText = stubClipboard(async () => undefined);
    await mountAlert(failureOf(new ApiError(500, OPEN_FAILED)));
    await click("Copy details");
    expect(writeText).toHaveBeenCalledWith(
      [
        "**Could not open the tables of caffeine/Example.**",
        "",
        "```text",
        "CalledProcessError: xdg-open exited with status 4",
        "no method available for opening",
        "```",
        "",
        "- Action: Open tables (POST /local/studies/tables)",
        "- Status: 500",
        "- Code: open_failed",
        "- Request: 3f9c2a71",
        "- Time: 2026-10-12T14:03:11+02:00",
        "",
      ].join("\n"),
    );
    expect(page().get(".failure-copied").text()).toBe("Details copied.");
  });

  it("says when the details could not be copied", async () => {
    stubClipboard(() => Promise.reject(new Error("Denied")));
    await mountAlert(failureOf(new ApiError(500, OPEN_FAILED)));
    await click("Copy details");
    expect(page().get(".failure-copied").text()).toBe(
      "The details could not be copied.",
    );
  });

  it("names the request that did not reach the local server", async () => {
    await mountAlert(
      failureOf(
        new ServerStopped(
          "POST /local/studies/tables",
          new TypeError("Failed to fetch"),
        ),
      ),
    );
    const alert = page().get(".action-failure");
    expect(alert.get(".action-failure-text").text()).toBe(
      "Could not reach the local server.",
    );
    expect(alert.get(".action-failure-detail").text()).toBe(
      "TypeError: Failed to fetch",
    );
    expect(alert.get(".failure-facts").text()).toContain(
      "POST /local/studies/tables",
    );
  });

  it("can stay without a close button", async () => {
    const router = makeRouter();
    mount(ActionFailureAlert, {
      attachTo: document.body,
      props: {
        failure: actionFailure("reference.json could not be read."),
        closable: false,
      },
      global: { plugins: [pinia, router] },
    });
    await flushPromises();
    expect(page().get(".action-failure").find(".v-alert__close").exists()).toBe(
      false,
    );
    expect(() => button("Close")).toThrow();
  });
});
