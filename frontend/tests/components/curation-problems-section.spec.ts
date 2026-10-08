import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DOMWrapper, enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import { defineComponent, h, type Component, type PropType } from "vue";
import { RouterView, type Router } from "vue-router";
import type {
  AcknowledgedWarning,
  Job,
  Snapshot,
  StudyDetail,
  Suggestion,
  TablesResult,
  ValidationIssue,
} from "../../src/curation-app/api/types";
import { formatTime } from "../../src/curation-app/overview";
import { makeRouter } from "../../src/curation-app/router";
import { useDialogStore } from "../../src/curation-app/stores/dialogs";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { useStudyStore } from "../../src/curation-app/stores/study";
import messagesFixture from "../fixtures/curation-contract/messages.json";
import { json, reviewItem, roster, snapshot, studyDetail } from "../unit/curation-fixtures";
import {
  button,
  click,
  focusDialog,
  page,
  serveApi,
  setViewport,
  textArea,
  type Handler,
  type ServedRequest,
} from "./curation-dom";

enableAutoUnmount(afterEach);

const EXAMPLE = "/local/studies/caffeine/Example";
const REVIEW = "/local/studies/review";
const TABLES = "/local/studies/tables";
const OPEN_FILE = "/local/files/open";
const SECTION = "/studies/caffeine/Example/problems";

const ROUNDED = "01JA33A1B2C3D4E5F6G7H8J9K0";
const SMOKERS = "01JA34B1C2D3E4F5G6H7J8K9M0";
const ADDED = "01JA40A1B2C3D4E5F6G7H8J9K0";

// Suggestions of the library: the spellings of an unknown substance and the candidates of an
// unknown subject group (python/tests/test_curation_contract.py).
const [termSuggestion, groupSuggestion] = messagesFixture.suggestions as Suggestion[];
const unknownGroup: ValidationIssue = {
  code: "unknown_reference",
  severity: "error",
  message: "subjects.tsv has no row named 'al'",
  source: { file: "outputs_Tab2.tsv", sheet: "outputs_Tab2", row: 3, column: "E", cell: "E3", header: "group" },
  suggestions: [groupSuggestion!],
};
const unknownSubstance: ValidationIssue = {
  code: "unknown_substance",
  severity: "error",
  message: "Unknown substance: cafeine",
  source: { file: "outputs_Tab2.tsv", sheet: "outputs_Tab2", row: 2, column: "H", cell: "H2", header: "substance" },
  suggestions: [termSuggestion!],
};
const unitDimension: ValidationIssue = {
  code: "unit_dimension",
  severity: "error",
  message: "mg/lightyear cannot be converted to a unit of cmax",
  source: { file: "outputs_Tab2.tsv", sheet: "outputs_Tab2", row: 2, column: "X", cell: "X2", header: "unit" },
  suggestions: [
    {
      kind: "fix",
      message: "Units of cmax; amounts of a substance convert with its molar mass.",
      candidates: ["g/l", "mol/l"],
    },
  ],
};
const outsideRange: ValidationIssue = {
  code: "outside_range",
  severity: "warning",
  message: "mean 512 is above the usual range of a plasma concentration",
  source: { file: "timecourses_Fig1.tsv", sheet: "timecourses_Fig1", row: 6, column: "O", cell: "O6", header: "mean" },
};
const unusedIntervention: ValidationIssue = {
  code: "unused_intervention",
  severity: "warning",
  message: "'caf_po_300' is not referenced by any row",
  source: { file: "interventions.tsv", sheet: "interventions", row: 3, column: "B", cell: "B3", header: "name" },
};
const digitizedMismatch: ValidationIssue = {
  code: "digitized_mismatch",
  severity: "warning",
  message: "1 point of dataset 'caf_plasma_D150' has no mapped row within 2 pixels",
  source: { file: "Example_Fig1.wpd.json", path: [] },
};
const studyJson: ValidationIssue = {
  code: "invalid_study_json",
  severity: "error",
  message: "study.json: curators.0.rating: Input should be a multiple of 0.5",
  source: { file: "study.json", path: [] },
};
const rowLimit: ValidationIssue = {
  code: "row_limit",
  severity: "error",
  message: "The study tables have more than 1000000 rows",
  source: null,
};

const rounded: AcknowledgedWarning = {
  id: ROUNDED,
  code: "digitized_mismatch",
  target: { file: "timecourses_Fig1.tsv", rows: { label: "caf_plasma_D150", time: "0.5" }, column: "mean" },
  text: "The 0.5 h point is rounded in the figure.",
  author: "mkoenig",
  resolved_by: "mkoenig",
  resolved: "2026-10-06T09:00:00Z",
};
const smokers: AcknowledgedWarning = {
  id: SMOKERS,
  code: "unused_subject",
  target: null,
  text: "The smokers are described but not measured.",
  author: "janekg",
  resolved_by: null,
  resolved: null,
};

