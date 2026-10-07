import { fileURLToPath } from "node:url";

/** The python/ project, whose environment runs `pkdb curate`. */
export const pythonProject = fileURLToPath(new URL("../../../python/", import.meta.url));
/** The fixture workspace and its helper scripts. */
export const testing = fileURLToPath(new URL("../../../tools/curation_testing/", import.meta.url));
/** The built app that `pkdb curate` serves (`npm run build:curation`). */
export const builtApp = fileURLToPath(new URL("../../../python/src/pkdb/curation/static/index.html", import.meta.url));

/** The environment variable through which the global setup hands its temporary folder to the workers. */
export const ROOT_VARIABLE = "PKDB_CURATION_E2E_ROOT";
/** The environment variable that names the Python interpreter of the python/ project. */
export const PYTHON_VARIABLE = "PKDB_CURATION_E2E_PYTHON";
