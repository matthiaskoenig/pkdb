import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DOMWrapper, enableAutoUnmount, flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import { defineComponent, h } from "vue";
import { RouterView, type Router } from "vue-router";
import { VAutocomplete, VCombobox, VSelect, VTextarea } from "vuetify/components";
import type { StudyDetail, StudyMetadata, ValidationIssue } from "../../src/curation-app/api/types";
import { makeRouter } from "../../src/curation-app/router";
import { useDialogStore } from "../../src/curation-app/stores/dialogs";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { useStudyStore } from "../../src/curation-app/stores/study";
import { NOTICE_MS } from "../../src/curation-app/study";
import messagesFixture from "../fixtures/curation-contract/messages.json";
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

/** Refuses a save as the local server does after `disk` was written to study.json by hand. */
function changedOnDisk(disk: StudyMetadata): Handler {
  return () => {
    served = withMetadata(disk, "study-2");
    return json(
      { error: "changed", file: "study.json", revision: "study-2", content: JSON.stringify(disk) },
      { status: 409 },
    );
  };
}

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
  return page().find(".study-savebar");
}

function ratingOf(name: string) {
  return page().get(`[role="slider"][aria-label="${name}"]`);
}

/** The value text of a rating, such as "3.5 of 5". */
function ratingText(name: string): string | null {
  return ratingOf(name).attributes("aria-valuetext") ?? null;
}

/** Waits until the dialog of a guarded navigation shows its buttons. */
function leaveDialog(): Promise<void> {
  return vi.waitFor(() => expect(buttons("Stay")).toHaveLength(1));
}

/** The label of the tab of a section with what screen readers hear after it, such as "Data, unsaved changes". */
function tabLabel(label: string): string {
  const found = page()
    .findAll('nav[aria-label="Study sections"] .section-tab-label')
    .map((entry) => entry.text())
    .find((text) => text === label || text.startsWith(`${label},`));
  if (found === undefined) throw new Error(`No tab ${label}`);
  return found;
}

/** An issue of study.json as the library gives it: the message names the field, the detail does not. */
function issue(field: string | null, detail: string): ValidationIssue {
  if (field === null) return { code: "invalid_study_json", severity: "error", message: detail, field };
  return { code: "invalid_study_json", severity: "error", message: `${field}: ${detail}`, field, context: { detail } };
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
    const rating = ratingOf("Rating of curator");
    expect(rating.attributes()).toMatchObject({
      tabindex: "0",
      "aria-valuemin": "0",
      "aria-valuemax": "5",
      "aria-valuenow": "4.5",
      "aria-valuetext": "4.5 of 5",
    });

    // A click on the left half of the third star gives 2.5, on its right half 3.
    await rating.get('[data-step="2.5"]').trigger("click");
    expect(ratingText("Rating of curator")).toBe("2.5 of 5");
    await rating.get('[data-step="3"]').trigger("click");
    expect(ratingText("Rating of curator")).toBe("3 of 5");

    await click("Add curator");
    await labeled(wrapper, VAutocomplete, "Curator 2").setValue("mkoenig");
    await ratingOf("Rating of mkoenig").get('[data-step="0.5"]').trigger("click");
    await click("Remove curator 1");
    expect(wrapper.findAllComponents(VAutocomplete).map((field) => field.props("label"))).toEqual([
      "Creator",
      "Curator 1",
    ]);

    await click("Save");
    expect(posted(METADATA)[0]?.metadata).toMatchObject({ curators: [{ user: "mkoenig", rating: 0.5 }] });
  });

  it("changes a rating with the keys of a slider", async () => {
    await mountSection();
    const rating = ratingOf("Rating of curator");
    const press = async (key: string) => {
      await rating.trigger("keydown", { key });
      return ratingText("Rating of curator");
    };
    expect(await press("ArrowRight")).toBe("5 of 5");
    expect(await press("ArrowUp")).toBe("5 of 5");
    expect(await press("ArrowLeft")).toBe("4.5 of 5");
    expect(await press("ArrowDown")).toBe("4 of 5");
    expect(await press("Home")).toBe("0 of 5");
    expect(await press("ArrowDown")).toBe("0 of 5");
    expect(await press("ArrowUp")).toBe("0.5 of 5");
    expect(await press("End")).toBe("5 of 5");
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
    expect(messagesOf(radio("Public"))).toBe("Public needs a release.");
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
    expect(field("Source key").element.value).toBe("pkdb.manual");
    expect(() => field("Method")).toThrow();

    await kind.setValue("automatic_curation");
    // The source key of a manual curation does not carry over.
    expect(field("Source key").element.value).toBe("");
    expect(page().get(".assets-block").text()).toContain("No assets. An automatic curation needs at least one.");
    await click("Add asset");
    await field("Source key").setValue("pkdb.ai");
    await field("Method").setValue("claude-opus-5-5");
    await field("Version").setValue("1");
    await field("Run ID").setValue("run-1");
    await field("Asset 1 URL").setValue("https://example.org/Example.pdf");
    await field("Asset 1 SHA-256").setValue("c".repeat(64));
    await click("Save");

    expect(posted(METADATA)[0]?.metadata).toMatchObject({
      provenance: {
        kind: "automatic_curation",
        source_key: "pkdb.ai",
        method: "claude-opus-5-5",
        version: "1",
        run_id: "run-1",
        assets: [{ url: "https://example.org/Example.pdf", sha256: "c".repeat(64) }],
      },
    });
  });

  it("shows a data import read only, so that it cannot change", async () => {
    await mountSection(
      withMetadata(
        studyMetadata({
          provenance: {
            kind: "data_import",
            source_key: "pkdb.import",
            release: "2026.1",
            revision: "abc",
            importer: "pkdb-importer",
            importer_version: "1.2",
            assets: [{ url: "https://example.org/data.zip", sha256: "b".repeat(64) }],
            dataset_ids: [],
            evidence_kind: "observed",
            reference_scope: "primary_publication",
          },
        }),
      ),
    );
    const access = card("Access and provenance");
    expect(labeled(wrapper, VSelect, "Provenance").props("readonly")).toBe(true);
    expect(access.text()).toContain("Set by the importer");
    expect(access.get(".data-import-facts").text()).toContain("pkdb-importer 1.2");
    for (const label of ["Source key", "Method", "Version", "Run ID"]) expect(() => field(label)).toThrow();
    expect(buttons("Add asset")).toHaveLength(0);
    expect(saveBar().exists()).toBe(false);
  });
});

