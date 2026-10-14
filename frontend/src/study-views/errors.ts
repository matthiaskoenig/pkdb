/**
 * The errors of the reads of the study views. `ApiError` carries the error body that the local
 * server of `pkdb curate` writes (`python/src/pkdb/curation/errors.py`): what could not be done,
 * why, and which request failed when; a page of the website throws it with the fields of its
 * own error body, which may lack the request id and the time.
 */

/** A text field of an error body; null when it is missing, empty or no string. */
function field(value: unknown): string | null {
  return typeof value === "string" && value ? value : null;
}

/**
 * A failed request to the local API with the error body of the server (`describe` in
 * python/src/pkdb/curation/errors.py): what could not be done (the message), why (`detail`)
 * and which request failed when (`action`, `requestId`, `time`).
 */
export class ApiError extends Error {
  override readonly name: string = "ApiError";
  /** The failure in snake case, such as `open_failed`. */
  readonly code: string | null;
  /** The type and the text of the error, or the command, its exit status and its stderr. */
  readonly detail: string | null;
  /** The request: its label with its method and path, such as `Open tables (POST /local/studies/tables)`. */
  readonly action: string | null;
  /** The 8 hex characters that name the failure in the log of pkdb curate. */
  readonly requestId: string | null;
  /** When it failed: ISO 8601 in the time zone of the local server. */
  readonly time: string | null;
  /** The traceback of an unexpected error, which the log has too. */
  readonly traceback: string | null;
  /** The entry of the failure in the activity of the study. */
  readonly activityId: string | null;

  /** `request` names the request, such as `POST /local/studies/tables`, for a body without `action`. */
  constructor(
    readonly status: number,
    readonly body: Record<string, unknown>,
    request: string | null = null,
  ) {
    super(field(body.message) ?? field(body.error) ?? `Request failed (${status}).`);
    this.code = field(body.code);
    this.detail = field(body.detail);
    this.action = field(body.action) ?? request;
    this.requestId = field(body.request_id);
    this.time = field(body.time);
    this.traceback = field(body.traceback);
    this.activityId = field(body.activity_id);
  }
}

/** The message of a request that did not reach the local server. */
export const UNREACHABLE = "Could not reach the local server.";

/** The local server cannot be reached: `pkdb curate` stopped or restarts. Its status is 0. */
export class ServerStopped extends ApiError {
  override readonly name: string = "ServerStopped";

  constructor(request: string, cause?: unknown) {
    super(
      0,
      {
        error: UNREACHABLE,
        code: "unreachable",
        detail: cause instanceof Error ? `${cause.name}: ${cause.message}` : null,
      },
      request,
    );
  }
}

/** What to do when the page has no session of the running server, which the status banner says too. */
export const NO_SESSION = "This page has no session. Open the link that pkdb curate printed.";

/** The browser has no session cookie of the running server (401). */
export class SessionMissing extends Error {
  override readonly name = "SessionMissing";
}

/** A successful response whose body is not the expected JSON; the request may have taken effect. */
export class UnexpectedResponse extends Error {
  override readonly name = "UnexpectedResponse";

  constructor(readonly status: number) {
    super("The local server sent an unexpected response.");
  }
}

/** A request that was canceled, for example of a study that was closed before the answer. */
export function isAbort(error: unknown): boolean {
  // An AbortError of another realm, such as a test environment, is no DOMException of this one.
  return typeof error === "object" && error !== null && "name" in error && error.name === "AbortError";
}
