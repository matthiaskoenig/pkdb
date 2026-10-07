import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createPinia, disposePinia, setActivePinia, type Pinia } from "pinia";
import { ApiError } from "../../src/curation-app/api/client";
import type { Directories } from "../../src/curation-app/api/types";
import WorkspaceDialog from "../../src/curation-app/components/WorkspaceDialog.vue";
import { useOverviewStore } from "../../src/curation-app/stores/overview";
import { snapshot } from "../unit/curation-fixtures";
import { button, buttons, click, field, loadSnapshot, page, setViewport } from "./curation-dom";

enableAutoUnmount(afterEach);

let pinia: Pinia;

/** The folders of `path`: `/work` holds a repository, a study and a plain folder. */
function directories(path = "/work"): Directories {
  return {
    path,
    parent: path === "/" ? null : "/",
    home: "/home/curator",
    kind: "folder",
    truncated: false,
    entries:
      path === "/work"
        ? [
            { name: "pkdb_data", path: "/work/pkdb_data", kind: "repository" },
            { name: "Example", path: "/work/Example", kind: "study" },
            { name: "notes", path: "/work/notes", kind: "folder" },
          ]
        : [],
  };
}

async function openDialog() {
  const wrapper = mount(WorkspaceDialog, {
    attachTo: document.body,
    props: { modelValue: true },
    global: { plugins: [pinia] },
  });
  await flushPromises();
  return wrapper;
}

function dialog() {
  return page().get('[role="dialog"]');
}

beforeEach(async () => {
  setViewport();
  pinia = createPinia();
  setActivePinia(pinia);
  await loadSnapshot(
    snapshot({
      workspace: "/work",
      recent_workspaces: [
        { path: "/work", exists: true },
        { path: "/old/pkdb_data", exists: true },
        { path: "/gone/studies", exists: false },
      ],
    }),
  );
});

afterEach(() => {
  disposePinia(pinia);
});