describe("issue and release card", () => {
  it("shows the issue and the release read only", async () => {
    await mountSection(withMetadata(fullStudyMetadata()));
    const issueCard = card("Issue and release");
    expect(issueCard.text()).toContain("#2158");
    expect(issueCard.text()).toContain("PKDB00198 · released 2026-09-28");
    expect(issueCard.text()).toContain("Set when the study is released.");
    expect(issueCard.findAll("input")).toHaveLength(0);
  });
});

describe("descriptions, comments and notes", () => {
  it("adds and removes descriptions and comments by the current user", async () => {
    await mountSection(withMetadata(fullStudyMetadata()));
    const notes = card("Descriptions and comments").element;
    expect(textArea("Description 1", notes).element.value).toBe("Plasma levels in µg/l.");
    expect(textArea("Comment 1 by mkoenig", notes).element.value).toBe("Checked against the PDF.");

    await click("Add description");
    await textArea("Description 2", notes).setValue("Doses in mg.");
    await click("Add comment");
    await textArea("Comment 2 by curator", notes).setValue("Looks good.");
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

  it("does not write a row that was added and left empty", async () => {
    await mountSection(withMetadata(fullStudyMetadata()));
    await click("Add description");
    await click("Add comment");
    await click("Add curator");
    await click("Save");
    expect(posted(METADATA)[0]?.metadata).toMatchObject({
      descriptions: ["Plasma levels in µg/l."],
      comments: [{ user: "mkoenig", text: "Checked against the PDF." }],
      curators: fullStudyMetadata().curators,
    });
    expect(page().find(".savebar-failure").exists()).toBe(false);
  });

  it("says that the notes of a table are in Data, above the table", async () => {
    await mountSection(withMetadata(fullStudyMetadata()));
    expect(page().findAll(".metadata-card h3").map((heading) => heading.text())).toEqual([
      "Reference",
      "People",
      "Access and provenance",
      "Issue and release",
      "Descriptions and comments",
    ]);
    const hint = card("Descriptions and comments").get(".metadata-notes-hint");
    expect(hint.text()).toBe("Notes of a table are in Data, above the table.");
    expect(hint.get("a").attributes("href")).toBe("#/studies/caffeine/Example/data");
    // outputs and timecourses have tables, so their notes show in Data only.
    expect(card("Descriptions and comments").find(".table-notes").exists()).toBe(false);
  });

  it("keeps the notes of a kind without a table in Metadata, where they are edited and saved", async () => {
    await mountSection(
      withMetadata(fullStudyMetadata({ notes: { scatters: { descriptions: ["From Figure 3."], comments: [] } } })),
    );
    const notes = card("Descriptions and comments");
    expect(notes.get(".metadata-orphans").text()).toContain("The study has no table of this kind, so its notes are here:");
    expect(notes.findAll(".table-notes-toggle").map((toggle) => toggle.text())).toEqual([
      "Notes of the scatters 1 description",
    ]);
    await notes.get(".table-notes-toggle").trigger("click");
    // The headings of the notes of the study are one level below the card, those of the panel below its own.
    expect(notes.findAll("h4, h5").map((heading) => `${heading.element.tagName} ${heading.text()}`)).toEqual([
      "H4 Descriptions",
      "H4 Comments",
      "H4 Notes of the scatters 1 description",
      "H5 Descriptions",
      "H5 Comments",
    ]);
    await textArea("Description 1", notes.get(".table-notes").element).setValue("From Figure 4.");
    expect(tabLabel("Metadata")).toBe("Metadata, unsaved changes");
    expect(tabLabel("Data")).toBe("Data");
    await click("Save");
    expect(posted(METADATA)[0]?.metadata).toMatchObject({
      notes: { scatters: { descriptions: ["From Figure 4."], comments: [] } },
    });
  });
});

describe("notes of kinds without a table", () => {
  it("names the kinds without a table in the plural when there are several", async () => {
    await mountSection(
      withMetadata(
        fullStudyMetadata({
          notes: {
            scatters: { descriptions: ["From Figure 3."], comments: [] },
            characteristica: { descriptions: ["From Table 1."], comments: [] },
          },
        }),
        "study-1",
        // Without characteristica.tsv.
        { tables: studyDetail().tables.filter((table) => table.kind !== "characteristica") },
      ),
    );
    const notes = card("Descriptions and comments");
    expect(notes.get(".metadata-orphans > .field-note").text()).toBe(
      "The study has no table of these kinds, so their notes are here:",
    );
    expect(notes.findAll(".table-notes-toggle").map((toggle) => toggle.text())).toEqual([
      "Notes of the characteristica 1 description",
      "Notes of the scatters 1 description",
    ]);
  });
});

describe("saving", () => {
  it("shows a sticky bar with Discard and Save for unsaved changes and marks the tab", async () => {
    await mountSection();
    expect(saveBar().exists()).toBe(false);

    await field("DOI").setValue("10.1000/xyz");

    expect(saveBar().text()).toContain("Unsaved changes in study.json");
    expect(button("Discard").element.disabled).toBe(false);
    expect(button("Save").element.disabled).toBe(false);
    const metadataLink = page().get('nav[aria-label="Study sections"] a');
    expect(metadataLink.get(".section-tab-label").text()).toBe("Metadata, unsaved changes");
    expect(metadataLink.find(".section-tab-unsaved").exists()).toBe(true);

    await click("Discard");
    expect(field("DOI").element.value).toBe("");
    expect(saveBar().text()).toContain("Changes discarded.");
    expect(page().get('nav[aria-label="Study sections"] a .section-tab-label').text()).toBe("Metadata");
  });

  it("undoes a discard for a few seconds, until the next edit", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    try {
      await mountSection();
      await field("DOI").setValue("10.1000/xyz");
      await click("Discard");
      expect(page().get(".savebar-notice").text()).toBe("Changes discarded.");

      await click("Undo");
      expect(field("DOI").element.value).toBe("10.1000/xyz");
      expect(saveBar().text()).toContain("Unsaved changes in study.json");
      expect(buttons("Undo")).toHaveLength(0);

      // The next edit ends the undo.
      await click("Discard");
      await field("PMID").setValue("1");
      expect(buttons("Undo")).toHaveLength(0);

      // So do a few seconds.
      await click("Discard");
      expect(buttons("Undo")).toHaveLength(1);
      vi.advanceTimersByTime(NOTICE_MS);
      await flushPromises();
      expect(buttons("Undo")).toHaveLength(0);
      expect(saveBar().exists()).toBe(false);
    } finally {
      vi.useRealTimers();
    }
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
      expect(page().get(".savebar-notice").text()).toBe("study.json saved.");
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
    expect(page().get(".savebar-reference-error").text()).toBe(
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
              issue("reference.doi", "String should match pattern '^10\\.\\d{4,9}/\\S+$'"),
              issue("curators.0.rating", "Input should be less than or equal to 5"),
              issue("format", "Input should be 2"),
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
    const failure = page().get(".savebar-failure").text();
    expect(failure).toContain("study.json was not saved. Fix the marked fields.");
    expect(failure).toContain("format: Input should be 2");
    expect(saveBar().exists()).toBe(true);
  });

  it("shows the messages of the library at their fields without the field", async () => {
    // A refusal of the local server: a creator with a space and a reference without identifiers.
    const refused = messagesFixture.metadata_issues as ValidationIssue[];
    await mountSection(studyDetail(), {
      [`POST ${METADATA}`]: () => json({ error: "Invalid study.json", issues: refused }, { status: 422 }),
    });
    await field("PMID").setValue("");
    await click("Save");

    expect(messagesOf(field("PMID"))).toBe("Give a pmid or a doi, or remove reference for a manual reference");
    expect(messagesOf(page().get(".creator-field").element)).toBe("A user name has no spaces.");
    expect(page().get(".savebar-failure").text()).toContain("study.json was not saved. Fix the marked fields.");
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

    expect(page().get(".savebar-conflict").text()).toContain(
      "study.json changed on disk after you started editing it",
    );
    expect(button("Save").element.disabled).toBe(true);

    await click("Reload");

    expect(radio("Closed").checked).toBe(true);
    expect(ratingText("Rating of curator")).toBe("5 of 5");
    const notes = card("Descriptions and comments").element;
    expect(textArea("Description 1", notes).element.value).toBe("From disk.");
    expect(page().get(".curators-block").text()).toContain("Changed on disk");
    expect(messagesOf(textArea("Description 1", notes))).toBe("");
    expect(page().get(".descriptions-block").text()).toContain("Changed on disk");
    expect(page().find(".savebar-conflict").exists()).toBe(false);
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
    await mountSection(studyDetail(), { [`POST ${METADATA}`]: changedOnDisk(disk) });
    await labeled(wrapper, VAutocomplete, "Creator").setValue("mkoenig");
    await click("Save");
    await click("Reload");
    expect(labeled(wrapper, VAutocomplete, "Creator").props("modelValue")).toBe("mkoenig");
    expect(page().get(".savebar-reloaded").text()).toContain("Changed on both sides, your version is kept: Creator");
    expect(messagesOf(page().get(".creator-field input"))).toBe(
      "Changed on disk too. Your edit is kept. On disk: janekg",
    );

    // The disk version replaces the edit of that field only.
    await click("Use the disk version of Creator");
    expect(labeled(wrapper, VAutocomplete, "Creator").props("modelValue")).toBe("janekg");
    expect(messagesOf(page().get(".creator-field input"))).toBe("Changed on disk");
    expect(buttons(/^Use the disk version/)).toHaveLength(0);
    expect(page().get(".savebar-reloaded").text()).not.toContain("Changed on both sides");
    expect(saveBar().text()).toContain("No unsaved changes");
  });

  it("offers the disk version of a list that changed on both sides", async () => {
    const disk = studyMetadata({ descriptions: ["From disk."] });
    await mountSection(studyDetail(), { [`POST ${METADATA}`]: changedOnDisk(disk) });
    await click("Add description");
    await textArea("Description 1", card("Descriptions and comments").element).setValue("Mine.");
    await click("Save");
    await click("Reload");
    const block = page().get(".descriptions-block");
    expect(block.text()).toContain("Changed on disk too. Your edit is kept. On disk: From disk.");
    await click("Use the disk version of Descriptions");
    expect(textArea("Description 1", card("Descriptions and comments").element).element.value).toBe("From disk.");
    expect(page().get(".descriptions-block").text()).not.toContain("Your edit is kept");
  });

  it("cannot merge a study.json on disk that is no JSON object, and saves again once it is fixed", async () => {
    // study.json on disk: no JSON object at the first save, fixed in an editor at the second.
    const fixed = studyMetadata({ licence: "closed" });
    let saves = 0;
    await mountSection(studyDetail(), {
      [`POST ${METADATA}`]: ((body) => {
        saves += 1;
        if (saves === 1)
          return json({ error: "changed", file: "study.json", revision: "study-2", content: "{ broken" }, { status: 409 });
        if (body?.revision !== "study-3")
          return json(
            { error: "changed", file: "study.json", revision: "study-3", content: JSON.stringify(fixed) },
            { status: 409 },
          );
        return write(body);
      }) satisfies Handler,
    });
    await field("DOI").setValue("10.1000/xyz");
    await click("Save");
    expect(page().get(".savebar-conflict").text()).toContain(
      "It is not valid JSON now, so it cannot be merged. Fix it in your editor, then save again.",
    );
    expect(buttons("Reload")).toHaveLength(0);
    expect(button("Save").element.disabled).toBe(false);
    expect(field("DOI").element.value).toBe("10.1000/xyz");

    // Saved again after the fix: the readable file can be merged, and Save waits for Reload.
    await click("Save");
    expect(page().get(".savebar-conflict").text()).toContain("Reload it to keep your edits on top of the new version.");
    expect(button("Save").element.disabled).toBe(true);
    await click("Reload");
    expect(radio("Closed").checked).toBe(true);
    expect(field("DOI").element.value).toBe("10.1000/xyz");

    await click("Save");
    expect(posted(METADATA).map((body) => body?.revision)).toEqual(["study-1", "study-1", "study-3"]);
    expect(posted(METADATA)[2]?.metadata).toMatchObject({ licence: "closed", reference: { doi: "10.1000/xyz" } });
    expect(saveBar().text()).toContain("study.json saved.");
    expect(page().find(".savebar-conflict").exists()).toBe(false);
  });

  it("brings back the edits over the revision they were read from when Undo follows a change on disk", async () => {
    const disk = studyMetadata({ licence: "closed" });
    await mountSection(studyDetail(), { [`POST ${METADATA}`]: changedOnDisk(disk) });
    await field("DOI").setValue("10.1000/xyz");
    served = withMetadata(disk, "study-2");
    await useStudyStore().refresh();
    await flushPromises();

    await click("Discard");
    expect(radio("Closed").checked).toBe(true);
    expect(field("DOI").element.value).toBe("");
    await click("Undo");
    expect(field("DOI").element.value).toBe("10.1000/xyz");
    expect(radio("Open").checked).toBe(true);

    // The save goes over the revision that the edits were read from, and Reload puts them on top.
    await click("Save");
    expect(posted(METADATA)[0]?.revision).toBe("study-1");
    await click("Reload");
    expect(radio("Closed").checked).toBe(true);
    expect(field("DOI").element.value).toBe("10.1000/xyz");
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

  it("shows what failed in a save, with Details and a link to its entry in the Activity", async () => {
    await mountSection(studyDetail(), {
      [`POST ${METADATA}`]: () =>
        json(
          {
            error: "Could not do it.",
            code: "unexpected",
            detail: "RuntimeError: boom",
            action: "Save study.json (POST /local/studies/metadata)",
            request_id: "3f9c2a71",
            time: "2026-10-12T14:03:11+02:00",
            activity_id: "act-7",
          },
          { status: 500 },
        ),
    });
    await field("DOI").setValue("10.1000/xyz");
    await click("Save");
    const alert = page().get(".savebar-failure");
    expect(alert.get(".action-failure-detail").text()).toBe("RuntimeError: boom");
    expect(alert.get("summary").text()).toBe("Details");
    expect(alert.get(".action-failure-activity").attributes("href")).toBe("#/studies/caffeine/Example/activity?entry=act-7");
  });

  it("asks to set the user when a save needs one", async () => {
    await mountSection(studyDetail(), {
      [`POST ${METADATA}`]: () =>
        json({ error: "no_user", message: "Set a user with --user or in the settings." }, { status: 403 }),
    });
    await field("DOI").setValue("10.1000/xyz");
    await click("Save");
    expect(page().get(".savebar-failure").text()).toContain("Set your PK-DB user in Connection settings");
    expect(useDialogStore().settings).toBe(false);
    await click("Open settings");
    expect(useDialogStore().settings).toBe(true);
  });

  it("marks the tab of the section of each changed field: Data for the notes of a table, Metadata for the others", async () => {
    await mountSection(withMetadata(fullStudyMetadata()));
    // outputs has a table, outputs_Tab2.tsv, above which the Data section shows its notes.
    useStudyStore().draft.form!.notes.outputs.descriptions.push("From Data.");
    await flushPromises();
    expect(tabLabel("Data")).toBe("Data, unsaved changes");
    expect(tabLabel("Metadata")).toBe("Metadata");
    expect(saveBar().text()).toContain("Unsaved changes in study.json");

    await field("DOI").setValue("10.1000/xyz");
    expect(tabLabel("Metadata")).toBe("Metadata, unsaved changes");
    expect(tabLabel("Data")).toBe("Data, unsaved changes");
  });

  it("names what failed when a save fails unexpectedly", async () => {
    await mountSection(studyDetail(), {
      [`POST ${METADATA}`]: () =>
        json(
          {
            error: "Could not save study.json of caffeine/Example.",
            code: "unexpected",
            detail: "OSError: disk full",
            action: "Save study.json (POST /local/studies/metadata)",
            request_id: "3f9c2a71",
            time: "2026-10-12T10:00:00+02:00",
          },
          { status: 500 },
        ),
    });
    await field("DOI").setValue("10.1000/xyz");
    await click("Save");
    const failure = page().get(".savebar-failure");
    expect(failure.get(".action-failure-text").text()).toBe("Could not save study.json of caffeine/Example.");
    expect(failure.text()).toContain("OSError: disk full");

    // Its alert closes it, in the draft of the store.
    await failure.get(".v-alert__close button").trigger("click");
    expect(page().find(".savebar-failure").exists()).toBe(false);
    expect(useStudyStore().draft.failure).toBeNull();
  });
});

describe("leaving the study with unsaved changes", () => {
  it("keeps the edits while other sections of the study open", async () => {
    await mountSection();
    await field("DOI").setValue("10.1000/xyz");
    await router.push("/studies/caffeine/Example/review");
    await flushPromises();
    expect(router.currentRoute.value.params.section).toBe("review");
    expect(buttons("Stay")).toHaveLength(0);
    expect(tabLabel("Metadata")).toBe("Metadata, unsaved changes");

    await router.push(SECTION);
    await flushPromises();
    expect(field("DOI").element.value).toBe("10.1000/xyz");
    expect(saveBar().text()).toContain("Unsaved changes in study.json");
  });

  it("asks before the overview opens, and stays or discards and leaves", async () => {
    await mountSection();
    await field("DOI").setValue("10.1000/xyz");

    const stay = router.push("/");
    await leaveDialog();
    expect(page().get('.v-overlay--active[role="dialog"]').text()).toContain("Leave without saving?");
    expect(page().get('.v-overlay--active[role="dialog"]').text()).toContain(
      "Your changes to study.json are not saved. Leaving discards them.",
    );
    await click("Stay");
    await stay;
    expect(router.currentRoute.value.params.section).toBe("metadata");
    expect(field("DOI").element.value).toBe("10.1000/xyz");

    const leave = router.push("/");
    await leaveDialog();
    await click("Discard and leave");
    await leave;
    expect(router.currentRoute.value.name).toBe("Overview");
    expect(useStudyStore().draft.form).toBeNull();
  });

  it("asks before another study opens", async () => {
    await mountSection();
    await field("DOI").setValue("10.1000/xyz");
    const stay = router.push("/studies/caffeine/Other/metadata");
    await leaveDialog();
    await click("Stay");
    await stay;
    expect(router.currentRoute.value.params.name).toBe("Example");
    expect(field("DOI").element.value).toBe("10.1000/xyz");
  });

  it("leaves without asking when nothing changed", async () => {
    await mountSection();
    await router.push("/");
    expect(router.currentRoute.value.name).toBe("Overview");
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

describe("text areas", () => {
  it("grow by CSS where browsers size fields by content", async () => {
    await mountSection(withMetadata(fullStudyMetadata()));
    expect(wrapper.findAllComponents(VTextarea).map((area) => area.props("autoGrow"))).toEqual([false, false]);
  });

  it("grow with Vuetify, up to ten rows, where they do not", async () => {
    vi.spyOn(CSS, "supports").mockReturnValue(false);
    await mountSection(withMetadata(fullStudyMetadata()));
    const areas = wrapper.findAllComponents(VTextarea);
    expect(areas.map((area) => area.props("autoGrow"))).toEqual([true, true]);
    expect(areas.map((area) => Number(area.props("maxRows")))).toEqual([10, 10]);
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
