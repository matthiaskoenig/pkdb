// Vuetify's styles declare the order of its cascade layers, so they load before the styles of
// any component; otherwise its reset of buttons wins over the sizes of buttons and chips.
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
