import { expect, it } from "vitest";
import { countLabel } from "../../src/features/search/model";
import { tabs } from "../../src/features/search/model";

it("counts every result tab in the singular and the plural", () => {
  const singular = {
    studies: "study",
    groups: "group",
    individuals: "individual",
    interventions: "intervention",
    measurements: "measurement",
    timecourses: "timecourse",
    scatters: "scatter data",
  };
  const plural = {
    studies: "studies",
    groups: "groups",
    individuals: "individuals",
    interventions: "interventions",
    measurements: "measurements",
    timecourses: "timecourses",
    scatters: "scatter data",
  };
  for (const tab of tabs) {
    expect(countLabel(tab, 1)).toBe(`1 ${singular[tab]}`);
    expect(countLabel(tab, 0)).toBe(`0 ${plural[tab]}`);
    expect(countLabel(tab, 2)).toBe(`2 ${plural[tab]}`);
  }
  expect(countLabel("measurements", 1234)).toBe(
    `${(1234).toLocaleString()} measurements`,
  );
});
