import { afterEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
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

describe("dragging the separator", () => {
  /** jsdom has no layout: the panes are 300 px wide from x = 100, with the separator at 45 %, at x = 235. */
  function layOut(): void {
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLElement) {
      if (this.classList.contains("split-pane")) return new DOMRect(100, 0, 300, 400);
      if (this.getAttribute("role") === "separator") return new DOMRect(235, 0, 6, 400);
      return new DOMRect();
    });
    // jsdom has no pointer capture.
    for (const name of ["setPointerCapture", "releasePointerCapture"])
      Object.defineProperty(HTMLElement.prototype, name, { configurable: true, value: vi.fn() });
  }

  afterEach(() => {
    for (const name of ["setPointerCapture", "releasePointerCapture"]) Reflect.deleteProperty(HTMLElement.prototype, name);
  });

  function pointer(element: Element, type: string, clientX: number): PointerEvent {
    const event = new PointerEvent(type, { clientX, pointerId: 1, bubbles: true, cancelable: true });
    element.dispatchEvent(event);
    return event;
  }

  it("follows the pointer from the place where it grabbed the separator", async () => {
    layOut();
    const wrapper = mountPane();
    const separator = wrapper.get('[role="separator"]');
    // Grabbed 6 px right of its start edge, which stays 6 px left of the pointer.
    pointer(separator.element, "pointerdown", 241);
    await flushPromises();
    expect(separator.attributes("aria-valuenow")).toBe("45");
    pointer(separator.element, "pointermove", 271);
    await flushPromises();
    expect(separator.attributes("aria-valuenow")).toBe("55");
    pointer(separator.element, "pointerup", 271);
    pointer(separator.element, "pointermove", 301);
    await flushPromises();
    expect(separator.attributes("aria-valuenow")).toBe("55");
    expect(localStorage.getItem(KEY)).toBe("55");
  });

  it("selects no text while it drags", async () => {
    layOut();
    const wrapper = mountPane();
    const separator = wrapper.get('[role="separator"]');
    const down = pointer(separator.element, "pointerdown", 241);
    expect(down.defaultPrevented).toBe(true);
    expect(document.body.classList).toContain("split-pane-dragging");
    pointer(separator.element, "pointercancel", 241);
    expect(document.body.classList).not.toContain("split-pane-dragging");
    pointer(separator.element, "pointerdown", 241);
    wrapper.unmount();
    expect(document.body.classList).not.toContain("split-pane-dragging");
  });
});
