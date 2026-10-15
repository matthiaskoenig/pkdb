/**
 * The reads of the study pages of the website (#963): the Studies page, a study, its tables and
 * sources, from the documents that the backend stores at upload (`/api/v2/study-rows`,
 * `/api/v2/studies/{substance}/{name}/view...`), adapted to the documents of the shared study
 * views. The backend decides per request what the reader sees: the curation view of a study
 * that the reader may write (`audience` "curator"), else the public one.
 */
import axios from "axios";
import { api, apiBase } from "../../api/client";
import { errorMessage } from "../../api/errors";
import { ApiError, isAbort, SessionMissing } from "../../study-views/errors";
import {
  hasKeys,
  isRecord,
  isSourceView,
  isTableResponse,
  type IssueState,
  type PaperFile,
  type People,
  type Problem,
  type Profile,
  type SourceSummary,
  type SourceView,
  type StudyDetail,
  type StudyRow,
  type SyncState,
  type TableResponse,
} from "../../study-views/types";

/** Who reads a study, as the backend decides: who may write it, or everyone else. */
export type Audience = "public" | "curator";

/** The URL of a path of the API, such as an avatar, a paper or an image of a study. */
export function apiUrl(path: string): string {
  return path.startsWith("/") ? `${apiBase}${path}` : path;
}

/** The path of the view of a study `<substance>/<name>`, or of a part of it. */
export function viewPath(id: string, ...parts: string[]): string {
  const slash = id.indexOf("/");
  return [
    "/api/v2/studies",
    encodeURIComponent(id.slice(0, slash)),
    encodeURIComponent(id.slice(slash + 1)),
    "view",
    ...parts.map(encodeURIComponent),
  ].join("/");
}

function unexpected(request: string): Error {
  return new Error(`PK-DB sent an unexpected answer to ${request}.`);
}

