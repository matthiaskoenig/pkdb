import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DOMWrapper, enableAutoUnmount, flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import { defineComponent, h } from "vue";
import { RouterView, type Router } from "vue-router";
import { VAutocomplete, VCombobox, VSelect } from "vuetify/components";
import type { StudyDetail, StudyMetadata, ValidationIssue } from "../../src/curation-app/api/types";
import { makeRouter } from "../../src/curation-app/router";
import { useDialogStore } from "../../src/curation-app/stores/dialogs";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { useStudyStore } from "../../src/curation-app/stores/study";
import { NOTICE_MS } from "../../src/curation-app/study";
import { fullStudyMetadata, json, roster, snapshot, studyDetail, studyMetadata } from "../unit/curation-fixtures";
import {
  button,
  buttons,
  click,
  field,
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
const METADATA = "/local/studies/metadata";
const SECTION = "/studies/caffeine/Example/metadata";

let pinia: Pinia;
let router: Router;
let requests: ServedRequest[];
let wrapper: VueWrapper;
/** The detail that `GET /local/studies/caffeine/Example` answers; a test may change it. */
let served: StudyDetail;

/** Writes study.json as the local server would: the detail has the new revision afterwards. */
const write: Handler = (body) => {
  const revision = `study-${posted(METADATA).length + 1}`;
  served = { ...served, metadata: { revision, value: body?.metadata as StudyMetadata, issues: [] } };
  return json({ revision, reference: null, reference_error: null });
};

/**
 * The metadata section of `detail` inside the app's router view, with `routes` besides the
 * defaults. A save writes like the local server, unless `routes` answers it otherwise.
 */
async function mountSection(detail: StudyDetail = studyDetail(), routes: Record<string, unknown> = {}) {
  served = detail;
  requests = serveApi({
    "GET /local/state": snapshot(),
    [`GET ${EXAMPLE}`]: (() => json(served)) satisfies Handler,
    "GET /local/curators": { curators: roster() },
    [`POST ${METADATA}`]: write,
    ...routes,
  });
  await useOverviewStore().refresh();
  router = makeRouter();
  await router.push(SECTION);
  await router.isReady();
  wrapper = mount(defineComponent({ render: () => h(RouterView) }), {
    attachTo: document.body,
    global: { plugins: [pinia, router] },
  });
  await flushPromises();
  return wrapper;
}

/** The detail of `caffeine/Example` with `metadata` as its valid study.json at `revision`. */
function withMetadata(metadata: StudyMetadata, revision = "study-1", changes: Partial<StudyDetail> = {}) {
  return studyDetail({ metadata: { revision, value: metadata, issues: [] }, ...changes });
}

function posted(path: string): (Record<string, unknown> | null)[] {
  return requests.filter((request) => request.method === "POST" && request.path === path).map(({ body }) => body);
}

/** The card of the form with the heading `title`. */
function card(title: string): DOMWrapper<Element> {
  const found = page()
    .findAll(".metadata-card")
    .find((candidate) => candidate.find("h3").text() === title);
  if (!found) throw new Error(`No card "${title}"`);
  return found;
}

function saveBar() {
  return page().find(".metadata-savebar");
}

function ratingOf(name: string) {
  return page().get(`[role="radiogroup"][aria-label="${name}"]`);
}

function checkedRating(name: string): string | null {
  return ratingOf(name).find('[aria-checked="true"]').attributes("aria-label") ?? null;
}

/** Waits until the dialog of a guarded navigation shows its buttons. */
function leaveDialog(): Promise<void> {
  return vi.waitFor(() => expect(buttons("Stay")).toHaveLength(1));
}

function issue(field: string | null, message: string): ValidationIssue {
  return { code: "invalid_study_json", severity: "error", message, field };
}

beforeEach(() => {
  setViewport(1440);
  pinia = createPinia();
  setActivePinia(pinia);
});

afterEach(() => {
  disposePinia(pinia);
});

describe("reference card", () => {
  it("shows the PMID and DOI of study.json and the title of reference.json", async () => {
    await mountSection(
      withMetadata(studyMetadata({ reference: { pmid: "2895442", doi: "10.1007/BF00637675" } }), "study-1", {
        reference_match: true,
        reference: {
          sid: "2895442",
          pmid: "2895442",
          doi: "10.1007/BF00637675",
          title: "Effect of smoking on caffeine clearance",
          journal: "Eur J Clin Pharmacol",
          abstract: null,
          publication_date: "1988",
          authors: ["S Harder", "U Fuhr"],
        },
      }),
    );
    const reference = card("Reference");
    expect(field("PMID").element.value).toBe("2895442");
    expect(field("DOI").element.value).toBe("10.1007/BF00637675");
    expect(reference.get(".reference-match").text()).toBe("reference.json matches");
    expect(reference.text()).toContain("Effect of smoking on caffeine clearance");
    expect(reference.text()).toContain("S Harder, U Fuhr");
    expect(reference.text()).toContain("Eur J Clin Pharmacol · 1988");
  });

  it.each([
    [false, "reference.json does not match study.json"],
    [null, "No identifiers"],
  ])("names the match state %s of reference.json", async (match, text) => {
    await mountSection(studyDetail({ reference_match: match }));
    expect(card("Reference").get(".reference-match").text()).toBe(text);
  });

  it("opens the reference dialog for corrections", async () => {
    await mountSection(studyDetail(), {
      "POST /local/reference/read": { reference: { sid: "3678553", name: "Example", title: "Caffeine" } },
    });
    await click("Correct title, authors, journal...");
    expect(page().get('.v-overlay--active[role="dialog"]').text()).toContain("Reference");
    expect(posted("/local/reference/read")).toEqual([{ id: "caffeine/Example" }]);
  });
});

describe("people card", () => {
  it("chooses the creator from the roster, with avatars", async () => {
    await mountSection();
    const creator = labeled(wrapper, VAutocomplete, "Creator");
    expect(creator.props("modelValue")).toBe("curator");
    const input = field("Creator");
    await input.trigger("focus");
    await input.setValue("Jan");
    await vi.waitFor(() => {
      const item = page()
        .findAll(".v-overlay--active .v-list-item")
        .find((candidate) => candidate.text().includes("Jan Grzegorzewski"));
      expect(item?.find('img[src="/avatars/janekg.webp"]').exists()).toBe(true);
    });
  });

  it("rates curators from 0 to 5 in half steps and adds and removes them", async () => {
    await mountSection();
    expect(checkedRating("Rating of curator")).toBe("4.5 stars");

    await ratingOf("Rating of curator").get('[aria-label="3 stars"]').trigger("click");
    expect(checkedRating("Rating of curator")).toBe("3 stars");
    // The arrow keys change the rating in half steps.
    await ratingOf("Rating of curator").get('[aria-checked="true"]').trigger("keydown", { key: "ArrowRight" });
    expect(checkedRating("Rating of curator")).toBe("3.5 stars");

    await click("Add curator");
    await labeled(wrapper, VAutocomplete, "Curator 2").setValue("mkoenig");
    await ratingOf("Rating of mkoenig").get('[aria-label="0.5 stars"]').trigger("click");
    await click("Remove curator 1");
    expect(wrapper.findAllComponents(VAutocomplete).map((field) => field.props("label"))).toEqual([
      "Creator",
      "Curator 1",
    ]);

    await click("Save");
    expect(posted(METADATA)[0]?.metadata).toMatchObject({ curators: [{ user: "mkoenig", rating: 0.5 }] });
  });

  it("lists collaborators in a combobox", async () => {
    await mountSection(withMetadata(fullStudyMetadata()));
    const collaborators = labeled(wrapper, VCombobox, "Collaborators");
    expect(collaborators.props("modelValue")).toEqual(["Jane Doe"]);
    await collaborators.setValue(["Jane Doe", "janekg"]);
    expect(saveBar().exists()).toBe(true);
  });
});

describe("access and provenance card", () => {
  it("allows public access only with a release", async () => {
    await mountSection(withMetadata(studyMetadata({ access: "private" })));
    expect(radio("Open").checked).toBe(true);
    expect(radio("Private").checked).toBe(true);
    expect(radio("Public").disabled).toBe(true);
    expect(messagesOf(radio("Public"))).toBe("Public needs a release (pkdb release)");
  });

  it("allows public access with a release", async () => {
    await mountSection(withMetadata(fullStudyMetadata()));
    expect(radio("Closed").checked).toBe(true);
    expect(radio("Public").checked).toBe(true);
    expect(radio("Public").disabled).toBe(false);
    expect(messagesOf(radio("Public"))).toBe("");
  });

  it("shows method, version and run id for an automatic curation", async () => {
    await mountSection();
    const kind = labeled(wrapper, VSelect, "Provenance");
    expect(kind.props("modelValue")).toBe("manual_curation");
    expect(() => field("Method")).toThrow();

    await kind.setValue("automatic_curation");
    expect(page().get(".assets-block").text()).toContain("No assets. An automatic curation needs at least one.");
    await click("Add asset");
    await field("Method").setValue("claude-opus-5-5");
    await field("Version").setValue("1");
    await field("Run ID").setValue("run-1");
    await field("Asset 1 URL").setValue("https://example.org/Example.pdf");
    await field("Asset 1 SHA-256").setValue("c".repeat(64));
    await click("Save");

    expect(posted(METADATA)[0]?.metadata).toMatchObject({
      provenance: {
        kind: "automatic_curation",
        source_key: "pkdb.manual",
        method: "claude-opus-5-5",
        version: "1",
        run_id: "run-1",
        assets: [{ url: "https://example.org/Example.pdf", sha256: "c".repeat(64) }],
      },
    });
  });
});

describe("issue and release card", () => {
  it("shows the issue and the release read only", async () => {
    await mountSection(withMetadata(fullStudyMetadata()));
    const issueCard = card("Issue and release");
    expect(issueCard.text()).toContain("#2158");
    expect(issueCard.text()).toContain("PKDB00198 · released 2026-09-28");
    expect(issueCard.text()).toContain("Set by pkdb release");
    expect(issueCard.findAll("input")).toHaveLength(0);
  });
});

describe("descriptions, comments and notes", () => {
  it("adds and removes descriptions and comments by the current user", async () => {
    await mountSection(withMetadata(fullStudyMetadata()));
    const notes = card("Descriptions and comments").element;
    expect(textArea("Description 1", notes).element.value).toBe("Plasma levels in µg/l.");
    expect(textArea("Comment by mkoenig", notes).element.value).toBe("Checked against the PDF.");

    await click("Add description");
    await textArea("Description 2", notes).setValue("Doses in mg.");
    await click("Add comment");
    await textArea("Comment by curator", notes).setValue("Looks good.");
    await click("Remove description 1");
    await click("Save");

    expect(posted(METADATA)[0]?.metadata).toMatchObject({
      descriptions: ["Doses in mg."],
      comments: [
        { user: "mkoenig", text: "Checked against the PDF." },
        { user: "curator", text: "Looks good." },
      ],
    });
  });

  // Typing in a field deep in a panel takes jsdom a second or two: the label animation of the
  // field reads inherited custom properties, which jsdom resolves through every ancestor.
  it("keeps notes per table kind", { timeout: 20_000 }, async () => {
    await mountSection(withMetadata(fullStudyMetadata()));
    const notes = card("Notes per table");
    expect(notes.findAll(".v-expansion-panel-title").map((title) => title.text())).toEqual([
      "Subjects No notes",
      "Interventions No notes",
      "Characteristica No notes",
      "Outputs 1 description, 1 comment",
      "Timecourses 1 description",
      "Scatters No notes",
    ]);
    await notes.findAll(".v-expansion-panel-title")[0]!.trigger("click");
    await flushPromises();
    await click("Add description to subjects");
    await textArea("Description 1", notes.findAll(".v-expansion-panel")[0]!.element).setValue("Healthy volunteers.");
    await click("Save");
    expect(posted(METADATA)[0]?.metadata).toMatchObject({
      notes: { subjects: { descriptions: ["Healthy volunteers."], comments: [] } },
    });
  });
});

describe("saving", () => {
  it("shows a sticky bar with Discard and Save for unsaved changes and marks the rail", async () => {
    await mountSection();
    expect(saveBar().exists()).toBe(false);

    await field("DOI").setValue("10.1000/xyz");

    expect(saveBar().text()).toContain("Unsaved changes in study.json");
    expect(button("Discard").element.disabled).toBe(false);
    expect(button("Save").element.disabled).toBe(false);
    const metadataLink = page().get('nav[aria-label="Study sections"] a');
    expect(metadataLink.get(".rail-label").text()).toBe("Metadata, unsaved changes");
    expect(metadataLink.find(".rail-unsaved").exists()).toBe(true);

    await click("Discard");
    expect(field("DOI").element.value).toBe("");
    expect(saveBar().exists()).toBe(false);
    expect(page().get('nav[aria-label="Study sections"] a .rail-label').text()).toBe("Metadata");
  });

  it("posts the full study.json with its revision and hides the bar after the save", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    try {
      await mountSection();
      await field("DOI").setValue("10.1000/xyz");
      await click("Save");

      expect(posted(METADATA)).toEqual([
        {
          study: "caffeine/Example",
          revision: "study-1",
          metadata: { ...studyMetadata(), reference: { pmid: "3678553", doi: "10.1000/xyz" } },
        },
      ]);
      // The bar says that the save worked, for a few seconds.
      expect(saveBar().text()).toContain("study.json saved.");
      expect(saveBar().text()).not.toContain("Unsaved changes");
      expect(button("Save").element.disabled).toBe(true);
      expect(page().get(".metadata-notice").text()).toBe("study.json saved.");
      vi.advanceTimersByTime(NOTICE_MS);
      await flushPromises();
      expect(saveBar().exists()).toBe(false);

      // The next save goes over the new revision.
      await field("DOI").setValue("10.1000/abc");
      await click("Save");
      expect(posted(METADATA)[1]?.revision).toBe("study-2");
    } finally {
      vi.useRealTimers();
    }
  });

  it("says when reference.json could not be refreshed after the save", async () => {
    await mountSection(studyDetail(), {
      [`POST ${METADATA}`]: { revision: "study-2", reference: null, reference_error: "PubMed is offline" },
    });
    await field("PMID").setValue("999");
    await click("Save");
    expect(page().get(".metadata-reference-error").text()).toBe(
      "study.json saved; reference.json could not be refreshed: PubMed is offline",
    );
  });

  it("shows the issues of a refused save at their fields and keeps the form", async () => {
    await mountSection(studyDetail(), {
      [`POST ${METADATA}`]: () =>
        json(
          {
            error: "Invalid study.json",
            issues: [
              issue("reference.doi", "reference.doi: String should match pattern '^10\\.\\d{4,9}/\\S+$'"),
              issue("curators.0.rating", "curators.0.rating: Input should be less than or equal to 5"),
              issue("format", "format: Input should be 2"),
            ],
          },
          { status: 422 },
        ),
    });
    await field("DOI").setValue("doi");
    await click("Save");

    expect(field("DOI").element.value).toBe("doi");
    expect(messagesOf(field("DOI"))).toBe("String should match pattern '^10\\.\\d{4,9}/\\S+$'");
    expect(page().get(".curator-row .curator-messages").text()).toBe("Input should be less than or equal to 5");
    const failure = page().get(".metadata-failure").text();
    expect(failure).toContain("study.json was not saved. Fix the marked fields.");
    expect(failure).toContain("format: Input should be 2");
    expect(saveBar().exists()).toBe(true);
  });

  it("reloads a study.json changed on disk, keeps the edits on top and saves over the new revision", async () => {
    const disk = studyMetadata({ curators: [{ user: "curator", rating: 5 }], descriptions: ["From disk."] });
    let saves = 0;
    await mountSection(studyDetail(), {
      [`POST ${METADATA}`]: (() => {
        saves += 1;
        if (saves === 1)
          return json(
            {
              error: "study.json changed on disk since it was read",
              file: "study.json",
              revision: "study-2",
              content: JSON.stringify(disk, null, 2),
            },
            { status: 409 },
          );
        return json({ revision: "study-3", reference: null, reference_error: null });
      }) satisfies Handler,
    });
    radio("Closed").click();
    await flushPromises();
    await click("Save");

    expect(page().get(".metadata-conflict").text()).toContain(
      "study.json changed on disk after you opened this form",
    );
    expect(button("Save").element.disabled).toBe(true);

    await click("Reload");

    expect(radio("Closed").checked).toBe(true);
    expect(checkedRating("Rating of curator")).toBe("5 stars");
    const notes = card("Descriptions and comments").element;
    expect(textArea("Description 1", notes).element.value).toBe("From disk.");
    expect(page().get(".curators-block").text()).toContain("Changed on disk");
    expect(messagesOf(textArea("Description 1", notes))).toBe("");
    expect(page().get(".descriptions-block").text()).toContain("Changed on disk");
    expect(page().find(".metadata-conflict").exists()).toBe(false);
    expect(button("Save").element.disabled).toBe(false);

    await click("Save");
    expect(posted(METADATA)[1]).toEqual({
      study: "caffeine/Example",
      revision: "study-2",
      metadata: { ...disk, licence: "closed" },
    });
  });

  it("names a field changed on both sides and keeps the local edit", async () => {
    const disk = studyMetadata({ licence: "open", access: "private", creator: "janekg" });
    await mountSection(studyDetail(), {
      [`POST ${METADATA}`]: () =>
        json(
          { error: "changed", file: "study.json", revision: "study-2", content: JSON.stringify(disk) },
          { status: 409 },
        ),
    });
    await labeled(wrapper, VAutocomplete, "Creator").setValue("mkoenig");
    await click("Save");
    await click("Reload");
    expect(labeled(wrapper, VAutocomplete, "Creator").props("modelValue")).toBe("mkoenig");
    expect(page().get(".metadata-reloaded").text()).toContain("Changed on both sides, your version is kept: Creator");
    expect(messagesOf(page().get(".creator-field input"))).toBe("Changed on disk too. Your edit is kept.");
  });

  it("follows study.json on disk while the form has no unsaved edits", async () => {
    await mountSection();
    served = withMetadata(studyMetadata({ licence: "closed" }), "study-2");
    await useStudyStore().refresh();
    await flushPromises();
    expect(radio("Closed").checked).toBe(true);

    // Edits keep the form; undoing them by hand shows the newer file.
    await field("DOI").setValue("10.1000/xyz");
    served = withMetadata(studyMetadata({ licence: "closed", descriptions: ["New."] }), "study-3");
    await useStudyStore().refresh();
    await flushPromises();
    expect(() => textArea("Description 1", card("Descriptions and comments").element)).toThrow();
    await field("DOI").setValue("");
    await flushPromises();
    expect(textArea("Description 1", card("Descriptions and comments").element).element.value).toBe("New.");
    expect(saveBar().exists()).toBe(false);
  });

  it("asks to set the user when a save needs one", async () => {
    await mountSection(studyDetail(), {
      [`POST ${METADATA}`]: () =>
        json({ error: "no_user", message: "Set a user with --user or in the settings." }, { status: 403 }),
    });
    await field("DOI").setValue("10.1000/xyz");
    await click("Save");
    expect(page().get(".metadata-failure").text()).toContain("Set your PK-DB user in Connection settings");
    expect(useDialogStore().settings).toBe(false);
    await click("Open settings");
    expect(useDialogStore().settings).toBe(true);
  });
});

