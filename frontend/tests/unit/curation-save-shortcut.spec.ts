import { afterEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { defineComponent, ref, watch } from "vue";
import { isApple, isSaveShortcut, saveShortcut, useSaveShortcut } from "../../src/curation-app/composables/useSaveShortcut";

enableAutoUnmount(afterEach);

/** A keydown of S with `init`. */
function key(init: KeyboardEventInit): KeyboardEvent {
  return new KeyboardEvent("keydown", { key: "s", ...init });
}

describe("the save shortcut", () => {
  it("is Ctrl+S or Cmd+S, also with Caps Lock, and not with Alt or Shift", () => {
    expect(isSaveShortcut(key({ ctrlKey: true }))).toBe(true);
    expect(isSaveShortcut(key({ metaKey: true }))).toBe(true);
    expect(isSaveShortcut(key({ ctrlKey: true, key: "S" }))).toBe(true);
    expect(isSaveShortcut(key({}))).toBe(false);
    expect(isSaveShortcut(key({ ctrlKey: true, shiftKey: true }))).toBe(false);
    expect(isSaveShortcut(key({ ctrlKey: true, altKey: true }))).toBe(false);
    expect(isSaveShortcut(key({ ctrlKey: true, key: "f" }))).toBe(false);
  });

  it("is the S key of the keyboard where the layout types no Latin letters, and the letter S elsewhere", () => {
    // Russian: the S key types ы, the D key в.
    expect(isSaveShortcut(key({ ctrlKey: true, key: "ы", code: "KeyS" }))).toBe(true);
    expect(isSaveShortcut(key({ ctrlKey: true, key: "Ы", code: "KeyS" }))).toBe(true);
    expect(isSaveShortcut(key({ ctrlKey: true, key: "в", code: "KeyD" }))).toBe(false);
    // Dvorak: the S key types o, which is Ctrl+O; the letter S is on the key of the semicolon.
    expect(isSaveShortcut(key({ ctrlKey: true, key: "o", code: "KeyS" }))).toBe(false);
    expect(isSaveShortcut(key({ ctrlKey: true, key: "s", code: "Semicolon" }))).toBe(true);
  });

  it("names Cmd on macOS and iOS and Ctrl elsewhere", () => {
    expect(isApple("MacIntel")).toBe(true);
    expect(isApple("iPad")).toBe(true);
    expect(isApple("Linux x86_64")).toBe(false);
    // The platforms of the client hints.
    expect(isApple("macOS")).toBe(true);
    expect(isApple("iOS")).toBe(true);
    expect(isApple("Windows")).toBe(false);
    expect(isApple("Chrome OS")).toBe(false);
    expect(saveShortcut("MacIntel")).toEqual({ label: "⌘S", keys: "Meta+S" });
    expect(saveShortcut("Win32")).toEqual({ label: "Ctrl+S", keys: "Control+S" });
  });

  it("reads the platform from the client hints of the browser, else from navigator.platform", () => {
    vi.spyOn(navigator, "platform", "get").mockReturnValue("Win32");
    expect(saveShortcut().label).toBe("Ctrl+S");
    Object.defineProperty(navigator, "userAgentData", { configurable: true, value: { platform: "macOS" } });
    onTestFinished(() => void Reflect.deleteProperty(navigator, "userAgentData"));
    expect(saveShortcut().label).toBe("⌘S");
  });
});

describe("useSaveShortcut", () => {
  /** A component that uses the save shortcut with `save`. */
  function mountShortcut(save: () => void): void {
    mount(defineComponent({ setup: () => useSaveShortcut(save), render: () => null }));
  }

  /** Sends the keydown of Ctrl+S with `init` to the window; whether the default was prevented. */
  function press(init: KeyboardEventInit = {}): boolean {
    const event = new KeyboardEvent("keydown", { key: "s", ctrlKey: true, cancelable: true, ...init });
    window.dispatchEvent(event);
    return event.defaultPrevented;
  }

  it("saves once while the key is held, and keeps the save dialog of the browser closed for every repeat", () => {
    const save = vi.fn();
    mountShortcut(save);
    expect(press()).toBe(true);
    expect(press({ repeat: true })).toBe(true);
    expect(press({ repeat: true })).toBe(true);
    expect(save).toHaveBeenCalledTimes(1);
    expect(press()).toBe(true);
    expect(save).toHaveBeenCalledTimes(2);
  });

  it("lets a focused combobox add the text typed into it before it saves, and gives the focus back", async () => {
    // A combobox that adds its text in a watcher once it loses the focus, as Vuetify's does.
    const added = ref<string[]>([]);
    const focused = ref(true);
    watch(focused, (value) => {
      if (!value && input.value) added.value = [...added.value, input.value];
      if (!value) input.value = "";
    });
    const box = Object.assign(document.createElement("div"), { className: "v-combobox" });
    const input = document.createElement("input");
    box.append(input);
    document.body.append(box);
    onTestFinished(() => box.remove());
    input.addEventListener("focus", () => (focused.value = true));
    input.addEventListener("blur", () => (focused.value = false));
    const save = vi.fn(() => expect(added.value).toEqual(["Jane Doe"]));
    mountShortcut(save);

    input.focus();
    input.value = "Jane Doe";
    expect(press()).toBe(true);
    await vi.waitFor(() => expect(save).toHaveBeenCalledOnce());
    expect(document.activeElement).toBe(input);
    expect(input.value).toBe("");
  });

  it("saves at once from a combobox without typed text and from any other field", () => {
    const save = vi.fn();
    const box = Object.assign(document.createElement("div"), { className: "v-combobox" });
    const input = document.createElement("input");
    const other = document.createElement("input");
    box.append(input);
    document.body.append(box, other);
    onTestFinished(() => (box.remove(), other.remove()));
    mountShortcut(save);
    input.focus();
    press();
    expect(save).toHaveBeenCalledTimes(1);
    other.value = "typed";
    other.focus();
    press();
    expect(save).toHaveBeenCalledTimes(2);
    expect(document.activeElement).toBe(other);
  });
});
