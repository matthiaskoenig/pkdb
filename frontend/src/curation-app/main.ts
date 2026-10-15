// Vuetify's styles first. The order of the cascade layers does not depend on it: the page declares
// it before any stylesheet (scripts/cascade-layers.ts), as the build links the files of shared
// chunks before this one.
import "vuetify/styles";
import { start } from "./start";
import "../study-views/styles.css";
import "./styles.css";

void start("#app");
