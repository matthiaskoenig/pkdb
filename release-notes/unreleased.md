# Unreleased

## Changes

- Security: the frontend overrides minimatch with 11.0.4, which fixes GHSA-g3hv-75wg-m249 (patched in 11.0.1, no fixed 10.x release), and glob with 14.0.3, the glob built against minimatch 11, in `overrides` of `package.json`. The newest releases of eslint (10.14.0), typescript-eslint (8.72.1) and editorconfig (3.0.2) still require minimatch 10. Only development tools use them: eslint, typescript-eslint, and js-beautify of `@vue/test-utils`. The overrides can be removed once they accept minimatch 11.
