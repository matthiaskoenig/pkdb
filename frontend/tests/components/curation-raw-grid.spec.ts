import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import RawGrid from "../../src/curation-app/components/RawGrid.vue";

describe("RawGrid", () => {
  it("keeps the spaces of the cells as printed", () => {
    const wrapper = mount(RawGrid, { props: { grid: [["  a  b ", "c"]], label: "Raw extraction" } });
    // text() trims, so the DOM text is compared.
    const cells = wrapper.findAll("td").map((cell) => cell.element.textContent);
    expect(cells).toEqual(["  a  b ", "c"]);
  });

  it("pads short rows to the widest one and names the columns as a spreadsheet does", () => {
    const wrapper = mount(RawGrid, { props: { grid: [["a"], ["b", "c", "d"]], label: "Raw extraction" } });
    expect(wrapper.findAll("thead th").map((cell) => cell.text())).toEqual(["Line", "A", "B", "C"]);
    expect(wrapper.findAll("tbody tr")[0]?.findAll("td").map((cell) => cell.text())).toEqual(["a", "", ""]);
    // The line column stays in view while wide rows scroll.
    expect(wrapper.get('[role="region"]').classes()).toContain("rows-scroll--sticky-line");
  });

  it("lists at most 500 rows and says how many there are", () => {
    const grid = Array.from({ length: 612 }, (_, index) => [`row ${index + 1}`]);
    const wrapper = mount(RawGrid, { props: { grid, label: "Raw extraction" } });
    expect(wrapper.findAll("tbody tr")).toHaveLength(500);
    expect(wrapper.text()).toContain("Showing 500 of 612 rows. The Tables section has all of them.");
    expect(wrapper.findAll("tbody th").at(-1)?.text()).toBe("500");
  });

  it("says nothing about the rows when it lists all of them", () => {
    const wrapper = mount(RawGrid, { props: { grid: [["a"]], label: "Raw extraction" } });
    expect(wrapper.text()).not.toContain("Showing");
  });
});
