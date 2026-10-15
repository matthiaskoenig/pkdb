/**
 * What a failed write of review.json says: a stale revision, a missing user, or a refusal with its
 * issues.
 */
import { isNoUser, isRevisionConflict, isValidationError } from "./api/client";
import { userHint } from "./local";
import { failureOf, issuesFailure, type ActionFailure } from "../study-views/study";

/** What a write over a stale revision of review.json says; the store has reloaded the items. */
export const REVIEW_CONFLICT = "review.json changed on disk; the items were reloaded. Repeat your action.";

/** Why a write of review.json failed: a stale revision, a missing user, or a refusal with its issues. */
export type ReviewFailure =
  | { kind: "conflict"; text: string }
  | { kind: "user"; text: string }
  | ({ kind: "error" } & ActionFailure);

/** The failure of a write; `refused` says what did not happen, such as `The item was not resolved.` */
export function reviewFailure(caught: unknown, refused: string): ReviewFailure {
  if (isRevisionConflict(caught)) return { kind: "conflict", text: REVIEW_CONFLICT };
  if (isNoUser(caught)) return { kind: "user", text: userHint(caught) };
  if (isValidationError(caught) && caught.body.issues.length)
    return { kind: "error", ...issuesFailure(refused, caught.body.issues.map((issue) => issue.message)) };
  return { kind: "error", ...failureOf(caught, refused) };
}
