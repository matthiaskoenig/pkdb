import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";
import { useChangedFields } from "../../src/curation-app/composables/useChangedFields";
import {
  clone,
  sameField,
  toForm,
  type MetadataForm,
} from "../../src/curation-app/metadata";
import { fullStudyMetadata, NOTE_KINDS } from "./curation-fixtures";

vi.mock("../../src/curation-app/metadata", async (importOriginal) => {
  const actual =
    await importOriginal<typeof import("../../src/curation-app/metadata")>();
  return { ...actual, sameField: vi.fn(actual.sameField) };
});

function setup() {
  const base = ref<MetadataForm | null>(
    toForm(fullStudyMetadata(), NOTE_KINDS),
  );
  const form = ref<MetadataForm | null>(clone(base.value!));
  return { base, form, changed: useChangedFields(base, form) };
}

beforeEach(() => {
  vi.mocked(sameField).mockClear();
});

describe("useChangedFields", () => {
  it("lists the changed fields in the order of the form", () => {
    const { form, changed } = setup();
    expect(changed.value).toEqual([]);
    form.value!.creator = "janekg";
    form.value!.reference.pmid = "99999999";
    expect(changed.value).toEqual(["reference.pmid", "creator"]);
  });

  it("compares only the field that a keystroke changed", () => {
    const { form, changed } = setup();
    expect(changed.value).toEqual([]);
    vi.mocked(sameField).mockClear();
    form.value!.reference.pmid = "9";
    expect(changed.value).toEqual(["reference.pmid"]);
    form.value!.reference.pmid = "98";
    expect(changed.value).toEqual(["reference.pmid"]);
    expect(vi.mocked(sameField).mock.calls.map(([, , key]) => key)).toEqual([
      "reference.pmid",
      "reference.pmid",
    ]);
  });

  it("follows a new base, as after a save, and lists nothing without a form", () => {
    const { base, form, changed } = setup();
    form.value!.creator = "janekg";
    expect(changed.value).toEqual(["creator"]);
    base.value = clone(form.value!);
    expect(changed.value).toEqual([]);
    form.value = null;
    expect(changed.value).toEqual([]);
  });
});
