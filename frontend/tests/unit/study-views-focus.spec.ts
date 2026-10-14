import { afterEach, describe, expect, it } from "vitest";
import { SECTION_HEADING, sectionHeading } from "../../src/study-views/focus";

afterEach(() => {
  document.body.innerHTML = "";
});

describe("the heading of the section of a study page", () => {
  it("is the element that the page marks, whatever its markup", () => {
    document.body.innerHTML = `<main><div><h3 ${SECTION_HEADING} tabindex="-1">Data</h3></div></main>`;
    expect(sectionHeading()?.textContent).toBe("Data");
  });

  it("is none on a page that marks none", () => {
    document.body.innerHTML = '<section class="study-section"><h2>Data</h2></section>';
    expect(sectionHeading()).toBeNull();
  });
});
