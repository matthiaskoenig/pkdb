import { afterEach, expect, it, vi } from "vitest";
import {
  readPosition,
  rememberResultPosition,
  restoreResultPosition,
  takeResultPosition,
} from "../../src/features/details/resultPosition";
afterEach(() => {
  document.body.innerHTML = "";
  window.history.replaceState({}, "");
});
it("restores the originating row focus and scroll only for its route and identity", () => {
  const button = document.createElement("button");
  button.className = "detail-button";
  button.setAttribute("aria-label", "View PKDB00198");
  document.body.append(button);
  button.focus();
  vi.spyOn(window, "scrollY", "get").mockReturnValue(620);
  vi.spyOn(window, "scrollX", "get").mockReturnValue(12);
  window.history.replaceState(
    { back: "/", current: "/data?page=3", position: 2 },
    "",
  );
  rememberResultPosition("/data?page=3", 4);
  expect(window.history.state.back).toBe("/");
  expect(takeResultPosition("/data?page=3", 5)).toBeUndefined();
  expect(takeResultPosition("/data?page=2", 4)).toBeUndefined();
  const position = takeResultPosition("/data?page=3", 4);
  expect(position).toBeDefined();
  button.blur();
  const scroll = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  if (position) restoreResultPosition(position);
  expect(document.activeElement).toBe(button);
  expect(scroll).toHaveBeenCalledWith({
    left: 12,
    top: 620,
    behavior: "instant",
  });
  expect(takeResultPosition("/data?page=3", 4)).toBeUndefined();
});
it("rejects external and malformed origin records", () => {
  expect(
    readPosition({
      path: "https://example.com",
      epoch: 1,
      x: 0,
      y: 0,
      focusLabel: "",
    }),
  ).toBeUndefined();
  expect(
    readPosition({ path: "/data", epoch: 1, x: 0, y: NaN, focusLabel: "" }),
  ).toBeUndefined();
});