/** The problems of the last validation of caffeine/Example in five files, with two acknowledged warnings. */
function withProblems(changes: Partial<StudyDetail> = {}): StudyDetail {
  const base = studyDetail();
  return studyDetail({
    status: "invalid",
    counts: { errors: 3, warnings: 3 },
    problems: [unknownGroup, unitDimension, outsideRange, unusedIntervention, digitizedMismatch, studyJson],
    acknowledged: [rounded, smokers],
    review: {
      revision: "review-7",
      value: { status: "in_review", reviewers: ["curator"], items: [] },
      issues: [],
    },
    files: [...base.files, "Example_Fig1.wpd.json"].sort(),
    ...changes,
  });
}

let pinia: Pinia;
let router: Router;
let requests: ServedRequest[];
/** The detail that `GET /local/studies/caffeine/Example` answers; a write may change it. */
let served: StudyDetail;

/** Acknowledges as the local server would: a resolved review item; the warning stays until the next validation. */
/** A job of the activity of caffeine/Example, queued at `created` (the server's ISO format). */
function job(id: string, action: Job["action"], created: string): Job {
  return {
    id,
    study_id: "caffeine/Example",
    study_name: "Example",
    action,
    status: "succeeded",
    created_at: created,
    message: action === "write" ? "Acknowledged a warning" : "Validated",
    automatic: action !== "write",
    report_id: action === "write" ? null : id,
  };
}

/** The time at which the local server records each acknowledgement in the activity. */
const WRITTEN = "2026-10-07T12:00:00.500000+00:00";

const acknowledge: Handler = (body) => {
  const item = reviewItem({
    id: ADDED,
    kind: "issue",
    state: "resolved",
    acknowledges: String(body?.code),
    text: String(body?.text),
    target: { file: String(body?.file) },
    author: "curator",
    resolved_by: "curator",
  });
  served = {
    ...served,
    review: { ...served.review, revision: "review-8" },
    // The server lists the write in the activity of the study, newest first.
    jobs: [job(`write-${served.jobs.length}`, "write", WRITTEN), ...served.jobs],
    acknowledged: [
      ...served.acknowledged,
      {
        id: ADDED,
        code: item.acknowledges!,
        target: item.target ?? null,
        text: item.text,
        author: "curator",
        resolved_by: "curator",
        resolved: "2026-10-07T12:00:00Z",
      },
    ],
  };
  return json({ revision: "review-8", item });
};

function tablesResult(changes: Partial<TablesResult> = {}): TablesResult {
  return { ok: true, workbook_action: "unchanged", changes: [], conflicts: [], issues: [], opened: true, ...changes };
}

/** The problems section inside the app's router view, with `routes` besides the defaults. */
/** A problem as a bare list item with its code, for tests of the list rather than its items. */
const ProblemItemStub = defineComponent({
  name: "ProblemItem",
  props: { issue: { type: Object as PropType<ValidationIssue>, required: true } },
  setup: (props) => () => h("li", { class: "problem" }, [h("code", { class: "problem-code" }, props.issue.code)]),
});

async function mountSection(
  detail: StudyDetail = withProblems(),
  routes: Record<string, unknown> = {},
  state: Snapshot = snapshot(),
  stubs: Record<string, Component> = {},
) {
  served = detail;
  requests = serveApi({
    "GET /local/state": state,
    [`GET ${EXAMPLE}`]: (() => json(served)) satisfies Handler,
    "GET /local/curators": { curators: roster() },
    [`POST ${REVIEW}`]: acknowledge,
    [`POST ${TABLES}`]: tablesResult(),
    [`POST ${OPEN_FILE}`]: { ok: true },
    ...routes,
  });
  await useOverviewStore().refresh();
  router = makeRouter();
  await router.push(SECTION);
  await router.isReady();
  const wrapper = mount(RouterView, { attachTo: document.body, global: { plugins: [pinia, router], stubs } });
  await flushPromises();
  return wrapper;
}

function posted(path: string): (Record<string, unknown> | null)[] {
  return requests.filter((request) => request.method === "POST" && request.path === path).map(({ body }) => body);
}

function section() {
  return page().get(".problems");
}

/** The severity chip `label`, such as Errors, with its count. */
function chip(label: string): DOMWrapper<HTMLButtonElement> {
  const found = page()
    .findAll<HTMLButtonElement>('[aria-label="Filter by severity"] button')
    .filter((candidate) => candidate.text().replace(/\s*\d+$/, "") === label);
  if (found.length !== 1) throw new Error(`Expected one chip "${label}", found ${found.length}`);
  return found[0]!;
}