describe("WorkspaceDialog", () => {
  it("lists the folders of the workspace with their kind", async () => {
    const list = vi.spyOn(useOverviewStore(), "listDirectories").mockResolvedValue(directories());
    await openDialog();
    expect(list).toHaveBeenCalledWith("/work");
    const rows = dialog().findAll(".folder-row");
    expect(rows.map((row) => row.text())).toEqual([
      expect.stringMatching(/pkdb_data.*repository/),
      expect.stringMatching(/Example.*study/),
      expect.stringMatching(/notes.*folder/),
    ]);
    expect(field("Folder on this computer").element.value).toBe("/work");
  });

  it("shows the folder with line breaks only after its separators", async () => {
    vi.spyOn(useOverviewStore(), "listDirectories").mockResolvedValue(directories("/work/a-long-name/pkdb_data"));
    await openDialog();
    const path = dialog().get(".folder-current .folder-path-text");
    expect(path.findAll(".folder-path-segment").map((segment) => segment.text())).toEqual([
      "/",
      "work/",
      "a-long-name/",
      "pkdb_data",
    ]);
    expect(path.findAll("wbr")).toHaveLength(3);
    expect(path.text()).toBe("/work/a-long-name/pkdb_data");
  });

  it("tells what the folder holds in its own element after the path", async () => {
    vi.spyOn(useOverviewStore(), "listDirectories").mockResolvedValue(directories());
    await openDialog();
    const current = dialog().get(".folder-current");
    expect(current.get(".folder-summary").text()).toBe("3 subfolders");
    expect(current.get(".folder-path-text").text()).toBe("/work");
  });

  it("browses into a folder, up and home", async () => {
    const list = vi
      .spyOn(useOverviewStore(), "listDirectories")
      .mockImplementation(async (path) => directories(path ?? "/work"));
    await openDialog();
    await click("pkdb_data");
    expect(list).toHaveBeenLastCalledWith("/work/pkdb_data");
    expect(field("Folder on this computer").element.value).toBe("/work/pkdb_data");
    await click("Up");
    expect(list).toHaveBeenLastCalledWith("/");
    expect(button("Up").attributes("disabled")).toBeDefined();
    await click("Home");
    expect(list).toHaveBeenLastCalledWith("/home/curator");
  });

  it("goes to a typed folder", async () => {
    const list = vi
      .spyOn(useOverviewStore(), "listDirectories")
      .mockImplementation(async (path) => directories(path ?? "/work"));
    await openDialog();
    await field("Folder on this computer").setValue("/data/studies");
    await click("Go");
    expect(list).toHaveBeenLastCalledWith("/data/studies");
  });

  it("opens the shown folder as the workspace and closes", async () => {
    vi.spyOn(useOverviewStore(), "listDirectories").mockResolvedValue(directories());
    const select = vi.spyOn(useOverviewStore(), "selectWorkspace").mockResolvedValue(snapshot());
    const wrapper = await openDialog();
    await click("Open this folder");
    expect(select).toHaveBeenCalledWith("/work");
    expect(wrapper.emitted("update:modelValue")).toEqual([[false]]);
  });

  it("opens a listed folder as the workspace", async () => {
    vi.spyOn(useOverviewStore(), "listDirectories").mockResolvedValue(directories());
    const select = vi.spyOn(useOverviewStore(), "selectWorkspace").mockResolvedValue(snapshot());
    await openDialog();
    await click("Open pkdb_data as workspace");
    expect(select).toHaveBeenCalledWith("/work/pkdb_data");
  });

  it("shows a recent workspace that no longer exists as unavailable and removes it", async () => {
    vi.spyOn(useOverviewStore(), "listDirectories").mockResolvedValue(directories());
    const forget = vi.spyOn(useOverviewStore(), "forgetWorkspace").mockResolvedValue(snapshot());
    await openDialog();
    // Each recent workspace shows its folder name, then its parent folder.
    const rows = dialog().findAll(".recent-item");
    expect(rows.map((row) => [row.get(".recent-name").text(), row.get(".recent-parent").text()])).toEqual([
      ["pkdb_data", "/old"],
      ["studies", "/gone"],
    ]);
    expect(rows[1]?.text()).toContain("Unavailable");
    // The current workspace is not listed again.
    expect(buttons("Open work in /")).toHaveLength(0);
    expect(button("Open studies in /gone").attributes("disabled")).toBeDefined();
    expect(button("Open pkdb_data in /old").attributes("disabled")).toBeUndefined();
    await click("Remove /gone/studies from recent workspaces");
    expect(forget).toHaveBeenCalledWith("/gone/studies");
  });

  it("shows the message of a refused folder inline", async () => {
    vi.spyOn(useOverviewStore(), "listDirectories").mockImplementation(async (path) => {
      if (path === "/nope") throw new ApiError(400, { error: "Folder does not exist: /nope" });
      return directories(path ?? "/work");
    });
    const select = vi
      .spyOn(useOverviewStore(), "selectWorkspace")
      .mockRejectedValue(new ApiError(400, { error: "Application state must be outside the selected source workspace" }));
    const wrapper = await openDialog();
    await field("Folder on this computer").setValue("/nope");
    await click("Go");
    expect(dialog().get(".v-alert").text()).toContain("Folder does not exist: /nope");
    // The listing of the last folder stays.
    expect(dialog().findAll(".folder-row")).toHaveLength(3);
    await click("Open this folder");
    expect(select).toHaveBeenCalledWith("/work");
    expect(dialog().get(".v-alert").text()).toContain(
      "Application state must be outside the selected source workspace",
    );
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
  });

  it("falls back to the home folder when the workspace cannot be listed", async () => {
    const list = vi.spyOn(useOverviewStore(), "listDirectories").mockImplementation(async (path) => {
      if (path === "/work") throw new ApiError(400, { error: "Permission denied: /work" });
      return directories("/home/curator");
    });
    await openDialog();
    expect(list).toHaveBeenLastCalledWith();
    expect(field("Folder on this computer").element.value).toBe("/home/curator");
    expect(dialog().get(".v-alert").text()).toContain("Permission denied: /work");
  });

  it("ignores a listing that arrives after a newer one", async () => {
    let answer: (value: Directories) => void = () => undefined;
    vi.spyOn(useOverviewStore(), "listDirectories").mockImplementation((path) => {
      if (path === "/slow") return new Promise((resolve) => (answer = resolve));
      return Promise.resolve(directories(path ?? "/work"));
    });
    await openDialog();
    await field("Folder on this computer").setValue("/slow");
    await click("Go");
    await click("Home");
    answer(directories("/slow"));
    await flushPromises();
    expect(field("Folder on this computer").element.value).toBe("/home/curator");
  });
});
