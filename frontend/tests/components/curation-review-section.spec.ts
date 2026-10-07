import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DOMWrapper, enableAutoUnmount, flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import { defineComponent, h, type PropType } from "vue";
import { RouterView, type Router } from "vue-router";
import { VCombobox, VSelect } from "vuetify/components";
import type {
  Review,
  ReviewItem,
  ReviewTarget,
  SourceView,
  StudyDetail,
  TableResponse,
} from "../../src/curation-app/api/types";
import { formatTime } from "../../src/curation-app/overview";
import { makeRouter } from "../../src/curation-app/router";
import { useDialogStore } from "../../src/curation-app/stores/dialogs";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { json, reviewItem, roster, snapshot, sourceSummary, studyDetail } from "../unit/curation-fixtures";
import {
  button,
  buttons,
  click,
  labeled,
  messagesOf,
  page,
  radio,
  serveApi,
  setViewport,
  textArea,
  type Handler,
  type ServedRequest,
} from "./curation-dom";

enableAutoUnmount(afterEach);

const EXAMPLE = "/local/studies/caffeine/Example";
const REVIEW = "/local/studies/review";
const SECTION = "/studies/caffeine/Example/review";

const QUESTION = "01JA2XK7Q8M3R5T6V9W0Y1Z2AB";
const AGENT = "01JA30B3C4D5E6F7G8H9J0K1M2";
const RESOLVED = "01JA31N3P4Q5R6S7T8V9W0X1Y2";
const ACKNOWLEDGEMENT = "01JA32Z3A4B5C6D7E8F9G0H1J2";
const ADDED = "01JA40A1B2C3D4E5F6G7H8J9K0";

const question = reviewItem({
  id: QUESTION,
  target: { file: "outputs_Tab2.tsv", rows: {}, column: "mean" },
});
const uncertainty = reviewItem({
  id: AGENT,
  kind: "uncertainty",
  target: { file: "timecourses_Fig1.tsv", rows: { label: "caf_plasma_D150" }, column: "error_type" },
  text: "The error bars may be SE rather than SD.",
  author: "mkoenig",
  agent: "claude-opus-5-5",
  created: "2026-10-06T08:30:00Z",
  thread: [
    { author: "janekg", created: "2026-10-06T09:15:00Z", text: "The legend says mean and SD." },
    { author: "mkoenig", created: "2026-10-06T10:00:00Z", text: "Then the error type stays sd." },
  ],
});
const resolved = reviewItem({
  id: RESOLVED,
  kind: "issue",
  state: "resolved",
  target: { rows: {} },
  text: "The dose unit was missing.",
  author: "janekg",
  created: "2026-10-04T12:00:00Z",
});
const acknowledgement = reviewItem({
  id: ACKNOWLEDGEMENT,
  kind: "issue",
  state: "dismissed",
  acknowledges: "digitized_mismatch",
  target: { file: "timecourses_Fig1.tsv", rows: {} },
  text: "The digitized points are rounded to two digits.",
  author: "mkoenig",
  created: "2026-10-03T07:45:00Z",
  resolved_by: "janekg",
  resolved: "2026-10-05T16:20:00Z",
});

/** An acknowledgement as `pkdb review acknowledge` writes it: resolved at once. */
const RESOLVED_ACKNOWLEDGEMENT = "01JA33A1B2C3D4E5F6G7H8J9K0";
const resolvedAcknowledgement = reviewItem({
  id: RESOLVED_ACKNOWLEDGEMENT,
  kind: "issue",
  state: "resolved",
  acknowledges: "digitized_mismatch",
  target: { file: "timecourses_Fig1.tsv", rows: { label: "caf_plasma_D150", time: "0.5" }, column: "mean" },
  text: "The 0.5 h point is rounded in the figure.",
  author: "mkoenig",
});

