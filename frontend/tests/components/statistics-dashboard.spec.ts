import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import StatisticsDashboard from "../../src/features/home/StatisticsDashboard.vue";
import StatisticsChart from "../../src/features/home/StatisticsChart.vue";
import { parseOverview } from "../../src/features/home/statistics";
import fixture from "../fixtures/statistics.json";

describe("coverage dashboard", () => {
  it("switches annual/cumulative counts, filters years and individual PK parameters", async () => {
    const wrapper = mount(StatisticsDashboard, { props: { overview: parseOverview(fixture) }, global: { stubs: { StatisticsChart: true } } });
    const charts = () => wrapper.findAllComponents(StatisticsChart);
    expect(charts()[0]!.props("traces")[0]!.y).toEqual([1, 1, 3]);
    expect(charts()[1]!.props("traces")[0]!.y).toEqual([1, 1, 2]);
    await wrapper.get('input[type="checkbox"]').setValue(false);
    expect(charts()[0]!.props("traces")[0]!.y).toEqual([1, 0, 2]);
    await wrapper.findAll("select")[0]!.setValue(2022);
    expect(charts()[0]!.props("traces")[0]!.x).toEqual([2022]);
    expect(charts()[2]!.props("traces")[0]!.y).toEqual([2]);
    await wrapper.findAll("select")[2]!.setValue("clearance");
    expect(charts()[2]!.props("traces")[0]!.y).toEqual([1]);
    expect(wrapper.text()).toContain("1 undated study");
    await wrapper.findAll("select")[1]!.setValue(2020);
    expect(wrapper.text()).toContain("No dated studies in this range");
    wrapper.unmount();
  });
  it("validates metrics, date basis and complete ordered timelines", () => {
    expect(parseOverview(fixture).counts.pk_count).toBe(8);
    expect(() => parseOverview({ ...fixture, date_basis: "reference.date" })).toThrow();
    expect(() => parseOverview({ ...fixture, years: [fixture.years[0], fixture.years[2]] })).toThrow();
    expect(() => parseOverview({ ...fixture, parameters: [{ ...fixture.parameters[0], calculated: -1 }] })).toThrow();
  });
});
