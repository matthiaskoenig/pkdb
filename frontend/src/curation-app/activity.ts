/**
 * The activity of a study: labels of its jobs (validations and uploads of the local server, and
 * writes of the app), the review items that their messages name, and saving a report.
 */
import type { Job, JobAction, JobStatus, ReviewItem } from "./api/types";
import { webUrl, type Tone } from "./overview";
import { KIND_LABELS } from "./review";

export const ACTION_LABELS: Record<JobAction, string> = {
  validate: "Validation",
  validate_remote: "Server validation",
  upload: "Upload",
  write: "Change in the app",
};

/** The Font Awesome icon of each action; neutral, as the status says how it ended. */
export const ACTION_ICONS: Record<JobAction, string> = {
  validate: "fas fa-clipboard-list",
  validate_remote: "fas fa-server",
  upload: "fas fa-cloud-arrow-up",
  write: "fas fa-pen",
};

export const JOB_STATUS_LABELS: Record<JobStatus, string> = {
  queued: "Queued",
  running: "Running",
  succeeded: "Succeeded",
  invalid: "Problems found",
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
  // As the problem chips of the overview show errors.
  invalid: "error",
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

/** A part of the text of a job: text, or the reference to a review item, linked to the item `item`. */
export type MessagePart = { text: string; item?: string };

/** The characters of an item text that a reference quotes. */
const QUOTE_LENGTH = 40;

/** The start of a text, cut after a word, in one line. */
function quote(text: string): string {
  const line = text.replace(/\s+/g, " ").trim();
  if (line.length <= QUOTE_LENGTH) return line;
  const cut = line.slice(0, QUOTE_LENGTH + 1);
  const space = cut.lastIndexOf(" ");
  return `${(space > 0 ? cut.slice(0, space) : line.slice(0, QUOTE_LENGTH)).replace(/[\s,;:.]+$/, "")}…`;
}

/**
 * The text of a job with readable references to the review items of `items` that it names: the
 * kind of the item and the start of its text, instead of its id. An item that no longer exists is
 * "a review item". The server splits the message around the item.
 */
export function messageParts(job: Job, items: readonly ReviewItem[]): MessagePart[] {
  if (!job.parts) return [{ text: jobText(job) }];
  const parts: MessagePart[] = [];
  let text = "";
  for (const part of job.parts) {
    if ("text" in part) {
      text += part.text;
      continue;
    }
    const item = items.find((candidate) => candidate.id === part.item);
    if (!item) {
      text += "a review item";
      continue;
    }
    parts.push({ text: `${text}the ` });
    parts.push({ text: `${KIND_LABELS[item.kind].toLowerCase()} “${quote(item.text)}”`, item: item.id });
    text = "";
  }
  if (text) parts.push({ text });
  return parts;
}

/** The name of the downloaded report of the job `id`. */
export function reportFileName(id: string): string {
  return `pkdb-report-${id}.json`;
}

/** The page of the uploaded study on the server, when it is a web page. */
export function uploadUrl(job: Job): string | null {
  return webUrl(job.upload?.url);
}

/**
 * The time of a job for the `datetime` of a `<time>` element, which allows at most milliseconds;
 * the server writes microseconds.
 */
export function datetime(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toISOString();
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
