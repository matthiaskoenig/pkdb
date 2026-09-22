import { beforeEach, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import AttachmentCard from "../../src/features/details/components/AttachmentCard.vue";
import { fileUrl } from "../../src/features/exports/useFileDownload";
import { useSessionStore } from "../../src/stores/session";
const mocks = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("../../src/api/client", () => ({
  api: { get: mocks.get },
  apiBase: "",
  errorMessage: (error: unknown) =>
    error instanceof Error ? error.message : "Request failed",
  clearCsrf: vi.fn(),
  cleanLegacyCredentials: vi.fn(),
  onUnauthorized: () => () => {},
}));
beforeEach(() => {
  setActivePinia(createPinia());
  mocks.get.mockReset();
  URL.createObjectURL = vi.fn(() => "blob:preview");
  URL.revokeObjectURL = vi.fn();
});
it("restricts attachment requests to media on the API origin", () => {
  expect(() => fileUrl("https://untrusted.example/media/file")).toThrow(
    "authorized",
  );
  expect(() => fileUrl("/api/v1/me")).toThrow("authorized");
  expect(fileUrl("/media/a/file.png")).toContain("/media/a/file.png");
});
it("revokes a private preview on identity change and unmount", async () => {
  mocks.get.mockResolvedValue({
    data: new Blob(["image"], { type: "image/png" }),
  });
  const wrapper = mount(AttachmentCard, {
    props: { path: "/media/a/image.png", name: "image.png" },
  });
  await wrapper.findAll("button")[1]?.trigger("click");
  await flushPromises();
  expect(wrapper.find("img").attributes("src")).toBe("blob:preview");
  useSessionStore().invalidate();
  await flushPromises();
  expect(wrapper.find("img").exists()).toBe(false);
  expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:preview");
  wrapper.unmount();
});
it("does not install a preview whose response arrives after cancellation", async () => {
  let finish: ((value: { data: Blob }) => void) | undefined;
  mocks.get.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const wrapper = mount(AttachmentCard, {
    props: { path: "/media/a/image.png", name: "image.png" },
  });
  await wrapper.findAll("button")[1]?.trigger("click");
  await wrapper
    .findAll("button")
    .find((button) => button.text() === "Cancel")
    ?.trigger("click");
  finish?.({ data: new Blob(["image"], { type: "image/png" }) });
  await flushPromises();
  expect(URL.createObjectURL).not.toHaveBeenCalled();
  wrapper.unmount();
});
