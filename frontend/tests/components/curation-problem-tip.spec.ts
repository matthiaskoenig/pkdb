import { afterEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import type { ValidationIssue } from "../../src/study-views/types";
import ProblemTip from "../../src/curation-app/components/ProblemTip.vue";

enableAutoUnmount(afterEach);

function issue(code: string, severity: ValidationIssue["severity"], changes: Partial<ValidationIssue> = {}): ValidationIssue {
  return { code, severity, message: `${code} message`, ...changes };
}

describe("ProblemTip", () => {
  it("shows the severity chip, the code, the message and the hint of each problem, errors first", () => {
    const hint = { kind: "inspect_source", message: "Check the reported error statistics against the publication." };
    const wrapper = mount(ProblemTip, {
      props: { issues: [issue("inconsistent_statistics", "warning", { suggestions: [hint] }), issue("missing_value", "error")] },
    });
    const items = wrapper.findAll(".problem-tip-item");
    expect(items.map((item) => item.get(".v-chip").text())).toEqual(["Error", "Warning"]);
    expect(items[0]!.get(".v-chip").classes()).toContain("text-error");
    expect(items[1]!.get(".v-chip").classes()).toContain("text-warning");
    expect(items.map((item) => item.get(".problem-tip-code").text())).toEqual(["missing_value", "inconsistent_statistics"]);
    expect(items.map((item) => item.get(".problem-tip-message").text())).toEqual([
      "missing_value message",
      "inconsistent_statistics message",
    ]);
    expect(items[0]!.find(".problem-tip-hint").exists()).toBe(false);
    expect(items[1]!.get(".problem-tip-hint").text()).toBe("Check the reported error statistics against the publication.");
    expect(wrapper.find(".problem-tip-more").exists()).toBe(false);
  });

  it("lists at most five problems and counts the others", () => {
    const issues = Array.from({ length: 8 }, (_, index) => issue(`code_${index}`, "warning"));
    const wrapper = mount(ProblemTip, { props: { issues } });
    expect(wrapper.findAll(".problem-tip-item")).toHaveLength(5);
    expect(wrapper.get(".problem-tip-more").text()).toBe("and 3 more");
  });
});
