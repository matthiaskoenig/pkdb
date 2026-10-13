import { describe, expect, it } from "vitest";
import { isApple, isSaveShortcut, saveShortcut } from "../../src/curation-app/composables/useSaveShortcut";

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

  it("names Cmd on macOS and iOS and Ctrl elsewhere", () => {
    expect(isApple("MacIntel")).toBe(true);
    expect(isApple("iPad")).toBe(true);
    expect(isApple("Linux x86_64")).toBe(false);
    expect(saveShortcut("MacIntel")).toEqual({ label: "⌘S", keys: "Meta+S" });
    expect(saveShortcut("Win32")).toEqual({ label: "Ctrl+S", keys: "Control+S" });
  });
});
