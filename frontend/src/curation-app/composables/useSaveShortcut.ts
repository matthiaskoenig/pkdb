/**
 * The keyboard shortcut of Save on the study page: Ctrl+S, or Cmd+S on macOS. While the page is
 * open, it saves the draft of study.json from any section and any field instead of opening the
 * save dialog of the browser. It does nothing more without unsaved changes, during a save, and
 * while a dialog is open, which answers with its own buttons.
 */
import { onBeforeUnmount, onMounted } from "vue";

/** Whether `event` is Ctrl+S or Cmd+S without Alt and Shift; both work on every system, as Ctrl+F does in the paper. */
export function isSaveShortcut(event: KeyboardEvent): boolean {
  return (event.ctrlKey || event.metaKey) && !event.altKey && !event.shiftKey && event.key.toLowerCase() === "s";
}

/** Whether the browser runs on macOS or iOS, where Cmd takes the place of Ctrl. */
export function isApple(platform: string = navigator.platform): boolean {
  return /Mac|iPhone|iPad|iPod/.test(platform);
}

/** The shortcut as the banner shows it (`label`) and as `aria-keyshortcuts` of Save names it (`keys`). */
export function saveShortcut(platform: string = navigator.platform): { label: string; keys: string } {
  return isApple(platform) ? { label: "⌘S", keys: "Meta+S" } : { label: "Ctrl+S", keys: "Control+S" };
}

/** While the calling component is mounted, Ctrl+S or Cmd+S calls `save` and never opens the save dialog of the browser. */
export function useSaveShortcut(save: () => void): void {
  function onKeydown(event: KeyboardEvent): void {
    if (event.isComposing || !isSaveShortcut(event)) return;
    event.preventDefault();
    // A dialog over the page, such as Leave without saving?, answers with its own buttons.
    if (document.querySelector(".v-dialog.v-overlay--active")) return;
    save();
  }
  // In the capture phase, so that no control that stops the key, such as a select, keeps it from the page.
  onMounted(() => window.addEventListener("keydown", onKeydown, { capture: true }));
  onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown, { capture: true }));
}
