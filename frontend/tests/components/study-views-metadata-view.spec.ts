import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, flushPromises, type VueWrapper } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import MetadataView from "../../src/study-views/components/MetadataView.vue";
import type { Curator, Profile, Provenance, StudyDetail, StudyMetadata } from "../../src/study-views/types";
import { fullStudyMetadata, profile, studyDetail } from "../unit/curation-fixtures";
import { CURATOR, memoryData, mountViews, PUBLIC, viewsContext } from "./study-views";

enableAutoUnmount(afterEach);
beforeEach(() => setActivePinia(undefined));

const REFERENCE = {
  sid: null,
  pmid: "2895442",
  doi: "10.1007/BF00637675",
  title: "Caffeine in plasma and saliva",
  journal: "Eur J Clin Pharmacol",
  abstract: null,
  publication_date: "1988-05",
  authors: ["Harder S", "Fuhr U", "Staib AH"],
};

function detail(ratings: [number | null, number | null], changes: Partial<StudyDetail> = {}): StudyDetail {
  return studyDetail({
    metadata: { revision: null, value: fullStudyMetadata(), issues: [] },
    people: {
      creator: profile("curator", "Curator", false),
      curators: [
        { user: "mkoenig", rating: ratings[0], profile: profile("mkoenig", "Matthias König") },
        { user: "janekg", rating: ratings[1], profile: profile("janekg", "Jan Grzegorzewski") },
      ],
      collaborators: [],
    },
    reference: REFERENCE,
    reference_match: true,
    issue: { number: 2158, state: null, labels: [], assignees: [], url: "https://github.com/matthiaskoenig/pkdb_data/issues/2158" },
    ...changes,
  });
}

/** study.json as the website sends it to the public: no issue, curators by name and the provenance by its kind alone. */
function publicMetadata(kind: Provenance["kind"]): StudyMetadata {
  const metadata = fullStudyMetadata({
    curators: [{ user: "mkoenig" }, { user: "janekg" }] as Curator[],
    provenance: { kind } as Provenance,
  });
  delete metadata.issue;
  return metadata;
}

function view(value: StudyDetail, capabilities = PUBLIC, profiles: Profile[] = []): VueWrapper {
  return mountViews(MetadataView, {
    context: viewsContext({
      capabilities,
      data: memoryData({ detail: value, repository: "matthiaskoenig/pkdb_data", profiles }),
    }),
  });
}

/** The facts of the card `title`, by name. */
function facts(wrapper: VueWrapper, title: string): Record<string, string> {
  const card = wrapper.findAll("section").find((section) => section.find("h3").exists() && section.get("h3").text() === title);
  if (!card) throw new Error(`There is no card ${title}`);
  const values = card.findAll("dd").map((value) => value.text());
  return Object.fromEntries(card.findAll("dt").map((term, index) => [term.text(), values[index] ?? ""]));
}

