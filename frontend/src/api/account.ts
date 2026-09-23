import { api } from "./client";
import {
  array,
  boolean,
  nullableText,
  number,
  record,
  text,
} from "./session";
export interface ProfileForm {
  display_name: string;
  title: string;
  affiliation: string;
  github?: string;
  orcid?: string;
  github_visible: boolean;
  orcid_visible: boolean;
}
export interface ApiKey {
  id: number;
  name: string;
  prefix: string;
  scopes: string[];
  expires_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}
export interface BrowserSession {
  id: number;
  current: boolean;
  device: string;
  last_seen_at: string | null;
  expires_at: string;
  revoked_at: string | null;
}
export interface AssignedStudy {
  sid: string;
  name: string;
}
export interface SecurityEvent {
  id: number;
  action: string;
  target: string;
  created_at: string;
}
export function parseEvent(value: unknown): SecurityEvent {
  const row = record(value);
  return {
    id: number(row.id),
    action: text(row.action),
    target: text(row.target),
    created_at: text(row.created_at),
  };
}
export function profilePayload(form: ProfileForm): ProfileForm {
  return { ...form };
}
export const accountApi = {
  async register(username: string, email: string, password: string) {
    await api.post("/api/v1/auth/register", { username, email, password });
  },
  async verify(key: string) {
    await api.post("/api/v1/auth/verify-email", { key });
  },
  async requestReset(email: string) {
    await api.post("/api/v1/auth/request-password-reset", { email });
  },
  async reset(key: string, password: string) {
    await api.post("/api/v1/auth/reset-password", { key, password });
  },
  async invite(token: string, password: string) {
    await api.post("/api/v1/auth/invitations/accept", {
      token: token.trim(),
      password,
    });
  },
  async saveProfile(values: ProfileForm) {
    await api.patch("/api/v1/me", values);
  },
  async avatar(file: File) {
    await api.put("/api/v1/me/avatar", file, {
      headers: { "Content-Type": file.type },
    });
  },
  async removeAvatar() {
    await api.delete("/api/v1/me/avatar");
  },
  async addEmail(email: string) {
    await api.post("/accounts/emails/", { email });
  },
  async makePrimary(id: number) {
    await api.patch(`/accounts/emails/${id}/`, { is_primary: true });
  },
  async removeEmail(id: number) {
    await api.delete(`/accounts/emails/${id}/`);
  },
  async resend(email: string) {
    await api.post("/api/v1/auth/resend-verification", { email });
  },
  async keys(signal: AbortSignal): Promise<ApiKey[]> {
    return array(
      (await api.get<unknown>("/api/v1/me/api-keys", { signal })).data,
      (item) => {
        const row = record(item);
        return {
          id: number(row.id),
          name: text(row.name),
          prefix: text(row.prefix),
          scopes: array(row.scopes, text),
          expires_at: text(row.expires_at),
          last_used_at: nullableText(row.last_used_at),
          revoked_at: nullableText(row.revoked_at),
        };
      },
    );
  },
  async createKey(name: string, lifetime_days: number, write: boolean) {
    return text(
      record(
        (
          await api.post<unknown>("/api/v1/me/api-keys", {
            name,
            lifetime_days,
            scopes: write ? ["read", "studies:write"] : ["read"],
          })
        ).data,
      ).secret,
    );
  },
  async rotateKey(id: number) {
    return text(
      record(
        (
          await api.post<unknown>(`/api/v1/me/api-keys/${id}/rotate`, {
            overlap_hours: 24,
          })
        ).data,
      ).secret,
    );
  },
  async revokeKey(id: number) {
    await api.delete(`/api/v1/me/api-keys/${id}`);
  },
  async sessions(signal: AbortSignal): Promise<BrowserSession[]> {
    return array(
      (await api.get<unknown>("/api/v1/me/sessions", { signal })).data,
      (item) => {
        const row = record(item);
        return {
          id: number(row.id),
          current: boolean(row.current),
          device: text(row.device),
          last_seen_at: nullableText(row.last_seen_at),
          expires_at: text(row.expires_at),
          revoked_at: nullableText(row.revoked_at),
        };
      },
    );
  },
  async revokeSession(id: number) {
    await api.delete(`/api/v1/me/sessions/${id}`);
  },
  async requestCurator(reason: string) {
    await api.post("/api/v1/me/role-requests", { reason });
  },
  async studies(offset: number, signal: AbortSignal): Promise<AssignedStudy[]> {
    return array(
      (
        await api.get<unknown>("/api/v1/me/studies", {
          params: { offset, limit: 50 },
          signal,
        })
      ).data,
      (item) => {
        const row = record(item);
        return { sid: text(row.sid), name: text(row.name) };
      },
    );
  },
  async events(offset: number, signal: AbortSignal): Promise<SecurityEvent[]> {
    return array(
      (
        await api.get<unknown>("/api/v1/me/security-events", {
          params: { offset, limit: 50 },
          signal,
        })
      ).data,
      parseEvent,
    );
  },
};
