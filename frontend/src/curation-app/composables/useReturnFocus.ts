import { nextTick, watch, type Ref } from "vue";

/** An element to focus, found when it is needed; nothing when there is none. */
export type FocusTarget = () => HTMLElement | null | undefined;

/**
 * The heading of the section of the study page, which takes the focus after a dialog of a section
 * when the control that opened it is gone.
 */
export const sectionHeading: FocusTarget = () => document.querySelector<HTMLElement>(".study-section-heading");

/**
 * The opener and, when it is an item of a menu, the controls that opened the menus around it: a
 * menu closes when its item opens a dialog, while its activator stays. Vuetify links a menu to its
 * activator with `aria-controls`.
 */
function openers(element: HTMLElement): HTMLElement[] {
  const chain = [element];
  let menu = element.closest<HTMLElement>(".v-menu[id]");
  while (menu) {
    const id = menu.id;
    const activator = [...document.querySelectorAll<HTMLElement>("[aria-controls]")].find(
      (candidate) => candidate.getAttribute("aria-controls") === id,
    );
    if (!activator || chain.includes(activator)) break;
    chain.push(activator);
    menu = activator.closest<HTMLElement>(".v-menu[id]");
  }
  return chain;
}

/** Whether `element` or an element around it is hidden, such as the content of a closed menu. */
function hidden(element: HTMLElement): boolean {
  for (let node: HTMLElement | null = element; node; node = node.parentElement)
    if (getComputedStyle(node).display === "none") return true;
  return false;
}

/** Whether `element` took the focus. */
function focused(element: HTMLElement | null | undefined): boolean {
  if (!element?.isConnected || element.matches(":disabled") || hidden(element)) return false;
  element.focus();
  return document.activeElement === element;
}

/**
 * Whether the focus has no place outside a dialog: on the body, or still in the content of the
 * closing dialog, which stays in the page during its transition.
 */
function lost(): boolean {
  const active = document.activeElement;
  return active === null || active === document.body || active.closest(".v-overlay__content") !== null;
}

/**
 * Return the keyboard focus to the control that opened a dialog when the dialog closes (WCAG
 * 2.4.3). Vuetify's VDialog returns it only to an activator, and the dialogs of the app open
 * through `v-model`. The element that has the focus when `open` becomes true is the opener. When
 * the dialog closes and the opener is gone or disabled, the control that opened its menu takes the
 * focus, else `fallback`. When something outside the dialog took the focus meanwhile, the focus
 * stays there.
 */
export function useReturnFocus(open: Readonly<Ref<boolean>>, fallback?: FocusTarget): void {
  let opened = false;
  let targets: HTMLElement[] = [];
  watch(
    open,
    async (value) => {
      if (value) {
        opened = true;
        // Before the dialog moves the focus into its content. A click on a button does not
        // focus it in every browser, which leaves the focus on the body: no opener.
        const active = document.activeElement;
        targets = active instanceof HTMLElement && active !== document.body ? openers(active) : [];
        return;
      }
      if (!opened) return;
      opened = false;
      const candidates = targets;
      targets = [];
      // After the render that closes the dialog: an opener that went with it is gone by then.
      await nextTick();
      if (lost() && !candidates.some(focused)) focused(fallback?.());
    },
    { flush: "sync", immediate: true },
  );
}
