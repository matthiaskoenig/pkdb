import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h } from "vue";
import { mount, flushPromises, enableAutoUnmount } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia } from "pinia";
import { useSessionStore } from "../../src/stores/session";
import {
  accountApi,
  profilePayload,
  type AssignedStudy,
} from "../../src/api/account";
import { useAccountActivity } from "../../src/features/account/useAccountActivity";
import { profileFixture, deferred } from "../unit/account-fixtures";
enableAutoUnmount(afterEach);
let pinia = createPinia();
beforeEach(() => {
  pinia = createPinia();
  setActivePinia(pinia);
  useSessionStore().profile = profileFixture();
});
afterEach(() => {
  disposePinia(pinia);
  vi.restoreAllMocks();
});
const ActivityHarness = defineComponent({
  setup() {
    const { studies, events } = useAccountActivity();
    return () =>
      h("div", [
        h("button", { onClick: () => studies.refresh(0) }, "Studies"),
        h(
          "button",
          { onClick: () => studies.refresh(studies.offset.value + 50) },
          "Next studies",
        ),
        h(
          "button",
          { onClick: () => events.refresh(events.offset.value + 50) },
          "Next events",
        ),
        h(
          "output",
          { "data-test": "studies" },
          studies.rows.value.map((row) => row.sid).join(","),
        ),
        h(
          "output",
          { "data-test": "events" },
          events.rows.value.map((row) => row.action).join(","),
        ),
        h("p", studies.error.value),
        h("p", `Study offset ${studies.offset.value}`),
      ]);
  },
});
describe("account activity privacy and pagination", () => {
  it("loads assignments independently of security-event pagination", async () => {
    const studies = vi
      .spyOn(accountApi, "studies")
      .mockResolvedValue([{ sid: "PKDB00001", name: "Assigned" }]);
    const events = vi.spyOn(accountApi, "events").mockResolvedValue([
      {
        id: 80,
        action: "key.revoke",
        target: "key:7",
        created_at: "2026-09-23",
      },
    ]);
    const wrapper = mount(ActivityHarness, { global: { plugins: [pinia] } });
    await wrapper.findAll("button")[0]?.trigger("click");
    await wrapper.findAll("button")[2]?.trigger("click");
    await flushPromises();
    expect(studies).toHaveBeenCalledWith(0, expect.any(AbortSignal));
    expect(events).toHaveBeenCalledWith(50, expect.any(AbortSignal));
    expect(wrapper.text()).toContain("PKDB00001");
    expect(wrapper.text()).toContain("key.revoke");
  });
  it("retains the page after a next-page error so retry cannot skip rows", async () => {
    vi.spyOn(accountApi, "studies")
      .mockResolvedValueOnce([{ sid: "PKDB00001", name: "Assigned" }])
      .mockRejectedValueOnce(new Error("offline"));
    const wrapper = mount(ActivityHarness, { global: { plugins: [pinia] } });
    await wrapper.findAll("button")[0]?.trigger("click");
    await flushPromises();
    await wrapper.findAll("button")[1]?.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("PKDB00001");
    expect(wrapper.text()).toContain("Study offset 0");
    expect(wrapper.text()).toContain("could not be completed");
  });
  it("discards private assignments completed after logout", async () => {
    const pending = deferred<AssignedStudy[]>();
    vi.spyOn(accountApi, "studies").mockReturnValue(pending.promise);
    const wrapper = mount(ActivityHarness, { global: { plugins: [pinia] } });
    await wrapper.findAll("button")[0]?.trigger("click");
    useSessionStore().invalidate();
    pending.complete([{ sid: "PRIVATE", name: "Private study" }]);
    await flushPromises();
    expect(wrapper.text()).not.toContain("PRIVATE");
    expect(wrapper.text()).toContain("Study offset 0");
  });
  it("saves optional editable profile references and their privacy switches", () => {
    const values = profilePayload(
      {
        display_name: "",
        title: "",
        affiliation: "",
        github: "scientist",
        orcid: "0000-0002-1825-0097",
        github_visible: false,
        orcid_visible: false,
      },
    );
    expect(values.github).toBe("scientist");
    expect(values.orcid).toBe("0000-0002-1825-0097");
    expect(values.github_visible).toBe(false);
    expect(values.orcid_visible).toBe(false);
  });
});
