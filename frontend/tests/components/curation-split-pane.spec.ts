import { afterEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import SplitPane from "../../src/curation-app/components/SplitPane.vue";

enableAutoUnmount(afterEach);

const KEY = "pkdb-curation:test-split";

function mountPane(props: Record<string, unknown> = {}) {
  return mount(SplitPane, {
    props: { storageKey: KEY, label: "Resize the panes", ...props },
    slots: { start: "<p>source</p>", end: "<p>rows</p>" },
    attachTo: document.body,
  });
}

afterEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

describe("split pane", () => {
  it("shows both panes with the separator at the default share", () => {
    const wrapper = mountPane();
    expect(wrapper.text()).toContain("source");
    expect(wrapper.text()).toContain("rows");
    const separator = wrapper.get('[role="separator"]');
    expect(separator.attributes("aria-valuenow")).toBe("45");
    expect(separator.attributes("aria-label")).toBe("Resize the panes");
    expect(separator.attributes("aria-orientation")).toBe("vertical");
  });

  it("moves by 2 % with the arrow keys and to the limits with Home and End, and stores the share", async () => {
    const wrapper = mountPane();
    const separator = wrapper.get('[role="separator"]');
    await separator.trigger("keydown", { key: "ArrowRight" });
    expect(separator.attributes("aria-valuenow")).toBe("47");
    expect(localStorage.getItem(KEY)).toBe("47");
    await separator.trigger("keydown", { key: "ArrowLeft" });
    await separator.trigger("keydown", { key: "ArrowLeft" });
    expect(separator.attributes("aria-valuenow")).toBe("43");
    await separator.trigger("keydown", { key: "Home" });
    expect(separator.attributes("aria-valuenow")).toBe(separator.attributes("aria-valuemin"));
    await separator.trigger("keydown", { key: "End" });
    expect(separator.attributes("aria-valuenow")).toBe(separator.attributes("aria-valuemax"));
  });

  it("opens with the stored share", () => {
    localStorage.setItem(KEY, "60");
    expect(mountPane().get('[role="separator"]').attributes("aria-valuenow")).toBe("60");
  });

  it("falls back to the default share when storage throws or holds no number", async () => {
    localStorage.setItem(KEY, "abc");
    expect(mountPane().get('[role="separator"]').attributes("aria-valuenow")).toBe("45");
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    const wrapper = mountPane({ defaultShare: 50 });
    const separator = wrapper.get('[role="separator"]');
    expect(separator.attributes("aria-valuenow")).toBe("50");
    await separator.trigger("keydown", { key: "ArrowRight" });
    expect(separator.attributes("aria-valuenow")).toBe("52");
  });
});
