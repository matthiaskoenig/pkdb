import type { Profile } from "../../src/api/session";
export const profileFixture = (overrides: Partial<Profile> = {}): Profile => ({
  id: 17,
  username: "researcher",
  role: "curator",
  display_name: "Researcher",
  affiliation: "",
  title: "",
  github: "",
  orcid: "",
  github_visible: true,
  orcid_visible: true,
  github_provenance: "",
  orcid_provenance: "",
  avatar_url: "/api/v1/avatars/default.svg",
  emails: [],
  mfa_required: false,
  mfa_enrolled: false,
  mfa_recent: false,
  ...overrides,
});
export function deferred<T>() {
  let complete: (value: T) => void = () => {
    throw new Error("Deferred not initialized");
  };
  let fail: (error: unknown) => void = () => {
    throw new Error("Deferred not initialized");
  };
  const promise = new Promise<T>((resolve, reject) => {
    complete = resolve;
    fail = reject;
  });
  return { promise, complete, fail };
}