function chipCount(label: string): string {
  return chip(label).get(".chip-count").text();
}

async function filter(label: string): Promise<void> {
  await chip(label).trigger("click");
  await flushPromises();
}

/** The file headings of the groups, in order. */
function groupFiles(): string[] {
  return section()
    .findAll(".problem-group .problem-file")
    .map((heading) => heading.text());
}

/** The codes of the shown issues, in order. */
function codes(): string[] {
  return section()
    .findAll(".problem .problem-code")
    .map((code) => code.text());
}

/** The shown issue with the code `code`. */
function problem(code: string): DOMWrapper<HTMLElement> {
  const found = section()
    .findAll<HTMLElement>(".problem")
    .filter((candidate) => candidate.get(".problem-code").text() === code);
  if (found.length !== 1) throw new Error(`Expected one issue ${code}, found ${found.length}`);
  return found[0]!;
}

/** An element of the page, from `get` or `find`. */
type Within = Pick<DOMWrapper<Element>, "findAll">;

/** The buttons and links of `within` with the text `name`. */
function controls(within: Within, name: string): DOMWrapper<HTMLElement>[] {
  return within
    .findAll<HTMLElement>("button, a")
    .filter((control) => control.text().replace(/\s+/g, " ").trim() === name);
}

function control(within: Within, name: string): DOMWrapper<HTMLElement> {
  const found = controls(within, name);
  if (found.length !== 1) throw new Error(`Expected one control "${name}", found ${found.length}`);
  return found[0]!;
}

function textOf(element: Pick<DOMWrapper<Element>, "text">): string {
  return element.text().replace(/\s+/g, " ").trim();
}

function dialog() {
  return page().get('.v-overlay--active[role="dialog"]');
}

async function openAcknowledge(code: string): Promise<void> {
  // As with a keyboard: the button has the focus when it opens the dialog.
  const opener = control(problem(code), "Acknowledge");
  opener.element.focus();
  await opener.trigger("click");
  await flushPromises();
}

/** Acknowledges the warning `code` with a reason in the dialog. */
async function acknowledgeWarning(code: string): Promise<void> {
  await openAcknowledge(code);
  await textArea("Reason", dialog().element).setValue("Expected in this study.");
  await control(dialog(), "Acknowledge").trigger("click");
  await flushPromises();
}

function notice(): string {
  return section().get(".problems-notice").text();
}

beforeEach(() => {
  setViewport(1440);
  pinia = createPinia();
  setActivePinia(pinia);
});

afterEach(() => {
  disposePinia(pinia);
});

