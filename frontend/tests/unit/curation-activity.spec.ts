import { afterEach, describe, expect, it, vi } from "vitest";
import {
  datetime,
  jobText,
  messageParts,
  persistenceLabel,
  REVOKE_MS,
  reportFileName,
  saveFile,
  uploadUrl,
} from "../../src/curation-app/activity";
import type { Job, JobMessagePart, ReviewItem } from "../../src/curation-app/api/types";

function job(changes: Partial<Job> = {}): Job {
  return {
    id: "job-1",
    study_id: "caffeine/Example",
    study_name: "Example",
    action: "validate",
    status: "succeeded",
    stage: "complete",
    created_at: "2026-10-07T12:00:00+00:00",
    message: "Validation passed",
    automatic: false,
    persistence: "not_attempted",
    report_id: "job-1",
    ...changes,
  };
}

afterEach(() => {
  vi.useRealTimers();
});

describe("jobText", () => {
  it("says what a queued or running job does, and the message of a finished one", () => {
    expect(jobText(job({ status: "queued", stage: "queued", message: "Queued" }))).toBe("Waiting to start");
    expect(jobText(job({ status: "running", stage: "queued", message: "Queued" }))).toBe("Starting");
    expect(jobText(job({ status: "running", stage: "validate", message: "Queued" }))).toBe("Validating");
    expect(jobText(job({ status: "running", stage: "transfer", message: "Queued" }))).toBe("Sending the study");
    expect(jobText(job({ status: "running", stage: "new_stage", message: "Queued" }))).toBe("Running");
    const unstaged = job({ status: "running", message: "Queued" });
    delete unstaged.stage;
    expect(jobText(unstaged)).toBe("Running");
    expect(jobText(job({ status: "invalid", message: "Validation found problems" }))).toBe("Validation found problems");
    expect(jobText(job({ status: "canceled", message: "Replaced by a newer validation" }))).toBe(
      "Replaced by a newer validation",
    );
  });
});

describe("persistenceLabel", () => {
  it("names what an upload did on the server", () => {
    expect(persistenceLabel(job({ action: "upload", persistence: "created" }))).toBe("created");
    expect(persistenceLabel(job({ action: "upload", persistence: "replaced" }))).toBe("replaced");
    expect(persistenceLabel(job({ action: "upload", status: "reviewed", persistence: "unknown" }))).toBe(
      "unknown outcome",
    );
    expect(persistenceLabel(job({ action: "upload", persistence: "reconciled" }))).toBe("confirmed on the server");
    expect(persistenceLabel(job({ action: "upload", status: "failed", persistence: "not_saved" }))).toBe(
      "not saved",
    );
  });

  it("says nothing for an upload that sent nothing, for an unknown status and for other jobs", () => {
    expect(persistenceLabel(job({ action: "upload", status: "failed", persistence: "not_attempted" }))).toBeNull();
    // The status chip says that the outcome is unknown.
    expect(persistenceLabel(job({ action: "upload", status: "unknown", persistence: "unknown" }))).toBeNull();
    expect(persistenceLabel(job({ action: "validate_remote", persistence: "not_attempted" }))).toBeNull();
    const written = job({ action: "write", report_id: null });
    delete written.persistence;
    expect(persistenceLabel(written)).toBeNull();
  });
});

describe("datetime", () => {
  it("gives the time of the server with milliseconds, as a datetime attribute allows", () => {
    expect(datetime("2026-10-07T12:00:00.123456+00:00")).toBe("2026-10-07T12:00:00.123Z");
    expect(datetime("2026-10-07T14:00:00+02:00")).toBe("2026-10-07T12:00:00.000Z");
    expect(datetime("not a time")).toBe("not a time");
  });
});

describe("uploadUrl", () => {
  it("links only to a web page", () => {
    const upload = { persistence: "created", at: "2026-10-07T12:00:00+00:00", endpoint: "https://pk-db.com" };
    expect(uploadUrl(job({ upload: { ...upload, url: "https://pk-db.com/data/PKDB00198" } }))).toBe(
      "https://pk-db.com/data/PKDB00198",
    );
    expect(uploadUrl(job({ upload: { ...upload, url: "javascript:alert(1)" } }))).toBeNull();
    expect(uploadUrl(job({ upload: { ...upload, url: null } }))).toBeNull();
    expect(uploadUrl(job())).toBeNull();
  });
});

