import { defineStore } from "pinia";
import { getJson, postJson } from "../api/client";
import {
  isDirectories,
  isGitHubAssignments,
  isRecord,
  isSnapshot,
  type Directories,
  type GitHubAssignments,
  type Guard,
  type SaveMode,
  type Snapshot,
} from "../api/types";
import { POLL_INTERVAL_MS, usePolling } from "../composables/usePolling";

/** The settings that `POST /local/settings` accepts; the API key is write-only. */
export interface Settings {
  endpoint?: string;
  api_key?: string;
  user?: string;
  github_user?: string;
  offline?: boolean;
  repository?: string;
}

/** The workspace, the connection, the study rows and the jobs of `GET /local/state`. */
export const useOverviewStore = defineStore("curation-overview", () => {
  const polling = usePolling<Snapshot>(
    (etag, signal) => getJson("/local/state", isSnapshot, { etag, signal }),
    POLL_INTERVAL_MS,
    { immediate: false },
  );

  /** POST an action, then load the state that it changed. */
  async function act<T>(path: string, body: Record<string, unknown>, accept: Guard<T>): Promise<T> {
    const result = await postJson(path, body, accept);
    await polling.refresh();
    return result;
  }

  function selectWorkspace(path: string): Promise<Snapshot> {
    return act("/local/workspace", { path }, isSnapshot);
  }

  function forgetWorkspace(path: string): Promise<Snapshot> {
    return act("/local/workspace/forget", { path }, isSnapshot);
  }

  /** The folders of `path`, by default of the workspace. */
  function listDirectories(path?: string): Promise<Directories> {
    return postJson("/local/directories", path === undefined ? {} : { path }, isDirectories);
  }

  function configure(settings: Settings): Promise<Snapshot> {
    return act("/local/settings", { ...settings }, isSnapshot);
  }

  function setMode(ids: string[], mode: SaveMode): Promise<Snapshot> {
    return act("/local/mode", { ids, mode }, isSnapshot);
  }

  async function enqueue(ids: string[], action: "validate" | "validate_remote" | "upload"): Promise<void> {
    await act("/local/jobs", { ids, action }, isRecord);
  }

  function cancelJobs(ids: string[]): Promise<Snapshot> {
    return act("/local/jobs/cancel", { ids }, isSnapshot);
  }

  function clearHistory(): Promise<Snapshot> {
    return act("/local/history/clear", {}, isSnapshot);
  }

  /** Upload again after the curator inspected the server for an upload with an unknown outcome. */
  function retry(id: string): Promise<Snapshot> {
    return act("/local/retry", { id, acknowledge_unknown: true }, isSnapshot);
  }

  function pause(paused: boolean): Promise<Snapshot> {
    return act("/local/pause", { paused }, isSnapshot);
  }

  /** Reconcile unknown uploads with the server, of the given studies or of all, and resume. */
  function resume(ids?: string[]): Promise<Snapshot> {
    return act("/local/resume", ids === undefined ? {} : { ids }, isSnapshot);
  }

  /** Open the folder of a study, or one of its files, with the system; `reveal` shows it in its folder. */
  async function openFile(studyId: string, file?: string, reveal?: boolean): Promise<void> {
    await postJson(
      "/local/files/open",
      { study_id: studyId, ...(file === undefined ? {} : { file }), ...(reveal === undefined ? {} : { reveal }) },
      isRecord,
    );
  }

  function refreshAssignments(): Promise<GitHubAssignments> {
    return act("/local/assignments/refresh", {}, isGitHubAssignments);
  }

  return {
    snapshot: polling.data,
    error: polling.error,
    start: polling.start,
    stop: polling.stop,
    refresh: polling.refresh,
    selectWorkspace,
    forgetWorkspace,
    listDirectories,
    configure,
    setMode,
    enqueue,
    cancelJobs,
    clearHistory,
    retry,
    pause,
    resume,
    openFile,
    refreshAssignments,
  };
});