const timecourses: TableResponse = {
  file: "timecourses_Fig1.tsv",
  kind: "table",
  header: ["study", "source", "label", "time", "mean", "sd", "error_type", "comment"],
  rows: [
    { line: 2, cells: ["Example", "Fig1", "caf_plasma_D150", "0", "0.166", "0.316", "sd", ""] },
    { line: 3, cells: ["Example", "Fig1", "caf_plasma_D150", "0.5", "2.419", "3.051", "sd", ""] },
    { line: 4, cells: ["Example", "Fig1", "caf_plasma_D300", "0", "0.2", "0.4", "sd", ""] },
  ],
};
const outputs: TableResponse = {
  file: "outputs_Tab2.tsv",
  kind: "table",
  header: ["study", "source", "label", "measurement", "mean", "unit"],
  rows: [
    { line: 2, cells: ["Example", "Tab2", "caf_cl", "clearance", "1.2", "ml/min/kg"] },
    { line: 3, cells: ["Example", "Tab2", "caf_thalf", "thalf", "4.8", "h"] },
  ],
};
const figure: SourceView = {
  source: "Fig1",
  image: "Example_Fig1.png",
  image_url: `${EXAMPLE}/files/Example_Fig1.png`,
  image_size: [600, 400],
  raw_grid: null,
  digitization: "Example_Fig1.wpd.json",
  mapped: [],
  overlay: [],
  unmatched: [],
  layout: "overlay",
  points: [],
  series: [],
};

/** Task 9 builds the figure overlay; the section passes it the source view and the series to emphasize. */
const OverlayStub = defineComponent({
  name: "SourceOverlay",
  props: {
    view: { type: Object as PropType<SourceView>, required: true },
    highlight: { type: String as PropType<string | null>, default: null },
  },
  emits: ["select-row"],
  setup(props, { emit }) {
    return () =>
      h("div", { class: "overlay-stub" }, [
        `${props.view.source} ${props.highlight ?? "none"}`,
        h(
          "button",
          { type: "button", onClick: () => emit("select-row", { file: "timecourses_Fig1.tsv", line: 3 }) },
          "Select a mapped point",
        ),
      ]);
  },
});

let pinia: Pinia;
let router: Router;
let requests: ServedRequest[];
let wrapper: VueWrapper;
/** The detail that `GET /local/studies/caffeine/Example` answers; a write may change it. */
let served: StudyDetail;

function withReview(review: Partial<Review> = {}, revision = "review-7"): StudyDetail {
  const base = studyDetail();
  return studyDetail({
    review: {
      revision,
      value: {
        status: "in_review",
        reviewers: ["curator"],
        items: [question, uncertainty, resolved, acknowledgement],
        ...review,
      },
      issues: [],
    },
    sources: [
      sourceSummary({
        source: "Fig1",
        kind: "figure",
        image: "Example_Fig1.png",
        raw: "Example_Fig1.wpd.json",
        raw_kind: "digitization",
        tables: ["timecourses_Fig1.tsv"],
      }),
      ...base.sources.slice(1),
    ],
    files: [...base.files, "Example_Fig1.wpd.json"].sort(),
  });
}

/** review.json at the next revision, with the item `id` replaced by `change` of it and the items of `more`. */
function changed(id: string, change: (item: ReviewItem) => ReviewItem, more: ReviewItem[] = []): StudyDetail {
  const current = served.review;
  const items = current.value?.items ?? [];
  const next = Number(current.revision?.split("-")[1] ?? 0) + 1;
  return {
    ...served,
    review: {
      revision: `review-${next}`,
      value: { ...current.value!, items: [...items.map((entry) => (entry.id === id ? change(entry) : entry)), ...more] },
      issues: [],
    },
  };
}

/** Changes review.json as the local server would for resolve, dismiss, reopen, reply and add. */
const write: Handler = (body) => {
  const id = String(body?.item ?? "");
  const text = typeof body?.text === "string" ? body.text : undefined;
  const reply = text ? [{ author: "curator", created: "2026-10-07T12:00:00Z", text }] : [];
  const thread = [...(served.review.value?.items.find((entry) => entry.id === id)?.thread ?? []), ...reply];
  switch (body?.action) {
    case "resolve":
    case "dismiss": {
      const state = body.action === "resolve" ? "resolved" : "dismissed";
      served = changed(id, (item) => ({ ...item, state, resolved_by: "curator", resolved: "2026-10-07T12:00:00Z", thread }));
      break;
    }
    case "reopen":
      served = changed(id, (item) => {
        const reopened: ReviewItem = { ...item, state: "open", thread };
        delete reopened.resolved_by;
        delete reopened.resolved;
        return reopened;
      });
      break;
    case "reply":
      served = changed(id, (item) => ({ ...item, thread }));
      break;
    case "add": {
      const item = reviewItem({
        id: ADDED,
        kind: body.kind as ReviewItem["kind"],
        text: String(body.text),
        ...(body.target ? { target: body.target as ReviewTarget } : {}),
      });
      served = changed("", (entry) => entry, [item]);
      return json({ revision: served.review.revision, item });
    }
  }
  return json({ revision: served.review.revision });
};

