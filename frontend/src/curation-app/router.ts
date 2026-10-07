import { createRouter, createWebHashHistory, type Router } from "vue-router";
// The views are imported eagerly: a browser keeps a failed dynamic import until the page reloads,
// so a lazy view requested while the local server is down would break navigation silently.
import OverviewPage from "./views/OverviewPage.vue";
import StudyPage from "./views/StudyPage.vue";

/**
 * The router of the app, with hash history: the local server has no fallback for unknown paths.
 *
 * Creating the hash history rewrites the address, so the app creates the router only after the
 * session took the launch token from `#token=...`.
 */
export function makeRouter(): Router {
  return createRouter({
    history: createWebHashHistory(),
    routes: [
      { path: "/", name: "Overview", component: OverviewPage },
      // Without a section, the study page shows the section that the study needs first.
      { path: "/studies/:substance/:name/:section?", name: "Study", component: StudyPage },
    ],
  });
}
