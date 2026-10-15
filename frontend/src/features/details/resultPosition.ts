import type { RouteLocationRaw, Router } from "vue-router";
import { isRecord } from "./types";

export interface ResultPosition {
  path: string;
  epoch: number;
  x: number;
  y: number;
  focusLabel: string;
}
const positionKey = "pkdbResultPosition";
export const studyOriginKey = "pkdbStudyOrigin";

export function readPosition(value: unknown): ResultPosition | undefined {
  if (
    !isRecord(value) ||
    typeof value.path !== "string" ||
    !(value.path === "/data" || value.path.startsWith("/data?")) ||
    typeof value.epoch !== "number" ||
    !Number.isInteger(value.epoch) ||
    typeof value.x !== "number" ||
    !Number.isFinite(value.x) ||
    typeof value.y !== "number" ||
    !Number.isFinite(value.y) ||
    typeof value.focusLabel !== "string"
  )
    return;
  return {
    path: value.path,
    epoch: value.epoch,
    x: value.x,
    y: value.y,
    focusLabel: value.focusLabel,
  };
}

export function rememberResultPosition(
  path: string,
  epoch: number,
): ResultPosition {
  const active = document.activeElement;
  const position = {
    path,
    epoch,
    x: window.scrollX,
    y: window.scrollY,
    focusLabel:
      active instanceof HTMLElement
        ? (active.getAttribute("aria-label") ?? "")
        : "",
  };
  const state: unknown = window.history.state;
  window.history.replaceState(
    { ...(isRecord(state) ? state : {}), [positionKey]: position },
    "",
  );
  return position;
}

export function takeResultPosition(
  path: string,
  epoch: number,
): ResultPosition | undefined {
  const state: unknown = window.history.state;
  if (!isRecord(state)) return;
  const value = readPosition(state[positionKey]);
  if (!value || value.path !== path || value.epoch !== epoch) return;
  const next = { ...state };
  delete next[positionKey];
  window.history.replaceState(next, "");
  return value;
}

export function studyOrigin(epoch: number): ResultPosition | undefined {
  const state: unknown = window.history.state;
  const value = isRecord(state)
    ? readPosition(state[studyOriginKey])
    : undefined;
  return value?.epoch === epoch ? value : undefined;
}

/**
 * Go back to the data search that opened a study, where the reader left it: back in the history
 * when the previous entry is that search, to its address otherwise, and to `fallback` when no
 * search of this session opened the study.
 */
export function returnToSearch(
  router: Router,
  epoch: number,
  fallback: RouteLocationRaw,
): void {
  const origin = studyOrigin(epoch);
  const previous: unknown = window.history.state;
  if (origin && isRecord(previous) && previous.back === origin.path)
    router.back();
  else if (origin) void router.push(origin.path);
  else void router.push(fallback);
}

export function restoreResultPosition(position: ResultPosition): void {
  const buttons = document.querySelectorAll<HTMLElement>(
    "button.detail-button",
  );
  const trigger = Array.from(buttons).find(
    (button) => button.getAttribute("aria-label") === position.focusLabel,
  );
  trigger?.focus({ preventScroll: true });
  window.scrollTo({ left: position.x, top: position.y, behavior: "instant" });
}
