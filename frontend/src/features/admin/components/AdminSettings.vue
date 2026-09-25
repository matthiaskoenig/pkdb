<script setup lang="ts">
import { onMounted } from "vue";
import { useAdministration } from "../useAdministration";
const {
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
  studySid,
  loadedSid,
  studyAccess,
  curatorIds,
  roles,
  canAdminister,
  load,
  search,
  closeInvitation,
  sendInvitation,
  update,
  resolve,
  loadAudit,
  loadStudy,
  saveStudy,
  date,
  statusLabel,
} = useAdministration();
onMounted(() => {
  void load();
});
</script>
<template>
  <v-card variant="outlined" class="pa-6">
    <h2 class="text-h6 mb-2">User administration</h2>
    <p>
      Role changes take effect immediately. Administrator privileges are
      reserved for the designated account.
    </p>
    <v-alert v-if="error" type="error">{{ error }}</v-alert
    ><v-alert v-if="notice" type="success">{{ notice }}</v-alert>
    <v-alert v-if="!canAdminister" type="info">
      Sign in with an administrator account to manage users.
    </v-alert>
    <v-form @submit.prevent="search">
      <v-text-field
        v-model="query"
        label="Search usernames"
        variant="outlined"
        append-icon="fas fa-search"
        @click:append="search"
      />
    </v-form>
    <v-table>
      <thead>
        <tr>
          <th>User</th>
          <th>Role</th>
          <th>Status</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.id">
          <td>
            <strong>{{ user.display_name }}</strong>
            <div class="text-caption">
              @{{ user.username }} · ID {{ user.id }} ·
              {{ user.email || "No email" }}
            </div>
          </td>
          <td>
            <v-select
              v-if="user.role !== 'admin'"
              v-model="user.proposedRole"
              :aria-label="'Role for @' + user.username"
              :items="roles"
              density="compact"
              hide-details
              style="min-width: 120px"
            /><span v-else>Administrator</span>
          </td>
          <td>{{ statusLabel(user) }}</td>
          <td v-if="user.role !== 'admin'">
            <v-btn
              size="small"
              variant="text"
              :disabled="busy || user.proposedRole === user.role"
              @click="update(user, { role: user.proposedRole })"
            >
              Save role </v-btn
            ><v-btn
              v-if="user.active || user.can_activate"
              size="small"
              variant="text"
              :color="user.active ? 'error' : 'primary'"
              :disabled="busy"
              @click="update(user, { active: !user.active })"
            >
              {{ user.active ? "Suspend" : "Activate" }} </v-btn
            ><v-btn
              v-if="user.can_invite"
              size="small"
              variant="text"
              color="primary"
              :disabled="busy || !canAdminister"
              @click="
                invitationError = '';
                invitationUser = user;
              "
            >
              Invite
            </v-btn>
          </td>
          <td v-else>Protected</td>
        </tr>
      </tbody>
    </v-table>
    <div class="d-flex justify-end mt-4">
      <v-btn
        variant="text"
        :disabled="offset === 0 || busy"
        @click="load(offset - 50)"
      >
        Previous </v-btn
      ><v-btn
        variant="text"
        :disabled="users.length < 50 || busy"
        @click="load(offset + 50)"
      >
        Next
      </v-btn>
    </div>
    <v-dialog
      :model-value="!!invitationUser"
      @update:model-value="closeInvitation"
      max-width="480"
    >
      <v-card>
        <v-card-title>Send account invitation</v-card-title
        ><v-card-text v-if="invitationUser">
          <p>
            Invite <strong>@{{ invitationUser.username }}</strong> to claim
            their existing account as {{ invitationUser.role }}.
          </p>
          <p>
            Send to <strong>{{ invitationUser.email }}</strong
            >. Confirm this is the reviewed contact address for this person.
          </p>
          <p>
            The invitation expires in seven days. Sending again replaces their
            previous invitation.
          </p>
          <v-alert v-if="invitationError" type="error">
            {{ invitationError }}
          </v-alert> </v-card-text
        ><v-card-actions>
          <v-spacer /><v-btn
            variant="text"
            :disabled="busy"
            @click="invitationUser = null"
          >
            Cancel </v-btn
          ><v-btn
            color="primary"
            :loading="busy"
            :disabled="!canAdminister"
            @click="sendInvitation"
          >
            Send invitation
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-divider class="my-6" />
    <h2 class="text-h6 mb-3">Curator access requests</h2>
    <p v-if="!requests.length">No pending requests.</p>
    <div v-for="request in requests" :key="request.id" class="mb-4">
      <strong>{{ request.username }}</strong>
      <p class="my-2">{{ request.reason }}</p>
      <v-btn
        size="small"
        color="primary"
        :disabled="busy"
        @click="resolve(request, 'approved')"
      >
        Approve </v-btn
      ><v-btn
        size="small"
        variant="text"
        :disabled="busy"
        @click="resolve(request, 'rejected')"
      >
        Reject
      </v-btn>
    </div>
    <v-divider class="my-6" />
    <h2 class="text-h6 mb-3">Study access</h2>
    <p>
      Load the existing grants before changing curator assignments or
      visibility.
    </p>
    <v-form @submit.prevent="loadStudy">
      <v-text-field
        v-model="studySid"
        label="Study identifier"
        variant="outlined"
      /><v-btn type="submit" variant="outlined" :disabled="!studySid || busy">
        Load study access
      </v-btn>
    </v-form>
    <v-form v-if="studyAccess" class="mt-5" @submit.prevent="saveStudy">
      <p class="font-weight-medium">{{ loadedSid }}</p>
      <v-select
        v-model="studyAccess.access"
        :items="['public', 'private']"
        label="Visibility"
        variant="outlined"
      />
      <v-select
        v-model="studyAccess.licence"
        :items="['open', 'closed']"
        label="File licence"
        variant="outlined"
      />
      <v-text-field
        v-model="curatorIds"
        label="Assigned curator account IDs"
        hint="Comma-separated IDs from user management"
        persistent-hint
        variant="outlined"
      />
      <v-btn type="submit" color="primary" class="mt-4" :disabled="busy">
        Save study access
      </v-btn>
    </v-form>
    <v-divider class="my-6" />
    <div class="d-flex align-center justify-space-between mb-3">
      <h2 class="text-h6">Security audit events</h2>
      <v-btn
        variant="outlined"
        size="small"
        :disabled="busy"
        @click="loadAudit(0)"
      >
        {{ auditLoaded ? "Refresh" : "Load events" }}
      </v-btn>
    </div>
    <p class="text-caption text-medium-emphasis">
      Account, credential and access changes. Events are shown newest first.
    </p>
    <p v-if="auditLoaded && !events.length">No events in this page.</p>
    <v-table v-if="events.length">
      <thead>
        <tr>
          <th>Time</th>
          <th>Actor ID</th>
          <th>Action</th>
          <th>Target</th>
          <th>Details</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="event in events" :key="event.id">
          <td class="text-no-wrap">{{ date(event.created_at) }}</td>
          <td>{{ event.actor_id || "System" }}</td>
          <td>{{ event.action }}</td>
          <td>{{ event.target }}</td>
          <td>
            <details v-if="event.details && Object.keys(event.details).length">
              <summary>View changes</summary>
              <pre class="audit-details">{{
                JSON.stringify(event.details, null, 2)
              }}</pre>
            </details>
            <span v-else>None</span>
          </td>
        </tr>
      </tbody>
    </v-table>
    <div v-if="auditLoaded" class="d-flex justify-end mt-4">
      <v-btn
        variant="text"
        :disabled="auditOffset === 0 || busy"
        @click="loadAudit(auditOffset - 50)"
      >
        Previous events </v-btn
      ><v-btn
        variant="text"
        :disabled="events.length < 50 || busy"
        @click="loadAudit(auditOffset + 50)"
      >
        Next events
      </v-btn>
    </div>
  </v-card>
</template>
<style scoped>
.audit-details {
  max-width: 380px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  padding: 8px 0;
  font-size: 12px;
}
summary {
  cursor: pointer;
}
</style>
