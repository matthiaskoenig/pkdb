import { describe, expect, it } from "vitest";
import type { Profile } from "../../src/curation-app/api/types";
import { rowItem } from "../../src/curation-app/studyTable";
import { studyRow } from "./curation-fixtures";

const profiles = new Map<string, Profile>([
  [
    "mkoenig",
    { username: "mkoenig", display_name: "Matthias König", title: null, affiliation: null, avatar_url: "/a.webp" },
  ],
]);

describe("rowItem", () => {
  it("shows two curators and counts the others beyond three", () => {
    const row = studyRow({ summary: { ...studyRow().summary, curators: ["mkoenig", "janekg", "curator", "alice"] } });
    const item = rowItem(row, profiles, "matthiaskoenig/pkdb_data");
    expect(item.curators).toEqual([
      { name: "Matthias König", avatar: "/a.webp", initials: "MK" },
      { name: "janekg", avatar: null, initials: "J" },
    ]);
    expect(item.hidden).toBe(2);
    expect(item.others).toBe("curator, alice");
  });

  it("links the issue of the configured repository and only web pages of uploads", () => {
    const row = studyRow({
      summary: { ...studyRow().summary, issue: 12 },
      last_upload: { persistence: "replaced", at: "2026-10-01T12:00:00Z", endpoint: "x", url: "javascript:alert(1)" },
    });
    const item = rowItem(row, profiles, "matthiaskoenig/pkdb_data");
    expect(item.issue).toEqual({ number: 12, url: "https://github.com/matthiaskoenig/pkdb_data/issues/12" });
    expect(item.upload).toBeNull();
  });
});
