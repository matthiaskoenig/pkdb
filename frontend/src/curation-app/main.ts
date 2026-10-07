// Vuetify's styles declare the order of its cascade layers, so they load before the styles of
// any component; otherwise its reset of buttons wins over the sizes of buttons and chips.
import "vuetify/styles";
import { start } from "./start";
import "./styles.css";

void start("#app");
