/**
 * Same-origin client of the local API of `pkdb curate`: CSRF header, ETags and error bodies.
 */
import { isSession, type RevisionConflictBody, type ValidationErrorBody } from "./types";
import { isRecord, type Guard } from "../../study-views/types";
import { ApiError, ServerStopped, SessionMissing, UnexpectedResponse } from "../../study-views/errors";

/** The `code` of the 403 for a missing or stale CSRF token (`ACTION_TOKEN` in server.py). */
const ACTION_TOKEN = "action_token";

let token = "";

export function setCsrfToken(value: string): void {
  token = value;
}

export function csrfToken(): string {
  return token;
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

/** `read()`, with the network failure of fetch (a TypeError) as ServerStopped of `request`. */
async function reaching<T>(request: string, read: () => Promise<T>): Promise<T> {
  try {
    return await read();
  } catch (error) {
    if (error instanceof TypeError) throw new ServerStopped(request, error);
    throw error;
  }
}

function send(path: string, init: RequestInit): Promise<Response> {
  return reaching(`${init.method ?? "GET"} ${path}`, () => fetch(path, { ...init, credentials: "same-origin" }));
}

async function failure(response: Response, request: string): Promise<never> {
  const body: unknown = await response.json().catch(() => ({}));
  const record = isRecord(body) ? body : {};
  if (response.status === 401)
    throw new SessionMissing(
      typeof record.error === "string" ? record.error : "Open the launch URL printed in your terminal",
    );
  throw new ApiError(response.status, record, request);
}

/** The JSON body of a successful response, checked by `accept`; it keeps a new CSRF token. */
async function content<T>(response: Response, accept: Guard<T>, request: string): Promise<T> {
  const text = await reaching(request, () => response.text());
  let value: unknown;
  try {
    value = JSON.parse(text);
  } catch {
    value = undefined;
  }
  if (isRecord(value) && typeof value.csrf_token === "string" && value.csrf_token) token = value.csrf_token;
  if (!accept(value)) throw new UnexpectedResponse(response.status);
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
  const request = `GET ${path}`;
  if (response.status === 304) return { status: 304, etag: response.headers.get("ETag") ?? etag ?? "" };
  if (!response.ok) return failure(response, request);
  return { status: 200, etag: response.headers.get("ETag"), data: await content(response, accept, request) };
}

/**
 * Ask for the first byte of the file at `path`: it resolves when the local server serves the
 * file, and throws its error as `getJson` does otherwise. A viewer that reads a file without this
 * client, as PDF.js does, learns from it why the file could not be read.
 */
export async function checkFile(path: string): Promise<void> {
  const response = await send(path, { headers: { Range: "bytes=0-0" } });
  if (!response.ok) return failure(response, `GET ${path}`);
  await response.body?.cancel();
}

async function post<T>(path: string, body: Record<string, unknown>, accept: Guard<T>): Promise<T> {
  const request = `POST ${path}`;
  const response = await send(path, {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json", "X-CSRF-Token": token },
    body: JSON.stringify(body),
  });
  if (!response.ok) return failure(response, request);
  return content(response, accept, request);
}

/**
 * POST a JSON action with the CSRF token.
 *
 * After a reload without the launch token, or a restart of the server, the token may be missing
 * or stale: then the action is sent once more with the token of `GET /local/state`.
 */
export async function postJson<T>(path: string, body: Record<string, unknown>, accept: Guard<T>): Promise<T> {
  try {
    return await post(path, body, accept);
  } catch (error) {
    if (!(error instanceof ApiError && error.status === 403 && error.body.code === ACTION_TOKEN)) throw error;
  }
  await getJson("/local/state", isSession);
  return post(path, body, accept);
}
