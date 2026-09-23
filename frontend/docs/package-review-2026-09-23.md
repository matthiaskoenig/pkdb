# Frontend package review

Reviewed the modernized frontend at `e61937a1`, not the already-removed Vue 2 stack. Registry versions, current deprecation notices, peer ranges and engines were checked live against the official npm registry. Source/configuration usage and the resolved dependency graph were inspected independently. [Machine-readable evidence](package-review-2026-09-23.json) records the results and timestamp.

## Findings and changes

| Priority | Finding | Decision |
| --- | --- | --- |
| Medium | `vite-plugin-vuetify` contributes no Vite plugin under the configured `autoImport: false` and default `styles: true`; installed implementation returns an empty array. Components are already explicitly registered. | Removed the dependency and no-op configuration. |
| Medium | `sass` has no source consumer after the migration. Application styles are plain CSS; `vuetify/styles` resolves to compiled CSS. | Removed. This also removes its native watcher chain and the previously blocked optional install hook. Restore only if Sass preprocessing is actually introduced. |
| Low | `@vue/compiler-dom` has no direct caller. Vue and `@vue/compiler-sfc` already depend on the matching compiler. | Removed the direct declaration. It remains transitively installed; this is manifest cleanup, not bundle-size reduction. |
| Medium | Font Awesome `all.css` includes unused brand and backward-compatibility styles/font declarations. | Replaced the CSS import with `fontawesome.css`, `solid.css`, and `regular.css`. Regular icons are required by Vuetify checkbox/radio aliases and must not be dropped. The package itself remains necessary. |
| Medium, follow-up | The full Plotly engine is much broader than the application’s 2D scatter/line traces. | Recommend evaluating `plotly.js-basic-dist-min@4.1.1` in a separate change. Keep the existing engine until error bars, log axes, modebar/export, resizing and scientific parity are verified with the smaller distribution. |
| Medium, maintenance | Strict compilation currently requires exact-version declaration corrections for Vue/Vuetify/Router/TypeScript. | Keep the fail-closed checks. Reassess and remove corrections when upstream fixes are available; do not bypass them with `skipLibCheck` or an unreviewed version edit. |

Three direct development dependencies were removed: **27 → 24 total direct packages**. The cross-platform lock graph fell from **328 to 309 package entries**, including removal of `@vuetify/loader-shared`, Sass, Immutable, `@parcel/watcher` and its platform variants, `node-addon-api`, and `upath`. On this Linux installation, npm installed 284 packages after the cleanup; lockfile totals include optional packages for other platforms.

Emitted production CSS fell from **461,384 to 444,395 bytes**. Emitted WOFF2 fonts fell from **258,588 to 139,000 bytes**. These are artifact sizes; browsers load fonts on demand, so the font reduction is not a claim that every user previously downloaded those bytes. Plotly remains lazy-loaded and unchanged by this cleanup.

## Updates, deprecation and security

**No direct package is deprecated.** The 27 direct packages inspected before removal are already on their latest stable release except the two intentionally constrained packages below. Fresh per-version registry requests also found **zero deprecation notices across all 308 unique versions in the remaining lock graph**. The graph has 309 entries because one identity appears at multiple installed paths. The npm security advisory audit reports **zero vulnerabilities** for the remaining graph. These results are time-specific observations.

| Package | Current | Registry latest | Recommendation |
| --- | --- | --- | --- |
| `typescript` | 6.0.3 | 7.0.2 | Keep 6.0.3: current `typescript-eslint@8.70.1` declares `>=4.8.4 <6.1.0`. A forced major upgrade violates the supported peer range and requires reassessing declaration corrections. |
| `@types/node` | 24.13.6 | 26.6.2 | Keep 24.13.6, the latest Node 24 line. Declarations should match the pinned Node 24 runtime rather than expose unsupported Node 26 APIs. |
| All other inspected direct packages | Exact versions in evidence | Same as installed | No version change justified by registry evidence. |

No package was replaced merely because it was assumed to be deprecated. The removed packages were unused or redundant, which is a separate finding.

## Keep these dependencies

- **Vue, Vuetify, Router and Pinia:** active application architecture with extensive template, routing, session and search usage. Replacing them would be another framework migration, not cleanup.
- **Axios:** the shared client owns CSRF acquisition, configured-origin restrictions, session invalidation, cancellation and binary downloads. Native fetch could replace it, but would require reconstructing this tested behavior; it is not an easy removal.
- **`@vue/compiler-sfc`:** directly used by `scripts/check-source.ts`, as well as the Vue toolchain. It is not redundant in the same way as the direct `compiler-dom` entry.
- **`jiti`:** used by ESLint to load the TypeScript configuration in the current supported setup. Native config loading is not enabled. Lack of an application import does not make this removable.
- **`vue-eslint-parser`, `typescript-eslint`, `eslint-plugin-vue`, `@eslint/js`, ESLint:** active configuration and peer dependencies; keep their ownership explicit.
- **Vite, its Vue plugin, `vue-tsc`, TypeScript and Node declarations:** build/type infrastructure. Keep the Vue compiler packages aligned with Vue.
- **Vitest, Vue Test Utils, jsdom, Playwright and axe:** actual unit/component and real-browser coverage. Moving all DOM tests into browsers could remove jsdom, but is a test-architecture change with no current need.
- **Font Awesome:** required by the selected Vuetify icon set. A deliberately curated SVG set could eventually replace the font package, but must cover every Vuetify alias plus application icons.

## Best next optimization

**Prefer the official basic Plotly distribution over changing chart libraries.** The application emits only `scatter` traces, including line-based timecourses. Plotly’s [official distribution documentation](https://github.com/plotly/plotly.js/blob/main/dist/README.md#plotlyjs-basic) identifies scatter, bar and pie as the basic bundle’s supported traces. The current application’s full engine chunk is approximately **4.63 MB minified**, loaded only on demand. The basic 4.1.1 npm package exists and is approximately 1.19 MB unpacked, but a resulting Vite/gzip saving has not been measured here and is not claimed as implemented. Validate scientific arrays, zero/null/precision, uncertainty bars, logarithmic scales, hover, zoom/reset, image export and lazy loading before switching.

A curated SVG icon set is the next optional removal opportunity after that. Removing Axios, Pinia, Router or DOM-test tooling offers less convincing benefit and creates broader behavior changes.

## Validation

Clean `npm ci --offline`, `npm ls --all`, source inventory, strict `vue-tsc`, ESLint, all **84 unit/component tests**, and the production build pass after the removals. The declaration correction installer also passed against freshly extracted dependencies. The existing Vite warning concerns the deliberately lazy full Plotly chunk; this review leaves it visible.

All **90 real-backend browser cases pass** across Chromium, Firefox and WebKit against the rebuilt artifact. Chromium/Firefox passed on the first run. WebKit initially failed to launch because its wrapper overrides `LD_LIBRARY_PATH` and this host lacks libavif16; rerunning its 30 cases with the already-extracted libgav1/libyuv/libavif libraries explicitly preloaded passed, without changing application code or assertions. CI installs browser system dependencies with Playwright. Logs are under `/tmp/pkdb-package-review/` (`ci.log`, `types.log`, `lint.log`, `unit.log`, `build.log`, `e2e.log`, `webkit.log`); registry and audit facts are retained in the adjacent evidence JSON. No backend implementation or scientific calculations changed.
