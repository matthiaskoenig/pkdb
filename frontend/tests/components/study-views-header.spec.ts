import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { enableAutoUnmount } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { h } from "vue";
import StudyHeader from "../../src/study-views/components/StudyHeader.vue";
import { studyDetail } from "../unit/curation-fixtures";
import { memoryData, mountViews, viewsContext } from "./study-views";

enableAutoUnmount(afterEach);
beforeEach(() => setActivePinia(undefined));

const DETAIL = studyDetail({
  issue: { number: 2158, state: null, labels: [], assignees: [], url: "https://github.com/matthiaskoenig/pkdb_data/issues/2158" },
});

describe("the shared study header", () => {
  it("shows the study from the reads of the page, without a store and without actions of its own", () => {
    const wrapper = mountViews(StudyHeader, {
      context: viewsContext({ data: memoryData({ detail: DETAIL }) }),
      props: { detail: DETAIL },
    });
    expect(wrapper.get(".study-identity").text()).toBe("caffeine/Example");
    expect(wrapper.get(".study-title").text()).toBe("Caffeine pharmacokinetics");
    expect(wrapper.get(".issue-chip").attributes("href")).toBe("https://github.com/matthiaskoenig/pkdb_data/issues/2158");
    expect(wrapper.findAll("button, select, input")).toHaveLength(0);
  });

  it("puts the actions of its page into the line and what follows them below it", () => {
    const wrapper = mountViews(StudyHeader, {
      context: viewsContext({ data: memoryData({ detail: DETAIL }) }),
      props: { detail: DETAIL },
      slots: {
        actions: () => h("div", { class: "page-actions" }, "Actions"),
        after: () => h("p", { class: "page-notice" }, "Notice"),
      },
    });
    expect(wrapper.get(".study-header-line > .page-actions").text()).toBe("Actions");
    expect(wrapper.get(".study-header > .page-notice").text()).toBe("Notice");
  });
});
