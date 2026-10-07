import { postJson } from "./client";
import { isSession } from "./types";

/** The launch token of a hash `#token=...`, or `#/token=...` after the hash router rewrote it. */
export function launchToken(hash: string): string | null {
  return new URLSearchParams(hash.replace(/^#\/?/, "")).get("token") || null;
}

/**
 * Exchange the launch token in the hash for the session cookie and the CSRF token.
 *
 * The token leaves the address bar before it is posted, so that it is neither kept in the
 * history nor sent again on reload. Without a token the existing cookie is used; the first
 * `GET /local/state` then tells whether there is a session.
 */
export async function bootstrap(location: Location, history: History): Promise<void> {
  const launch = launchToken(location.hash);
  if (!launch) return;
  history.replaceState(null, "", `${location.pathname}${location.search}`);
  // postJson keeps the csrf_token of the response.
  await postJson("/local/session", { token: launch }, isSession);
}
