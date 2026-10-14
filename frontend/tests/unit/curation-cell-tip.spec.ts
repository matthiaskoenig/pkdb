import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { effectScope, type EffectScope } from "vue";
import { TIP_DELAY, TIP_LINGER, useCellTip, type CellTip } from "../../src/study-views/composables/useCellTip";

/** The `matches` of jsdom, which guesses `:focus-visible` from the events before a focus. */
const MATCHES = Element.prototype.matches;

/** Whether a focus shows its ring, as after a key (`true`) or after a click (`false`). */
function focusRing(shown: boolean): void {
  vi.spyOn(Element.prototype, "matches").mockImplementation(function (this: Element, selector: string): boolean {
    return selector === ":focus-visible" ? shown && this === document.activeElement : MATCHES.call(this, selector);
  });
}

let scope: EffectScope;
let tip: CellTip;
let grid: HTMLElement | undefined;

/**
 * A row with a line cell whose button has the tip `2:line`, two cells with a tip, `2:1` (with text
 * in a span) and `3:1`, and a cell without one. The cells are focusable here only to test focus.
 */
function cells() {
  grid = document.createElement("div");
  grid.innerHTML =
    '<table><tr><th data-tip="2:line"><button type="button">2</button></th><td data-tip="2:1" tabindex="0"><span>2.4</span></td><td data-tip="3:1" tabindex="0">3.1</td><td tabindex="0">1.2</td></tr></table>';
  document.body.append(grid);
  grid.addEventListener("mouseover", tip.over);
  grid.addEventListener("mouseout", tip.out);
  grid.addEventListener("focusin", tip.focusIn);
  grid.addEventListener("focusout", tip.focusOut);
  const [first, second, plain] = [...grid.querySelectorAll<HTMLElement>("td")] as [HTMLElement, HTMLElement, HTMLElement];
  return { first, second, plain, inner: first.querySelector("span")!, lineButton: grid.querySelector("button")! };
}

function enter(element: Element, from: Element | null = null): void {
  element.dispatchEvent(new MouseEvent("mouseover", { bubbles: true, relatedTarget: from }));
}

function leave(element: Element, to: Element | null = null): void {
  element.dispatchEvent(new MouseEvent("mouseout", { bubbles: true, relatedTarget: to }));
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  scope = effectScope();
  tip = scope.run(() => useCellTip())!;
});

afterEach(() => {
  scope.stop();
  grid?.remove();
  grid = undefined;
  vi.useRealTimers();
});

