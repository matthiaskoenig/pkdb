// Vuetify's styles declare the order of its cascade layers, so they load before the styles of
// any component; otherwise its reset of buttons wins over the sizes of buttons and chips.
import "vuetify/styles";
import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import { router } from "./router/index";
import { makeVuetify } from "./plugins/vuetify";
import "./styles/app.css";
createApp(App).use(createPinia()).use(router).use(makeVuetify()).mount("#app");
