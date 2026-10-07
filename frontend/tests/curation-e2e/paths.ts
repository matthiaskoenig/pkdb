import { fileURLToPath } from "node:url";

/** The repository, whose python/ project runs `pkdb curate` and whose tools/ hold the fixture. */
export const repository = fileURLToPath(new URL("../../../", import.meta.url));
export const pythonProject = fileURLToPath(new URL("../../../python/", import.meta.url));
export const testing = fileURLToPath(new URL("../../../tools/curation_testing/", import.meta.url));
/** The built app that `pkdb curate` serves (`npm run build:curation`). */
export const builtApp = fileURLToPath(new URL("../../../python/src/pkdb/curation/static/index.html", import.meta.url));

/** The environment variable through which the global setup hands its temporary folder to the workers. */
export const ROOT_VARIABLE = "PKDB_CURATION_E2E_ROOT";
