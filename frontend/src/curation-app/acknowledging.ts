/**
 * The acknowledgement of warnings in the curation app: the refusals of the acknowledge action,
 * whether the local server validates after a write, and the marks of warnings acknowledged in the
 * app until a later report.
 */
import { isValidationError } from "./api/client";
import type { Snapshot } from "./api/types";
import type { Job, StudyDetail } from "../study-views/types";
import { reviewFailure, type ReviewFailure } from "./reviewWrites";
import { issuesFailure } from "../study-views/study";

/** What the dialog says when the warning is no longer in the files that the server validated. */
export const NO_SUCH_WARNING = "This warning is not in the current files. Validate the study and try again.";

/** What the dialog says when warnings at several locations match the one to acknowledge. */
export const AMBIGUOUS_WARNING = "Several warnings match this location. Validate the study and try again.";

/** What the dialog says for a warning without a row of a data table and without a key. */
export const NO_EXACT_TARGET = "This warning cannot be acknowledged on its own.";

/**
 * The plain sentences of the refusals of the `acknowledge` action, by their code
 * (`studyformat/review_edit.py`). Their messages are written for `pkdb review acknowledge`: they
 * list locations and name its options.
 */
const ACKNOWLEDGE_REFUSALS: ReadonlyMap<string, string> = new Map([
  ["no_such_warning", NO_SUCH_WARNING],
  ["ambiguous_warning", AMBIGUOUS_WARNING],
  ["no_exact_target", NO_EXACT_TARGET],
]);

/** The failure of an acknowledgement; a refusal of the warning itself gets a plain sentence. */
export function acknowledgeFailure(caught: unknown): ReviewFailure {
  const text = isValidationError(caught) ? ACKNOWLEDGE_REFUSALS.get(caught.body.code ?? "") : undefined;
  if (text) return { kind: "error", ...issuesFailure(text, []) };
  return reviewFailure(caught, "The warning was not acknowledged.");
}

/**
 * Whether the local server validates the study by itself after a write. It does not with On
 * save Off, while file watching is paused, or for an upload on save without an account that
 * can upload. Without the state of the server, it is assumed to.
 */
export function validatesAfterWrite(
  snapshot: Pick<Snapshot, "mode" | "paused" | "offline" | "account" | "can_upload"> | null,
): boolean {
  if (!snapshot) return true;
  if (snapshot.mode === "off" || snapshot.paused) return false;
  return snapshot.mode !== "upload" || (!snapshot.offline && snapshot.account !== null && snapshot.can_upload);
}

/**
 * A warning acknowledged in the app: its location key, the time of the write in the activity of
 * the study, and the report of the study at that time.
 */
export interface AcknowledgedMark {
  key: string;
  since: string | null;
  report: string | null;
}

/** The time of the newest write of the app in the activity of a study (newest first), such as an acknowledgement. */
export function lastWrite(jobs: readonly Job[]): string | null {
  return jobs.find((job) => job.action === "write")?.created_at ?? null;
}

/**
 * Whether the report of a study comes from a job queued after the acknowledgement was written:
 * only such a job validated the acknowledgement. A job that was queued or running during the
 * write can still list the warning. The times are the server's, in one ISO format, so they
 * compare as text. Without the job of the report, any other report counts.
 */
export function reportAfter(detail: Pick<StudyDetail, "jobs" | "report_id">, mark: AcknowledgedMark): boolean {
  const job = detail.jobs.find((entry) => entry.id === detail.report_id);
  if (job && mark.since !== null) return job.created_at > mark.since;
  return detail.report_id !== mark.report;
}