/** The review section inside the app's router view at `path`, with `routes` besides the defaults. */
async function mountSection(
  detail: StudyDetail = withReview(),
  routes: Record<string, unknown> = {},
  path = SECTION,
) {
  served = detail;
  requests = serveApi({
    "GET /local/state": snapshot(),
    [`GET ${EXAMPLE}`]: (() => json(served)) satisfies Handler,
    "GET /local/curators": { curators: roster() },
    [`GET ${EXAMPLE}/tables/timecourses_Fig1.tsv`]: timecourses,
    [`GET ${EXAMPLE}/tables/outputs_Tab2.tsv`]: outputs,
    [`GET ${EXAMPLE}/sources/Fig1`]: figure,
    [`POST ${REVIEW}`]: write,
    ...routes,
  });
  await useOverviewStore().refresh();
  router = makeRouter();
  await router.push(path);
  await router.isReady();
  wrapper = mount(RouterView, {
    attachTo: document.body,
    global: { plugins: [pinia, router], stubs: { SourceOverlay: OverlayStub } },
  });
  await flushPromises();
  return wrapper;
}

/** Waits until the route selects the item `id`: a navigation guard of Vuetify waits for a timer. */
function routedTo(id: string): Promise<void> {
  return vi.waitFor(() => expect(router.currentRoute.value.query.item).toBe(id));
}

function posted(): (Record<string, unknown> | null)[] {
  return requests.filter((request) => request.method === "POST" && request.path === REVIEW).map(({ body }) => body);
}

function fetched(path: string): number {
  return requests.filter((request) => request.method === "GET" && request.path === path).length;
}

/** The state chip `label`, such as Open, with its count. */
function chip(label: string): DOMWrapper<HTMLButtonElement> {
  const found = page()
    .findAll<HTMLButtonElement>('[aria-label="Filter by state"] button')
    .filter((candidate) => candidate.text().replace(/\s*\d+$/, "") === label);
  if (found.length !== 1) throw new Error(`Expected one chip "${label}", found ${found.length}`);
  return found[0]!;
}

function chipCount(label: string): string {
  return chip(label).get(".chip-count").text();
}

/** The cards of the shown items. */
function cards(): DOMWrapper<HTMLButtonElement>[] {
  return page().findAll<HTMLButtonElement>(".review-card");
}

/** The card of the item with the text `text`. */
function card(text: string): DOMWrapper<HTMLButtonElement> {
  const found = cards().filter((candidate) => candidate.text().includes(text));
  if (found.length !== 1) throw new Error(`Expected one card "${text}", found ${found.length}`);
  return found[0]!;
}

async function select(text: string): Promise<void> {
  await card(text).trigger("click");
  await flushPromises();
}

function detail() {
  return page().get(".review-detail");
}

function target() {
  return page().get(".review-target");
}

function dialog() {
  return page().get('.v-overlay--active[role="dialog"]');
}

function notice(): string {
  return page().get(".review-notice").text();
}

/** The TSV lines of the rows in the target view. */
function targetLines(): string[] {
  return target()
    .findAll("tbody tr")
    .map((row) => row.get("th").text());
}

beforeEach(() => {
  setViewport(1440);
  pinia = createPinia();
  setActivePinia(pinia);
});

afterEach(() => {
  disposePinia(pinia);
});

