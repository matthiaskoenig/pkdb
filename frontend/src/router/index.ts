import { createRouter, createWebHistory } from "vue-router";
export const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(to, from, saved) {
    if (saved) return saved;
    if (to.path === from.path) return false;
    return { top: 0 };
  },
  routes: [
    {
      path: "/",
      name: "Home",
      component: () => import("../features/home/HomePage.vue"),
    },
    {
      path: "/data",
      name: "Data",
      component: () => import("../features/search/components/SearchPage.vue"),
    },
    {
      path: "/data/:sid",
      name: "DataSingle",
      props: true,
      component: () =>
        import("../features/details/components/StudyDetailPage.vue"),
    },
    {
      path: "/curation",
      name: "Curation",
      component: () =>
        import("../features/curation/components/CurationPage.vue"),
    },
    {
      path: "/account",
      name: "Account",
      component: () => import("../features/account/components/AccountPage.vue"),
    },
    {
      path: "/invitation",
      name: "Invitation",
      component: () =>
        import("../features/account/components/InvitationPage.vue"),
    },
    {
      path: "/registration",
      name: "Registration",
      component: () =>
        import("../features/account/components/RegistrationPage.vue"),
    },
    {
      path: "/verification/:id",
      name: "Verification",
      component: () =>
        import("../features/account/components/VerificationPage.vue"),
    },
    {
      path: "/request-password-reset",
      name: "RequestPasswordReset",
      component: () =>
        import("../features/account/components/RequestPasswordResetPage.vue"),
    },
    {
      path: "/reset-password/:id",
      name: "PasswordReset",
      component: () =>
        import("../features/account/components/PasswordResetPage.vue"),
    },
    {
      path: "/:pathMatch(.*)*",
      name: "NotFound",
      component: () => import("../features/home/NotFoundPage.vue"),
    },
  ],
});