describe("issues", () => {
  it("filters by severity with chips that count the issues", async () => {
    await mountSection();
    expect(chipCount("All")).toBe("6");
    expect(chipCount("Errors")).toBe("3");
    expect(chipCount("Warnings")).toBe("3");
    expect(chip("All").attributes("aria-pressed")).toBe("true");
    expect(codes()).toHaveLength(6);

    await filter("Errors");
    expect(chip("Errors").attributes("aria-pressed")).toBe("true");
    expect(codes().sort()).toEqual(["invalid_study_json", "unit_dimension", "unknown_reference"]);
    await filter("Warnings");
    expect(codes().sort()).toEqual(["digitized_mismatch", "outside_range", "unused_intervention"]);
    expect(groupFiles()).toEqual(["timecourses_Fig1.tsv", "interventions.tsv", "Example_Fig1.wpd.json"]);
  });

  it("says when a filter leaves no issues", async () => {
    await mountSection(withProblems({ problems: [unitDimension], counts: { errors: 1, warnings: 0 } }));
    await filter("Warnings");
    expect(codes()).toEqual([]);
    expect(section().get(".problems-empty").text()).toBe("No warnings.");
  });

  it("groups the issues by file with code, message, location and suggestions", async () => {
    await mountSection();
    // The files with errors first.
    expect(groupFiles()).toEqual([
      "outputs_Tab2.tsv",
      "study.json",
      "timecourses_Fig1.tsv",
      "interventions.tsv",
      "Example_Fig1.wpd.json",
    ]);
    const outputs = section().findAll(".problem-group")[0]!;
    expect(outputs.get(".problem-group-counts").text()).toBe("2 errors");
    // By line within the file.
    const ordered = outputs.findAll(".problem-code").map((code) => code.text());
    expect(ordered).toEqual(["unit_dimension", "unknown_reference"]);

    const group = problem("unknown_reference");
    expect(group.get(".problem-severity").text()).toBe("Error");
    expect(group.get(".problem-message").text()).toBe("subjects.tsv has no row named 'al'");
    expect(group.get(".problem-location").text()).toBe("line 3 · group · sheet cell outputs_Tab2!E3");
    // Each candidate is a chip of its own.
    expect(group.get(".problem-suggestion-lead").text()).toBe("Did you mean:");
    expect(group.findAll(".problem-candidate").map((item) => item.text())).toEqual(["all"]);
    expect(group.find(".problem-suggestion-note").exists()).toBe(false);

    const unit = problem("unit_dimension");
    expect(unit.get(".problem-suggestion-lead").text()).toBe(
      "Units of cmax; amounts of a substance convert with its molar mass.",
    );
    expect(unit.findAll(".problem-candidates li").map((item) => item.text())).toEqual(["g/l", "mol/l"]);

    expect(problem("outside_range").get(".problem-severity").text()).toBe("Warning");
    // An issue of a whole file names no location below the file.
    expect(problem("digitized_mismatch").find(".problem-location").exists()).toBe(false);
  });

  it("offers the spellings of an unknown term with their caveat after them", async () => {
    await mountSection(withProblems({ problems: [unknownSubstance], counts: { errors: 1, warnings: 0 } }));
    const term = problem("unknown_substance");
    expect(term.get(".problem-suggestion-lead").text()).toBe("Did you mean:");
    expect(term.findAll(".problem-candidate").map((item) => item.text())).toEqual(termSuggestion!.candidates);
    expect(term.get(".problem-suggestion-note").text()).toBe("Candidates are spelling suggestions, not equivalent terms.");
  });

  it("renders a long list in steps, so that the first issues show at once", async () => {
    // The frames run when the test says so: a busy machine neither skips nor delays a step.
    const frames = new Map<number, FrameRequestCallback>();
    let frameIds = 0;
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => {
      frames.set(++frameIds, callback);
      return frameIds;
    });
    vi.spyOn(window, "cancelAnimationFrame").mockImplementation((id) => void frames.delete(id));
    async function nextFrame(): Promise<void> {
      const due = [...frames.values()];
      frames.clear();
      for (const callback of due) callback(performance.now());
      await flushPromises();
    }
    const many: ValidationIssue[] = Array.from({ length: 250 }, (_, index) => ({
      ...outsideRange,
      message: `mean ${index} lies outside [min, max]`,
      source: { ...outsideRange.source!, row: index + 2, cell: `O${index + 2}` },
    }));
    // Only the steps count here: the items are bare list items.
    await mountSection(withProblems({ problems: many, counts: { errors: 0, warnings: 250 } }), {}, snapshot(), {
      ProblemItem: ProblemItemStub,
    });
    // The first step of 100 issues shows at once, and each frame adds the next step.
    expect(codes()).toHaveLength(100);
    expect(section().get(".problem-group-counts").text()).toBe("250 warnings");
    await nextFrame();
    expect(codes()).toHaveLength(200);
    await nextFrame();
    expect(codes()).toHaveLength(250);
    await nextFrame();
    expect(codes()).toHaveLength(250);
  });

  it("says how many problems the last validation left out", async () => {
    await mountSection(withProblems({ counts: { errors: 1203, warnings: 3 } }));
    expect(section().get(".problems-omitted").text()).toBe("The last validation listed 6 of 1,206 problems.");
  });

  it("says when the study has no problems", async () => {
    await mountSection(
      withProblems({ status: "valid", problems: [], counts: { errors: 0, warnings: 0 }, acknowledged: [] }),
    );
    expect(section().get(".problems-empty").text()).toBe("No errors or warnings.");
    expect(section().find('[aria-label="Filter by severity"]').exists()).toBe(false);
    expect(section().find(".problems-acknowledged").exists()).toBe(false);
  });

  it("shows the limit issue at the top of a study beyond the upload limits", async () => {
    await mountSection(
      withProblems({
        problems: [rowLimit, unitDimension],
        counts: { errors: 2, warnings: 0 },
        files: [],
        tables: [],
        sources: [],
      }),
    );
    const limit = section().get(".problems-limit");
    expect(section().element.firstElementChild).toBe(limit.element);
    expect(limit.text()).toContain("This study is beyond the upload limits.");
    expect(limit.text()).toContain("The study tables have more than 1000000 rows");
    expect(limit.text()).toContain("row_limit");
    // The limit is not listed again, and the tables beyond it cannot be shown.
    expect(codes()).toEqual(["unit_dimension"]);
    expect(chipCount("Errors")).toBe("1");
    expect(controls(problem("unit_dimension"), "Show in table")).toHaveLength(0);
  });
});

