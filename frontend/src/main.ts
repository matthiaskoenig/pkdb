// Vuetify's styles first. The order of the cascade layers does not depend on it: the page declares
// it before any stylesheet (scripts/cascade-layers.ts), as the build links the files of shared
// chunks before this one.
import "vuetify/styles";
import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import { router } from "./router/index";
import { makeVuetify } from "./plugins/vuetify";
import { STUDY_VIEW_THEMES } from "./study-views/themes";
import "./styles/app.css";
// The study pages (#963) use the info and caution colors of the study views; named colors that change nothing else of the website.
createApp(App).use(createPinia()).use(router).use(makeVuetify({ themes: STUDY_VIEW_THEMES })).mount("#app");
