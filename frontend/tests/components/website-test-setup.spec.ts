import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { defineComponent, h } from "vue";
import { useStudyViews } from "../../src/study-views/context";

describe("the setup of the tests of the website", () => {
  it("gives a mounted component no study views, so that a page that provides none fails as in the browser", () => {
    vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const Probe = defineComponent({
      setup() {
        useStudyViews();
        return () => h("p");
      },
    });
    expect(() => mount(Probe)).toThrow("The study views need a context");
  });
});