describe("leaving with unsaved changes", () => {
  it("asks before another section opens", async () => {
    await mountSection();
    await field("DOI").setValue("10.1000/xyz");

    const stay = router.push("/studies/caffeine/Example/review");
    await leaveDialog();
    expect(page().get('.v-overlay--active[role="dialog"]').text()).toContain("Leave without saving?");
    await click("Stay");
    await stay;
    expect(router.currentRoute.value.params.section).toBe("metadata");
    expect(field("DOI").element.value).toBe("10.1000/xyz");

    const leave = router.push("/studies/caffeine/Example/review");
    await leaveDialog();
    await click("Discard and leave");
    await leave;
    expect(router.currentRoute.value.params.section).toBe("review");
    expect(page().get('nav[aria-label="Study sections"] a .rail-label').text()).toBe("Metadata");
  });

  it("asks before the overview opens", async () => {
    await mountSection();
    await field("DOI").setValue("10.1000/xyz");
    const leave = router.push("/");
    await leaveDialog();
    await click("Discard and leave");
    await leave;
    expect(router.currentRoute.value.name).toBe("Overview");
  });

  it("leaves without asking when nothing changed", async () => {
    await mountSection();
    await router.push("/studies/caffeine/Example/review");
    expect(router.currentRoute.value.params.section).toBe("review");
  });

  it("asks the browser to confirm closing the tab", async () => {
    await mountSection();
    const clean = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(clean);
    expect(clean.defaultPrevented).toBe(false);

    await field("DOI").setValue("10.1000/xyz");
    const edited = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(edited);
    expect(edited.defaultPrevented).toBe(true);
  });
});

describe("invalid study.json", () => {
  const broken = [issue(null, "study.json: Expecting ',' delimiter: line 3 column 5")];

  it("shows the issues and starts a new study.json from the fields of the summary", async () => {
    await mountSection(studyDetail({ metadata: { revision: "broken-1", value: null, issues: broken } }));
    expect(page().get(".metadata-invalid").text()).toContain("study.json: Expecting ',' delimiter: line 3 column 5");
    expect(page().find(".metadata-card").exists()).toBe(false);

    await click("Start a new study.json from these fields");
    expect(labeled(wrapper, VAutocomplete, "Creator").props("modelValue")).toBe("curator");
    expect(saveBar().exists()).toBe(true);
    await click("Save");
    expect(posted(METADATA)[0]).toMatchObject({ revision: "broken-1", metadata: { creator: "curator" } });
  });

  it("is read only without a revision, for a file that the app cannot write", async () => {
    await mountSection(studyDetail({ metadata: { revision: null, value: null, issues: broken } }));
    expect(page().get(".metadata-invalid").text()).toContain("study.json cannot be written from the app.");
    expect(buttons("Start a new study.json from these fields")).toHaveLength(0);
  });
});
