import { createRouter, createWebHashHistory } from "vue-router";

// Hash history: the local server has no fallback for unknown paths.
export const router = createRouter({
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
