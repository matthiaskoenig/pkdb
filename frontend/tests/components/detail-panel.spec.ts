import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { nextTick } from "vue";
import DetailPanel from "../../src/features/details/components/DetailPanel.vue";
import RecordFields from "../../src/features/details/components/RecordFields.vue";
import { useSessionStore } from "../../src/stores/session";
const mocks = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("../../src/api/client", () => ({
  api: { get: mocks.get },
  apiBase: "",
  errorMessage: (error: unknown) =>
    error instanceof Error ? error.message : "Request failed",
  clearCsrf: vi.fn(),
  cleanLegacyCredentials: vi.fn(),
  onUnauthorized: () => () => {},
}));

beforeEach(() => {
  setActivePinia(createPinia());
  mocks.get.mockReset();
});
describe("record exploration", () => {
  it("identifies automatically imported studies with their provider and release", async () => {
    mocks.get.mockResolvedValueOnce({ data: { sid: "OSP1", name: "OSP study", provenance: {
      kind: "data_import", source_key: "osp.observed-data", release: "v1.9",
    } } });
    const wrapper = mount(DetailPanel, {
      props: { entity: "studies", identifier: "OSP1" },
      global: { stubs: { StudyContents: true } },
    });
    await flushPromises();
    expect(wrapper.get('[aria-label="Data source"]').text()).toContain("Automatic import · osp.observed-data · v1.9");
    wrapper.unmount();
  });
  it("keeps zero and uncertainty visible and prevents unsafe external links", () => {
    const wrapper = mount(RecordFields, {
      props: {
        data: {
          mean: 0,
          gmean: null,
          sd: 1e-9,
          annotations: [{ url: "javascript:alert(1)", term: "<b>escaped</b>" }],
        },
      },
    });
    expect(wrapper.text()).toContain("0");
    expect(wrapper.text()).toContain("Not reported");
    expect(wrapper.text()).toContain("1e-9");
    expect(wrapper.find("a").exists()).toBe(false);
    expect(wrapper.find("b").exists()).toBe(false);
    wrapper.unmount();
  });
  it("discards a stale detail response after navigation despite cancellation racing", async () => {
    let finish: ((value: { data: unknown }) => void) | undefined;
    mocks.get
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            finish = resolve;
          }),
      )
      .mockResolvedValueOnce({
        data: { pk: 2, name: "Current record", mean: 0 },
      });
    const wrapper = mount(DetailPanel, {
      props: { entity: "outputs", identifier: 1 },
    });
    await wrapper.setProps({ identifier: 2 });
    await flushPromises();
    finish?.({ data: { pk: 1, name: "Obsolete private record" } });
    await flushPromises();
    expect(wrapper.text()).toContain("Current record");
    expect(wrapper.text()).not.toContain("Obsolete private record");
    wrapper.unmount();
  });
  it("clears protected details immediately when the session changes", async () => {
    mocks.get
      .mockResolvedValueOnce({ data: { pk: 1, name: "Private subject" } })
      .mockImplementationOnce(() => new Promise(() => {}));
    const wrapper = mount(DetailPanel, {
      props: { entity: "groups", identifier: 1 },
    });
    await flushPromises();
    expect(wrapper.text()).toContain("Private subject");
    useSessionStore().invalidate();
    await nextTick();
    expect(wrapper.text()).not.toContain("Private subject");
    wrapper.unmount();
  });
  it("opens a linked scientific record and returns to the original detail", async () => {
    mocks.get
      .mockResolvedValueOnce({
        data: {
          pk: 1,
          name: "Measurement",
          group: { pk: 4, name: "Participants" },
        },
      })
      .mockResolvedValueOnce({
        data: { pk: 4, name: "Participants", count: 0 },
      })
      .mockResolvedValueOnce({ data: { pk: 1, name: "Measurement" } });
    const wrapper = mount(DetailPanel, {
      props: { entity: "outputs", identifier: 1 },
    });
    await flushPromises();
    const related = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Group: Participants"));
    expect(related).toBeDefined();
    await related?.trigger("click");
    await flushPromises();
    expect(mocks.get).toHaveBeenLastCalledWith(
      "/api/v1/groups/4/",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    const back = wrapper
      .findAll("button")
      .find((button) => button.text().includes("Back to previous record"));
    await back?.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Measurement");
    wrapper.unmount();
  });
  describe("study release, issue and review", () => {
    const study = {
      pk: "5",
      sid: "caffeine/Harder1988",
      name: "Harder1988",
      pkdb_id: "PKDB00198",
      release_date: "2026-09-28",
      issue: 2158,
      review_status: "in_review",
      open_review_items: 2,
    };
    const mountStudy = async (data: Record<string, unknown>) => {
      mocks.get.mockResolvedValueOnce({ data });
      const wrapper = mount(DetailPanel, {
        props: { entity: "studies", identifier: "caffeine/Harder1988" },
        global: { stubs: { StudyContents: true } },
      });
      await flushPromises();
      return wrapper;
    };
    it("reads a study by its two path segments", async () => {
      const wrapper = await mountStudy(study);
      expect(mocks.get).toHaveBeenCalledWith(
        "/api/v1/studies/caffeine/Harder1988/",
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      );
      wrapper.unmount();
    });
    it("shows identifier, release date, issue link and open review items compactly", async () => {
      const wrapper = await mountStudy(study);
      const status = wrapper.get('[aria-label="Release and review"]');
      expect(status.text()).toContain("PKDB00198");
      expect(status.text()).toContain("2026-09-28");
      expect(status.text()).toContain("In review");
      expect(status.text()).toContain("2 open items");
      const issue = status.get("a");
      expect(issue.text()).toBe("#2158");
      expect(issue.attributes("href")).toBe(
        "https://github.com/matthiaskoenig/pkdb_data/issues/2158",
      );
      expect(issue.attributes("rel")).toContain("noopener");
      const labels = wrapper.findAll("dt").map((term) => term.text());
      expect(labels).not.toContain("Pkdb id");
      expect(labels).not.toContain("Open review items");
      expect(labels).not.toContain("Review status");
      wrapper.unmount();
    });
    it("shows a draft without release or issue and says when nothing is open", async () => {
      const wrapper = await mountStudy({
        ...study,
        pkdb_id: null,
        release_date: null,
        issue: null,
        review_status: "draft",
        open_review_items: 0,
      });
      const status = wrapper.get('[aria-label="Release and review"]');
      expect(status.text()).toContain("Draft");
      expect(status.text()).toContain("no open items");
      expect(status.text()).not.toContain("PKDB identifier");
      expect(status.text()).not.toContain("Released");
      expect(status.find("a").exists()).toBe(false);
      wrapper.unmount();
    });
    it("counts a single open item and an approved review", async () => {
      const wrapper = await mountStudy({
        ...study,
        review_status: "approved",
        open_review_items: 1,
      });
      expect(wrapper.get('[aria-label="Release and review"]').text()).toContain(
        "Approved · 1 open item",
      );
      wrapper.unmount();
    });
    it("shows nothing for a study format 1 study", async () => {
      const wrapper = await mountStudy({
        pk: "1",
        sid: "PKDB00057",
        name: "Old",
        pkdb_id: null,
        release_date: null,
        issue: null,
        review_status: null,
        open_review_items: 0,
      });
      expect(wrapper.find('[aria-label="Release and review"]').exists()).toBe(
        false,
      );
      expect(wrapper.text()).not.toContain("Open review items");
      wrapper.unmount();
    });
    it("announces the sid a PKDB identifier resolved to and does not reload for it", async () => {
      mocks.get.mockResolvedValueOnce({ data: study });
      const wrapper = mount(DetailPanel, {
        props: { entity: "studies", identifier: "PKDB00198" },
        global: { stubs: { StudyContents: true } },
      });
      await flushPromises();
      expect(wrapper.emitted("loaded")?.[0]?.[0]).toMatchObject({
        sid: "caffeine/Harder1988",
      });
      await wrapper.setProps({ identifier: "caffeine/Harder1988" });
      await flushPromises();
      expect(mocks.get).toHaveBeenCalledTimes(1);
      expect(wrapper.text()).toContain("Harder1988");
      await wrapper.setProps({ identifier: "caffeine/Other" });
      await flushPromises();
      expect(mocks.get).toHaveBeenCalledTimes(2);
      wrapper.unmount();
    });
  });
  it("opens the study of a record by its two path segments", async () => {
    mocks.get
      .mockResolvedValueOnce({
        data: {
          pk: 1,
          name: "Measurement",
          study: { sid: "caffeine/Harder1988", name: "Harder1988" },
        },
      })
      .mockResolvedValueOnce({
        data: { pk: "5", sid: "caffeine/Harder1988", name: "Harder1988" },
      });
    const wrapper = mount(DetailPanel, {
      props: { entity: "outputs", identifier: 1 },
      global: { stubs: { StudyContents: true } },
    });
    await flushPromises();
    await wrapper
      .findAll("button")
      .find((button) => button.text().includes("Study: Harder1988"))
      ?.trigger("click");
    await flushPromises();
    expect(mocks.get).toHaveBeenLastCalledWith(
      "/api/v1/studies/caffeine/Harder1988/",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
    expect(wrapper.emitted("loaded")).toHaveLength(1);
    wrapper.unmount();
  });
  it("shows an intervention schedule readably instead of its raw fields", async () => {
    mocks.get.mockResolvedValueOnce({
      data: {
        pk: 3,
        name: "D1",
        mean: 10,
        unit: "mg",
        time: 0,
        interval: 24,
        doses: 7,
        time_end: null,
        time_unit: "h",
        subject: { pk: 2, name: "all" },
      },
    });
    const wrapper = mount(DetailPanel, {
      props: { entity: "interventions", identifier: 3 },
    });
    await flushPromises();
    const schedule = wrapper.get('[aria-label="Schedule"]');
    expect(schedule.text()).toContain("every 24 h, 7 doses from 0 h");
    const labels = wrapper.findAll("dt").map((term) => term.text());
    expect(labels).toEqual(expect.arrayContaining(["Mean", "Unit", "Subject"]));
    for (const raw of ["Time", "Interval", "Doses", "Time unit", "End time"])
      expect(labels).not.toContain(raw);
    wrapper.unmount();
  });
  it("lists irregular administration times and labels geometric statistics", async () => {
    mocks.get.mockResolvedValueOnce({
      data: {
        pk: 4,
        name: "D2",
        time: [0, 12, 40],
        time_unit: "h",
        gmean: 3,
        gsd: 1.5,
        gcv: 40,
        error_bar: 5,
        error_type: "gsd",
      },
    });
    const wrapper = mount(DetailPanel, {
      props: { entity: "interventions", identifier: 4 },
    });
    await flushPromises();
    expect(wrapper.get('[aria-label="Schedule"]').text()).toContain(
      "0, 12, 40 h",
    );
    const labels = wrapper.findAll("dt").map((term) => term.text());
    expect(labels).toEqual(
      expect.arrayContaining([
        "Geometric mean",
        "Geometric SD",
        "Geometric CV",
        "Error bar",
        "Error bar type",
      ]),
    );
    wrapper.unmount();
  });
  it("keeps the raw time of a record that is not an intervention", async () => {
    mocks.get.mockResolvedValueOnce({
      data: { pk: 9, name: "Concentration", time: 2, time_unit: "h", mean: 1 },
    });
    const wrapper = mount(DetailPanel, {
      props: { entity: "outputs", identifier: 9 },
    });
    await flushPromises();
    expect(wrapper.find('[aria-label="Schedule"]').exists()).toBe(false);
    expect(wrapper.findAll("dt").map((term) => term.text())).toContain("Time");
    wrapper.unmount();
  });
});
