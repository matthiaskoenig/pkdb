// A study format 2 study has the sid `<substance>/<name>` and is addressed by
// two path segments; a study format 1 sid (or a PKDB identifier) takes one.
export function studyPath(sid: string): string {
  const slash = sid.indexOf("/");
  return (slash < 0 ? [sid] : [sid.slice(0, slash), sid.slice(slash + 1)])
    .map(encodeURIComponent)
    .join("/");
}
export function studyLocation(sid: string): string {
  return `/data/${studyPath(sid)}`;
}
export function studyApiPath(sid: string): string {
  return `/api/v1/studies/${studyPath(sid)}/`;
}
