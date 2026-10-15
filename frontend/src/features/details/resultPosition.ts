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
 * The way back from a study to the data search that opened it: the search and the position of its
 * history entry, which vue-router keeps as `position` in the state of each entry.
 */
export interface StudyReturn {
  origin: ResultPosition;
  position: number;
}
const studyReturnKey = "pkdbStudyReturn";

/**
 * The way back to the search, of this session, from the current history entry: the entry that the
 * search pushed has the origin and follows the search; a later entry of the same study page has
 * what `keepStudyReturn` gave it.
 */
export function studyReturn(epoch: number): StudyReturn | undefined {
  const state: unknown = window.history.state;
  if (!isRecord(state)) return;
  const kept = state[studyReturnKey];
  if (isRecord(kept)) {
    const origin = readPosition(kept.origin);
    return origin?.epoch === epoch && Number.isInteger(kept.position)
      ? { origin, position: Number(kept.position) }
      : undefined;
  }
  const origin = studyOrigin(epoch);
  return origin &&
    state.back === origin.path &&
    typeof state.position === "number"
    ? { origin, position: state.position - 1 }
    : undefined;
}

/**
 * Give the current history entry, which a study page pushed after the one that a search opened,
 * the way back to that search, unless it has a way of its own. vue-router keeps the key when it
 * replaces the entry, but a push starts a state without it.
 */
export function keepStudyReturn(way: StudyReturn): void {
  const state: unknown = window.history.state;
  if (!isRecord(state) || studyReturn(way.origin.epoch)) return;
  window.history.replaceState({ ...state, [studyReturnKey]: way }, "");
}

/**
 * Go back to the data search that opened a study, where the reader left it: back in the history
 * to the entry of that search, which restores its scroll position and focus; to its address when
 * the way back is lost, such as after a reload of another entry; and to `fallback` when no search
 * of this session opened the study.
 */
export function returnToSearch(
  router: Router,
  epoch: number,
  fallback: RouteLocationRaw,
): void {
  const way = studyReturn(epoch);
  const state: unknown = window.history.state;
  const origin = way?.origin ?? studyOrigin(epoch);
  if (
    way &&
    isRecord(state) &&
    typeof state.position === "number" &&
    way.position < state.position
  )
    router.go(way.position - state.position);
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
