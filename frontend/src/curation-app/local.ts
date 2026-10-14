/**
 * What only the local curation app says about a study: the notices and refusals of its actions, the
 * folder of a study in the workspace, the folders of a duplicate identity and the page of its last
 * upload.
 */
import type { ApiError } from "../study-views/errors";
import type { StudyDetail } from "../study-views/types";
import type { TablesResult } from "./api/types";
import { webUrl } from "../study-views/overview";
import { actionFailure, type ActionFailure } from "../study-views/study";

/** The requirements of approval, followed by the reason of the refusal from the server. */
export function approvalRefusal(reason: string): string {
  const sentence = reason.trim().replace(/\.?$/, ".");
  return `Approved needs zero open review items and zero validation errors. ${sentence}`;
}

/** How long the header and the sections show the notice of an action that succeeded. */
export const NOTICE_MS = 5000;

/** What to do about a write that was refused without a user (`isNoUser`). */
export function userHint(error: ApiError): string {
  return error.body.error === "no_user" ? "Set your PK-DB user in Connection settings." : error.message;
}

/** What the curator should know after Open tables: nothing for a clean sync. */
export function tablesOutcome(result: TablesResult): ActionFailure | null {
  const issues = result.issues.map((item) => item.message);
  const unresolved = result.conflicts.filter((conflict) => conflict.kept === null).length;
  const link: ActionFailure["link"] = unresolved ? { section: "data", label: "Show the conflicts" } : null;
  if (unresolved === 1) issues.unshift("A sheet conflicts with its table.");
  if (unresolved > 1) issues.unshift(`${unresolved} sheets conflict with their tables.`);
  if (!result.opened) return actionFailure("The workbook could not be opened.", issues, link);
  return issues.length ? actionFailure("The workbook opened, but the sync found problems.", issues, link) : null;
}

// Paths

/** The folder of a study, given relative to the workspace with `/`, joined with the separator of the workspace. */
export function folderPath(workspace: string, relative: string): string {
  const separator = workspace.includes("\\") && !workspace.includes("/") ? "\\" : "/";
  const base = workspace.replace(/[\\/]+$/, "");
  return [base, ...relative.split("/").filter(Boolean)].join(separator);
}

/** The folders of a duplicate identity, relative to the workspace, from the `paths` of the 409 answer. */
export function duplicateFolders(body: Record<string, unknown>): string[] {
  const paths = body.paths;
  return Array.isArray(paths) ? paths.filter((path): path is string => typeof path === "string") : [];
}

const NUMBERS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"];

/** `This identity belongs to two folders`, for the number of folders that the server listed. */
export function duplicateHeading(folders: number): string {
  if (folders < 2) return "This identity belongs to more than one folder";
  return `This identity belongs to ${NUMBERS[folders] ?? folders} folders`;
}

/** The page of the last upload of the study on PK-DB; null without an upload or when its URL is not a web page. */
export function lastUploadUrl(detail: StudyDetail): string | null {
  return webUrl(detail.last_upload?.url);
}
