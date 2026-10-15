import { afterEach, expect, it, vi } from "vitest";
import {
  createMemoryHistory,
  createRouter,
  createWebHistory,
  type Router,
} from "vue-router";
import {
  keepStudyReturn,
  readPosition,
  rememberResultPosition,
  restoreResultPosition,
  returnToSearch,
  studyOriginKey,
  studyReturn,
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
const anyPath = [{ path: "/:path(.*)*", component: { render: () => null } }];

/** Resolves when the next navigation of `router`, such as one through the history, ended. */
function navigation(router: Router): Promise<void> {
  return new Promise((resolve) => {
    const stop = router.afterEach(() => {
      stop();
      resolve();
    });
  });
}

it("returns through the history to the search that opened a study, also from later entries of the study", async () => {
  // The history of the browser, with the state that vue-router keeps in each entry from its start.
  window.history.replaceState(null, "");
  const router = createRouter({ history: createWebHistory(), routes: anyPath });
  await router.push("/data?page=3");
  const origin = rememberResultPosition("/data?page=3", 4);
  await router.push({
    path: "/data/drug/A/metadata",
    state: { [studyOriginKey]: { ...origin } },
  });
  const way = studyReturn(4);
  expect(way).toEqual({ origin, position: window.history.state.position - 1 });
  expect(studyReturn(5)).toBeUndefined();
  await router.replace("/data/drug/A/metadata?file=x");
  expect(studyReturn(4)).toEqual(way);
  // A push starts a state without the way back, which the study page then keeps on it.
  await router.push("/data/drug/A/data");
  expect(studyReturn(4)).toBeUndefined();
  if (way) keepStudyReturn(way);
  await router.push("/data/drug/A/review");
  if (way) keepStudyReturn(way);
  await router.replace("/data/drug/A/review?item=1");
  expect(studyReturn(4)).toEqual(way);
  const entries = window.history.length;
  const back = navigation(router);
  returnToSearch(router, 4, "/data");
  await back;
  expect(router.currentRoute.value.fullPath).toBe("/data?page=3");
  // The entry of the search itself, with the position of its results; no new entry.
  expect(window.history.length).toBe(entries);
  expect(takeResultPosition("/data?page=3", 4)).toEqual(origin);
});

it("goes to the search by its address without the way back, and to the fallback without a search of this session", () => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: anyPath,
  });
  const go = vi.spyOn(router, "go").mockImplementation(() => {});
  const push = vi.spyOn(router, "push").mockResolvedValue(undefined);
  const origin = { path: "/data?page=3", epoch: 4, x: 0, y: 0, focusLabel: "" };
  const fallback = { path: "/data", query: { v: "1" } };
  window.history.replaceState(
    { back: "/", position: 2, [studyOriginKey]: origin },
    "",
  );
  returnToSearch(router, 4, fallback);
  expect(push).toHaveBeenLastCalledWith("/data?page=3");
  returnToSearch(router, 5, fallback);
  expect(push).toHaveBeenLastCalledWith(fallback);
  window.history.replaceState(
    { back: "/data?page=3", position: 2, [studyOriginKey]: origin },
    "",
  );
  returnToSearch(router, 4, fallback);
  expect(go).toHaveBeenCalledWith(-1);
  expect(push).toHaveBeenCalledTimes(2);
});
