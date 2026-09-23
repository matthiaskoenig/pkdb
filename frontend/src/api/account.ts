import { api } from "./client";
import {
  array,
  boolean,
  nullableText,
  number,
  provider,
  record,
  text,
  type Profile,
  type Provider,
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
export interface Identity {
  id: number;
  provider: Provider;
  label: string;
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
export function profilePayload(
  form: ProfileForm,
  profile: Profile,
): ProfileForm {
  const values = { ...form };
  if (profile.github_provenance === "authenticated") delete values.github;
  if (profile.orcid_provenance === "authenticated") delete values.orcid;
  return values;
}
export const accountApi = {
  async providers(signal?: AbortSignal) {
    return array(
      record(
        (
          await api.get<unknown>(
            "/api/v1/auth/providers",
            signal ? { signal } : {},
          )
        ).data,
      ).providers,
      provider,
    );
  },
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
  async onboarding(username: string, email: string) {
    await api.post("/api/v1/auth/onboarding", { username, email });
  },
  async claimInvitation(token: string) {
    await api.post("/api/v1/auth/onboarding/invitation", {
      token: token.trim(),
    });
  },
  async enroll() {
    const row = record(
      (await api.post<unknown>("/api/v1/auth/mfa/enroll")).data,
    );
    return { secret: text(row.secret) };
  },
  async verifyMfa(code: string, confirm: boolean) {
    const row = record(
      (
        await api.post<unknown>(
          "/api/v1/auth/mfa/" + (confirm ? "confirm" : "verify"),
          { code },
        )
      ).data,
    );
    return row.recovery_codes === undefined
      ? []
      : array(row.recovery_codes, text);
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
  async identities(signal: AbortSignal): Promise<Identity[]> {
    return array(
      (await api.get<unknown>("/api/v1/me/identities", { signal })).data,
      (item) => {
        const row = record(item);
        return {
          id: number(row.id),
          provider: provider(row.provider),
          label: text(row.label),
        };
      },
    );
  },
  async providerAction(value: Provider, action: "link" | "reauthenticate") {
    const url = text(
      record(
        (await api.post<unknown>(`/api/v1/me/identities/${value}/${action}`))
          .data,
      ).authorization_url,
    );
    const target = new URL(url);
    if (
      target.protocol !== "https:" ||
      !["github.com", "orcid.org"].includes(target.hostname)
    )
      throw new Error("Invalid provider redirect");
    return url;
  },
  async unlink(id: number) {
    await api.delete(`/api/v1/me/identities/${id}`);
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