describe("filters", () => {
  it("shows the state chips with counts and the open items first", async () => {
    await mountSection();
    expect(chipCount("Open")).toBe("2");
    expect(chipCount("Resolved")).toBe("1");
    expect(chipCount("Dismissed")).toBe("1");
    expect(chipCount("All")).toBe("4");
    expect(chip("Open").attributes("aria-pressed")).toBe("true");
    expect(cards()).toHaveLength(2);

    await chip("Resolved").trigger("click");
    await flushPromises();
    expect(cards().map((entry) => entry.text())).toEqual([expect.stringContaining("The dose unit was missing.")]);
    await chip("All").trigger("click");
    await flushPromises();
    expect(cards()).toHaveLength(4);
  });

  it("filters by kind and counts the items of that kind", async () => {
    const wrapper = await mountSection();
    await chip("All").trigger("click");
    await labeled(wrapper, VSelect, "Kind").setValue("issue");
    await flushPromises();
    expect(cards()).toHaveLength(2);
    expect(chipCount("Open")).toBe("0");
    expect(chipCount("Resolved")).toBe("1");
    expect(chipCount("All")).toBe("2");

    await chip("Open").trigger("click");
    await flushPromises();
    expect(cards()).toHaveLength(0);
    expect(page().get(".review-empty").text()).toBe("No open issues.");
  });

  it("opens on the item of the route and shows its state", async () => {
    await mountSection(withReview(), {}, `${SECTION}?item=${ACKNOWLEDGEMENT}`);
    expect(chip("Dismissed").attributes("aria-pressed")).toBe("true");
    expect(detail().text()).toContain("The digitized points are rounded to two digits.");
    expect(card("The digitized points").attributes("aria-current")).toBe("true");
  });
});

describe("item cards", () => {
  it("show the kind, the state, the target and the markers of an agent and a thread", async () => {
    await mountSection();
    const agent = card("The error bars may be SE rather than SD.");
    expect(agent.get(".review-card-kind").text()).toBe("Uncertainty");
    expect(agent.get(".review-card-state").text()).toBe("Open");
    // Chrome leaves the text of a draggable="false" element, such as a VChip, out of the button name.
    expect(agent.find('[draggable="false"]').exists()).toBe(false);
    expect(agent.get(".review-card-target").text()).toBe(
      "timecourses_Fig1.tsv · label = caf_plasma_D150 · column error_type",
    );
    expect(agent.find('[role="img"][aria-label="Written by claude-opus-5-5"]').exists()).toBe(true);
    expect(agent.get(".review-card-thread").attributes("aria-label")).toBe("2 replies");
    expect(agent.get(".review-card-thread").text()).toBe("2");

    const plain = card("Is the mean read from the table?");
    expect(plain.find(".review-card-agent").exists()).toBe(false);
    expect(plain.find(".review-card-thread").exists()).toBe(false);
  });

  it("show the code of an acknowledged warning and the whole study as a target", async () => {
    await mountSection();
    await chip("All").trigger("click");
    await flushPromises();
    const acknowledged = card("The digitized points");
    expect(acknowledged.get(".review-card-state").text()).toBe("Dismissed");
    expect(acknowledged.get(".review-card-code").text()).toContain("digitized_mismatch");
    expect(card("The dose unit was missing.").get(".review-card-target").text()).toBe("Whole study");
  });
});

