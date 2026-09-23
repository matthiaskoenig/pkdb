import { computed, onScopeDispose, ref, watch } from "vue";
import {
  adminApi,
  type AdminUser,
  type AuditEvent,
  type EditableRole,
  type RoleRequest,
  type StudyAccess,
  type Usage,
  type UsageKind,
} from "../../api/admin";
import { errorMessage } from "../../api/client";
import { useSessionStore } from "../../stores/session";
import { useAccountAction } from "../account/useAccountAction";
export function parseAccountIds(value: string): number[] {
  if (!value.trim()) return [];
  return [
    ...new Set(
      value.split(",").map((item) => {
        if (!/^\d+$/.test(item.trim()))
          throw new RangeError(
            "Enter positive account IDs separated by commas.",
          );
        const id = Number(item.trim());
        if (!Number.isSafeInteger(id) || id < 1)
          throw new RangeError(
            "Enter positive account IDs separated by commas.",
          );
        return id;
      }),
    ),
  ];
}
export function useAdministration() {
  const session = useSessionStore();
  const { busy, error, notice, run } = useAccountAction();
  const users = ref<AdminUser[]>([]),
    requests = ref<RoleRequest[]>([]),
    events = ref<AuditEvent[]>([]);
  const query = ref(""),
    offset = ref(0),
    auditOffset = ref(0),
    auditLoaded = ref(false);
  const invitationUser = ref<AdminUser | null>(null),
    invitationError = ref("");
  const usageUser = ref<AdminUser | null>(null),
    usage = ref<Usage | null>(null);
  const studySid = ref(""),
    loadedSid = ref(""),
    studyAccess = ref<StudyAccess | null>(null),
    curatorIds = ref(""),
    readerIds = ref("");
  const roles: EditableRole[] = ["user", "curator", "reviewer"];
  const usageKinds: UsageKind[] = ["account", "upload", "export"];
  const usageLabels: Record<UsageKind, string> = {
    account: "All requests",
    upload: "Study uploads",
    export: "Exports",
  };
  const recent = computed(
    () => session.profile?.role === "admin" && session.profile.mfa_recent,
  );
  let controller = new AbortController();
  function reset() {
    controller.abort();
    controller = new AbortController();
    users.value = [];
    requests.value = [];
    events.value = [];
    invitationUser.value = null;
    invitationError.value = "";
    usage.value = null;
    usageUser.value = null;
    studyAccess.value = null;
    loadedSid.value = "";
    curatorIds.value = "";
    readerIds.value = "";
  }
  watch(() => session.epoch, reset, { flush: "sync" });
  onScopeDispose(reset);
  async function loadPage(next: number, current: () => boolean) {
    const [accounts, pending] = await Promise.all([
      adminApi.users(query.value, next, controller.signal),
      adminApi.requests(controller.signal),
    ]);
    if (current()) {
      users.value = accounts;
      requests.value = pending.filter((row) => row.status === "pending");
      offset.value = next;
    }
  }
  function load(next = offset.value) {
    return run((current) => loadPage(next, current));
  }
  function search() {
    return load(0);
  }
  function closeInvitation(value: boolean) {
    if (!value) {
      invitationUser.value = null;
      invitationError.value = "";
    }
  }
  function sendInvitation() {
    return run(async (current) => {
      const user = invitationUser.value;
      if (!user) return;
      invitationError.value = "";
      try {
        await adminApi.invite(user);
        if (current()) {
          user.status = "pending";
          invitationUser.value = null;
          notice.value =
            "Invitation sent to " + user.email + ". It expires in seven days.";
        }
      } catch (cause) {
        if (current()) invitationError.value = errorMessage(cause);
      }
    });
  }
  function update(
    user: AdminUser,
    values: { role?: EditableRole; active?: boolean },
  ) {
    return run(async (current) => {
      await adminApi.updateUser(user.id, values);
      if (current()) await loadPage(offset.value, current);
    }, "Account updated.");
  }
  function resolve(request: RoleRequest, status: "approved" | "rejected") {
    return run(
      async (current) => {
        await adminApi.decide(request.id, status);
        if (current()) await loadPage(offset.value, current);
      },
      "Request " + status + ".",
    );
  }
  function loadUsage(user: AdminUser) {
    return run(async (current) => {
      usageUser.value = user;
      usage.value = null;
      const result = await adminApi.usage(user.id, controller.signal);
      if (current()) usage.value = result;
    });
  }
  function loadAudit(next = auditOffset.value) {
    return run(async (current) => {
      const result = await adminApi.audit(next, controller.signal);
      if (current()) {
        events.value = result;
        auditOffset.value = next;
        auditLoaded.value = true;
      }
    });
  }
  function loadStudy() {
    return run(async (current) => {
      studyAccess.value = null;
      const sid = studySid.value.trim();
      const result = await adminApi.access(sid, controller.signal);
      if (current()) {
        studyAccess.value = result;
        loadedSid.value = sid;
        curatorIds.value = result.curator_ids.join(", ");
        readerIds.value = result.reader_ids.join(", ");
      }
    });
  }
  function saveStudy() {
    return run(async () => {
      if (!studyAccess.value) return;
      await adminApi.saveAccess(loadedSid.value, {
        ...studyAccess.value,
        curator_ids: parseAccountIds(curatorIds.value),
        reader_ids: parseAccountIds(readerIds.value),
      });
    }, "Study access updated.");
  }
  function date(value: string | null) {
    return value ? new Date(value).toLocaleString() : "No active window";
  }
  function statusLabel(user: AdminUser) {
    const labels: Record<string, string> = {
      active: "Active",
      suspended: "Suspended",
      pending: "Awaiting verification",
      unclaimed: "Unclaimed",
      inactive: "Inactive",
    };
    return labels[user.status] || "Inactive";
  }
  return {
    users,
    requests,
    events,
    busy,
    error,
    notice,
    query,
    offset,
    auditOffset,
    auditLoaded,
    invitationUser,
    invitationError,
    usageUser,
    usage,
    studySid,
    loadedSid,
    studyAccess,
    curatorIds,
    readerIds,
    roles,
    usageKinds,
    usageLabels,
    recent,
    load,
    search,
    closeInvitation,
    sendInvitation,
    update,
    resolve,
    loadUsage,
    loadAudit,
    loadStudy,
    saveStudy,
    date,
    statusLabel,
  };
}
