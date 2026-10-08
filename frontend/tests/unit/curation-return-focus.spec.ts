import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { effectScope, nextTick, ref, type EffectScope } from "vue";
import { useReturnFocus } from "../../src/curation-app/composables/useReturnFocus";

let scope: EffectScope;

/** A button in the page, and the content of a dialog with a field, as Vuetify renders it. */
function page() {
  document.body.innerHTML = `
    <button id="opener">Open</button>
    <button id="fallback">Fallback</button>
    <button id="other">Other</button>
    <div class="v-overlay__content"><input id="field" /></div>
  `;
  const get = (id: string) => document.getElementById(id) as HTMLElement;
  return { opener: get("opener"), fallback: get("fallback"), other: get("other"), field: get("field") };
}

/** Open the dialog from the focused `opener`, focus its field, and close it. */
async function openAndClose(open: { value: boolean }, opener: HTMLElement, field: HTMLElement, between = () => {}) {
  opener.focus();
  open.value = true;
  field.focus();
  between();
  open.value = false;
  await nextTick();
}

beforeEach(() => {
  scope = effectScope();
});

afterEach(() => {
  scope.stop();
  document.body.innerHTML = "";
});

describe("useReturnFocus", () => {
  it("returns the focus to the control that opened the dialog", async () => {
    const elements = page();
    const open = ref(false);
    scope.run(() => useReturnFocus(open, () => elements.fallback));
    await openAndClose(open, elements.opener, elements.field);
    expect(document.activeElement).toBe(elements.opener);
  });

  it("focuses the fallback when the opener is gone", async () => {
    const elements = page();
    const open = ref(false);
    scope.run(() => useReturnFocus(open, () => elements.fallback));
    await openAndClose(open, elements.opener, elements.field, () => elements.opener.remove());
    expect(document.activeElement).toBe(elements.fallback);
  });

  it("focuses the fallback when the opener is disabled", async () => {
    const elements = page();
    const open = ref(false);
    scope.run(() => useReturnFocus(open, () => elements.fallback));
    await openAndClose(open, elements.opener, elements.field, () => elements.opener.setAttribute("disabled", ""));
    expect(document.activeElement).toBe(elements.fallback);
  });

  it("focuses the fallback when no control had the focus, as after a click in Safari", async () => {
    const elements = page();
    const open = ref(false);
    scope.run(() => useReturnFocus(open, () => elements.fallback));
    open.value = true;
    elements.field.focus();
    open.value = false;
    await nextTick();
    expect(document.activeElement).toBe(elements.fallback);
  });

  it("leaves the focus where something outside the dialog put it", async () => {
    const elements = page();
    const open = ref(false);
    scope.run(() => useReturnFocus(open, () => elements.fallback));
    await openAndClose(open, elements.opener, elements.field, () => elements.other.focus());
    expect(document.activeElement).toBe(elements.other);
  });

  it("moves no focus before the dialog was open", async () => {
    const elements = page();
    elements.other.focus();
    scope.run(() => useReturnFocus(ref(false), () => elements.fallback));
    await nextTick();
    expect(document.activeElement).toBe(elements.other);
  });

  it("keeps the focus in the dialog's content when there is no fallback and the opener is gone", async () => {
    const elements = page();
    const open = ref(false);
    scope.run(() => useReturnFocus(open));
    await openAndClose(open, elements.opener, elements.field, () => elements.opener.remove());
    expect(document.activeElement).toBe(elements.field);
  });
});
