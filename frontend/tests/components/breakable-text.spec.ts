import { expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import HighlightText from "../../src/components/common/HighlightText.vue";

it("allows a line break after a slash and nowhere inside a word", () => {
  const wrapper = mount(HighlightText, {
    props: { text: "drug/Format2Fixture" },
  });
  expect(wrapper.text()).toBe("drug/Format2Fixture");
  expect(wrapper.html()).toContain("drug/<wbr>Format2Fixture");
  expect(wrapper.findAll("wbr")).toHaveLength(1);
  wrapper.unmount();
});
it("keeps the highlighted match and the text intact", () => {
  const wrapper = mount(HighlightText, {
    props: { text: "acetaminophen/Abernethy1982", query: "abernethy" },
  });
  expect(wrapper.text()).toBe("acetaminophen/Abernethy1982");
  expect(wrapper.get("mark").text()).toBe("Abernethy");
  expect(wrapper.findAll("wbr")).toHaveLength(1);
  const plain = mount(HighlightText, { props: { text: "FRONTEND_SCOPE" } });
  expect(plain.findAll("wbr")).toHaveLength(0);
  wrapper.unmount();
  plain.unmount();
});
it("does not offer a break inside an operator or around spaced slashes", () => {
  for (const text of ["2.7 ×/÷ 1.3 (GSD)", "gram / liter", "a/ b", "/x"]) {
    const wrapper = mount(HighlightText, { props: { text } });
    expect(wrapper.findAll("wbr")).toHaveLength(0);
    expect(wrapper.text()).toBe(text);
    wrapper.unmount();
  }
});
it("keeps text up to the given length together", () => {
  const short = mount(HighlightText, {
    props: { text: "drug/Format2Fixture", keepUpTo: 40 },
  });
  expect(short.findAll("wbr")).toHaveLength(0);
  const highlighted = mount(HighlightText, {
    props: { text: "drug/Format2Fixture", keepUpTo: 40, query: "format" },
  });
  expect(highlighted.findAll("wbr")).toHaveLength(0);
  expect(highlighted.get("mark").text()).toBe("Format");
  const long = mount(HighlightText, {
    props: { text: `${"a".repeat(30)}/${"b".repeat(30)}`, keepUpTo: 40 },
  });
  expect(long.findAll("wbr")).toHaveLength(1);
  short.unmount();
  highlighted.unmount();
  long.unmount();
});