describe("messageParts", () => {
  const ID = "01K6Y4ZJ6Q8D3W6B6V5N1S2T3X";
  const question: ReviewItem = {
    id: ID,
    kind: "question",
    state: "open",
    author: "curator",
    created: "2026-10-07T12:00:00Z",
    text: "Is the dose of 150 mg the caffeine base or the citrate salt of caffeine?",
    thread: [],
  };

  /** A write of the app as the server sends it: its message split around the item it names. */
  function write(message: string, parts: JobMessagePart[]): Job {
    return job({ action: "write", message, item: ID, parts, report_id: null });
  }

  it("names a review item by its kind and a short quote of its text, linked to it", () => {
    expect(messageParts(write(`Added review item ${ID}`, [{ text: "Added " }, { item: ID }]), [question])).toEqual([
      { text: "Added the " },
      { text: "question “Is the dose of 150 mg the caffeine base…”", item: ID },
    ]);
    const acknowledged = write(`Acknowledged warning unknown_unit with review item ${ID}`, [
      { text: "Acknowledged warning unknown_unit with " },
      { item: ID },
    ]);
    expect(messageParts(acknowledged, [{ ...question, kind: "issue", text: "Unit  as\nprinted" }])).toEqual([
      { text: "Acknowledged warning unknown_unit with the " },
      { text: "issue “Unit as printed”", item: ID },
    ]);
  });

  it("keeps the text after the item", () => {
    const parts = [{ text: "Replied to " }, { item: ID }, { text: " twice" }];
    expect(messageParts(write(`Replied to review item ${ID} twice`, parts), [question])).toEqual([
      { text: "Replied to the " },
      { text: "question “Is the dose of 150 mg the caffeine base…”", item: ID },
      { text: " twice" },
    ]);
  });

  it("says a review item when the item no longer exists, and keeps other messages", () => {
    const resolved = write(`Resolved review item ${ID}`, [{ text: "Resolved " }, { item: ID }]);
    expect(messageParts(resolved, [])).toEqual([{ text: "Resolved a review item" }]);
    expect(messageParts(job({ action: "write", message: "Saved study.json" }), [question])).toEqual([
      { text: "Saved study.json" },
    ]);
  });

  it("reads only the parts of the server, never review items in the message", () => {
    expect(messageParts(job({ status: "failed", message: `Could not read review item ${ID}` }), [question])).toEqual([
      { text: `Could not read review item ${ID}` },
    ]);
  });

  it("says what a running job does", () => {
    expect(messageParts(job({ status: "running", stage: "validate", message: "Queued" }), [question])).toEqual([
      { text: "Validating" },
    ]);
  });
});

describe("saveFile", () => {
  it("saves a text through a link to a Blob and revokes the link afterwards", async () => {
    vi.useFakeTimers();
    const create = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:report");
    const revoke = vi.spyOn(URL, "revokeObjectURL").mockReturnValue(undefined);
    // jsdom does not download.
    const clicked: { href: string; download: string; attached: boolean }[] = [];
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      clicked.push({ href: this.getAttribute("href") ?? "", download: this.download, attached: this.isConnected });
    });

    saveFile(reportFileName("job-1"), '{"ok": true}', "application/json");

    expect(clicked).toEqual([{ href: "blob:report", download: "pkdb-report-job-1.json", attached: true }]);
    expect(document.querySelector("a[download]")).toBeNull();
    const blob = create.mock.calls[0]![0];
    if (!(blob instanceof Blob)) throw new Error("Expected a Blob");
    expect(blob.type).toBe("application/json");
    expect(await blob.text()).toBe('{"ok": true}');
    expect(revoke).not.toHaveBeenCalled();
    vi.advanceTimersByTime(REVOKE_MS);
    expect(revoke).toHaveBeenCalledWith("blob:report");
  });
});
