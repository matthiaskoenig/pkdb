/**
 * What the local server said about a failure: the details that the alert of a failed action
 * discloses and that Copy details puts into a GitHub issue.
 */
import type { FailureDetails } from "../study-views/study";
import type { ErrorBody } from "../study-views/types";

/** The details of a failure that the activity of a study lists. */
export function detailsOfBody(body: ErrorBody): FailureDetails {
  return {
    status: null,
    code: body.code,
    detail: body.detail,
    action: body.action,
    requestId: body.request_id,
    time: body.time,
    traceback: body.traceback ?? null,
    activityId: null,
  };
}

/** The type of the error at the start of a detail, such as `CalledProcessError`. */
export function errorType(detail: string | null): string | null {
  return detail?.match(/^([A-Za-z_][\w.]*)(?::|$)/)?.[1] ?? null;
}

/** The facts of the Details disclosure that are known, in order; `logFile` from the state. */
export function failureFacts(
  details: FailureDetails,
  logFile: string | null = null,
): { name: string; value: string }[] {
  const facts: [string, string | null][] = [
    ["Action", details.action],
    ["Status", details.status === null ? null : String(details.status)],
    ["Code", details.code],
    ["Error type", errorType(details.detail)],
    ["Request", details.requestId],
    ["Time", details.time],
    ["Log", logFile],
  ];
  return facts.filter((fact): fact is [string, string] => fact[1] !== null).map(([name, value]) => ({ name, value }));
}

/** The facts that Copy details writes; the error type is in the detail, the log is local. */
const MARKDOWN_FACTS: ReadonlySet<string> = new Set(["Action", "Status", "Code", "Request", "Time"]);

/** `text` in a fenced block whose fence is longer than every run of backticks in it. */
function fenced(text: string): string[] {
  const longest = Math.max(0, ...(text.match(/`+/g) ?? []).map((run) => run.length));
  const fence = "`".repeat(Math.max(3, longest + 1));
  return [`${fence}text`, text.trimEnd(), fence];
}

/** A failure as Markdown for a GitHub issue: the message, the detail, the request and the traceback. */
export function failureMarkdown(text: string, details: FailureDetails): string {
  const lines = [`**${text}**`];
  if (details.detail) lines.push("", ...fenced(details.detail));
  const facts = failureFacts(details).filter((fact) => MARKDOWN_FACTS.has(fact.name));
  if (facts.length) lines.push("", ...facts.map((fact) => `- ${fact.name}: ${fact.value}`));
  if (details.traceback) lines.push("", ...fenced(details.traceback));
  return `${lines.join("\n")}\n`;
}
