import { api } from "./client";
import { isRecord } from "./errors";
export type Role = "user" | "curator" | "reviewer" | "admin";
export type Provider = "github" | "orcid";
export interface EmailAddress {
  id: number;
  email: string;
  is_primary: boolean;
  is_verified: boolean;
}
export interface Profile {
  id: number;
  username: string;
  role: Role;
  display_name: string;
  affiliation: string;
  title: string;
  github: string;
  orcid: string;
  github_visible: boolean;
  orcid_visible: boolean;
  github_provenance: string;
  orcid_provenance: string;
  avatar_url: string;
  emails: EmailAddress[];
  mfa_required: boolean;
  mfa_enrolled: boolean;
  mfa_recent: boolean;
}
export function record(value: unknown): Record<string, unknown> {
  if (!isRecord(value)) throw new Error("Invalid API response");
  return value;
}
export function text(value: unknown): string {
  if (typeof value !== "string") throw new Error("Invalid API text");
  return value;
}
export function number(value: unknown): number {
  if (typeof value !== "number" || !Number.isFinite(value))
    throw new Error("Invalid API number");
  return value;
}
export function boolean(value: unknown): boolean {
  if (typeof value !== "boolean") throw new Error("Invalid API boolean");
  return value;
}
export function array<T>(value: unknown, parse: (item: unknown) => T): T[] {
  if (!Array.isArray(value)) throw new Error("Invalid API list");
  return value.map(parse);
}
export function nullableText(value: unknown): string | null {
  return value === null ? null : text(value);
}
export function role(value: unknown): Role {
  if (
    value === "user" ||
    value === "curator" ||
    value === "reviewer" ||
    value === "admin"
  )
    return value;
  throw new Error("Invalid role");
}
export function provider(value: unknown): Provider {
  if (value === "github" || value === "orcid") return value;
  throw new Error("Invalid provider");
}
export function parseProfile(value: unknown): Profile {
  const p = record(value);
  return {
    id: number(p.id),
    username: text(p.username),
    role: role(p.role),
    display_name: text(p.display_name),
    affiliation: nullableText(p.affiliation) || "",
    title: nullableText(p.title) || "",
    github: nullableText(p.github) || "",
    orcid: nullableText(p.orcid) || "",
    github_visible: boolean(p.github_visible),
    orcid_visible: boolean(p.orcid_visible),
    github_provenance: nullableText(p.github_provenance) || "",
    orcid_provenance: nullableText(p.orcid_provenance) || "",
    avatar_url: text(p.avatar_url),
    emails: array(p.emails, (item) => {
      const e = record(item);
      return {
        id: number(e.id),
        email: text(e.email),
        is_primary: boolean(e.is_primary),
        is_verified: boolean(e.is_verified),
      };
    }),
    mfa_required: boolean(p.mfa_required),
    mfa_enrolled: boolean(p.mfa_enrolled),
    mfa_recent: boolean(p.mfa_recent),
  };
}
export const sessionApi = {
  async profile() {
    return parseProfile((await api.get<unknown>("/api/v1/me")).data);
  },
  async login(username: string, password: string) {
    await api.post("/api/v1/auth/login", { username, password });
  },
  async logout() {
    await api.post("/api/v1/auth/logout");
  },
  async reauthenticate(password: string) {
    await api.post("/api/v1/auth/reauthenticate", { password });
  },
};