describe("actions", () => {
  it("shows a cell in its table by file, line and column", async () => {
    await mountSection();
    const link = control(problem("outside_range"), "Show in table");
    expect(link.attributes("href")).toBe(
      "#/studies/caffeine/Example/tables?file=timecourses_Fig1.tsv&line=6&column=mean",
    );
    // Only the tables of the study can be shown.
    expect(controls(problem("invalid_study_json"), "Show in table")).toHaveLength(0);
    expect(controls(problem("digitized_mismatch"), "Show in table")).toHaveLength(0);

    await link.trigger("click");
    await vi.waitFor(() =>
      expect(router.currentRoute.value.fullPath).toBe(
        "/studies/caffeine/Example/tables?file=timecourses_Fig1.tsv&line=6&column=mean",
      ),
    );
  });

  it("opens the workbook with Open tables and reports what the sync found", async () => {
    await mountSection();
    await control(section(), "Open tables").trigger("click");
    await flushPromises();
    expect(posted(TABLES)).toEqual([{ study: "caffeine/Example", action: "open" }]);
    expect(notice()).toBe("The workbook opened.");
  });

  it("explains a workbook that could not be opened until the alert is closed", async () => {
    await mountSection(withProblems(), {
      [`POST ${TABLES}`]: tablesResult({ ok: false, opened: false, issues: [unitDimension] }),
    });
    await control(section(), "Open tables").trigger("click");
    await flushPromises();
    const alert = section().get(".problems-failure");
    expect(alert.text()).toContain("The workbook could not be opened.");
    expect(alert.text()).toContain("mg/lightyear cannot be converted to a unit of cmax");
    await alert.get('button[aria-label="Close"]').trigger("click");
    await flushPromises();
    expect(section().find(".problems-failure").exists()).toBe(false);
  });

  it("asks to set the user when Open tables needs one", async () => {
    await mountSection(withProblems(), {
      [`POST ${TABLES}`]: () =>
        json({ error: "no_user", message: "Set a user with --user or in the settings." }, { status: 403 }),
    });
    await control(section(), "Open tables").trigger("click");
    await flushPromises();
    expect(section().get(".user-hint").text()).toContain("Set your PK-DB user in Connection settings.");
    expect(section().find(".problems-failure").exists()).toBe(false);
  });

  it("opens a file that is not a table", async () => {
    await mountSection();
    await click("Open study.json");
    expect(posted(OPEN_FILE)).toEqual([{ study_id: "caffeine/Example", file: "study.json" }]);
    // The tables open in the workbook.
    expect(page().find('button[aria-label="Open outputs_Tab2.tsv"]').exists()).toBe(false);
  });
});

