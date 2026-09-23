import type { Criteria } from "./model";
import { canonicalCriteria } from "./codec";
export function serializeCriteria(value: Criteria): URLSearchParams {
  const c = canonicalCriteria(value),
    p = new URLSearchParams({
      format: "json",
      concise: String(c.scope === "matching"),
    });
  for (const [key, values] of Object.entries(c.filters)) {
    if (key.startsWith("subjects__")) {
      for (const subject of ["groups", "individuals"] as const)
        if (c.subjects[subject])
          p.set(key.replace("subjects__", `${subject}__`), values.join("__"));
    } else p.set(key, values.join("__"));
  }
  for (const subject of ["groups", "individuals"] as const)
    if (!c.subjects[subject]) p.set(`${subject}__id__in`, "0");
  const licences = (["open", "closed"] as const).filter((v) => c.licences[v]);
  if (licences.length !== 2)
    p.set("studies__licence__in", licences.join("__") || "0");
  const types = (["output", "timecourse", "array"] as const).filter(
    (v) => c.types[v],
  );
  if (types.length !== 3)
    p.set("outputs__output_type__in", types.join("__") || "0");
  return p;
}
