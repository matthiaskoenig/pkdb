# Pinned declaration corrections

The current Vue 3.5.43, Vuetify 4.2.1, Vue Router 5.3.1 and TypeScript 6.0.3 combination has declaration errors under full strict checking with `exactOptionalPropertyTypes`. `scripts/patch-declarations.ts` corrects only the installed declaration files. It checks all four package versions, expected declaration shapes, and generated-file counts before writing. Running it twice is a no-op. Package runtime JavaScript is unchanged; `skipLibCheck`, global index signatures, and application type suppressions are not used.

| Upstream declaration | Correction and reason |
| --- | --- |
| Vuetify generated component declarations and `lib/framework.d.ts` | Vue's open `GlobalComponents` and `GlobalDirectives` interfaces are passed as local registry arguments constrained by `Record<string, …>`. A finite `Pick<T, keyof T>` copy preserves exactly their declared members and allows TypeScript to check each member against that constraint. It does not add arbitrary component/directive names. |
| Vuetify `lib/composables/directiveComponent.d.ts` | `DirectiveHook`'s previous vnode admits `null`, as required by Vue's creation/mount hooks. Vuetify's runtime hook ignores this fourth argument. |
| Vuetify `lib/framework.d.ts` | `ViewTransition.finished` is readonly, matching the DOM declaration. |
| Vuetify `lib/util/index.d.ts` | Explicitly re-export the existing `Slot` type from `defineComponent`, resolving two identical-shaped aliases exported by the barrel. |
| Vue Router's bundled experimental resolver declarations | The base record's optional `name`, `path`, and `hash` admit explicit `undefined`, matching its group subtype. Ordinary route definitions are unchanged. |

The script runs during `postinstall`. Upgrading any pinned package fails closed until these corrections are reviewed against the new declarations. Prefer removing a correction when upstream resolves its defect. Do not carry these changes forward by loosening version checks without reviewing the original error and replacement.

Run `npm run typecheck` to check libraries, application scripts, Vue templates and tests together. `tests/types/declaration-contracts.ts` also proves that the corrected component declarations retain finite supported button/select variants: arbitrary variant strings must remain rejected. Real component tests and browser tests validate runtime behavior separately.
