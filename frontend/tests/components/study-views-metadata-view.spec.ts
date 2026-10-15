import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, flushPromises, type VueWrapper } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import MetadataView from "../../src/study-views/components/MetadataView.vue";
import type { Curator, Profile, Provenance, StudyDetail, StudyMetadata } from "../../src/study-views/types";
import { fullStudyMetadata, profile, studyDetail } from "../unit/curation-fixtures";
import { CURATOR, EVERYTHING, memoryData, mountViews, PUBLIC, viewsContext } from "./study-views";

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
    expect(facts(wrapper, "Release")).toEqual({ Release: "PKDB00198 · released 2026-09-28" });
    expect(wrapper.findAll("h3").map((heading) => heading.text())).not.toContain("Issue and release");
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

  it("shows a curator the issue, the ratings and whether the reference matches", () => {
    const wrapper = view(detail([3, 4.5]), CURATOR);
    expect(wrapper.get(".reference-match").text()).toBe("The reference matches");
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
      expect(facts(wrapper, "Release")).toEqual({ Release: "PKDB00198 · released 2026-09-28" });
      expect(wrapper.findAll("h3").map((heading) => heading.text())).not.toContain("Issue and release");
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

  it("names each link by what it opens, in a new tab", () => {
    const wrapper = view(detail([null, null]), CURATOR);
    expect(wrapper.get('a[href="https://pubmed.ncbi.nlm.nih.gov/2895442/"]').attributes("aria-label")).toBe(
      "PubMed 2895442 (opens in a new tab)",
    );
    expect(wrapper.get('a[href="https://doi.org/10.1007/BF00637675"]').attributes("aria-label")).toBe(
      "DOI 10.1007/BF00637675 (opens in a new tab)",
    );
    expect(wrapper.get('a[href="https://github.com/matthiaskoenig/pkdb_data/issues/2158"]').attributes("aria-label")).toBe(
      "Issue #2158 on GitHub (opens in a new tab)",
    );
    for (const link of wrapper.findAll("a")) {
      expect(link.attributes("target")).toBe("_blank");
      expect(link.attributes("rel")).toBe("noopener noreferrer");
    }
  });

  it("encodes a DOI in its link, also with the characters that end a path", () => {
    const doi = "10.1002/(SICI)1097-4636(199706)35:4<477::AID-JBM8>3.0.CO;2-#";
    const value = fullStudyMetadata({ reference: { doi } });
    const wrapper = view(detail([null, null], { metadata: { revision: null, value, issues: [] } }));
    const link = wrapper.get('a[aria-label^="DOI "]');
    expect(link.attributes("href")).toBe("https://doi.org/10.1002/(SICI)1097-4636(199706)35%3A4%3C477%3A%3AAID-JBM8%3E3.0.CO%3B2-%23");
    expect(link.text()).toBe(doi);
    expect(wrapper.find('a[aria-label^="PubMed "]').exists()).toBe(false);
  });

  it("says when study.json is not valid, naming the file only to a reader who may edit it", () => {
    const invalid = detail([null, null], { metadata: { revision: null, value: null, issues: [] } });
    expect(view(invalid, EVERYTHING).text()).toBe("study.json is not valid, so its metadata cannot show.");
    for (const capabilities of [PUBLIC, CURATOR])
      expect(view(invalid, capabilities).text()).toBe("The metadata of this study cannot show.");
  });

  it("says when reference.json has no title or is not valid, naming the file only to a reader who may edit it", () => {
    const untitled = detail([null, null], { reference: { ...REFERENCE, title: null } });
    expect(view(untitled, EVERYTHING).get(".reference-title").text()).toBe("No title in reference.json");
    expect(view(untitled, CURATOR).get(".reference-title").text()).toBe("No title");
    const broken = detail([null, null], { reference: { error: "reference.json is not valid JSON" } });
    expect(view(broken, EVERYTHING).get(".reference-line").text()).toBe("reference.json is not valid JSON");
    expect(view(broken, PUBLIC).get(".reference-line").text()).toBe("The reference cannot show.");
  });

  it("says whether reference.json matches study.json, naming the files only to a reader who may edit them", () => {
    const chip = (match: boolean, capabilities: typeof CURATOR) =>
      view(detail([null, null], { reference_match: match }), capabilities).get(".reference-match").text();
    expect(chip(false, EVERYTHING)).toBe("reference.json does not match study.json");
    expect(chip(true, EVERYTHING)).toBe("reference.json matches");
    expect(chip(false, CURATOR)).toBe("The reference does not match the study");
    expect(chip(true, CURATOR)).toBe("The reference matches");
    const unmatched = detail([null, null], { reference_match: false });
    expect(view(unmatched, PUBLIC).find(".reference-match").exists()).toBe(false);
  });
});
