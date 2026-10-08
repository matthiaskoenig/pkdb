import { ref } from "vue";
import { defineStore } from "pinia";

/**
 * The dialogs of the header, which any page can open: for example the settings after a write
 * that was refused for a missing user.
 */
export const useDialogStore = defineStore("curation-dialogs", () => {
  const settings = ref(false);
  const workspace = ref(false);

  function openSettings(): void {
    settings.value = true;
  }

  function openWorkspace(): void {
    workspace.value = true;
  }

  return { settings, workspace, openSettings, openWorkspace };
});
