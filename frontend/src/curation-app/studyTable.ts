/**
 * The rows of the study table of the overview: what each row shows besides the fields of its
 * study.
 */
import type { RouteLocationRaw } from "vue-router";
import type { Profile, StudyRow } from "./api/types";
import { activityLabel, issueUrl, problemLabels, type Tone, webUrl } from "./overview";
import { findProfile } from "./study";

/** The circles of the curators of a row: avatars, or avatars and a count of the others. */
export const CURATOR_SLOTS = 3;

export interface Curator {
  name: string;
  avatar: string | null;
  initials: string;
}

/** What a row shows besides the fields of its study row. */
export interface RowItem {
  row: StudyRow;
  curators: Curator[];
  /** The names of the curators that the count stands for. */
  others: string;
  /** How many curators the count stands for. */
  hidden: number;
  problems: { label: string; tone: Tone }[];
  activity: string | null;
  issue: { number: number; url: string } | null;
  upload: string | null;
}

function curatorOf(user: string, profiles: ReadonlyMap<string, Profile>): Curator {
  const profile = findProfile(profiles, user);
  const name = profile?.display_name ?? user;
  const words = name.split(/\s+/).filter(Boolean);
  const initials = (words.length > 1 ? `${words[0]![0]}${words.at(-1)![0]}` : name.slice(0, 1)).toUpperCase();
  return { name, avatar: profile?.avatar_url ?? null, initials };
}

/** The item of `row`; the study table builds it once per row object, so once per snapshot. */
export function rowItem(row: StudyRow, profiles: ReadonlyMap<string, Profile>, repository: string): RowItem {
  const people = (row.summary.curators ?? []).map((user) => curatorOf(user, profiles));
  // Beyond the slots, the last slot counts the curators that it hides.
  const cut = people.length > CURATOR_SLOTS ? CURATOR_SLOTS - 1 : people.length;
  const number = row.issue?.number ?? row.summary.issue ?? null;
  const url = issueUrl(row, repository);
  return {
    row,
    curators: people.slice(0, cut),
    others: people
      .slice(cut)
      .map((person) => person.name)
      .join(", "),
    hidden: people.length - cut,
    problems: problemLabels(row),
    activity: activityLabel(row),
    issue: number !== null && url !== null ? { number, url } : null,
    upload: webUrl(row.last_upload?.url),
  };
}

export function studyRoute(row: StudyRow): RouteLocationRaw {
  return { name: "Study", params: { substance: row.substance, name: row.name } };
}

export function aiTitle(row: StudyRow): string {
  const method = row.summary.provenance?.method;
  return method ? `AI curated with ${method}` : "AI curated";
}
