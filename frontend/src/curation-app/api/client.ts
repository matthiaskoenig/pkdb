/**
 * Same-origin client of the local API of `pkdb curate`: CSRF header, ETags and error bodies.
 */
import {
  isRecord,
  type Guard,
  type RevisionConflictBody,
  type ValidationErrorBody,
} from "./types";

let token = "";

export function setCsrfToken(value: string): void {
  token = value;
}

export function csrfToken(): string {
  return token;
}

/** A refusal of the local API with its JSON body `{error, ...}`. */
export class ApiError extends Error {
  override readonly name = "ApiError";

  constructor(
    readonly status: number,
    readonly body: Record<string, unknown>,
  ) {
    super(
      typeof body.message === "string"
        ? body.message
        : typeof body.error === "string"
          ? body.error
          : `Request failed (${status})`,
    );
  }
}

/** The local server cannot be reached: `pkdb curate` stopped or restarts. */
export class ServerStopped extends Error {
  override readonly name = "ServerStopped";
}

/** The browser has no session cookie of the running server (401). */
export class SessionMissing extends Error {
  override readonly name = "SessionMissing";
}

/** A file changed on disk since the app read it; the body holds its current content. */
export function isRevisionConflict(
  error: unknown,
): error is ApiError & { readonly body: RevisionConflictBody } {
  return (
    error instanceof ApiError &&
    error.status === 409 &&
    typeof error.body.file === "string" &&
    "content" in error.body
  );
}

/** The library refused a document (422); the body holds its issues. */
export function isValidationError(
  error: unknown,
): error is ApiError & { readonly body: ValidationErrorBody } {
  return error instanceof ApiError && error.status === 422 && Array.isArray(error.body.issues);
}

/** Writes are refused without a user, or with a key of another account than the user. */
export function isNoUser(error: unknown): error is ApiError {
  return (
    error instanceof ApiError &&
    error.status === 403 &&
    (error.body.error === "no_user" || error.body.error === "user_mismatch")
  );
}

/** The path of a study route; each segment of the identity and the route is percent-encoded. */
export function studyPath(identity: string, ...parts: string[]): string {
  return `/local/studies/${[...identity.split("/"), ...parts].map(encodeURIComponent).join("/")}`;
}

export type Fetched<T> = { status: 200; etag: string | null; data: T } | { status: 304; etag: string };

/** `read()`, with the network failure of fetch (a TypeError) as ServerStopped. */
async function reaching<T>(read: () => Promise<T>): Promise<T> {
  try {
    return await read();
  } catch (error) {
    if (error instanceof TypeError) throw new ServerStopped("The local server stopped. Start pkdb curate again.");
    throw error;
  }
}

function send(path: string, init: RequestInit): Promise<Response> {
  return reaching(() => fetch(path, { ...init, credentials: "same-origin" }));
}

async function failure(response: Response): Promise<never> {
  const body: unknown = await response.json().catch(() => ({}));
  const record = isRecord(body) ? body : {};
  if (response.status === 401)
    throw new SessionMissing(
      typeof record.error === "string" ? record.error : "Open the launch URL printed in your terminal",
    );
  throw new ApiError(response.status, record);
}

/** The JSON body of a successful response, checked by `accept`; it keeps a new CSRF token. */
async function content<T>(response: Response, accept: Guard<T>): Promise<T> {
  const text = await reaching(() => response.text());
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    value = undefined;
  }
  if (isRecord(value) && typeof value.csrf_token === "string" && value.csrf_token) token = value.csrf_token;
  if (!accept(value)) throw new ApiError(response.status, { error: "The local server sent an unexpected response" });
  return value;
}

/** GET a JSON resource; with the ETag of the last response, 304 means that nothing changed. */
export async function getJson<T>(
  path: string,
  accept: Guard<T>,
  { etag = null, signal = null }: { etag?: string | null; signal?: AbortSignal | null } = {},
): Promise<Fetched<T>> {
  const response = await send(path, {
    headers: { Accept: "application/json", ...(etag ? { "If-None-Match": etag } : {}) },
    signal,
  });
  if (response.status === 304) return { status: 304, etag: response.headers.get("ETag") ?? etag ?? "" };
  if (!response.ok) return failure(response);
  return { status: 200, etag: response.headers.get("ETag"), data: await content(response, accept) };
}

/** POST a JSON action with the CSRF token. */
export async function postJson<T>(path: string, body: Record<string, unknown>, accept: Guard<T>): Promise<T> {
  const response = await send(path, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json", "X-CSRF-Token": token },
    body: JSON.stringify(body),
  });
  if (!response.ok) return failure(response);
  return content(response, accept);
}