describe("the metadata of a study as text", () => {
  it("shows the public the reference, the people, the access, the provenance, the release and the notes, without fields", () => {
    const wrapper = view(detail([null, null]));
    const reference = wrapper.findAll("section").find((section) => section.find("h3").exists() && section.get("h3").text() === "Reference")!;
    expect(reference.text()).toContain("Caffeine in plasma and saliva");
    expect(reference.text()).toContain("Harder S, Fuhr U, Staib AH");
    expect(reference.text()).toContain("Eur J Clin Pharmacol · 1988-05");
    expect(reference.get('a[href="https://pubmed.ncbi.nlm.nih.gov/2895442/"]').text()).toBe("2895442");
    expect(reference.get('a[href="https://doi.org/10.1007/BF00637675"]').text()).toBe("10.1007/BF00637675");
    expect(wrapper.find(".reference-match").exists()).toBe(false);
    expect(facts(wrapper, "People")).toEqual({
      Creator: "Curator",
      Curators: "Matthias König, Jan Grzegorzewski",
      Collaborators: "Jane Doe",
    });
    expect(facts(wrapper, "Access and provenance")).toEqual({
      Licence: "Closed",
      Access: "Public",
      Provenance: "Automatic curation",
      Method: "claude-opus-5-5",
      Version: "2026-10",
      "Run ID": "run-2026-10-07-01",
    });
    expect(facts(wrapper, "Issue and release")).toEqual({ Release: "PKDB00198 · released 2026-09-28" });
    expect(wrapper.text()).toContain("Plasma levels in µg/l.");
    expect(wrapper.get(".metadata-view-comment").text()).toContain("Checked against the PDF.");
    expect(wrapper.get(".metadata-view-author").text()).toBe("Matthias König");
    expect(wrapper.findAll("input, textarea, select, button")).toHaveLength(0);
  });

  it("leaves out the facts of an automatic curation that the page does not give", () => {
    const metadata = fullStudyMetadata();
    const stripped = { ...metadata, provenance: { ...metadata.provenance, method: "", version: "", run_id: "" } };
    const wrapper = view(detail([null, null], { metadata: { revision: null, value: stripped, issues: [] } }));
    expect(facts(wrapper, "Access and provenance")).toEqual({ Licence: "Closed", Access: "Public", Provenance: "Automatic curation" });
  });

  it("shows a curator the issue, the ratings and whether reference.json matches", () => {
    const wrapper = view(detail([3, 4.5]), CURATOR);
    expect(wrapper.get(".reference-match").text()).toBe("reference.json matches");
    expect(facts(wrapper, "People").Curators).toBe("Matthias König (rating 3 of 5), Jan Grzegorzewski (rating 4.5 of 5)");
    expect(facts(wrapper, "Issue and release")).toEqual({ Issue: "#2158", Release: "PKDB00198 · released 2026-09-28" });
    expect(wrapper.get('a[href="https://github.com/matthiaskoenig/pkdb_data/issues/2158"]').text()).toBe("#2158");
  });

  it("shows the study.json of the website's public page whole: no issue, curators without ratings, the provenance by its kind", () => {
    for (const [kind, label] of [
      ["automatic_curation", "Automatic curation"],
      ["data_import", "Data import"],
      ["manual_curation", "Manual curation"],
    ] as const) {
      const metadata = { revision: null, value: publicMetadata(kind), issues: [] };
      const wrapper = view(detail([null, null], { issue: null, metadata }));
      expect(facts(wrapper, "People").Curators).toBe("Matthias König, Jan Grzegorzewski");
      expect(facts(wrapper, "Access and provenance")).toEqual({ Licence: "Closed", Access: "Public", Provenance: label });
      expect(facts(wrapper, "Issue and release")).toEqual({ Release: "PKDB00198 · released 2026-09-28" });
      expect(wrapper.text()).not.toMatch(/null|undefined|rating|#\d/);
      for (const card of wrapper.findAll("section")) expect(card.text()).not.toBe(card.get("h3").text());
    }
  });

  it("links a curator to the issue that study.json names when GitHub has not told of it", () => {
    const wrapper = view(detail([null, null], { issue: null }), CURATOR);
    expect(wrapper.get('a[href="https://github.com/matthiaskoenig/pkdb_data/issues/2158"]').text()).toBe("#2158");
    const metadata = { revision: null, value: publicMetadata("manual_curation"), issues: [] };
    expect(facts(view(detail([null, null], { issue: null, metadata }), CURATOR), "Issue and release").Issue).toBe("No issue");
  });

  it("names the author of a comment by the curators that the page knows, also outside the people of the study", async () => {
    const value = fullStudyMetadata({ comments: [{ user: "reviewer", text: "Units checked." }] });
    const wrapper = view(
      detail([null, null], { metadata: { revision: null, value, issues: [] } }),
      PUBLIC,
      [profile("reviewer", "Rita Reviewer")],
    );
    await flushPromises();
    expect(wrapper.get(".metadata-view-author").text()).toBe("Rita Reviewer");
  });

  it("says when study.json is not valid", () => {
    const wrapper = view(detail([null, null], { metadata: { revision: null, value: null, issues: [] } }));
    expect(wrapper.text()).toBe("study.json is not valid, so its metadata cannot show.");
  });
});
