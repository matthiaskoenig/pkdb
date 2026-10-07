import { createRouter, createWebHashHistory, type Router } from "vue-router";

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
      {
        path: "/",
        name: "Overview",
        component: () => import("./views/OverviewPage.vue"),
      },
      {
        path: "/studies/:substance/:name/:section?",
        name: "Study",
        component: () => import("./views/StudyPage.vue"),
      },
    ],
  });
}
