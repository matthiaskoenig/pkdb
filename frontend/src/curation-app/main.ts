import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import { cspNonce } from "./csp";
import { router } from "./router";
import { makeVuetify } from "../plugins/vuetify";
import "./styles.css";

createApp(App)
  .use(createPinia())
  .use(router)
  .use(makeVuetify({ cspNonce: cspNonce() }))
  .mount("#app");
