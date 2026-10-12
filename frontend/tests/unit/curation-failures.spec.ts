import { describe, expect, it } from "vitest";
import { ApiError, ServerStopped } from "../../src/curation-app/api/client";
import {
  detailsOf,
  detailsOfBody,
  errorType,
  failureFacts,
  failureMarkdown,
  type FailureDetails,
} from "../../src/curation-app/failures";

/** The error body as the activity keeps it, and as the server answers it with its entry. */
const STORED = {
  error: "Could not open the tables of caffeine/Example.",
  code: "open_failed",
  detail: "CalledProcessError: xdg-open exited with status 4\nno method available for opening",
  action: "Open tables (POST /local/studies/tables)",
  request_id: "3f9c2a71",
  time: "2026-10-12T14:03:11+02:00",
};
const OPEN_FAILED = { ...STORED, activity_id: "0123456789abcdef0123456789abcdef" };

const DETAILS: FailureDetails = {
  status: 500,
  code: "open_failed",
  detail: OPEN_FAILED.detail,
  action: OPEN_FAILED.action,
  requestId: "3f9c2a71",
  time: "2026-10-12T14:03:11+02:00",
  traceback: null,
  activityId: OPEN_FAILED.activity_id,
};

describe("detailsOf", () => {
  it("takes the details of an error body of the local server", () => {
    expect(detailsOf(new ApiError(500, OPEN_FAILED))).toEqual(DETAILS);
  });

  it("has none for an answer without the error body, or for another error", () => {
    expect(detailsOf(new ApiError(500, { error: "Unable to open the workbook" }))).toBeNull();
    expect(detailsOf(new Error("Disk full"))).toBeNull();
    expect(detailsOf("refused")).toBeNull();
  });

  it("names the request that did not reach the local server", () => {
    expect(detailsOf(new ServerStopped("POST /local/jobs", new TypeError("Failed to fetch")))).toEqual({
      status: 0,
      code: "unreachable",
      detail: "TypeError: Failed to fetch",
      action: "POST /local/jobs",
      requestId: null,
      time: null,
      traceback: null,
      activityId: null,
    });
  });

  it("takes the details of an entry of the activity, which has no status", () => {
    expect(detailsOfBody(STORED)).toEqual({ ...DETAILS, status: null, activityId: null });
  });
});

describe("errorType", () => {
  it("is the name before the first colon of a detail", () => {
    expect(errorType("CalledProcessError: xdg-open exited with status 4\nstderr: x")).toBe("CalledProcessError");
    expect(errorType("RuntimeError")).toBe("RuntimeError");
    expect(errorType("no type here")).toBeNull();
    expect(errorType(null)).toBeNull();
  });
});

describe("failureFacts", () => {
  it("lists what is known, in order, with the log file", () => {
    expect(failureFacts(DETAILS, "/home/curator/.cache/pkdb/curation/logs/curation.log")).toEqual([
      { name: "Action", value: "Open tables (POST /local/studies/tables)" },
      { name: "Status", value: "500" },
      { name: "Code", value: "open_failed" },
      { name: "Error type", value: "CalledProcessError" },
      { name: "Request", value: "3f9c2a71" },
      { name: "Time", value: "2026-10-12T14:03:11+02:00" },
      { name: "Log", value: "/home/curator/.cache/pkdb/curation/logs/curation.log" },
    ]);
    expect(failureFacts({ ...DETAILS, status: null, requestId: null, time: null }).map((fact) => fact.name)).toEqual([
      "Action",
      "Code",
      "Error type",
    ]);
  });
});

describe("failureMarkdown", () => {
  it("writes the message, the detail, the request and the traceback for an issue", () => {
    expect(failureMarkdown(OPEN_FAILED.error, { ...DETAILS, traceback: "Traceback (most recent call last):\n  boom\n" })).toBe(
      [
        "**Could not open the tables of caffeine/Example.**",
        "",
        "```text",
        "CalledProcessError: xdg-open exited with status 4",
        "no method available for opening",
        "```",
        "",
        "- Action: Open tables (POST /local/studies/tables)",
        "- Status: 500",
        "- Code: open_failed",
        "- Request: 3f9c2a71",
        "- Time: 2026-10-12T14:03:11+02:00",
        "",
        "```text",
        "Traceback (most recent call last):",
        "  boom",
        "```",
        "",
      ].join("\n"),
    );
  });

  it("fences a detail or a traceback that holds backticks with a longer fence", () => {
    const markdown = failureMarkdown("Could not save the settings.", {
      ...DETAILS,
      detail: "ValueError: a ```fenced``` value",
      traceback: "line ````four````",
    });
    expect(markdown).toContain("````text\nValueError: a ```fenced``` value\n````");
    expect(markdown).toContain("`````text\nline ````four````\n`````");
  });
});
