import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import { router } from "./router/index";
import { makeVuetify } from "./plugins/vuetify";
import "./styles/app.css";
createApp(App).use(createPinia()).use(router).use(makeVuetify()).mount("#app");
