import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mount, flushPromises, enableAutoUnmount } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia } from "pinia";
import { createMemoryHistory, createRouter } from "vue-router";
import { AxiosError, AxiosHeaders } from "axios";
import { defineComponent, h } from "vue";
import { useSessionStore } from "../../src/stores/session";
import { adminApi, type AdminUser } from "../../src/api/admin";
import UserLogin from "../../src/features/account/components/UserLogin.vue";
import AdminSettings from "../../src/features/admin/components/AdminSettings.vue";
import { profileFixture } from "../unit/account-fixtures";
enableAutoUnmount(afterEach);
let pinia = createPinia();
beforeEach(() => {
  vi.stubGlobal(
    "visualViewport",
    Object.assign(new EventTarget(), {
      width: 1024,
      height: 768,
      offsetTop: 0,
      offsetLeft: 0,
    }),
  );
  pinia = createPinia();
  setActivePinia(pinia);
});
afterEach(() => {
  disposePinia(pinia);
  vi.restoreAllMocks();
});
function failure(detail: string) {
  return new AxiosError(
    "Request failed",
    "ERR_BAD_RESPONSE",
    undefined,
    undefined,
    {
      status: 503,
      statusText: "Unavailable",
      headers: new AxiosHeaders(),
      config: { headers: new AxiosHeaders() },
      data: { detail },
    },
  );
}
async function router() {
  const value = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/:pathMatch(.*)*", component: { template: "<div/>" } }],
  });
  await value.push("/account");
  await value.isReady();
  return value;
}
describe("account user-visible behavior", () => {
  it("clears the submitted password and completes administrator login immediately", async () => {
    const store = useSessionStore();
    const login = vi.spyOn(store, "login").mockImplementation(async () => {
      store.profile = profileFixture({
        role: "admin",
      });
      return store.profile;
    });
    const wrapper = mount(UserLogin, {
      global: { plugins: [pinia, await router()] },
    });
    await wrapper.get('input[autocomplete="username"]').setValue("admin");
    await wrapper.get('input[type="password"]').setValue("one-use-password");
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(login).toHaveBeenCalledWith("admin", "one-use-password");
    expect(wrapper.find('input[type="password"]').exists()).toBe(false);
    expect(wrapper.text()).toContain("Your account");
    expect(wrapper.emitted("close")).toHaveLength(1);
  });
  it("does not close the login card after a failed logout", async () => {
    const store = useSessionStore();
    store.profile = profileFixture();
    vi.spyOn(store, "logout").mockRejectedValue(new Error("offline"));
    const wrapper = mount(UserLogin, {
      global: { plugins: [pinia, await router()] },
    });
    const button = wrapper
      .findAll("button")
      .find((value) => value.text() === "Sign out");
    expect(button).toBeDefined();
    await button?.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("could not be completed");
    expect(wrapper.emitted("close")).toBeUndefined();
  });
  it("keeps reviewed invitation contact and dialog on delivery failure, then permits retry", async () => {
    const store = useSessionStore();
    store.profile = profileFixture({ role: "admin" });
    const user: AdminUser = {
      id: 42,
      username: "invited",
      display_name: "Invited",
      role: "curator",
      proposedRole: "curator",
      email: "reviewed@example.org",
      invitation_email_id: 73,
      status: "unclaimed",
      active: false,
      can_activate: false,
      can_invite: true,
    };
    vi.spyOn(adminApi, "users").mockResolvedValue([user]);
    vi.spyOn(adminApi, "requests").mockResolvedValue([]);
    const invite = vi
      .spyOn(adminApi, "invite")
      .mockRejectedValueOnce(failure("Invitation delivery unavailable; retry"))
      .mockResolvedValueOnce();
    const wrapper = mount(AdminSettings, {
      attachTo: document.body,
      global: {
        plugins: [pinia],
        stubs: {
          VDialog: defineComponent({
            props: { modelValue: Boolean },
            setup(props, { slots }) {
              return () =>
                props.modelValue
                  ? h("div", { role: "dialog" }, slots.default?.())
                  : null;
            },
          }),
        },
      },
    });
    await flushPromises();
    await wrapper
      .findAll("button")
      .find((value) => value.text() === "Invite")
      ?.trigger("click");
    await flushPromises();
    await wrapper
      .findAll("button")
      .find((value) => value.text() === "Send invitation")
      ?.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Invitation delivery unavailable; retry");
    expect(wrapper.text()).toContain("reviewed@example.org");
    await wrapper
      .findAll("button")
      .find((value) => value.text() === "Send invitation")
      ?.trigger("click");
    await flushPromises();
    expect(invite).toHaveBeenLastCalledWith(user);
    expect(wrapper.text()).toContain("Invitation sent to reviewed@example.org");
  });
});
