# PK-DB frontend

Start the complete local stack with the two-command [local setup guide](../docs/installation.md).

The maintained application uses Vue, Vuetify, Pinia, strict TypeScript and Vite. Install Node **24.21.0**, then explicitly bootstrap npm **12.1.0** (`npm install --global npm@12.1.0`). The `packageManager` field documents the version; it does not switch npm automatically.

```bash
npm ci
npm run dev
npm run test:source
npm run typecheck
npm run lint
npm run test:unit -- --run
npm run build
npx playwright install --with-deps
npm run test:e2e
```

For live GUI development, keep `npm run dev` running and open **http://localhost:8080**. Saving Vue, TypeScript, or CSS source updates the browser automatically through Vite hot module replacement; public asset changes reload the page. With Docker, use `docker compose --profile dev up --build --wait` from the repository root for the same live workflow; Docker enables polling to detect changes reliably across bind mounts. Native development can opt into polling with `PKDB_DEV_USE_POLLING=true`. `npm run build` and `npm run preview` serve production-build workflows and do not provide live source updates.

Development uses port 8080. The Vite development proxy defaults to `http://127.0.0.1:18083`. The backend browser origin must match the browser-visible origin exactly. `VITE_API_BASE` is a public API origin, normally empty for same-origin requests; never place passwords or bearer credentials in Vite variables. Frontend requests use same-origin session cookies and CSRF.

Browser tests run the actual `dist/` through Nginx against the isolated `compose.frontend-test.yaml` backend. The harness owns only the `pkdb-frontend-test` Compose project and removes its disposable resources after testing. It never seeds the default deployment. Scientific fixture data and test passwords are artificial. Traces are disabled to avoid recording passwords or session tokens; failure screenshots and reports remain local/CI artifacts.

`Dockerfile-production` builds static assets and retains the existing **`/vue` artifact handoff**. It does not serve HTTP. The deployment operator supplies the static server/reverse proxy. Use `tests/deployment/nginx.conf` as a tested example: backend routes precede SPA fallback; hashed assets receive immutable caching; HTML is revalidated; missing assets return 404. The Compose `dev` profile provides a Vite frontend for local development only.

Preserve the currently deployed image/artifact before replacing `/vue`, and retain the corresponding source and dependency graph. Roll back by atomically restoring that artifact in the existing static server; this frontend cutover requires no database migration. Local migration artifact details and limitations are in [the baseline](docs/modernization-baseline.md).

The fixture seeds separate reader accounts per browser project to exercise the real account throttle without tests interfering with one another. Administrators sign in with the same username/password form as other users. Fixture passwords are accepted only by the guarded disposable database loader and are never deployment credentials. Account tests disable screenshots as well as traces while exercising show-once secrets.
