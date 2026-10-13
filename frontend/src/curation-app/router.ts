import { createRouter, createWebHashHistory, type Router } from "vue-router";
// The views are imported eagerly: a browser keeps a failed dynamic import until the page reloads,
// so a lazy view requested while the local server is down would break navigation silently.
import OverviewPage from "./views/OverviewPage.vue";
import PaperPage from "./views/PaperPage.vue";
import StudyPage from "./views/StudyPage.vue";

/**
 * The router of the app, with hash history: the local server has no fallback for unknown paths.
 *
 * Creating the hash history rewrites the address, so the app creates the router only after the
 * session took the launch token from `#token=...`.
 *
 * As on the website, another page or section starts at the top, back and forward return to the
 * saved position, and a change of the query alone, such as the row of the Data section, keeps the
 * position.
 */
export function makeRouter(): Router {
  return createRouter({
    history: createWebHashHistory(),
    scrollBehavior(to, from, saved) {
      if (saved) return saved;
      if (to.path === from.path) return false;
      return { top: 0 };
    },
    routes: [
      { path: "/", name: "Overview", component: OverviewPage },
      // The Data section replaced the Sources and Tables sections; their links keep working.
      {
        path: "/studies/:substance/:name/:section(sources|tables)",
        redirect: (to) => ({ name: "Study", params: { ...to.params, section: "data" }, query: to.query }),
      },
      // A PDF of a study in a tab of its own, which New tab of the paper pane opens: no app bar.
      { path: "/studies/:substance/:name/paper/:file", name: "Paper", component: PaperPage, meta: { bare: true } },
      // Without a section, the study page shows the section that the study needs first.
      { path: "/studies/:substance/:name/:section?", name: "Study", component: StudyPage },
      // An address that the app does not know, such as a launch URL pasted into the open app,
      // shows the overview; the guard of the launch token takes the token first.
      { path: "/:unknown(.*)*", redirect: "/" },
    ],
  });
}
