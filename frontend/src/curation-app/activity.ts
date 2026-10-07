/**
 * The activity of a study: labels of its jobs (validations and uploads of the local server, and
 * writes of the app), whether clearing the history removes any, and saving a report.
 */
import type { Job, JobAction, JobStatus } from "./api/types";
import type { Tone } from "./overview";

export const ACTION_LABELS: Record<JobAction, string> = {
  validate: "Validation",
  validate_remote: "Server validation",
  upload: "Upload",
  write: "Change in the app",
};

/** The Font Awesome icon of each action; validations and uploads have those of the study header. */
export const ACTION_ICONS: Record<JobAction, string> = {
  validate: "fas fa-circle-check",
  validate_remote: "fas fa-server",
  upload: "fas fa-cloud-arrow-up",
  write: "fas fa-pen",
};

export const JOB_STATUS_LABELS: Record<JobStatus, string> = {
  queued: "Queued",
  running: "Running",
  succeeded: "Succeeded",
  failed: "Failed",
  canceled: "Canceled",
  conflict: "Conflict",
  unknown: "Outcome unknown",
  // The curator checked an uncertain upload and uploaded the study again.
  reviewed: "Reviewed",
};

export const JOB_STATUS_TONES: Record<JobStatus, Tone> = {
  queued: undefined,
  running: "info",
  succeeded: "success",
  failed: "error",
  canceled: undefined,
  // As the sync status shows a conflict.
  conflict: "error",
  unknown: "warning",
  reviewed: undefined,
};

/** What an upload did on the server; `not_attempted` sent nothing. */
const PERSISTENCE_LABELS: Partial<Record<string, string>> = {
  created: "created",
  replaced: "replaced",
  unknown: "unknown outcome",
  // Resume found the upload on the server.
  reconciled: "confirmed on the server",
  not_saved: "not saved",
};

/** What an upload did on the server; null for other jobs, and while the status says that the outcome is unknown. */
export function persistenceLabel(job: Job): string | null {
  if (job.action !== "upload" || job.status === "unknown" || job.persistence === undefined) return null;
  return PERSISTENCE_LABELS[job.persistence] ?? null;
}

/** The progress stages of a running job (`pkdb.progress` events of the library and the client). */
const STAGE_LABELS: Partial<Record<string, string>> = {
  // Before the first event, while the workbook syncs and the reference updates.
  queued: "Starting",
  read: "Reading the files",
  parse: "Reading the tables",
  validate: "Validating",
  compatibility: "Checking the server",
  transfer: "Sending the study",
  server_validation: "Validating on the server",
  complete: "Finishing",
};

/**
 * What a job does or did: a queued or running job keeps the message "Queued" of the server
 * until it ends, so its status and stage say what it does.
 */
export function jobText(job: Job): string {
  if (job.status === "queued") return "Waiting to start";
  if (job.status === "running") return (job.stage && STAGE_LABELS[job.stage]) || "Running";
  return job.message;
}

/** The name of the downloaded report of the job `id`. */
export function reportFileName(id: string): string {
  return `pkdb-report-${id}.json`;
}

/** The page of the uploaded study on the server, when it is a web page. */
export function uploadUrl(job: Job): string | null {
  const url = job.upload?.url;
  if (!url) return null;
  try {
    return ["https:", "http:"].includes(new URL(url).protocol) ? url : null;
  } catch {
    return null;
  }
}

/**
 * The time of a job for the `datetime` of a `<time>` element, which allows at most milliseconds;
 * the server writes microseconds.
 */
export function datetime(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toISOString();
}

/** The statuses of the jobs that clearing the history keeps. */
const KEPT_STATUSES: ReadonlySet<JobStatus> = new Set(["queued", "running", "unknown"]);

/**
 * Whether clearing the history removes a job of `jobs`, the jobs of the workspace in the order of
 * the server (oldest first). It keeps queued and running jobs, uploads with an unknown outcome and
 * the last upload of each study (`_kept` in jobs.py).
 */
export function clearable(jobs: readonly Job[]): boolean {
  const uploads = new Map<string, Job>();
  for (const job of jobs) if (job.upload) uploads.set(job.study_id, job);
  const latest = new Set(uploads.values());
  return jobs.some((job) => !KEPT_STATUSES.has(job.status) && !latest.has(job));
}

/**
 * How long a Blob link of a saved file stays valid. The browser reads the Blob after the click,
 * so the link is revoked later rather than at once.
 */
export const REVOKE_MS = 60_000;

/** Save `text` as the file `name` through a link to a Blob, which is revoked afterwards. */
export function saveFile(name: string, text: string, type: string): void {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  // In the page while it is clicked, as some browsers download only a link of the page.
  document.body.append(link);
  try {
    link.click();
  } finally {
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), REVOKE_MS);
  }
}
