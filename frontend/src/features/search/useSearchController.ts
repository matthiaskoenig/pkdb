import { watch, onScopeDispose } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useSearchStore } from "../../stores/search";
import { useSessionStore } from "../../stores/session";
import { decodeLocation, encodeLocation } from "./codec";
import { defaultView } from "./defaults";
import type { ResultView, SearchLocation } from "./model";
const pageNotice =
  "The data changed and this page is no longer available. Returned to page 1.";
export function useSearchController() {
  const route = useRoute(),
    router = useRouter(),
    search = useSearchStore(),
    session = useSessionStore();
  // Consume each marker once. A later Back/Forward to the same URL restores draft.
  const viewNavigations = new Map<string, number>();
  let restoration = 0;
  function queryPath(location: SearchLocation) {
    return router.resolve({ path: route.path, query: encodeLocation(location) })
      .fullPath;
  }
  async function recoverPage(
    location: SearchLocation,
    preserveDraft: boolean,
    own: number,
  ) {
    if (own !== restoration) return;
    const replacement = { ...location, view: { ...location.view, page: 1 } };
    const path = queryPath(replacement);
    if (preserveDraft) viewNavigations.set(path, session.epoch);
    try {
      await router.replace({
        path: route.path,
        query: encodeLocation(replacement),
      });
      if (route.fullPath === path) search.notice = pageNotice;
    } finally {
      viewNavigations.delete(path);
    }
  }
  async function restore() {
    const own = ++restoration;
    if (!session.ready) return;
    const preserveDraft = viewNavigations.get(route.fullPath) === session.epoch;
    viewNavigations.delete(route.fullPath);
    try {
      const location = decodeLocation(route.query);
      const page = await search.load(
        location,
        session.epoch,
        false,
        preserveDraft,
      );
      if (page && own === restoration)
        await recoverPage(location, preserveDraft, own);
    } catch (error) {
      if (own === restoration)
        search.rejectUrl(
          error instanceof Error ? error.message : "Invalid search URL.",
        );
    }
  }
  watch(
    () => session.epoch,
    () => {
      viewNavigations.clear();
      search.invalidate();
    },
    { flush: "sync" },
  );
  watch(() => [route.query, session.epoch, session.ready], restore, {
    immediate: true,
    flush: "sync",
  });
  onScopeDispose(() => {
    restoration++;
    viewNavigations.clear();
    search.invalidate();
  });
  async function submit() {
    try {
      const location = {
        criteria: search.draft,
        view: { ...defaultView(), tab: search.view.tab },
      };
      const query = encodeLocation(location);
      if (router.resolve({ path: "/data", query }).fullPath === route.fullPath)
        await restore();
      else await router.push({ path: "/data", query });
    } catch (error) {
      search.urlError =
        error instanceof Error ? error.message : "Invalid criteria.";
    }
  }
  async function changeView(patch: Partial<ResultView>) {
    const view = { ...search.view, ...patch };
    if (patch.tab && patch.tab !== search.view.tab) {
      view.page = 1;
      view.order = "";
      view.tableSearch = "";
    } else if (
      patch.order !== undefined ||
      patch.pageSize !== undefined ||
      patch.tableSearch !== undefined
    )
      view.page = 1;
    const location = { criteria: search.applied, view },
      path = queryPath(location);
    viewNavigations.set(path, session.epoch);
    try {
      await router.push({ path: route.path, query: encodeLocation(location) });
    } finally {
      viewNavigations.delete(path);
    }
  }
  async function retry() {
    const own = ++restoration,
      location = { criteria: search.applied, view: search.view };
    const page = await search.load(location, session.epoch, true, true);
    if (page && own === restoration) await recoverPage(location, true, own);
  }
  return { search, submit, changeView, retry };
}
