import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import StudyContents from "../../src/features/details/components/StudyContents.vue";
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

const page = (rows: unknown[]) => ({
  data: { data: { count: rows.length, data: rows } },
});
beforeEach(() => {
  setActivePinia(createPinia());
  mocks.get.mockReset();
});
describe("whole-study contents", () => {
  it("filters a two-segment study by its complete sid", async () => {
    mocks.get.mockResolvedValue(page([]));
    const wrapper = mount(StudyContents, {
      props: { sid: "caffeine/Harder1988" },
    });
    await flushPromises();
    expect(mocks.get.mock.calls[0]?.[1]?.params).toMatchObject({
      study_sid: "caffeine/Harder1988",
    });
    wrapper.unmount();
  });
  it("lists the dose and readable schedule of each intervention", async () => {
    mocks.get.mockResolvedValue(
      page([
        {
          pk: 1,
          name: "D1",
          mean: 10,
          unit: "mg",
          time: 0,
          interval: 24,
          doses: 7,
          time_unit: "h",
        },
        {
          pk: 2,
          name: "D2",
          gmean: 5,
          unit: "mg",
          time: [0, 12, 40],
          time_unit: "h",
        },
        { pk: 3, name: "D3", choice: { name: "fasted" }, time: null },
      ]),
    );
    const wrapper = mount(StudyContents, { props: { sid: "caffeine/X" } });
    await flushPromises();
    await wrapper.getComponent({ name: "VSelect" }).setValue("interventions");
    await flushPromises();
    const items = wrapper.findAll("li").map((item) => item.text());
    expect(items[0]).toContain("10 mg");
    expect(items[0]).toContain("every 24\u00a0h, 7\u00a0doses from 0\u00a0h");
    expect(items[1]).toContain("5 mg");
    expect(items[1]).toContain("0, 12, 40\u00a0h");
    expect(items[2]).toContain("fasted");
    expect(items[2]).not.toContain("Not reported");
    expect(items[2]).not.toContain("-");
    wrapper.unmount();
  });
  it("lists the reported statistic of each measurement without value", async () => {
    mocks.get.mockResolvedValue(
      page([
        {
          pk: 1,
          measurement_type: { name: "Concentration" },
          mean: 0,
          unit: "mg/l",
        },
        {
          pk: 2,
          measurement_type: { name: "Concentration" },
          gmean: 4.5,
          unit: "mg/l",
        },
      ]),
    );
    const wrapper = mount(StudyContents, { props: { sid: "caffeine/X" } });
    await flushPromises();
    await wrapper.getComponent({ name: "VSelect" }).setValue("outputs");
    await flushPromises();
    const items = wrapper.findAll("li").map((item) => item.text());
    expect(items[0]).toMatch(/0 mg\/l$/);
    expect(items[1]).toMatch(/4\.5 mg\/l$/);
    wrapper.unmount();
  });
  it("says one record in the singular and rounds values", async () => {
    mocks.get.mockResolvedValue(
      page([
        {
          pk: 1,
          measurement_type: { name: "Concentration" },
          mean: 0.009000000000000001,
          unit: "mg/l",
        },
      ]),
    );
    const wrapper = mount(StudyContents, { props: { sid: "caffeine/X" } });
    await flushPromises();
    await wrapper.getComponent({ name: "VSelect" }).setValue("outputs");
    await flushPromises();
    expect(wrapper.text()).toContain("1 record");
    expect(wrapper.text()).not.toContain("1 records");
    expect(wrapper.get("li").text()).toMatch(/0\.009 mg\/l$/);
    wrapper.unmount();
  });
});
