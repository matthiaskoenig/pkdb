import { ref } from "vue";
import { defineStore } from "pinia";

/**
 * The dialogs of the header, which any page can open: for example the settings after a write
 * that was refused for a missing user.
 */
export const useDialogStore = defineStore("curation-dialogs", () => {
  const settings = ref(false);
  const workspace = ref(false);
  /** The confirmation of upload on save, which the On save menu of the header opens. */
  const uploadOnSave = ref(false);

  function openSettings(): void {
    settings.value = true;
  }

  function openWorkspace(): void {
    workspace.value = true;
  }

  function openUploadOnSave(): void {
    uploadOnSave.value = true;
  }

  return { settings, workspace, uploadOnSave, openSettings, openWorkspace, openUploadOnSave };
});