function textOrNull(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

/** A profile as the views name people, with its avatar on the API; the backend sends more fields. */
function profileOf(value: unknown, request: string): Profile {
  if (!isRecord(value) || typeof value.username !== "string") throw unexpected(request);
  const avatar = textOrNull(value.avatar_url);
  return {
    username: value.username,
    display_name: textOrNull(value.display_name) ?? value.username,
    title: textOrNull(value.title),
    affiliation: textOrNull(value.affiliation),
    avatar_url: avatar === null ? null : apiUrl(avatar),
  };
}

function peopleOf(value: unknown, request: string): People {
  if (!isRecord(value) || !Array.isArray(value.curators) || !Array.isArray(value.collaborators))
    throw unexpected(request);
  return {
    creator: value.creator === null || value.creator === undefined ? null : profileOf(value.creator, request),
    curators: value.curators.map((entry: unknown) => {
      if (!isRecord(entry) || typeof entry.user !== "string") throw unexpected(request);
      return {
        user: entry.user,
        rating: typeof entry.rating === "number" ? entry.rating : null,
        profile: profileOf(entry.profile, request),
      };
    }),
    collaborators: value.collaborators.map((entry: unknown) => profileOf(entry, request)),
  };
}

// The study list

interface RowBody {
  id: string;
  name: string;
  substance: string;
  substances: string[];
  summary: StudyRow["summary"];
  counts: StudyRow["counts"];
  issue: IssueState | null;
  curator: boolean;
}

const isRowBody = hasKeys<RowBody>("id", "name", "substance", "substances", "summary", "counts", "issue", "curator");

export interface StudyRows {
  rows: StudyRow[];
  profiles: Profile[];
}

/**
 * The rows of `GET /api/v2/study-rows` as rows of the shared study list: what the local server
 * adds of its folders and jobs is neutral (a study uploads only without errors, so its check is
 * valid), and `curator` says whether the reader may write it.
 */
export function studyRows(body: unknown, request: string): StudyRows {
  if (!isRecord(body) || !Array.isArray(body.rows) || !isRecord(body.profiles)) throw unexpected(request);
  const rows = body.rows.map((row: unknown): StudyRow => {
    if (!isRowBody(row)) throw unexpected(request);
    return {
      id: row.id,
      name: row.name,
      path: row.id,
      duplicate: false,
      substance: row.substance,
      substances: row.substances,
      status: "valid",
      stale: false,
      files: [],
      last_upload: null,
      progress: null,
      report_id: null,
      summary: row.summary,
      reference: null,
      counts: row.counts,
      issue: row.issue,
      curator: row.curator,
    };
  });
  return { rows, profiles: Object.values(body.profiles).map((profile) => profileOf(profile, request)) };
}

// A study

interface ViewBody {
  id: string;
  audience: string;
  summary: StudyDetail["summary"];
  metadata: NonNullable<StudyDetail["metadata"]["value"]>;
  review: StudyDetail["review"]["value"];
  reference: StudyDetail["reference"];
  reference_match: boolean | null;
  people: unknown;
  acknowledged: StudyDetail["acknowledged"];
  sources: SourceSummary[];
  files: string[];
  papers: PaperFile[];
  tables: StudyDetail["tables"];
  table_kinds: StudyDetail["table_kinds"];
  targets: StudyDetail["targets"];
  name_lines: StudyDetail["name_lines"];
  issue: IssueState | null;
  problems: Problem[];
  counts: StudyDetail["counts"];
}

const isViewBody = hasKeys<ViewBody>(
  "id",
  "audience",
  "summary",
  "metadata",
  "review",
  "reference",
  "reference_match",
  "people",
  "acknowledged",
  "sources",
  "files",
  "papers",
  "tables",
  "table_kinds",
  "targets",
  "name_lines",
  "issue",
  "problems",
  "counts",
);

/** A study on the website has no workbook. */
const NO_SYNC: SyncState = { status: "not_checked", changes: 0, conflicts: 0 };

export interface StudyViewAnswer {
  audience: Audience;
  detail: StudyDetail;
}

/**
 * The view of a study as the detail of the shared views: study.json and review.json as documents
 * without a revision, which the website does not write, no jobs, conflicts or local files, and the
 * papers and images on the API.
 */
export function studyView(body: unknown, request: string): StudyViewAnswer {
  if (!isViewBody(body)) throw unexpected(request);
  const audience = body.audience;
  if (audience !== "public" && audience !== "curator") throw unexpected(request);
  return {
    audience,
    detail: {
      id: body.id,
      path: body.id,
      status: "valid",
      sync: NO_SYNC,
      counts: body.counts,
      summary: body.summary,
      issue: body.issue,
      problems: body.problems,
      message: null,
      last_upload: null,
      jobs: [],
      report_id: null,
      files_version: null,
      metadata: { revision: null, value: body.metadata, issues: [] },
      reference: body.reference,
      reference_match: body.reference_match,
      people: peopleOf(body.people, request),
      review: { revision: null, value: body.review, issues: [] },
      acknowledged: body.acknowledged,
      conflicts: [],
      sources: body.sources.map((source) => ({
        ...source,
        image_url: source.image_url === null ? null : apiUrl(source.image_url),
      })),
      files: body.files,
      papers: body.papers.map((paper) => ({ ...paper, url: apiUrl(paper.url) })),
      tables: body.tables,
      table_kinds: body.table_kinds,
      targets: body.targets,
      name_lines: body.name_lines,
    },
  };
}

export function tableView(body: unknown, request: string): TableResponse {
  if (!isTableResponse(body)) throw unexpected(request);
  return body;
}

export function sourceView(body: unknown, request: string): SourceView {
  if (!isSourceView(body)) throw unexpected(request);
  return { ...body, image_url: body.image_url === null ? null : apiUrl(body.image_url) };
}

// Requests

/**
 * The error of a failed read as the shared views know it: a cancelled read is an AbortError,
 * which no view shows; an answer of the server is an ApiError with its status and message.
 */
export function readError(caught: unknown, request: string): Error {
  if (axios.isCancel(caught) || isAbort(caught)) return new DOMException("The read was aborted.", "AbortError");
  if (axios.isAxiosError(caught)) {
    const status = caught.response?.status ?? 0;
    return new ApiError(status, { message: errorMessage(caught), code: status === 404 ? "not_found" : null }, request);
  }
  return caught instanceof Error ? caught : new Error(String(caught));
}

async function read(path: string, signal: AbortSignal | undefined): Promise<unknown> {
  try {
    return (await api.get<unknown>(path, signal ? { signal } : {})).data;
  } catch (caught) {
    throw readError(caught, `GET ${path}`);
  }
}

export const studyViewsApi = {
  async rows(signal?: AbortSignal): Promise<StudyRows> {
    const path = "/api/v2/study-rows";
    return studyRows(await read(path, signal), `GET ${path}`);
  },
  async study(id: string, signal?: AbortSignal): Promise<StudyViewAnswer> {
    const path = viewPath(id);
    return studyView(await read(path, signal), `GET ${path}`);
  },
  async table(id: string, file: string, signal?: AbortSignal): Promise<TableResponse> {
    const path = viewPath(id, "tables", file);
    return tableView(await read(path, signal), `GET ${path}`);
  },
  async source(id: string, name: string, signal?: AbortSignal): Promise<SourceView> {
    const path = viewPath(id, "sources", name);
    return sourceView(await read(path, signal), `GET ${path}`);
  },
  /** Resolves when the server serves the file at `url`; SessionMissing when the session ended. */
  async checkFile(url: string): Promise<void> {
    try {
      await api.get(url, { headers: { Range: "bytes=0-0" }, responseType: "arraybuffer" });
    } catch (caught) {
      if (axios.isAxiosError(caught) && caught.response?.status === 401)
        throw new SessionMissing("The session has ended.");
      throw readError(caught, `GET ${url}`);
    }
  },
};
