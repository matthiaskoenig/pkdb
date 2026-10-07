import { postJson } from "./client";
import { isSession } from "./types";

/**
 * Exchange the launch token of `#token=...` for the session cookie and the CSRF token.
 *
 * The token leaves the address bar before it is posted, so that it is neither kept in the
 * history nor sent again on reload. Without a token the existing cookie is used; the first
 * `GET /local/state` then tells whether there is a session.
 */
export async function bootstrap(location: Location, history: History): Promise<void> {
  const launch = new URLSearchParams(location.hash.slice(1)).get("token");
  if (!launch) return;
  history.replaceState(null, "", `${location.pathname}${location.search}`);
  // postJson keeps the csrf_token of the response.
  await postJson("/local/session", { token: launch }, isSession);
}
