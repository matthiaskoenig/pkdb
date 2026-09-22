# Modernization baseline

Baseline source: `0562a566`, inspected 2026-09-23. The original package manifest declared ranges without a committed npm lockfile; those ranges are not a historical installed graph. `/tmp/pkdb-frontend-qa/src` was compared recursively with the preserved `/tmp/pkdb-frontend-legacy/src`; there were no source differences. The successful legacy build log is `/tmp/pkdb-frontend-build.log`. Its already-built artifact was retained before replacing application source.

| Local rollback evidence | SHA-256 |
| --- | --- |
| `/tmp/pkdb-frontend-legacy/source.tar` | `615f55980e5241b715d99a2afcac1ab0a51cf6fc6d2ffed206821791d1643169` |
| `/tmp/pkdb-frontend-legacy/dist.tar` | `14f6dc00915ee21b80cedf127a58784d32ed45c39984766d9289884b022b0be7` |
| `/tmp/pkdb-frontend-legacy/resolved-packages.json` | `0ded2bb6996f081f4eebb76bb17bd1d1adae65872a92b6796c3bf3d8625da85f` |

The archived dist contains 97 files totaling 28,852,888 bytes including source maps, icons and images. Per-file sizes are retained in [asset sizes](baseline/asset-sizes.json), and the recovered dependency graph is retained in [resolved packages](baseline/resolved-packages.json). This is a recovered local build, not a claim about the deployed production image or historical reproducibility. These `/tmp` artifacts must be copied to durable release storage before cutover. Production proxy verification and actual deployed-artifact retention remain operator release gates.

Preserved history routes: `/`, `/data`, `/data/:sid`, `/curation`, `/invitation`, `/account`, `/verification/:id`, `/registration`, `/request-password-reset`, `/reset-password/:id`, `/404`, and catch-all. Curation is vocabulary browsing, not study editing. Account includes provider callbacks, password/verification/invitation flows, keys, MFA, sessions, activity and administration. The existing public avatar files remain inputs to `scripts/check_curator_roster.py`.

Existing defects deliberately corrected by the migration: Reset aliases mutable defaults and omits licence/scope reset; no-licence selection uses an invalid unprefixed filter; table ordering is commented out. Scientific matching scope derives related entities from normalized measurements. Whole-study scope can qualify through different records. Flat export rows expand relationships and cannot be compared numerically with entity badges.

The baseline archive is evidence of source/build recovery only. No legacy visual, keyboard, browser console or authenticated staging inspection is claimed here. Modern browser acceptance and remaining staging limitations belong in `modernization-verification.md`.

## Comparable entry-asset measurement

The same Python `gzip.compress` measurement was applied to JS/CSS directly referenced by each build's `index.html` (including modern module preloads). The recovered legacy artifact references 5,694,889 raw bytes / 1,576,876 gzip bytes; the modern implementation build inspected on 2026-09-23 references 1,015,517 raw bytes / 263,919 gzip bytes. This comparison excludes fonts, images, source maps and dynamically requested route chunks for both artifacts; it is not a page-load timing claim. Browser acceptance checks observe that the Plotly engine is absent before the explicit Show plot action and appears afterward.

The isolated browser fixture uses the complete bootstrap vocabulary, whose authoritative concentration normalization turns reported 2.125 mg/l into 0.002125 `gram / liter`. The small backend unit fixture uses its deliberately minimal mg/l vocabulary and retains 2.125 mg/l. Both are expected backend outputs; the frontend neither converts nor recalculates them. Real-browser trace assertions use the complete-vocabulary values and units.
