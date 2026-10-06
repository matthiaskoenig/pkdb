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
it("keeps a value on one line and sorts it by the value of the row", async () => {
  const wrapper = table();
  expect(wrapper.findAll("td.nowrap")).toHaveLength(2);
  const sort = wrapper
    .findAll("button.sort-button")
    .find((button) => button.text().startsWith("Value"));
  await sort?.trigger("click");
  expect(wrapper.emitted("order")?.[0]).toEqual(["central_value"]);
  wrapper.unmount();
});
it("keeps a study identifier whole and breaks only a very long one after its slash", () => {
  const long = `${"a".repeat(30)}/${"b".repeat(30)}`;
  const wrapper = table([
    ...rows,
    { ...rows[0]!, pk: 3, study: { sid: long, name: "Long" } },
  ]);
  const cells = wrapper.findAll("tbody tr").map((row) => row.findAll("td")[7]);
  expect(cells[0]?.html()).not.toContain("<wbr>");
  expect(cells[0]?.text()).toBe("drug/Format2Fixture");
  expect(cells[2]?.html()).toContain(
    `${"a".repeat(30)}/<wbr>${"b".repeat(30)}`,
  );
  wrapper.unmount();
});
it("shows a dash in every empty cell of an intervention without route and substance", () => {
  const wrapper = mount(ResultsTable, {
    props: {
      tab: "interventions",
      items: [{ pk: 3, name: "D3", substance: null, route: null, study: null }],
      order: "",
      query: "",
    },
  });
  expect(
    wrapper
      .findAll("tbody tr")[0]
      ?.findAll("td")
      .map((cell) => cell.text()),
  ).toEqual(["View ↗", "D3", "-", "-", "-", "-", "-", "-"]);
  wrapper.unmount();
});
it("keeps a study identifier together and lets the name of a format 1 study wrap", () => {
  const wrapper = table();
  const [first, second] = wrapper.findAll("tbody tr");
  expect(first?.findAll("td")[7]?.classes()).toContain("identifier");
  expect(second?.findAll("td")[7]?.classes()).not.toContain("identifier");
  wrapper.unmount();
});
