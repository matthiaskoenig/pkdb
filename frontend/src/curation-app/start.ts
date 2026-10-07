import { createApp, type App as VueApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import { bootstrap } from "./api/session";
import { cspNonce } from "./csp";
import { makeRouter } from "./router";
import { makeVuetify } from "../plugins/vuetify";

/**
 * Create the session from the launch URL, then mount the app on `target`.
 *
 * The router comes second because its hash history rewrites `#token=...` when it is created.
 */
export async function start(target: string | Element): Promise<VueApp> {
  try {
    await bootstrap(window.location, window.history);
  } catch {
    // The app still starts: its first GET /local/state reports the missing session or the
    // stopped server, which the page shows.
  }
  const app = createApp(App)
    .use(createPinia())
    .use(makeRouter())
    .use(makeVuetify({ cspNonce: cspNonce() }));
  app.mount(target);
  return app;
}
