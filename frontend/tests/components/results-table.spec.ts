import { expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import ResultsTable from "../../src/features/results/components/ResultsTable.vue";

const rows = [
  {
    pk: 1,
    measurement_type: { name: "concentration" },
    substance: { name: "drug" },
    unit: "mg/l",
    mean: 2.5,
    sd: 0.5,
    group: { name: "all" },
    interventions: [{ name: "D1" }],
    study: { sid: "drug/Format2Fixture", name: "Format2Fixture" },
  },
  {
    pk: 2,
    measurement_type: { name: "concentration" },
    substance: { name: "drug" },
    unit: null,
    mean: null,
    group: { name: "all" },
    interventions: [],
    study: { sid: "PKDB00057", name: "Abernethy1982" },
  },
];
function table(items = rows) {
  return mount(ResultsTable, {
    props: { tab: "measurements", items, order: "", query: "" },
  });
}
it("shows unit before one value column and the study identifier", () => {
  const wrapper = table();
  expect(wrapper.findAll("th").map((header) => header.text())).toEqual([
    "Explore",
    "Measurement ↕",
    "Substance ↕",
    "Unit ↕",
    "Value ↕",
    "Subject",
    "Related interventions",
    "Study ↕",
  ]);
  const [first, second] = wrapper.findAll("tbody tr");
  expect(first?.findAll("td").map((cell) => cell.text())).toEqual([
    "View ↗",
    "concentration",
    "drug",
    "mg/l",
    "2.5 ± 0.5 (SD)",
    "all",
    "D1",
    "drug/Format2Fixture",
  ]);
  // Missing statistics, units and related interventions read as a dash.
  expect(second?.findAll("td").map((cell) => cell.text())).toEqual([
    "View ↗",
    "concentration",
    "drug",
    "-",
    "-",
    "all",
    "-",
    "Abernethy1982",
  ]);
  wrapper.unmount();
});
it("keeps a value on one line and sorts it by the mean", async () => {
  const wrapper = table();
  expect(wrapper.findAll("td.nowrap")).toHaveLength(2);
  const sort = wrapper
    .findAll("button.sort-button")
    .find((button) => button.text().startsWith("Value"));
  await sort?.trigger("click");
  expect(wrapper.emitted("order")?.[0]).toEqual(["mean"]);
  wrapper.unmount();
});
it("allows a break after the slash of a study identifier only", () => {
  const wrapper = table();
  const cell = wrapper.findAll("tbody tr")[0]?.findAll("td")[7];
  expect(cell?.html()).toContain("drug/<wbr>Format2Fixture");
  wrapper.unmount();
});