describe("acknowledgements", () => {
  it("offers Acknowledge only for warnings", async () => {
    await mountSection();
    for (const code of ["outside_range", "unused_intervention", "digitized_mismatch"])
      expect(controls(problem(code), "Acknowledge")).toHaveLength(1);
    for (const code of ["unknown_reference", "unit_dimension", "invalid_study_json"])
      expect(controls(problem(code), "Acknowledge")).toHaveLength(0);
  });

  it("acknowledges a warning at its file, line and column with a required reason", async () => {
    await mountSection();
    await openAcknowledge("unused_intervention");
    const shown = dialog();
    expect(shown.get("h2").text()).toBe("Acknowledge warning");
    expect(shown.text()).toContain("unused_intervention");
    expect(shown.text()).toContain("interventions.tsv · line 3 · name · sheet cell interventions!B3");
    expect(shown.text()).toContain("'caf_po_300' is not referenced by any row");
    const reason = textArea("Reason", shown.element);
    expect(reason.attributes("required")).toBeDefined();
    const submit = control(shown, "Acknowledge");
    expect(submit.attributes("disabled")).toBeDefined();
    await reason.setValue("   ");
    expect(submit.attributes("disabled")).toBeDefined();

    await reason.setValue("  The paper lists the dose, but no group received it.  ");
    await submit.trigger("click");
    await flushPromises();
    expect(posted(REVIEW)).toEqual([
      {
        study: "caffeine/Example",
        revision: "review-7",
        action: "acknowledge",
        code: "unused_intervention",
        file: "interventions.tsv",
        line: 3,
        column: "name",
        text: "The paper lists the dose, but no group received it.",
      },
    ]);
    expect(page().find('.v-overlay--active[role="dialog"]').exists()).toBe(false);
    expect(notice()).toBe("Warning unused_intervention acknowledged.");
    expect(section().get(".problems-acknowledged h3").text()).toBe("Acknowledged warnings (3)");

    // Until the next validation leaves it out, the warning says that it is acknowledged.
    const pending = problem("unused_intervention");
    expect(controls(pending, "Acknowledge")).toHaveLength(0);
    expect(pending.get(".problem-acknowledged").text()).toBe(
      "Acknowledged. It leaves this list after the next validation.",
    );
    served = { ...served, problems: served.problems.filter((entry) => entry !== unusedIntervention) };
    await useStudyStore().refresh();
    await flushPromises();
    expect(codes()).not.toContain("unused_intervention");
  });

  it("marks no warning that the validation left out before the page loaded the study again", async () => {
    await mountSection(withProblems(), {
      [`POST ${REVIEW}`]: ((body) => {
        const answer = acknowledge(body);
        served = { ...served, problems: served.problems.filter((entry) => entry !== outsideRange) };
        return answer;
      }) satisfies Handler,
    });
    await openAcknowledge("outside_range");
    await textArea("Reason", dialog().element).setValue("Read from the figure as printed.");
    await control(dialog(), "Acknowledge").trigger("click");
    await flushPromises();
    expect(codes()).not.toContain("outside_range");

    // A warning that comes back, such as after its item was dismissed, can be acknowledged again.
    served = { ...served, problems: [...served.problems, outsideRange] };
    await useStudyStore().refresh();
    await flushPromises();
    expect(controls(problem("outside_range"), "Acknowledge")).toHaveLength(1);
  });

  it("asks to validate when no automatic validation will leave the warning out", async () => {
    await mountSection(withProblems({ mode: "off" }), { "POST /local/jobs": { ok: true } });
    await acknowledgeWarning("unused_intervention");
    const pending = problem("unused_intervention");
    expect(pending.get(".problem-acknowledged").text()).toBe("Acknowledged. Validate the study to update this list.");
    await control(pending, "Validate").trigger("click");
    await flushPromises();
    expect(posted("/local/jobs")).toEqual([{ ids: ["caffeine/Example"], action: "validate" }]);
    expect(notice()).toBe("Validation queued.");
  });

  it("asks to validate while file watching is paused", async () => {
    await mountSection(withProblems(), {}, snapshot({ paused: true }));
    await acknowledgeWarning("unused_intervention");
    expect(problem("unused_intervention").get(".problem-acknowledged").text()).toBe(
      "Acknowledged. Validate the study to update this list.",
    );
  });

  it("keeps the mark when the section opens again, until a report of a job queued after the write", async () => {
    const before = job("job-1", "validate", "2026-10-07T11:59:58.000000+00:00");
    await mountSection(withProblems({ jobs: [before], report_id: "job-1" }));
    await acknowledgeWarning("unused_intervention");
    await router.push("/studies/caffeine/Example/review");
    await flushPromises();
    await router.push(SECTION);
    await flushPromises();
    expect(controls(problem("unused_intervention"), "Acknowledge")).toHaveLength(0);
    expect(problem("unused_intervention").find(".problem-acknowledged").exists()).toBe(true);

    // A validation that was queued before the write, and ran during it, reports the warning still.
    const running = job("job-2", "validate", "2026-10-07T12:00:00+00:00");
    served = { ...served, jobs: [running, ...served.jobs], report_id: "job-2" };
    await useStudyStore().refresh();
    await flushPromises();
    expect(problem("unused_intervention").find(".problem-acknowledged").exists()).toBe(true);
    expect(controls(problem("unused_intervention"), "Acknowledge")).toHaveLength(0);

    // The report of a job queued after the write ends the mark.
    const after = job("job-3", "validate", "2026-10-07T12:00:02.250000+00:00");
    served = { ...served, jobs: [after, ...served.jobs], report_id: "job-3" };
    await useStudyStore().refresh();
    await flushPromises();
    expect(problem("unused_intervention").find(".problem-acknowledged").exists()).toBe(false);
    expect(controls(problem("unused_intervention"), "Acknowledge")).toHaveLength(1);
  });

  it("moves the focus to the next warning after an acknowledgement, else to the heading of the file", async () => {
    await mountSection();
    await acknowledgeWarning("outside_range");
    expect(document.activeElement).toBe(control(problem("unused_intervention"), "Acknowledge").element);

    // The last warning of the list leaves the heading of its file.
    await acknowledgeWarning("digitized_mismatch");
    const heading = section()
      .findAll(".problem-file")
      .find((candidate) => candidate.text() === "Example_Fig1.wpd.json");
    expect(document.activeElement).toBe(heading?.element);
  });

  it("returns the focus to Acknowledge after Cancel", async () => {
    await mountSection();
    await openAcknowledge("outside_range");
    focusDialog();
    await control(dialog(), "Cancel").trigger("click");
    await flushPromises();
    expect(document.activeElement).toBe(control(problem("outside_range"), "Acknowledge").element);
  });

  it("acknowledges nothing while Open tables runs, and opens nothing while it acknowledges", async () => {
    let answer: (response: Response) => void = () => undefined;
    await mountSection(withProblems(), {
      [`POST ${TABLES}`]: () => new Promise<Response>((resolve) => (answer = resolve)),
    });
    await control(section(), "Open tables").trigger("click");
    await flushPromises();
    for (const code of ["outside_range", "unused_intervention", "digitized_mismatch"])
      expect(control(problem(code), "Acknowledge").attributes("disabled")).toBeDefined();
    answer(json(tablesResult()));
    await flushPromises();
    expect(control(problem("outside_range"), "Acknowledge").attributes("disabled")).toBeUndefined();

    let written: (response: Response) => void = () => undefined;
    requests = serveApi({
      [`GET ${EXAMPLE}`]: (() => json(served)) satisfies Handler,
      "GET /local/curators": { curators: roster() },
      [`POST ${REVIEW}`]: () => new Promise<Response>((resolve) => (written = resolve)),
      [`POST ${TABLES}`]: tablesResult(),
    });
    await openAcknowledge("outside_range");
    await textArea("Reason", dialog().element).setValue("Read from the figure as printed.");
    await control(dialog(), "Acknowledge").trigger("click");
    await flushPromises();
    expect(control(section(), "Open tables").attributes("disabled")).toBeDefined();
    expect(button("Open study.json").attributes("disabled")).toBeDefined();
    await control(section(), "Open tables").trigger("click");
    await flushPromises();
    expect(posted(TABLES)).toEqual([]);
    written(json({ revision: "review-8" }));
    await flushPromises();
    expect(control(section(), "Open tables").attributes("disabled")).toBeUndefined();
  });

  it("says plainly that a warning is no longer in the files", async () => {
    await mountSection(withProblems(), {
      [`POST ${REVIEW}`]: () =>
        json(
          {
            error: "No warning [outside_range] in timecourses_Fig1.tsv matches",
            issues: [],
            code: "no_such_warning",
          },
          { status: 422 },
        ),
    });
    await openAcknowledge("outside_range");
    await textArea("Reason", dialog().element).setValue("Read from the figure as printed.");
    await control(dialog(), "Acknowledge").trigger("click");
    await flushPromises();
    expect(dialog().get(".acknowledge-failure").text()).toBe(
      "This warning is not in the current files. Validate the study and try again.",
    );
  });

  it("acknowledges a warning of a whole file without a line or column", async () => {
    await mountSection();
    await openAcknowledge("digitized_mismatch");
    await textArea("Reason", dialog().element).setValue("The point lies on the axis.");
    await control(dialog(), "Acknowledge").trigger("click");
    await flushPromises();
    expect(posted(REVIEW)).toEqual([
      {
        study: "caffeine/Example",
        revision: "review-7",
        action: "acknowledge",
        code: "digitized_mismatch",
        file: "Example_Fig1.wpd.json",
        // Null is exact: only the warnings of the file without a line or column.
        line: null,
        column: null,
        text: "The point lies on the axis.",
      },
    ]);
  });

  it("tells that a warning without a row in a data table is acknowledged in its whole file", async () => {
    const second: ValidationIssue = {
      ...digitizedMismatch,
      message: "2 points of dataset 'caf_plasma_D300' have no mapped row within 2 pixels",
    };
    const problems = [outsideRange, digitizedMismatch, second];
    await mountSection(withProblems({ problems, counts: { errors: 0, warnings: 3 } }));
    const items = section().findAll<HTMLElement>(".problem");
    const opener = control(items[1]!, "Acknowledge");
    opener.element.focus();
    await opener.trigger("click");
    await flushPromises();
    const scope = dialog().get(".acknowledge-scope");
    expect(textOf(scope.get(".acknowledge-scope-text"))).toBe(
      "This warning has no row in a data table. The acknowledgement covers every digitized_mismatch warning in " +
        "Example_Fig1.wpd.json, also later ones. It covers 2 warnings now.",
    );
    expect(scope.findAll(".acknowledge-covered li").map(textOf)).toEqual([digitizedMismatch.message, second.message]);

    await textArea("Reason", dialog().element).setValue("The points lie on the axis.");
    await control(dialog(), "Acknowledge").trigger("click");
    await flushPromises();
    // Both warnings leave the list after the next validation.
    expect(section().findAll(".problem-acknowledged")).toHaveLength(2);
    expect(notice()).toBe("2 warnings digitized_mismatch acknowledged.");
  });

  it("names no wider scope for a warning at a row of a data table", async () => {
    await mountSection();
    await openAcknowledge("outside_range");
    expect(dialog().find(".acknowledge-scope").exists()).toBe(false);
  });

  it("keeps the dialog open with the locations when several warnings match", async () => {
    const ambiguous =
      "2 warnings [digitized_mismatch] match in Example_Fig1.wpd.json at line 3, line 5; " +
      "give the line and column of one";
    await mountSection(withProblems(), {
      [`POST ${REVIEW}`]: () => json({ error: ambiguous, issues: [] }, { status: 422 }),
    });
    await openAcknowledge("digitized_mismatch");
    await textArea("Reason", dialog().element).setValue("The point lies on the axis.");
    await control(dialog(), "Acknowledge").trigger("click");
    await flushPromises();
    expect(dialog().get(".acknowledge-failure").text()).toBe(`The warning was not acknowledged. ${ambiguous}`);
    expect(textArea("Reason", dialog().element).element.value).toBe("The point lies on the axis.");
  });

  it("reloads after review.json changed on disk and asks to acknowledge again", async () => {
    await mountSection(withProblems(), {
      [`POST ${REVIEW}`]: (() => {
        served = { ...served, review: { ...served.review, revision: "review-9" } };
        return json(
          { error: "review.json changed on disk", file: "review.json", revision: "review-9", content: "{}" },
          { status: 409 },
        );
      }) satisfies Handler,
    });
    await openAcknowledge("outside_range");
    await textArea("Reason", dialog().element).setValue("Read from the figure as printed.");
    await control(dialog(), "Acknowledge").trigger("click");
    await flushPromises();
    expect(dialog().get(".acknowledge-conflict").text()).toBe(
      "review.json changed on disk; the items were reloaded. Repeat your action.",
    );

    // The next try writes over the reloaded revision.
    await control(dialog(), "Acknowledge").trigger("click");
    await flushPromises();
    expect(posted(REVIEW).map((body) => body?.revision)).toEqual(["review-7", "review-9"]);
  });

  it("asks to set the user when the write needs one", async () => {
    await mountSection(withProblems(), {
      [`POST ${REVIEW}`]: () =>
        json({ error: "no_user", message: "Set a user with --user or in the settings." }, { status: 403 }),
    });
    await openAcknowledge("outside_range");
    await textArea("Reason", dialog().element).setValue("Read from the figure as printed.");
    await control(dialog(), "Acknowledge").trigger("click");
    await flushPromises();
    expect(dialog().get(".user-hint").text()).toContain("Set your PK-DB user in Connection settings.");
    await click("Open settings");
    expect(useDialogStore().settings).toBe(true);
  });

  it("starts the reason of another warning empty", async () => {
    await mountSection();
    await openAcknowledge("outside_range");
    await textArea("Reason", dialog().element).setValue("Read from the figure as printed.");
    await control(dialog(), "Cancel").trigger("click");
    await flushPromises();
    await openAcknowledge("outside_range");
    expect(textArea("Reason", dialog().element).element.value).toBe("Read from the figure as printed.");
    await control(dialog(), "Cancel").trigger("click");
    await flushPromises();
    await openAcknowledge("unused_intervention");
    expect(textArea("Reason", dialog().element).element.value).toBe("");
  });

  it("cannot acknowledge while review.json is invalid", async () => {
    await mountSection(withProblems({ review: { revision: "review-7", value: null, issues: [] } }));
    expect(control(problem("outside_range"), "Acknowledge").attributes("disabled")).toBeDefined();
    expect(section().get(".problems-blocked").text()).toBe(
      "review.json is not valid, so warnings cannot be acknowledged. Fix it in your editor.",
    );
  });

  it("lists the acknowledged warnings with links to their review items", async () => {
    await mountSection();
    const list = section().get(".problems-acknowledged");
    expect(list.get("h3").text()).toBe("Acknowledged warnings (2)");
    const entries = list.findAll("li");
    expect(entries).toHaveLength(2);
    expect(entries[0]!.get(".problem-code").text()).toBe("digitized_mismatch");
    expect(entries[0]!.text()).toContain("timecourses_Fig1.tsv · label = caf_plasma_D150, time = 0.5 · column mean");
    expect(entries[0]!.text()).toContain("The 0.5 h point is rounded in the figure.");
    expect(entries[0]!.text()).toContain(`Acknowledged by Matthias König on ${formatTime("2026-10-06T09:00:00Z")}.`);
    expect(control(entries[0]!, "Show the review item").attributes("href")).toBe(
      `#/studies/caffeine/Example/review?item=${ROUNDED}`,
    );
    expect(entries[1]!.text()).toContain("Whole study");
    // The time stays with its date.
    expect(entries[0]!.get(".acknowledged-time").text()).toBe(formatTime("2026-10-06T09:00:00Z"));
    expect(entries[1]!.text()).toContain("Acknowledged by Jan Grzegorzewski. The review item is open.");
    expect(control(entries[1]!, "Show the review item").attributes("href")).toBe(
      `#/studies/caffeine/Example/review?item=${SMOKERS}`,
    );
  });

  it("names the file of an Open button and every control", async () => {
    await mountSection();
    expect(button("Open study.json").text()).toBe("Open");
    for (const element of section().findAll("button, a"))
      expect((element.attributes("aria-label") ?? element.text()).trim()).not.toBe("");
  });
});
