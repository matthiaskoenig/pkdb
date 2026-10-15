/**
 * The routes of the study views in the curation app (router.ts): the overview at `#/`, a study
 * and its sections at `#/studies/<substance>/<name>/<section>`, and a PDF in a tab of its own.
 * A section gets the query it asks for.
 */
import type { RouteLocationRaw } from "vue-router";
import type { StudyViewRoutes } from "../study-views/context";
import { isSection, studyName } from "../study-views/study";

function params(id: string): { substance: string; name: string } {
  return { substance: id.slice(0, id.indexOf("/")), name: studyName({ id }) };
}

export const curationRoutes: StudyViewRoutes = {
  overview: () => ({ name: "Overview" }),
  study: (id) => ({ name: "Study", params: params(id) }),
  section(id, section, query = {}): RouteLocationRaw {
    const target = { name: "Study", params: { ...params(id), section } };
    return Object.keys(query).length ? { ...target, query } : target;
  },
  paper: (id, file) => ({ name: "Paper", params: { ...params(id), file } }),
  current(route) {
    if (route.name !== "Study") return null;
    const { substance, name, section } = route.params;
    return { id: `${String(substance)}/${String(name)}`, section: isSection(section) ? section : null };
  },
  query: (_current, own) => own,
};