describe("selected item", () => {
  it("shows the text, the author with avatar, the agent, the time and the thread", async () => {
    await mountSection();
    expect(card("Is the mean read from the table?").attributes("aria-current")).toBe("true");

    await select("The error bars");
    await routedTo(AGENT);
    expect(card("The error bars").attributes("aria-current")).toBe("true");
    const shown = detail();
    expect(shown.get(".review-detail-text").text()).toBe("The error bars may be SE rather than SD.");
    expect(shown.get(".review-detail-author").text()).toContain("Matthias König");
    expect(shown.get(".review-detail-author img").attributes("src")).toBe("/avatars/mkoenig.webp");
    expect(shown.text()).toContain("written by claude-opus-5-5");
    expect(shown.text()).toContain(formatTime("2026-10-06T08:30:00Z"));
    const entries = shown.findAll(".thread-entry");
    expect(entries).toHaveLength(2);
    expect(entries[0]!.text()).toContain("Jan Grzegorzewski");
    expect(entries[0]!.text()).toContain(formatTime("2026-10-06T09:15:00Z"));
    expect(entries[0]!.text()).toContain("The legend says mean and SD.");
    expect(entries[1]!.text()).toContain("Then the error type stays sd.");
  });

  it("offers a reply box, Reply, Resolve and Dismiss for an open item", async () => {
    await mountSection();
    expect(textArea("Reply", detail().element).exists()).toBe(true);
    expect(buttons("Reply")).toHaveLength(1);
    expect(buttons("Resolve")).toHaveLength(1);
    expect(buttons("Dismiss")).toHaveLength(1);
    expect(buttons("Reopen")).toHaveLength(0);
    expect(button("Reply").attributes("disabled")).toBeDefined();
  });

  it("offers a reply box, Reply, Reopen and Dismiss for a resolved item", async () => {
    await mountSection();
    await chip("Resolved").trigger("click");
    await flushPromises();
    expect(detail().text()).toContain("The dose unit was missing.");
    expect(detail().text()).toContain(`Resolved by Matthias König on ${formatTime("2026-10-06T09:00:00Z")}.`);
    expect(messagesOf(textArea("Reply", detail().element))).toBe("Dismiss and Reopen add it to the thread too.");
    expect(buttons("Reply")).toHaveLength(1);
    expect(buttons("Resolve")).toHaveLength(0);
    expect(buttons("Reopen")).toHaveLength(1);
    expect(buttons("Dismiss")).toHaveLength(1);
  });

  it("dismisses a resolved acknowledgement with the reply, so that its warning comes back", async () => {
    await mountSection(withReview({ items: [question, resolvedAcknowledgement] }), {}, `${SECTION}?item=${RESOLVED_ACKNOWLEDGEMENT}`);
    expect(detail().text()).toContain(
      "Acknowledges the warning digitized_mismatch. Dismissing the item brings the warning back.",
    );
    await textArea("Reply", detail().element).setValue("  The point is not rounded after all.  ");
    await click("Dismiss");
    expect(posted()).toEqual([
      {
        study: "caffeine/Example",
        revision: "review-7",
        action: "dismiss",
        item: RESOLVED_ACKNOWLEDGEMENT,
        text: "The point is not rounded after all.",
      },
    ]);
    expect(notice()).toBe("Item dismissed. Its warning digitized_mismatch is no longer acknowledged.");
    expect(detail().get(".review-detail-state").text()).toBe("Dismissed");
    expect(() => textArea("Reply", detail().element)).toThrow();
    expect(buttons("Reopen")).toHaveLength(1);
    expect(buttons("Dismiss")).toHaveLength(0);
  });

  it("reopens a resolved item with the reply as its text", async () => {
    await mountSection();
    await chip("Resolved").trigger("click");
    await flushPromises();
    await textArea("Reply", detail().element).setValue("The unit is still missing in one row.");
    await click("Reopen");
    expect(posted()).toEqual([
      {
        study: "caffeine/Example",
        revision: "review-7",
        action: "reopen",
        item: RESOLVED,
        text: "The unit is still missing in one row.",
      },
    ]);
    expect(notice()).toBe("Item reopened.");
  });

  it("posts a reply and empties the box", async () => {
    await mountSection();
    await select("The error bars");
    await textArea("Reply", detail().element).setValue("SD, see the legend of Figure 1.\n");
    await click("Reply");
    expect(posted()).toEqual([
      { study: "caffeine/Example", revision: "review-7", action: "reply", item: AGENT, text: "SD, see the legend of Figure 1." },
    ]);
    expect(notice()).toBe("Reply posted.");
    expect(textArea("Reply", detail().element).element.value).toBe("");
    expect(detail().findAll(".thread-entry")).toHaveLength(3);
  });

  it("resolves with the reply as its text over the revision of review.json", async () => {
    await mountSection();
    await textArea("Reply", detail().element).setValue("The mean is in Table 2.");
    await click("Resolve");
    expect(posted()).toEqual([
      { study: "caffeine/Example", revision: "review-7", action: "resolve", item: QUESTION, text: "The mean is in Table 2." },
    ]);
    expect(notice()).toBe("Item resolved.");
    // The resolved item stays selected, so that it can be reopened, though the Open chip hides it.
    await routedTo(QUESTION);
    expect(cards()).toHaveLength(1);
    expect(detail().get(".review-detail-state").text()).toBe("Resolved");
    expect(buttons("Reopen")).toHaveLength(1);
  });

  it("resolves and dismisses without a text", async () => {
    await mountSection();
    await click("Resolve");
    await select("The error bars");
    await click("Dismiss");
    expect(posted()).toEqual([
      { study: "caffeine/Example", revision: "review-7", action: "resolve", item: QUESTION },
      { study: "caffeine/Example", revision: "review-8", action: "dismiss", item: AGENT },
    ]);
    expect(notice()).toBe("Item dismissed.");
  });

  it("reopens a dismissed acknowledgement, so that it acknowledges its warning again", async () => {
    await mountSection(withReview(), {}, `${SECTION}?item=${ACKNOWLEDGEMENT}`);
    expect(detail().text()).toContain("Dismissed, so it no longer acknowledges the warning digitized_mismatch.");
    await click("Reopen");
    expect(posted()).toEqual([
      { study: "caffeine/Example", revision: "review-7", action: "reopen", item: ACKNOWLEDGEMENT },
    ]);
    expect(notice()).toBe("Item reopened. It acknowledges digitized_mismatch again.");
    expect(detail().text()).toContain("Acknowledges the warning digitized_mismatch.");
    expect(buttons("Dismiss")).toHaveLength(1);
  });

  it("refuses new items and reopening while the study is approved", async () => {
    await mountSection(
      withReview({
        status: "approved",
        reviewers: ["mkoenig"],
        approved_by: "mkoenig",
        approved: "2026-10-07T09:00:00Z",
        items: [resolved],
      }),
    );
    expect(chip("All").attributes("aria-pressed")).toBe("true");
    expect(page().get(".review-approved").text()).toBe(
      "The study is approved. Set the review status to In review to add or reopen items.",
    );
    expect(button("New item").attributes("disabled")).toBeDefined();
    expect(button("Reopen").attributes("disabled")).toBeDefined();
    // The local server dismisses and replies on an approved study, but reopens nothing.
    expect(button("Dismiss").attributes("disabled")).toBeUndefined();
    expect(textArea("Reply", detail().element).element.disabled).toBe(false);
  });

  it("shows the issues of an invalid review.json instead of the items", async () => {
    await mountSection(
      studyDetail({
        review: {
          revision: "review-3",
          value: null,
          issues: [{ code: "invalid_json", severity: "error", message: "review.json is not valid JSON: line 4" }],
        },
      }),
    );
    expect(page().get(".review-invalid").text()).toContain("review.json is not valid, so the items cannot be shown.");
    expect(page().get(".review-invalid").text()).toContain("review.json is not valid JSON: line 4");
    expect(cards()).toHaveLength(0);
    expect(buttons("New item")).toHaveLength(0);
  });
});

