/**
 * The last folder name of a path and the path of its parent folder, for showing a path in
 * little space. A root such as `/` is its own name, without a parent.
 */
export function splitPath(path: string): { name: string; parent: string } {
  const trimmed = path.length > 1 ? path.replace(/[\\/]+$/, "") : path;
  const cut = Math.max(trimmed.lastIndexOf("/"), trimmed.lastIndexOf("\\"));
  const name = trimmed.slice(cut + 1);
  if (cut < 0 || !name) return { name: trimmed, parent: "" };
  // The parent of `/work` is the root `/`.
  return { name, parent: trimmed.slice(0, cut) || trimmed.slice(0, cut + 1) };
}
