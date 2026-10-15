/**
 * The test files of the website (#963): `website-*.spec.ts` below tests/. tests/setup.ts gives
 * every other test file the study views of the curation app; a test of the website gets none, so
 * that a page of the website that does not provide its context fails as it would in the browser.
 */
export function isWebsiteTest(path: string): boolean {
  return /(^|[\\/])website-[^\\/]+\.spec\.ts$/.test(path);
}
