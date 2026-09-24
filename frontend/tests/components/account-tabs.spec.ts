import { afterEach, expect, it, vi } from "vitest";
import { mount, flushPromises, enableAutoUnmount } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { accountApi } from "../../src/api/account";
import { adminApi } from "../../src/api/admin";
import { useSessionStore } from "../../src/stores/session";
import AccountPage from "../../src/features/account/components/AccountPage.vue";
import { profileFixture } from "../unit/account-fixtures";
enableAutoUnmount(afterEach);
afterEach(() => vi.restoreAllMocks());
it("associates every account tab with its named panel and activates the selected panel", async () => {
  const pinia = createPinia();
  setActivePinia(pinia);
  const session = useSessionStore();
  session.profile = profileFixture({
    role: "admin",
    title: "Prof. Dr.",
    affiliation: "Humboldt-Universität zu Berlin; University Hospital Schleswig-Holstein",
  });
  session.ready = true;
  vi.spyOn(accountApi, "keys").mockResolvedValue([]);
  vi.spyOn(accountApi, "sessions").mockResolvedValue([]);
  vi.spyOn(accountApi, "studies").mockResolvedValue([]);
  vi.spyOn(accountApi, "events").mockResolvedValue([]);
  vi.spyOn(adminApi, "users").mockResolvedValue([]);
  vi.spyOn(adminApi, "requests").mockResolvedValue([]);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/account", component: { template: "<div />" } }],
  });
  await router.push("/account");
  await router.isReady();
  const wrapper = mount(AccountPage, {
    attachTo: document.body,
    global: { plugins: [pinia, router] },
  });
  await flushPromises();
  expect(wrapper.get('[role="tablist"]').attributes("aria-label")).toBe(
    "Account settings sections",
  );
  for (const [label, expected] of [
    ["Title (optional)", session.profile.title],
    ["Affiliation (optional)", session.profile.affiliation],
  ]) {
    const input = wrapper.findAll("input").find((value) => {
      const id = value.attributes("id");
      return id && wrapper.find(`label[for="${id}"]`).text() === label;
    });
    expect(input?.element.value).toBe(expected);
  }
  const tabs = wrapper.findAll('[role="tab"]');
  expect(tabs).toHaveLength(7);
  expect(wrapper.text()).not.toContain("Connected accounts");
  expect(wrapper.text()).not.toContain("Confirm administrator identity");
  for (const label of ["GitHub handle (optional)", "ORCID iD (optional)"]) {
    const input = wrapper.findAll("input").find((value) => {
      const id = value.attributes("id");
      return id && wrapper.find(`label[for="${id}"]`).text() === label;
    });
    expect(input).toBeDefined();
    expect(input?.attributes("readonly")).toBeUndefined();
  }
  for (const tab of tabs) {
    const panel = wrapper.get("#" + tab.attributes("aria-controls"));
    expect(panel.attributes("role")).toBe("tabpanel");
    expect(panel.attributes("aria-labelledby")).toBe(tab.attributes("id"));
    expect(panel.attributes("tabindex")).toBe(
      tab.attributes("aria-selected") === "true" ? "0" : "-1",
    );
  }
  await wrapper.get("#account-tab-3").trigger("click");
  await flushPromises();
  expect(wrapper.get("#account-tab-3").attributes("aria-selected")).toBe(
    "true",
  );
  expect(wrapper.get("#account-panel-3").isVisible()).toBe(true);
  expect(wrapper.get("#account-panel-0").attributes("aria-hidden")).toBe(
    "true",
  );
  expect(wrapper.get("#account-panel-0").attributes("inert")).toBeDefined();
  expect(wrapper.get("#account-panel-3").attributes("aria-hidden")).toBe(
    "false",
  );
  expect(wrapper.get("#account-panel-3").attributes("inert")).toBeUndefined();
  wrapper.unmount();
  disposePinia(pinia);
});
