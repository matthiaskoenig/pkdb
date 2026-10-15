import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { createApp, defineComponent, h } from "vue";
import { useStudyViews } from "../../src/study-views/context";
import { CURATOR, mountViews, viewsContext } from "../components/study-views";

/** Shows the capabilities of the context that it gets. */
const Reader = defineComponent({
  setup() {
    const views = useStudyViews();
    return () => h("p", JSON.stringify(views.capabilities.value));
  },
});

describe("the context of the study views", () => {
  it("is the curation app's in every component test, as tests/setup.ts installs it", () => {
    expect(JSON.parse(mount(Reader).text())).toEqual({ edit: true, curation: true, files: true, jobs: true });
  });

  it("is the one of the nearest page that provides it, over the one of the app", () => {
    const page = mountViews(Reader, { context: viewsContext({ capabilities: CURATOR }) });
    expect(JSON.parse(page.text())).toEqual(CURATOR);
  });

  it("is required: a view without a page that provides it says so", () => {
    const app = createApp(Reader);
    app.config.warnHandler = () => undefined;
    expect(() => app.mount(document.createElement("div"))).toThrow("provideStudyViews");
  });
});