describe("useCellTip", () => {
  it("shows the tip of a cell once the pointer rested on it for 300 ms", () => {
    const { first } = cells();
    enter(first);
    vi.advanceTimersByTime(TIP_DELAY - 1);
    expect(tip.cell.value).toBeNull();
    vi.advanceTimersByTime(1);
    expect(tip.cell.value).toBe(first);
    expect(tip.key.value).toBe("2:1");
  });

  it("shows nothing for a cell that the pointer leaves before, or for a cell without a tip", () => {
    const { first, plain } = cells();
    enter(first);
    vi.advanceTimersByTime(TIP_DELAY - 100);
    leave(first, plain);
    enter(plain, first);
    vi.advanceTimersByTime(1000);
    expect(tip.cell.value).toBeNull();
  });

  it("moves an open tip to the next cell with a tip once the pointer rested there for 150 ms", () => {
    const { first, second } = cells();
    enter(first);
    vi.advanceTimersByTime(TIP_DELAY);
    leave(first, second);
    enter(second, first);
    vi.advanceTimersByTime(TIP_LINGER - 1);
    expect(tip.cell.value).toBe(first);
    vi.advanceTimersByTime(1);
    expect(tip.cell.value).toBe(second);
    expect(tip.key.value).toBe("3:1");
  });

  it("keeps the tip at its cell while the pointer crosses another cell with a tip on its way onto the tooltip", () => {
    const { first, second } = cells();
    const tooltip = document.createElement("div");
    enter(first);
    vi.advanceTimersByTime(TIP_DELAY);
    // The gap below the cell lies in the next row, whose cell has a tip too.
    leave(first, second);
    enter(second, first);
    vi.advanceTimersByTime(TIP_LINGER - 1);
    leave(second, tooltip);
    tip.enterTip();
    vi.advanceTimersByTime(1000);
    expect(tip.cell.value).toBe(first);
    expect(tip.key.value).toBe("2:1");
  });

  it("keeps the tip at its cell when the pointer comes back from another cell with a tip before the tip moved", () => {
    const { first, second } = cells();
    enter(first);
    vi.advanceTimersByTime(TIP_DELAY);
    leave(first, second);
    enter(second, first);
    vi.advanceTimersByTime(TIP_LINGER - 1);
    leave(second, first);
    enter(first, second);
    vi.advanceTimersByTime(1000);
    expect(tip.cell.value).toBe(first);
  });

  it("hides the tip 150 ms after the pointer crossed another cell with a tip to a cell without one", () => {
    const { first, second, plain } = cells();
    enter(first);
    vi.advanceTimersByTime(TIP_DELAY);
    leave(first, second);
    enter(second, first);
    vi.advanceTimersByTime(TIP_LINGER - 1);
    leave(second, plain);
    enter(plain, second);
    vi.advanceTimersByTime(TIP_LINGER - 1);
    expect(tip.cell.value).toBe(first);
    vi.advanceTimersByTime(1);
    expect(tip.cell.value).toBeNull();
  });

  it("moves a tip of the focus at once when the keyboard moves on, also while the pointer leaves a tip", () => {
    focusRing(true);
    const { first, second } = cells();
    enter(first);
    vi.advanceTimersByTime(TIP_DELAY);
    leave(first, second);
    enter(second, first);
    second.focus();
    expect(tip.cell.value).toBe(second);
    expect(tip.key.value).toBe("3:1");
    vi.advanceTimersByTime(1000);
    expect(tip.cell.value).toBe(second);
  });

  it("keeps the tip while the pointer moves within its cell and onto the tooltip, and hides it 150 ms after the pointer left both", () => {
    const { first, inner } = cells();
    const tooltip = document.createElement("div");
    enter(first);
    vi.advanceTimersByTime(TIP_DELAY);
    leave(first, inner);
    enter(inner, first);
    vi.advanceTimersByTime(1000);
    expect(tip.cell.value).toBe(first);
    leave(inner, tooltip);
    vi.advanceTimersByTime(TIP_LINGER - 1);
    tip.enterTip();
    vi.advanceTimersByTime(1000);
    expect(tip.cell.value).toBe(first);
    tip.leaveTip();
    vi.advanceTimersByTime(TIP_LINGER - 1);
    expect(tip.cell.value).toBe(first);
    vi.advanceTimersByTime(1);
    expect(tip.cell.value).toBeNull();
  });

  it("shows the tip of a cell that the keyboard focuses at once, and hides it when the focus leaves the cell", () => {
    focusRing(true);
    const { first, second, plain } = cells();
    first.focus();
    expect(tip.key.value).toBe("2:1");
    second.focus();
    expect(tip.key.value).toBe("3:1");
    plain.focus();
    expect(tip.cell.value).toBeNull();
  });

  it("shows the tip of the cell around a focused button, such as the line button of a row", () => {
    focusRing(true);
    const { lineButton, first } = cells();
    lineButton.focus();
    expect(tip.key.value).toBe("2:line");
    first.focus();
    expect(tip.key.value).toBe("2:1");
  });

  it("keeps a tip of the focus while the focus moves within its cell", () => {
    focusRing(true);
    const { lineButton } = cells();
    const line = lineButton.closest("th")!;
    line.tabIndex = -1;
    lineButton.focus();
    expect(tip.cell.value).toBe(line);
    line.focus();
    expect(document.activeElement).toBe(line);
    expect(tip.cell.value).toBe(line);
    expect(tip.key.value).toBe("2:line");
  });

  it("shows no tip for a focus without a focus ring, as of a click or of a script after a click", () => {
    focusRing(false);
    const { first } = cells();
    first.focus();
    expect(tip.cell.value).toBeNull();
  });

  it("keeps a tip of the focus when the pointer leaves its cell", () => {
    focusRing(true);
    const { first, plain } = cells();
    first.focus();
    leave(first, plain);
    vi.advanceTimersByTime(1000);
    expect(tip.cell.value).toBe(first);
  });

  it("hides the tip on Escape, wherever the focus is", () => {
    const { first } = cells();
    enter(first);
    vi.advanceTimersByTime(TIP_DELAY);
    document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    expect(tip.cell.value).toBeNull();
  });

  it("shows no tip again at a cell whose tip Escape hid until the pointer left the cell", () => {
    const { first, inner, plain } = cells();
    enter(first);
    vi.advanceTimersByTime(TIP_DELAY);
    document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    leave(first, inner);
    enter(inner, first);
    vi.advanceTimersByTime(1000);
    expect(tip.cell.value).toBeNull();
    leave(inner, plain);
    enter(plain, inner);
    leave(plain, first);
    enter(first, plain);
    vi.advanceTimersByTime(TIP_DELAY);
    expect(tip.cell.value).toBe(first);
  });

  it("shows no tip at a cell that the tip was to move to when Escape hid it, until the pointer left the cell", () => {
    const { first, second, inner } = cells();
    enter(second);
    vi.advanceTimersByTime(TIP_DELAY);
    leave(second, first);
    enter(first, second);
    document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    expect(tip.cell.value).toBeNull();
    leave(first, inner);
    enter(inner, first);
    vi.advanceTimersByTime(1000);
    expect(tip.cell.value).toBeNull();
  });

  it("shows the tip of a cell again after Escape hid it while the pointer rested on the tooltip", () => {
    const { first } = cells();
    const tooltip = document.createElement("div");
    enter(first);
    vi.advanceTimersByTime(TIP_DELAY);
    leave(first, tooltip);
    tip.enterTip();
    document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    expect(tip.cell.value).toBeNull();
    tip.leaveTip();
    enter(first, tooltip);
    vi.advanceTimersByTime(TIP_DELAY);
    expect(tip.cell.value).toBe(first);
  });

  it("shows the tip of a cell whose tip Escape hid when the keyboard focuses it", () => {
    const { lineButton } = cells();
    const line = lineButton.closest("th")!;
    enter(lineButton);
    vi.advanceTimersByTime(TIP_DELAY);
    document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    focusRing(true);
    lineButton.focus();
    expect(tip.cell.value).toBe(line);
  });

  it("hides a tip of the pointer when the cells scroll, and a tip of the focus once its cell left the view", () => {
    const { first } = cells();
    enter(first);
    vi.advanceTimersByTime(TIP_DELAY);
    tip.scrolled(grid!);
    expect(tip.cell.value).toBeNull();

    focusRing(true);
    vi.spyOn(grid!, "getBoundingClientRect").mockReturnValue(new DOMRect(0, 0, 600, 300));
    const at = vi.spyOn(first, "getBoundingClientRect").mockReturnValue(new DOMRect(64, 44, 80, 22));
    first.focus();
    tip.scrolled(grid!);
    expect(tip.cell.value).toBe(first);
    at.mockReturnValue(new DOMRect(64, -30, 80, 22));
    tip.scrolled(grid!);
    expect(tip.cell.value).toBeNull();
  });

  it("keeps a tip of the focus in a view without a layout", () => {
    focusRing(true);
    const { first } = cells();
    first.focus();
    tip.scrolled(grid!);
    expect(tip.cell.value).toBe(first);
  });

  it("stops listening to Escape once the tip hides", () => {
    const add = vi.spyOn(document, "addEventListener");
    const remove = vi.spyOn(document, "removeEventListener");
    const { first, plain } = cells();
    enter(first);
    vi.advanceTimersByTime(TIP_DELAY);
    const listener = add.mock.calls.find(([type]) => type === "keydown")?.[1];
    expect(listener).toBeInstanceOf(Function);
    expect(remove).not.toHaveBeenCalledWith("keydown", listener, true);
    leave(first, plain);
    enter(plain, first);
    vi.advanceTimersByTime(TIP_LINGER);
    expect(tip.cell.value).toBeNull();
    expect(remove).toHaveBeenCalledWith("keydown", listener, true);
  });

  it("hides the tip and stops listening to Escape when its scope ends", () => {
    const remove = vi.spyOn(document, "removeEventListener");
    const { first } = cells();
    enter(first);
    vi.advanceTimersByTime(TIP_DELAY);
    scope.stop();
    expect(tip.cell.value).toBeNull();
    expect(remove).toHaveBeenCalledWith("keydown", expect.any(Function), true);
  });

  it("shows no tip and listens to no key after its scope ended", () => {
    focusRing(true);
    const add = vi.spyOn(document, "addEventListener");
    const { first, second } = cells();
    enter(first);
    scope.stop();
    vi.advanceTimersByTime(TIP_DELAY);
    enter(second, first);
    vi.advanceTimersByTime(TIP_DELAY);
    second.focus();
    expect(tip.cell.value).toBeNull();
    expect(add).not.toHaveBeenCalledWith("keydown", expect.any(Function), true);
  });
});
