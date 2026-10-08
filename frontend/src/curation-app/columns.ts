/**
 * The letters of a column of a spreadsheet: A for the first (index 0), AA after Z. A module
 * without imports, so that the e2e tests and tools/curation_docs/render.mjs import it as well.
 */
export function columnLetters(index: number): string {
  let letters = "";
  for (let rest = index + 1; rest > 0; rest = Math.floor((rest - 1) / 26))
    letters = String.fromCharCode(65 + ((rest - 1) % 26)) + letters;
  return letters;
}
