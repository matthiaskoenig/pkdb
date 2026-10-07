import { createApp, type App as VueApp } from "vue";
import { createPinia, type Pinia } from "pinia";
import type { Router } from "vue-router";
import App from "./App.vue";
import { bootstrap, launchToken } from "./api/session";
import { cspNonce } from "./csp";
import { makeRouter } from "./router";
import { useOverviewStore } from "./stores/overview";
import { makeVuetify } from "../plugins/vuetify";

/** Create the session; a failure shows in the next GET /local/state, as a missing session or a stopped server. */
async function session(): Promise<void> {
  try {
    await bootstrap(window.location, window.history);
  } catch {
    // The app still runs: the state of the local server tells the curator what to do.
  }
}

/**
 * Take a launch URL pasted into the open app, which changes only the hash, as at the start:
 * create the session, show the overview and load its state.
 */
function takeLaunchTokens(router: Router, pinia: Pinia): void {
  router.beforeEach(async () => {
    if (!launchToken(window.location.hash)) return true;
    await session();
    void useOverviewStore(pinia).refresh();
    return { path: "/", replace: true };
  });
}

/**
 * Create the session from the launch URL, then mount the app on `target`.
 *
 * The router comes second because its hash history rewrites `#token=...` when it is created.
 */
export async function start(target: string | Element): Promise<VueApp> {
  await session();
  const pinia = createPinia();
  const router = makeRouter();
  takeLaunchTokens(router, pinia);
  const app = createApp(App)
    .use(pinia)
    .use(router)
    .use(makeVuetify({ cspNonce: cspNonce() }));
  app.mount(target);
  return app;
}
