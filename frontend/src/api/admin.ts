import { api } from "./client";
import {
  array,
  boolean,
  nullableText,
  number,
  record,
  role,
  text,
  type Role,
} from "./session";
import { parseEvent, type SecurityEvent } from "./account";
export type EditableRole = Exclude<Role, "admin">;
export interface AdminUser {
  id: number;
  username: string;
  display_name: string;
  role: Role;
  proposedRole: EditableRole;
  email: string | null;
  status: string;
  invitation_email_id: number | null;
  active: boolean;
  can_activate: boolean;
  can_invite: boolean;
}
export interface RoleRequest {
  id: number;
  username: string;
  reason: string;
  status: string;
}
export interface StudyAccess {
  access: string;
  licence: string;
  creator_id: number | null;
  curator_ids: number[];
}
export interface AuditEvent extends SecurityEvent {
  actor_id: number | null;
  details: Record<string, unknown>;
}
export const adminApi = {
  async users(
    q: string,
    offset: number,
    signal: AbortSignal,
  ): Promise<AdminUser[]> {
    return array(
      (
        await api.get<unknown>("/api/v1/admin/users", {
          params: { q, offset, limit: 50 },
          signal,
        })
      ).data,
      (item) => {
        const row = record(item),
          permission = role(row.role);
        return {
          id: number(row.id),
          username: text(row.username),
          display_name: text(row.display_name),
          role: permission,
          proposedRole: permission === "admin" ? "user" : permission,
          email: nullableText(row.email),
          status: text(row.status),
          invitation_email_id:
            row.invitation_email_id === null
              ? null
              : number(row.invitation_email_id),
          active: boolean(row.active),
          can_activate: boolean(row.can_activate),
          can_invite: boolean(row.can_invite),
        };
      },
    );
  },
  async updateUser(
    id: number,
    values: { role?: EditableRole; active?: boolean },
  ) {
    await api.patch(`/api/v1/admin/users/${id}`, values);
  },
  async invite(user: AdminUser) {
    if (user.invitation_email_id === null)
      throw new Error("No reviewed email address");
    await api.post(`/api/v1/admin/users/${user.id}/invitations`, {
      email_id: user.invitation_email_id,
    });
  },
  async requests(signal: AbortSignal): Promise<RoleRequest[]> {
    return array(
      (await api.get<unknown>("/api/v1/admin/role-requests", { signal })).data,
      (item) => {
        const row = record(item);
        return {
          id: number(row.id),
          username: text(row.username),
          reason: text(row.reason),
          status: text(row.status),
        };
      },
    );
  },
  async decide(id: number, status: "approved" | "rejected") {
    await api.patch(`/api/v1/admin/role-requests/${id}`, { status });
  },
  async access(sid: string, signal: AbortSignal): Promise<StudyAccess> {
    const row = record(
      (
        await api.get<unknown>(
          `/api/v1/admin/studies/${encodeURIComponent(sid)}/access`,
          { signal },
        )
      ).data,
    );
    return {
      access: text(row.access),
      licence: text(row.licence),
      creator_id: row.creator_id === null ? null : number(row.creator_id),
      curator_ids: array(row.curator_ids, number),
    };
  },
  async saveAccess(sid: string, values: StudyAccess) {
    await api.put(
      `/api/v1/admin/studies/${encodeURIComponent(sid)}/access`,
      values,
    );
  },
  async audit(offset: number, signal: AbortSignal): Promise<AuditEvent[]> {
    return array(
      (
        await api.get<unknown>("/api/v1/admin/audit-events", {
          params: { offset, limit: 50 },
          signal,
        })
      ).data,
      (item) => {
        const row = record(item);
        return {
          ...parseEvent(item),
          actor_id: row.actor_id === null ? null : number(row.actor_id),
          details: record(row.details),
        };
      },
    );
  },
};
