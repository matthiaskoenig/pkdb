# Dependency audit

Inspected 2026-09-23. Versions below are recovered from the local legacy build, not inferred from manifest ranges. npm deprecation metadata is separate from source reachability; exact recovered-version metadata was queried from the official npm registry. The replacement graph is defined by the committed lockfile.

| Package | Declared | Recovered version | Disposition / callers | npm deprecated |
| --- | --- | --- | --- | --- |
| `@fortawesome/fontawesome-free` | `^5.15.2` | `5.15.4` | Upgrade: maintained framework/style/test caller | Not deprecated |
| `@statnett/vue-plotly` | `^0.3.2` | `0.3.2` | Replace active ScatterPlot/TimecoursePlot wrapper with lazy typed Plotly | Not deprecated |
| `acorn` | `^8.0.5` | `8.18.0` | Remove: no maintained caller | Not deprecated |
| `axios` | `^0.21.1` | `0.21.4` | Upgrade: maintained framework/style/test caller | Not deprecated |
| `base-64` | `^1.0.0` | `1.0.0` | Remove: no maintained caller | Not deprecated |
| `vega` | `^5.19.1` | `5.33.1` | Remove orphan StatisticsVegaPlot; Home reference commented | Not deprecated |
| `vega-embed` | `^6.15.1` | `6.29.0` | Remove orphan StatisticsVegaPlot; Home reference commented | Not deprecated |
| `vega-lite` | `^4.17.0` | `4.17.0` | Remove orphan StatisticsVegaPlot; Home reference commented | Not deprecated |
| `vue` | `^2.6.12` | `2.7.16` | Upgrade: maintained framework/style/test caller | Vue 2 has reached EOL and is no longer actively maintained. See https://v2.vuejs.org/eol/ for more details. |
| `vue-auth-image` | `^0.0.3` | `0.0.3` | Remove bootstrap registration; no active directive/$http caller | Not deprecated |
| `vue-multiselect` | `^2.1.6` | `2.1.9` | Replace search controls with Vuetify autocomplete | Not deprecated |
| `vue-plotly` | `^1.1.0` | `1.1.0` | Remove: no maintained caller | Not deprecated |
| `vue-resource` | `^1.5.1` | `1.5.3` | Remove bootstrap registration; no active directive/$http caller | Not deprecated |
| `vue-router` | `^3.5.1` | `3.6.5` | Upgrade: maintained framework/style/test caller | Not deprecated |
| `vue-text-highlight` | `^2.0.10` | `2.0.10` | Replace table highlighting with escaped text component | Not deprecated |
| `vuetify` | `^2.4.3` | `2.7.2` | Upgrade: maintained framework/style/test caller | Not deprecated |
| `vuex` | `^3.6.2` | `3.6.2` | Replace store and mixins with Pinia | Not deprecated |
| `vuex-persist` | `^3.1.3` | `3.1.3` | Remove: no maintained caller | Not deprecated |
| `@vue/cli-plugin-babel` | `^3.12.1` | `3.12.1` | Replace legacy Vue CLI/Webpack/Mocha chain with Vite/Vitest | Not deprecated |
| `@vue/cli-plugin-eslint` | `^3.12.1` | `3.12.1` | Replace legacy Vue CLI/Webpack/Mocha chain with Vite/Vitest | Not deprecated |
| `@vue/cli-plugin-unit-mocha` | `^3.11.1` | `3.12.1` | Replace legacy Vue CLI/Webpack/Mocha chain with Vite/Vitest | Not deprecated |
| `@vue/cli-service` | `^4.1.2` | `4.5.19` | Replace legacy Vue CLI/Webpack/Mocha chain with Vite/Vitest | Not deprecated |
| `@vue/test-utils` | `^1.0.0-beta.30` | `1.3.6` | Upgrade: maintained framework/style/test caller | Not deprecated |
| `chai` | `^4.2.0` | `4.5.0` | Replace legacy Vue CLI/Webpack/Mocha chain with Vite/Vitest | Not deprecated |
| `css-loader` | `^3.6.0` | `3.6.0` | Replace legacy Vue CLI/Webpack/Mocha chain with Vite/Vitest | Not deprecated |
| `sass-loader` | `^8.0.2` | `8.0.2` | Replace legacy Vue CLI/Webpack/Mocha chain with Vite/Vitest | Not deprecated |
| `style-loader` | `^1.2.1` | `1.3.0` | Replace legacy Vue CLI/Webpack/Mocha chain with Vite/Vitest | Not deprecated |
| `stylus` | `^0.54.8` | `0.54.8` | Replace legacy Vue CLI/Webpack/Mocha chain with Vite/Vitest | Not deprecated |
| `stylus-loader` | `^3.0.2` | `3.0.2` | Replace legacy Vue CLI/Webpack/Mocha chain with Vite/Vitest | Not deprecated |
| `vue-cli-plugin-vuetify` | `^0.2.1` | `0.2.1` | Replace legacy Vue CLI/Webpack/Mocha chain with Vite/Vitest | Not deprecated |
| `vue-template-compiler` | `^2.6.12` | `2.7.16` | Replace legacy Vue CLI/Webpack/Mocha chain with Vite/Vitest | Not deprecated |
| `sass` | `^1.93.0` | `1.104.1` | Upgrade: maintained framework/style/test caller | Not deprecated |

Vue 2 wrappers/compiler/store and CLI tooling are incompatible with the chosen Vue 3 architecture regardless of their npm deprecation fields. There are no Stylus application sources. The obsolete `_deprecated/StudyDetail.vue`, `TimecoursesPlot.vue` and `StatisticsVegaPlot.vue` are not maintained routes.

Final `npm ls --all` passes; npm advisory audit reports zero vulnerabilities and the locked graph contains no `deprecated` markers. Commands, optional install-hook handling, declaration corrections and dated evidence are recorded in [modernization verification](modernization-verification.md). No unresolved transitive deprecation chain was found in this graph.

## Pinned declaration compatibility

The selected current packages expose declaration defects under strict TypeScript: Vuetify 4.2.1's open global component/directive interfaces, ViewTransition readonly augmentation and duplicate Slot barrel, plus Router 5.3.1's experimental optional fields. `scripts/patch-declarations.ts` applies narrowly scoped, exact-version and exact-shape checked declaration corrections during clean installation. It changes no runtime code or application types; `skipLibCheck` remains false. Reassess and remove each correction when upstream packages change. Both Dockerfiles copy this script before `npm ci` so clean image builds exercise the same checks.

Plot presentation correction: legacy charts treated coefficient of variation as an absolute error bar. The migrated plot retains CV in its accessible data table with an explanation, and uses only SD/SE as dimensional error bars; it performs no numerical conversion.
