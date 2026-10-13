import { afterEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { defineComponent } from "vue";
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
    expect(saveShortcut("MacIntel")).toEqual({ label: "⌘S", keys: "Meta+S" });
    expect(saveShortcut("Win32")).toEqual({ label: "Ctrl+S", keys: "Control+S" });
  });
});

describe("useSaveShortcut", () => {
  /** Sends the keydown of Ctrl+S with `init` to the window; whether the default was prevented. */
  function press(init: KeyboardEventInit = {}): boolean {
    const event = new KeyboardEvent("keydown", { key: "s", ctrlKey: true, cancelable: true, ...init });
    window.dispatchEvent(event);
    return event.defaultPrevented;
  }

  it("saves once while the key is held, and keeps the save dialog of the browser closed for every repeat", () => {
    const save = vi.fn();
    mount(defineComponent({ setup: () => useSaveShortcut(save), render: () => null }));
    expect(press()).toBe(true);
    expect(press({ repeat: true })).toBe(true);
    expect(press({ repeat: true })).toBe(true);
    expect(save).toHaveBeenCalledTimes(1);
    expect(press()).toBe(true);
    expect(save).toHaveBeenCalledTimes(2);
  });
});