describe("new item", () => {
  it("adds an item about the whole study and selects it", async () => {
    await mountSection();
    await click("New item");
    expect(dialog().get("h2").text()).toBe("New review item");
    expect(radio("Question").checked).toBe(true);
    expect(button("Add").attributes("disabled")).toBeDefined();

    radio("Issue").click();
    await textArea("Text").setValue("The subjects table lacks the smokers. ");
    await click("Add");
    expect(posted()).toEqual([
      {
        study: "caffeine/Example",
        revision: "review-7",
        action: "add",
        kind: "issue",
        text: "The subjects table lacks the smokers.",
      },
    ]);
    expect(page().find('.v-overlay--active[role="dialog"]').exists()).toBe(false);
    expect(notice()).toBe("Item added.");
    await routedTo(ADDED);
    expect(detail().get(".review-detail-text").text()).toBe("The subjects table lacks the smokers.");
  });

  it("targets rows of a table by values of its columns, and a column", async () => {
    const wrapper = await mountSection();
    await click("New item");
    const file = labeled(wrapper, VSelect, "File");
    expect(file.props("items")).toEqual(served.files);

    await textArea("Text").setValue("Check the error type of the 150 mg series.");
    await file.setValue("timecourses_Fig1.tsv");
    await flushPromises();
    await click("Add row filter");
    const column = labeled(wrapper, VSelect, "Column 1");
    expect(column.props("items")).toEqual(timecourses.kind === "table" ? timecourses.header : []);
    await column.setValue("label");
    await flushPromises();
    const value = labeled(wrapper, VCombobox, "Value 1");
    expect(value.props("items")).toEqual(["caf_plasma_D150", "caf_plasma_D300"]);
    // A filter with a column waits for its value.
    expect(messagesOf(value.element)).toBe("Choose or type the value of the rows.");
    expect(button("Add").attributes("disabled")).toBeDefined();
    await value.setValue("caf_plasma_D150");
    await labeled(wrapper, VSelect, "Column").setValue("error_type");
    await flushPromises();
    expect(dialog().get(".new-item-matches").text()).toBe("Matches 2 of 3 rows.");
    expect(messagesOf(value.element)).toBe("");

    await click("Add");
    expect(posted()).toEqual([
      {
        study: "caffeine/Example",
        revision: "review-7",
        action: "add",
        kind: "question",
        text: "Check the error type of the 150 mg series.",
        target: { file: "timecourses_Fig1.tsv", rows: { label: "caf_plasma_D150" }, column: "error_type" },
      },
    ]);
  });

  it("warns about a row filter that matches no row and offers no rows for other files", async () => {
    const wrapper = await mountSection();
    await click("New item");
    await labeled(wrapper, VSelect, "File").setValue("timecourses_Fig1.tsv");
    await flushPromises();
    await click("Add row filter");
    await labeled(wrapper, VSelect, "Column 1").setValue("label");
    await labeled(wrapper, VCombobox, "Value 1").setValue("caf_plasma_D75");
    await flushPromises();
    expect(dialog().get(".new-item-matches").text()).toBe("Matches none of 3 rows.");
    expect(dialog().get(".new-item-matches").attributes("role")).toBe("status");

    await labeled(wrapper, VSelect, "File").setValue("Example.pdf");
    await flushPromises();
    expect(buttons("Add row filter")).toHaveLength(0);
    expect(() => labeled(wrapper, VSelect, "Column")).toThrow();
    expect(dialog().text()).toContain("Rows and a column narrow only a table.");
  });
});

