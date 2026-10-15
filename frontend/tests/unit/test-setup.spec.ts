import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { defineComponent, h } from "vue";
import { POLL_INTERVAL_MS } from "../../src/curation-app/composables/usePolling";
import { curationRoutes } from "../../src/curation-app/routes";
import { useStudyViews, type StudyViewRoutes } from "../../src/study-views/context";

describe("the setup of the unit and component tests", () => {
  it("lets the stores poll only when a test asks, by the path of usePolling that tests/setup.ts mocks", () => {
    expect(POLL_INTERVAL_MS).toBe(2 ** 31 - 1);
  });

  it("gives every mounted component the study views of the curation app", () => {
    let routes: StudyViewRoutes | null = null;
    mount(
      defineComponent({
        setup() {
          routes = useStudyViews().routes;
          return () => h("p");
        },
      }),
    );
    expect(routes).toBe(curationRoutes);
  });
});
