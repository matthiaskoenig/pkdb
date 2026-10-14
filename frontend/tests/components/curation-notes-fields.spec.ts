import { afterEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import type { Comment, Profile } from "../../src/curation-app/api/types";
import NotesFields from "../../src/curation-app/components/NotesFields.vue";
import type { FieldMark } from "../../src/curation-app/metadata";
import { profile } from "../unit/curation-fixtures";
import { messagesOf, textArea } from "./curation-dom";

enableAutoUnmount(afterEach);
afterEach(() => vi.restoreAllMocks());

const DESCRIPTIONS = ["Plasma levels in µg/l.", "Doses in mg."];
const COMMENTS: Comment[] = [
  { user: "mkoenig", text: "Checked against the PDF." },
  { user: "janekg", text: "AUC rounded." },
];
const PROFILES: ReadonlyMap<string, Profile> = new Map([
  ["mkoenig", profile("mkoenig", "Matthias König")],
  ["janekg", profile("janekg", "Jan Grzegorzewski")],
]);
const BLANK = "Enter some text or remove this entry.";

interface Notes {
  descriptions?: string[];
  comments?: Comment[];
  kind?: string | null;
  errors?: ReadonlyMap<string, string[]>;
  marks?: ReadonlyMap<string, FieldMark>;
}

/** The fields of the notes of the study, or of `kind`, whose models update their props as a parent would. */
function mountFields({
  descriptions = DESCRIPTIONS,
  comments = COMMENTS,
  kind = null,
  errors = new Map(),
  marks = new Map(),
}: Notes = {}) {
  const wrapper = mount(NotesFields, {
    attachTo: document.body,
    props: {
      descriptions,
      comments,
      prefix: kind ? `notes.${kind}.` : "",
      kind,
      author: "curator",
      profiles: PROFILES,
      errors,
      marks,
      disk: new Map(),
      "onUpdate:descriptions": (value: string[]) => wrapper.setProps({ descriptions: value }),
      "onUpdate:comments": (value: Comment[]) => wrapper.setProps({ comments: value }),
    },
  });
  return wrapper;
}

/** The text areas that the curator types into, without the hidden sizers of Vuetify's auto-grow. */
function textAreas(wrapper: VueWrapper) {
  return wrapper.findAll<HTMLTextAreaElement>("textarea:not(.v-textarea__sizer)");
}

/** The accessible name and the text of each text area, in the order of the page. */
function named(wrapper: VueWrapper): [string | undefined, string][] {
  return textAreas(wrapper).map((area) => [area.attributes("aria-label"), area.element.value]);
}

describe("descriptions and comments", () => {
  it("name each text area for screen readers and show no label", () => {
    const wrapper = mountFields();
    expect(named(wrapper)).toEqual([
      ["Description 1", "Plasma levels in µg/l."],
      ["Description 2", "Doses in mg."],
      ["Comment 1 by mkoenig", "Checked against the PDF."],
      ["Comment 2 by janekg", "AUC rounded."],
    ]);
    expect(wrapper.findAll("label")).toHaveLength(0);
    expect(wrapper.text()).not.toMatch(/Description \d|Comment \d/);
    // Vuetify points aria-labelledby at the label of a field, which these fields do not have.
    expect(textAreas(wrapper).filter((area) => area.attributes("aria-labelledby") !== undefined)).toHaveLength(0);
    // The groups keep their headings.
    expect(wrapper.findAll("h4").map((heading) => heading.text())).toEqual(["Descriptions", "Comments"]);
  });

  it("shows the author of each comment once, above its text, also an author outside the roster", () => {
    const wrapper = mountFields({ comments: [...COMMENTS, { user: "visitor", text: "Seen." }] });
    const rows = wrapper.findAll(".comment-row");
    expect(rows.map((row) => row.findAll(".comment-author").length)).toEqual([1, 1, 1]);
    expect(rows.map((row) => row.findAll("label").length)).toEqual([0, 0, 0]);
    expect(rows.map((row) => row.get(".comment-author").text())).toEqual([
      "Matthias König",
      "Jan Grzegorzewski",
      // Outside the roster: the initial of the user name in the avatar, then the user name.
      expect.stringMatching(/visitor$/),
    ]);
    for (const row of rows) {
      const after = row.get(".comment-author").element.compareDocumentPosition(row.get("textarea").element);
      expect(after & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
    expect(textArea("Comment 3 by visitor", wrapper.element).element.value).toBe("Seen.");
    expect(wrapper.text().match(/Matthias König/g)).toHaveLength(1);
  });

  it("numbers the text areas by their position again after a removal", async () => {
    const wrapper = mountFields({ descriptions: ["First.", "Second.", "Third."], comments: [] });
    await wrapper.get('button[aria-label="Remove description 1"]').trigger("click");
    await flushPromises();
    expect(wrapper.props("descriptions")).toEqual(["Second.", "Third."]);
    expect(named(wrapper)).toEqual([
      ["Description 1", "Second."],
      ["Description 2", "Third."],
    ]);
  });

  it("marks a text area with a problem by its outline and message, which screen readers hear", () => {
    const wrapper = mountFields({
      kind: "outputs",
      errors: new Map([
        ["notes.outputs.descriptions.1", [BLANK]],
        ["notes.outputs.comments.0", [BLANK]],
      ]),
    });
    const second = textArea("Description 2", wrapper.element);
    expect(second.element.closest(".v-field")!.classList).toContain("v-field--error");
    expect(messagesOf(second)).toBe(BLANK);
    const describedBy = second.attributes("aria-describedby") ?? "";
    expect(document.getElementById(describedBy)?.textContent).toContain(BLANK);
    expect(textArea("Description 1", wrapper.element).element.closest(".v-field")!.classList).not.toContain(
      "v-field--error",
    );
    expect(messagesOf(textArea("Comment 1 by mkoenig", wrapper.element))).toBe(BLANK);
  });

  it("keeps the bar and the message of a list that changed on disk", () => {
    const wrapper = mountFields({ marks: new Map<string, FieldMark>([["descriptions", "conflict"]]) });
    const block = wrapper.get(".descriptions-block");
    expect(block.classes()).toContain("field-block--conflict");
    expect(block.get(".field-mark").text()).toBe("Changed on disk too. Your edit is kept.");
  });

  it("starts every text area at one row and lets Vuetify grow it", () => {
    // Where the browser does not size fields by content (Firefox), Vuetify's auto-grow sizes them.
    vi.spyOn(CSS, "supports").mockReturnValue(false);
    const wrapper = mountFields();
    for (const area of textAreas(wrapper)) {
      expect(area.attributes("rows")).toBe("1");
      expect(area.element.closest(".v-textarea")!.classList).toContain("v-textarea--auto-grow");
    }
  });
});