describe("new item filters", () => {
  it("keeps the values of a filter when a filter above it is removed", async () => {
    const wrapper = await mountSection();
    await click("New item");
    await labeled(wrapper, VSelect, "File").setValue("timecourses_Fig1.tsv");
    await flushPromises();
    await click("Add row filter");
    await labeled(wrapper, VSelect, "Column 1").setValue("label");
    await labeled(wrapper, VCombobox, "Value 1").setValue("caf_plasma_D150");
    await click("Add row filter");
    await labeled(wrapper, VSelect, "Column 2").setValue("time");
    await labeled(wrapper, VCombobox, "Value 2").setValue("0");
    await flushPromises();
    expect(dialog().get(".new-item-matches").text()).toBe("Matches 1 of 3 rows.");

    await click("Remove row filter 1");
    expect(labeled(wrapper, VSelect, "Column 1").props("modelValue")).toBe("time");
    expect(labeled(wrapper, VCombobox, "Value 1").props("modelValue")).toBe("0");
    expect(dialog().get(".new-item-matches").text()).toBe("Matches 2 of 3 rows.");
  });
});

describe("target", () => {
  it("lists the rows of the target table and marks its column", async () => {
    await mountSection();
    expect(target().text()).toContain("outputs_Tab2.tsv · column mean");
    expect(targetLines()).toEqual(["2", "3"]);
    expect(target().text()).toContain("The table has 2 rows.");
    expect(target().get("thead .target-column").text()).toContain("mean");
    expect(target().findAll("tbody .target-column").map((cell) => cell.text())).toEqual(["1.2", "4.8"]);
    expect(target().find(".overlay-stub").exists()).toBe(false);
  });

  it("lists the matching rows and shows the overlay of a digitized series with the series emphasized", async () => {
    await mountSection();
    await select("The error bars");
    expect(fetched(`${EXAMPLE}/tables/timecourses_Fig1.tsv`)).toBe(1);
    expect(targetLines()).toEqual(["2", "3"]);
    expect(target().text()).toContain("Matches 2 of 3 rows.");
    // The empty comment column is hidden.
    expect(target().findAll("thead th").map((cell) => cell.text())).not.toContain("comment");
    expect(fetched(`${EXAMPLE}/sources/Fig1`)).toBe(1);
    const overlay = wrapper.findComponent(OverlayStub);
    expect(overlay.props("view")).toEqual(figure);
    expect(overlay.props("highlight")).toBe("caf_plasma_D150");
  });

  it("opens the Tables section at the row of a clicked mapped point", async () => {
    await mountSection();
    await select("The error bars");
    await click("Select a mapped point");
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe("/studies/caffeine/Example/tables"));
    expect(router.currentRoute.value.query).toEqual({ file: "timecourses_Fig1.tsv", line: "3" });
  });

  it("shows the overlay of a digitized scatter series", async () => {
    const scatter = reviewItem({
      id: ADDED,
      kind: "question",
      target: { file: "scatters_Fig1.tsv", rows: { name: "age_vs_cmax" } },
      text: "Is the age the median?",
    });
    await mountSection(withReview({ items: [scatter] }));
    expect(fetched(`${EXAMPLE}/sources/Fig1`)).toBe(1);
    expect(wrapper.findComponent(OverlayStub).props("highlight")).toBe("age_vs_cmax");
  });
});

