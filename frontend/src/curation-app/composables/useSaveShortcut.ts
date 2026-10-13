/**
 * The keyboard shortcut of Save on the study page: Ctrl+S, or Cmd+S on macOS. While the page is
 * open, it saves the draft of study.json from any section and any field instead of opening the
 * save dialog of the browser, with the text typed into a combobox but not yet added. It does
 * nothing more without unsaved changes, during a save, for the repeats of a held key, and while a
 * dialog is open, which answers with its own buttons.
 */
import { nextTick, onBeforeUnmount, onMounted } from "vue";

/**
 * Whether `event` is Ctrl+S or Cmd+S without Alt and Shift; both work on every system, as Ctrl+F
 * does in the paper. S is the letter that the key types, or the S key of the keyboard where the
 * layout types no Latin letter, such as ы on a Russian layout, as browsers do for their shortcuts.
 */
export function isSaveShortcut(event: KeyboardEvent): boolean {
  if (!(event.ctrlKey || event.metaKey) || event.altKey || event.shiftKey) return false;
  return /^[a-z]$/i.test(event.key) ? event.key.toLowerCase() === "s" : event.code === "KeyS";
}

/**
 * The platform of the browser, such as `macOS` or `Windows` from the client hints where the
 * browser has them, else the older `navigator.platform`, such as `MacIntel` or `Win32`.
 */
function platformName(): string {
  const hints = (navigator as Navigator & { userAgentData?: { platform?: string } }).userAgentData;
  return hints?.platform || navigator.platform;
}

/** Whether the browser runs on macOS or iOS, where Cmd takes the place of Ctrl. */
export function isApple(platform: string = platformName()): boolean {
  return /^(mac|iphone|ipad|ipod|ios)/i.test(platform);
}

/** The shortcut as the banner shows it (`label`) and as `aria-keyshortcuts` of Save names it (`keys`). */
export function saveShortcut(platform: string = platformName()): { label: string; keys: string } {
  return isApple(platform) ? { label: "⌘S", keys: "Meta+S" } : { label: "Ctrl+S", keys: "Control+S" };
}

/** Whether a modal dialog is open over the page; Vuetify removes a dialog from the page once it has closed. */
function dialogOpen(): boolean {
  return document.querySelector('[role="dialog"][aria-modal="true"]') !== null;
}

/**
 * The focused input of a combobox, such as Collaborators, with text that is typed into it but not
 * yet added to its list, which a combobox does only on Enter or when it loses the focus; null for
 * any other focus, whose value is in the form already.
 */
export function typedComboboxInput(): HTMLInputElement | null {
  const active = document.activeElement;
  return active instanceof HTMLInputElement && active.value.trim() !== "" && active.closest(".v-combobox") ? active : null;
}

/** Lets the combobox of `input` add the text typed into it: blurs it, and resolves once the form has the text. */
export async function commitTypedText(input: HTMLInputElement): Promise<void> {
  input.blur();
  await nextTick();
}

/**
 * While the calling component is mounted, Ctrl+S or Cmd+S calls `save` and never opens the save
 * dialog of the browser. The text typed into a combobox is added first, and the combobox has the
 * focus again afterwards.
 */
export function useSaveShortcut(save: () => void): void {
  function onKeydown(event: KeyboardEvent): void {
    if (event.isComposing || !isSaveShortcut(event)) return;
    event.preventDefault();
    // A held key saves once; its repeats only keep the save dialog of the browser closed.
    if (event.repeat) return;
    // A dialog over the page, such as Leave without saving?, answers with its own buttons.
    if (dialogOpen()) return;
    const input = typedComboboxInput();
    if (!input) {
      save();
      return;
    }
    void commitTypedText(input).then(() => {
      save();
      if (input.isConnected) input.focus({ preventScroll: true });
    });
  }
  // In the capture phase, so that no control that stops the key, such as a select, keeps it from the page.
  onMounted(() => window.addEventListener("keydown", onKeydown, { capture: true }));
  onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown, { capture: true }));
}
