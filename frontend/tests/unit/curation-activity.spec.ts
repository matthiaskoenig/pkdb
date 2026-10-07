import { afterEach, describe, expect, it, vi } from "vitest";
import {
  clearable,
  datetime,
  jobText,
  persistenceLabel,
  REVOKE_MS,
  reportFileName,
  saveFile,
  uploadUrl,
} from "../../src/curation-app/activity";
import type { Job } from "../../src/curation-app/api/types";

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
    expect(jobText(job({ status: "failed", message: "Validation found problems" }))).toBe("Validation found problems");
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

describe("clearable", () => {
  it("is true when the history has a job that clearing removes", () => {
    expect(clearable([job({ status: "queued" }), job({ id: "job-2", status: "failed" })])).toBe(true);
    expect(clearable([job({ action: "write", status: "succeeded" })])).toBe(true);
  });

  it("is false when only active jobs, uncertain uploads and the last upload of each study remain", () => {
    const upload = { persistence: "created", at: "2026-10-07T12:00:00+00:00", endpoint: "", url: null };
    const last = job({ id: "upload-2", action: "upload", upload });
    expect(clearable([])).toBe(false);
    expect(
      clearable([
        job({ status: "queued" }),
        job({ id: "job-2", status: "running" }),
        job({ id: "job-3", action: "upload", status: "unknown" }),
        last,
        job({ id: "upload-3", study_id: "caffeine/Other", action: "upload", upload }),
      ]),
    ).toBe(false);
    // An earlier upload of the same study goes.
    expect(clearable([job({ id: "upload-1", action: "upload", upload }), last])).toBe(true);
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