describe("failures", () => {
  it("reloads the items after review.json changed on disk", async () => {
    const onDisk = reviewItem({ id: ADDED, kind: "issue", text: "Added in the editor." });
    await mountSection(withReview(), {
      [`POST ${REVIEW}`]: (() => {
        served = withReview({ items: [question, uncertainty, resolved, acknowledgement, onDisk] }, "review-8");
        return json(
          { error: "review.json changed on disk", file: "review.json", revision: "review-8", content: "{}" },
          { status: 409 },
        );
      }) satisfies Handler,
    });
    const loads = fetched(EXAMPLE);
    await textArea("Reply", detail().element).setValue("Yes, from Table 2.");
    await click("Resolve");
    expect(fetched(EXAMPLE)).toBe(loads + 1);
    expect(page().get(".review-conflict").text()).toBe(
      "review.json changed on disk; the items were reloaded. Repeat your action.",
    );
    expect(card("Added in the editor.").exists()).toBe(true);
    expect(textArea("Reply", detail().element).element.value).toBe("Yes, from Table 2.");
  });

  it("asks to set the user when a write needs one", async () => {
    await mountSection(withReview(), {
      [`POST ${REVIEW}`]: () =>
        json({ error: "no_user", message: "Set a user with --user or in the settings." }, { status: 403 }),
    });
    await click("Resolve");
    expect(page().get(".user-hint").text()).toContain("Set your PK-DB user in Connection settings");
    expect(useDialogStore().settings).toBe(false);
    await click("Open settings");
    expect(useDialogStore().settings).toBe(true);
  });

  it("says why the local server refused an action, until another item is selected", async () => {
    await mountSection(withReview(), {
      [`POST ${REVIEW}`]: () =>
        json({ error: `Review item ${QUESTION} is resolved, not open`, issues: [] }, { status: 422 }),
    });
    await click("Resolve");
    expect(page().get(".review-failure").text()).toContain(
      `The item was not resolved. Review item ${QUESTION} is resolved, not open`,
    );
    await select("The error bars");
    expect(page().find(".review-failure").exists()).toBe(false);
  });

  it("waits with New item while an item changes, and with the items while a new one is added", async () => {
    let finish = () => undefined as void;
    await mountSection(withReview(), {
      [`POST ${REVIEW}`]: ((body) =>
        new Promise<Response>((resolve) => {
          finish = () => resolve(write(body));
        })) satisfies Handler,
    });
    await button("Resolve").trigger("click");
    await flushPromises();
    expect(button("New item").attributes("disabled")).toBeDefined();
    finish();
    await flushPromises();
    expect(button("New item").attributes("disabled")).toBeUndefined();

    await click("New item");
    await textArea("Text").setValue("Check the doses.");
    await button("Add").trigger("click");
    await flushPromises();
    // The actions of the selected item wait behind the dialog.
    expect(button("Dismiss").attributes("disabled")).toBeDefined();
    expect(button("Reopen").attributes("disabled")).toBeDefined();
    finish();
    await flushPromises();
    expect(button("Dismiss").attributes("disabled")).toBeUndefined();
  });
});
