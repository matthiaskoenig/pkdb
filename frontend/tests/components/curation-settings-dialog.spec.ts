import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import { ApiError } from "../../src/study-views/errors";
import SettingsDialog from "../../src/curation-app/components/SettingsDialog.vue";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { snapshot } from "../unit/curation-fixtures";
import { button, buttons, click, field, loadSnapshot, page, setViewport } from "./curation-dom";

const FAILED = { request_id: "3f9c2a71", time: "2026-10-12T14:03:11+02:00" };

enableAutoUnmount(afterEach);

let pinia: Pinia;

async function openDialog() {
  const wrapper = mount(SettingsDialog, {
    attachTo: document.body,
    props: { modelValue: true, "onUpdate:modelValue": (value: boolean) => wrapper.setProps({ modelValue: value }) },
    global: { plugins: [pinia] },
  });
  await flushPromises();
  return wrapper;
}

function key() {
  return field("Personal API key");
}

beforeEach(async () => {
  setViewport();
  pinia = createPinia();
  setActivePinia(pinia);
  await loadSnapshot(snapshot({ endpoint: "https://beta.pk-db.com", user: "curator", offline: true }));
});

afterEach(() => {
  disposePinia(pinia);
});

describe("SettingsDialog", () => {
  it("shows the current settings and never an API key", async () => {
    await openDialog();
    expect(field("PK-DB server").element.value).toBe("https://beta.pk-db.com");
    expect(field("PK-DB user").element.value).toBe("curator");
    expect(field("Work offline").element.checked).toBe(true);
    expect(key().element.value).toBe("");
    expect(key().attributes("type")).toBe("password");
    expect(key().attributes("autocomplete")).toBe("new-password");
  });

  it("tells why writes are refused", async () => {
    const reason = "A PK-DB user name is required: set it in Connection settings";
    await loadSnapshot(snapshot({ user: "", author: { user: null, reason } }));
    await openDialog();
    expect(page().get('[role="dialog"] .v-alert').text()).toContain(reason);
  });

  it("submits only the changed user", async () => {
    const configure = vi.spyOn(useOverviewStore(), "configure").mockResolvedValue(snapshot());
    const wrapper = await openDialog();
    await field("PK-DB user").setValue(" other ");
    await click("Save settings");
    expect(configure).toHaveBeenCalledWith({ user: "other" });
    expect(wrapper.emitted("update:modelValue")).toEqual([[false]]);
  });

  it("submits only the changed server and offline mode", async () => {
    const configure = vi.spyOn(useOverviewStore(), "configure").mockResolvedValue(snapshot());
    await openDialog();
    await field("PK-DB server").setValue("https://pk-db.com");
    await field("Work offline").setValue(false);
    await click("Save settings");
    expect(configure).toHaveBeenCalledWith({ endpoint: "https://pk-db.com", offline: false });
  });

  it("sends the API key only when typed and clears it after the submit", async () => {
    const configure = vi.spyOn(useOverviewStore(), "configure").mockResolvedValue(snapshot());
    const wrapper = await openDialog();
    await key().setValue("secret-key");
    await click("Save settings");
    expect(configure).toHaveBeenCalledWith({ api_key: "secret-key" });
    await wrapper.setProps({ modelValue: true });
    await flushPromises();
    expect(key().element.value).toBe("");
  });

  it("sends the typed API key without surrounding spaces", async () => {
    const configure = vi.spyOn(useOverviewStore(), "configure").mockResolvedValue(snapshot());
    await openDialog();
    await key().setValue("  secret-key \n");
    await click("Save settings");
    expect(configure).toHaveBeenCalledWith({ api_key: "secret-key" });
  });

  it("removes a stored API key", async () => {
    await loadSnapshot(snapshot({ authenticated: true }));
    const configure = vi
      .spyOn(useOverviewStore(), "configure")
      .mockImplementation(async () => {
        await loadSnapshot(snapshot({ authenticated: false }));
        return snapshot();
      });
    const wrapper = await openDialog();
    expect(page().get('[role="dialog"]').text()).toContain("A key is set.");
    // The action sits on the hint row of the key field.
    expect(button("Remove key").element.closest(".v-input__details")).not.toBeNull();
    await click("Remove key");
    expect(configure).toHaveBeenCalledWith({ api_key: "" });
    expect(buttons("Remove key")).toHaveLength(0);
    expect(page().get('[role="dialog"]').text()).toContain("No key is set.");
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
  });

  it("offers Remove key only when a key is set", async () => {
    await openDialog();
    expect(buttons("Remove key")).toHaveLength(0);
  });

  it("shows why the key could not be removed", async () => {
    await loadSnapshot(snapshot({ authenticated: true }));
    vi.spyOn(useOverviewStore(), "configure").mockRejectedValue(
      new ApiError(400, { error: "Wait for the running job before changing connection" }),
    );
    await openDialog();
    await click("Remove key");
    expect(page().get('[role="dialog"] .v-alert').text()).toContain("Wait for the running job");
    expect(button("Remove key").exists()).toBe(true);
  });

  it("clears the API key when the submit fails", async () => {
    vi.spyOn(useOverviewStore(), "configure").mockRejectedValue(new ApiError(400, { error: "Refused" }));
    await openDialog();
    await key().setValue("secret-key");
    await click("Save settings");
    expect(key().element.value).toBe("");
  });

  it("closes without a request when nothing changed", async () => {
    const configure = vi.spyOn(useOverviewStore(), "configure").mockResolvedValue(snapshot());
    const wrapper = await openDialog();
    await click("Save settings");
    expect(configure).not.toHaveBeenCalled();
    expect(wrapper.emitted("update:modelValue")).toEqual([[false]]);
  });

  it("clears the API key on Cancel", async () => {
    const configure = vi.spyOn(useOverviewStore(), "configure").mockResolvedValue(snapshot());
    const wrapper = await openDialog();
    await key().setValue("secret-key");
    await click("Cancel");
    expect(wrapper.emitted("update:modelValue")).toEqual([[false]]);
    await wrapper.setProps({ modelValue: true });
    await flushPromises();
    expect(key().element.value).toBe("");
    expect(configure).not.toHaveBeenCalled();
  });

  it("clears the API key when the dialog closes otherwise", async () => {
    const wrapper = await openDialog();
    await key().setValue("secret-key");
    await wrapper.setProps({ modelValue: false });
    await flushPromises();
    await wrapper.setProps({ modelValue: true });
    await flushPromises();
    expect(key().element.value).toBe("");
  });

  it("shows what failed inline, with its details, and stays open", async () => {
    vi.spyOn(useOverviewStore(), "configure").mockRejectedValue(
      new ApiError(400, {
        error: "Could not save the settings.",
        code: "invalid_request",
        detail: "ValueError: Enter an http or https URL",
        action: "Save the settings (POST /local/settings)",
        ...FAILED,
      }),
    );
    const wrapper = await openDialog();
    await field("PK-DB server").setValue("https://pk-db.com/?release=1");
    await click("Save settings");
    const alert = page().get('[role="dialog"] .action-failure');
    expect(alert.get(".action-failure-text").text()).toBe("Could not save the settings.");
    expect(alert.get(".action-failure-detail").text()).toBe("ValueError: Enter an http or https URL");
    expect(alert.get("summary").text()).toBe("Details");
    // It goes with the next attempt and when the dialog opens again: no close button, which would drop the focus.
    expect(alert.find(".v-alert__close").exists()).toBe(false);
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
    expect(field("PK-DB server").element.value).toBe("https://pk-db.com/?release=1");
  });

  it("takes the current settings each time it opens", async () => {
    const wrapper = await openDialog();
    await field("PK-DB user").setValue("draft");
    await wrapper.setProps({ modelValue: false });
    await loadSnapshot(snapshot({ user: "reviewer" }));
    await wrapper.setProps({ modelValue: true });
    await flushPromises();
    expect(field("PK-DB user").element.value).toBe("reviewer");
  });
});
