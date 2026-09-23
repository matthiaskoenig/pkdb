<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { apiBase } from "../../../api/client";
import { useSessionStore } from "../../../stores/session";
import { useAccountAction } from "../useAccountAction";
import { useAccountActivity } from "../useAccountActivity";
import { useProfile } from "../useProfile";
import { useCredentials } from "../useCredentials";
import { useReauthentication } from "../useReauthentication";
import type { EmailAddress } from "../../../api/session";
import type { ApiKey, BrowserSession } from "../../../api/account";
import UserLogin from "./UserLogin.vue";
import AdminSettings from "../../admin/components/AdminSettings.vue";
const session = useSessionStore();
const profile = computed(() => session.profile);
const avatarUrl = computed(() =>
  profile.value ? apiBase + profile.value.avatar_url : "",
);
const { busy, error, notice, run } = useAccountAction();
const profileActions = useProfile();
const { form, photo, newEmail, curatorReason } = profileActions;
const credentials = useCredentials();
const {
  keys,
  sessions,
  secret,
  secretDialog,
  rotated,
  keyName,
  keyDays,
  keyWrite,
  canWrite,
} = credentials;
const {
  reauthDialog,
  reauthPassword,
  reauthError,
  reauthBusy,
  clearPending,
  secure,
  reauthenticate,
} = useReauthentication();
const activity = useAccountActivity();
const {
  rows: studies,
  offset: studiesOffset,
  loading: studiesLoading,
  error: studiesError,
} = activity.studies;
const {
  rows: events,
  offset: eventsOffset,
  loading: eventsLoading,
  error: eventsError,
} = activity.events;
const tab = ref(0);
watch(
  () => session.epoch,
  () => {
    tab.value = 0;
  },
);
watch(
  profile,
  (value) => {
    if (value) {
      void run(async () => {
        await credentials.loadCredentials();
      });
      void activity.studies.refresh();
      void activity.events.refresh();
    }
  },
  { immediate: true },
);
function loadActivity(kind: "studies" | "events", offset: number) {
  return activity[kind].refresh(offset);
}
function date(value: string | null) {
  return value ? new Date(value).toLocaleString() : "Never";
}
function expired(value: string) {
  return new Date(value).getTime() <= Date.now();
}
const saveProfile = () => run(profileActions.saveProfile, "Profile saved.");
const uploadPhoto = () => run(profileActions.uploadPhoto, "Photo updated.");
const removePhoto = () => run(profileActions.removePhoto, "Photo removed.");
const requestCurator = () =>
  run(
    profileActions.requestCurator,
    "Your curator access request has been sent.",
  );
const addEmail = () =>
  run(profileActions.addEmail, "Verification email requested.");
const makePrimary = (value: EmailAddress) =>
  run(() => profileActions.makePrimary(value), "Primary address updated.");
const removeEmail = (value: EmailAddress) =>
  run(() => profileActions.removeEmail(value), "Address removed.");
const resend = (value: EmailAddress) =>
  run(() => profileActions.resend(value), "Verification email requested.");
const createKey = () => run(credentials.createKey);
const rotateKey = (value: ApiKey) => run(() => credentials.rotateKey(value));
const revokeKey = (value: ApiKey) =>
  run(() => credentials.revokeKey(value), "API key revoked.");
const revokeSession = (value: BrowserSession) =>
  run(() => credentials.revokeSession(value), "Session revoked.");
</script>
<template>
  <v-container class="account-page py-8">
    <v-progress-linear
      v-if="!session.ready"
      indeterminate
      aria-label="Loading account"
    />
    <user-login v-else-if="!profile" class="login-card mx-auto" />
    <template v-else-if="profile">
      <div class="d-flex align-center mb-7">
        <v-avatar size="72" color="surface-variant" class="mr-5">
          <img
            :src="avatarUrl"
            :alt="profile.display_name"
            style="object-fit: cover"
          />
        </v-avatar>
        <div>
          <h1 class="text-h4 font-weight-medium">Account settings</h1>
          <p class="mb-0 mt-2 text-medium-emphasis">
            @{{ profile.username }}
            <v-chip size="small" class="ml-2">{{ profile.role }}</v-chip>
          </p>
        </div>
      </div>
      <v-btn
        class="mb-4"
        variant="outlined"
        :loading="busy"
        @click="
          run(async () => {
            await session.logout();
          })
        "
      >
        Sign out
      </v-btn>
      <v-alert
        v-if="error"
        type="error"
        closable
        @update:model-value="error = ''"
      >
        {{ error }}
      </v-alert>
      <v-alert
        v-if="notice"
        type="success"
        closable
        @update:model-value="notice = ''"
      >
        {{ notice }}
      </v-alert>
      <v-card
        v-if="profile.role === 'user'"
        variant="outlined"
        class="pa-5 mb-5"
      >
        <h2 class="text-h6">Request curator access</h2>
        <p>Curators can upload studies and edit studies assigned to them.</p>
        <v-textarea
          v-model="curatorReason"
          label="Tell us about your planned contributions"
          variant="outlined"
          rows="2"
          maxlength="2000"
        /><v-btn
          color="primary"
          :disabled="!curatorReason.trim() || busy"
          @click="requestCurator"
        >
          Send request
        </v-btn>
      </v-card>
      <v-tabs
        aria-label="Account settings sections"
        v-model="tab"
        class="mb-6"
        show-arrows
      >
        <v-tab id="account-tab-0" aria-controls="account-panel-0" :value="0"
          >Profile</v-tab
        ><v-tab id="account-tab-1" aria-controls="account-panel-1" :value="1"
          >Email addresses</v-tab
        ><v-tab id="account-tab-2" aria-controls="account-panel-2" :value="2"
          >API keys</v-tab
        ><v-tab id="account-tab-3" aria-controls="account-panel-3" :value="3"
          >Sessions</v-tab
        ><v-tab id="account-tab-5" aria-controls="account-panel-5" :value="5"
          >Assigned studies</v-tab
        ><v-tab id="account-tab-6" aria-controls="account-panel-6" :value="6"
          >Security history</v-tab
        ><v-tab
          id="account-tab-7"
          aria-controls="account-panel-7"
          :value="7"
          v-if="profile.role === 'admin'"
        >
          Administration
        </v-tab>
      </v-tabs>
      <v-window v-model="tab">
        <v-window-item
          id="account-panel-0"
          role="tabpanel"
          aria-labelledby="account-tab-0"
          :aria-hidden="tab !== 0"
          :inert="tab !== 0 || undefined"
          :tabindex="tab === 0 ? 0 : -1"
          :value="0"
        >
          <v-card variant="outlined" class="pa-6">
            <h2 class="text-h6 mb-2">Public profile</h2>
            <p class="text-medium-emphasis">
              These details can appear with your scientific contributions. Your
              email addresses stay private.
            </p>
            <v-row>
              <v-col cols="12" md="8">
                <v-text-field
                  v-model="form.display_name"
                  label="Display name"
                  variant="outlined"
                  maxlength="200"
                  hint="Leave blank to use your username"
                  persistent-hint
                />
                <v-row>
                  <v-col cols="12" sm="4">
                    <v-text-field
                      v-model="form.title"
                      label="Title (optional)"
                      variant="outlined"
                      maxlength="100"
                    /> </v-col
                  ><v-col cols="12" sm="8">
                    <v-text-field
                      v-model="form.affiliation"
                      label="Affiliation (optional)"
                      variant="outlined"
                      maxlength="250"
                    />
                  </v-col>
                </v-row>
                <v-text-field
                  v-model="form.github"
                  label="GitHub handle (optional)"
                  variant="outlined"
                  hint="Optional public profile reference"
                  persistent-hint
                  maxlength="39"
                />
                <v-checkbox
                  v-model="form.github_visible"
                  label="Show GitHub on my public profile"
                />
                <v-text-field
                  v-model="form.orcid"
                  label="ORCID iD (optional)"
                  variant="outlined"
                  placeholder="0000-0000-0000-0000"
                  hint="Optional public profile reference"
                  persistent-hint
                  class="mt-4"
                />
                <v-checkbox
                  v-model="form.orcid_visible"
                  label="Show ORCID on my public profile"
                />
                <v-btn
                  color="primary"
                  :loading="busy"
                  class="mt-4"
                  @click="saveProfile"
                >
                  Save profile
                </v-btn> </v-col
              ><v-col cols="12" md="4">
                <h3 class="text-subtitle-1 mb-3">Profile photo</h3>
                <v-file-input
                  v-model="photo"
                  accept="image/jpeg,image/png,image/webp"
                  label="Choose photo"
                  variant="outlined"
                  density="compact"
                  hint="JPEG, PNG or WebP. Up to 5 MiB."
                  persistent-hint
                />
                <v-btn
                  size="small"
                  color="primary"
                  :disabled="!photo || busy"
                  class="mt-4 mr-2"
                  @click="uploadPhoto"
                >
                  Upload </v-btn
                ><v-btn
                  size="small"
                  variant="text"
                  :disabled="busy"
                  class="mt-4"
                  @click="removePhoto"
                >
                  Remove photo
                </v-btn>
              </v-col>
            </v-row>
          </v-card>
        </v-window-item>
        <v-window-item
          id="account-panel-1"
          role="tabpanel"
          aria-labelledby="account-tab-1"
          :aria-hidden="tab !== 1"
          :inert="tab !== 1 || undefined"
          :tabindex="tab === 1 ? 0 : -1"
          :value="1"
        >
          <v-card variant="outlined" class="pa-6">
            <h2 class="text-h6 mb-2">Private contact addresses</h2>
            <p>
              Verify an address before using it for recovery or making it
              primary.
            </p>
            <v-list>
              <v-list-item
                v-for="email in profile.emails"
                :key="email.id"
                class="px-0"
              >
                <div>
                  <v-list-item-title>{{ email.email }}</v-list-item-title
                  ><v-list-item-subtitle>
                    {{ email.is_primary ? "Primary · " : ""
                    }}{{
                      email.is_verified ? "Verified" : "Awaiting verification"
                    }}
                  </v-list-item-subtitle>
                </div>
                <v-btn
                  v-if="!email.is_verified"
                  size="small"
                  variant="text"
                  :disabled="busy"
                  @click="resend(email)"
                >
                  Resend
                </v-btn>
                <v-btn
                  v-if="!email.is_primary && email.is_verified"
                  size="small"
                  variant="text"
                  :disabled="busy"
                  @click="secure(() => makePrimary(email))"
                >
                  Make primary
                </v-btn>
                <v-btn
                  v-if="!email.is_primary"
                  size="small"
                  variant="text"
                  color="error"
                  :disabled="busy"
                  @click="secure(() => removeEmail(email))"
                >
                  Remove
                </v-btn>
              </v-list-item>
            </v-list>
            <v-form
              v-if="profile.emails.length < 2"
              @submit.prevent="secure(addEmail)"
              class="mt-5"
            >
              <v-text-field
                v-model="newEmail"
                type="email"
                label="Secondary email"
                variant="outlined"
                class="email-field"
              />
              <v-btn
                type="submit"
                color="primary"
                :disabled="!newEmail || busy"
              >
                Add and verify
              </v-btn>
            </v-form>
          </v-card>
        </v-window-item>
        <v-window-item
          id="account-panel-2"
          role="tabpanel"
          aria-labelledby="account-tab-2"
          :aria-hidden="tab !== 2"
          :inert="tab !== 2 || undefined"
          :tabindex="tab === 2 ? 0 : -1"
          :value="2"
        >
          <v-card variant="outlined" class="pa-6">
            <h2 class="text-h6 mb-2">Personal API keys</h2>
            <p>
              Use a separate key for each script or application. Keys follow
              your current role and study assignments.
            </p>
            <v-form @submit.prevent="secure(createKey)">
              <v-row align="center">
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model="keyName"
                    label="Key name"
                    placeholder="Laptop analysis"
                    variant="outlined"
                    maxlength="100"
                    hide-details
                  /> </v-col
                ><v-col cols="6" md="3">
                  <v-text-field
                    v-model.number="keyDays"
                    type="number"
                    min="1"
                    max="365"
                    label="Expires in days"
                    variant="outlined"
                    hide-details
                  /> </v-col
                ><v-col cols="6" md="3">
                  <v-btn
                    type="submit"
                    color="primary"
                    :disabled="!keyName.trim() || busy"
                  >
                    Create key
                  </v-btn>
                </v-col>
              </v-row>
              <v-checkbox
                v-if="canWrite"
                v-model="keyWrite"
                label="Allow study uploads and edits within my permissions"
              />
              <p v-else class="text-caption mt-3">Read access only</p>
            </v-form>
            <v-divider class="my-5" />
            <p v-if="!keys.length" class="text-medium-emphasis">
              No API keys yet.
            </p>
            <div v-for="key in keys" :key="key.id" class="credential-row py-4">
              <div>
                <strong>{{ key.name }}</strong>
                <v-chip size="small" class="ml-2">
                  {{
                    key.revoked_at
                      ? "Revoked"
                      : expired(key.expires_at)
                        ? "Expired"
                        : key.scopes.join(", ")
                  }}
                </v-chip>
                <div class="text-caption text-medium-emphasis mt-2">
                  {{ key.prefix }}… · Expires {{ date(key.expires_at) }} · Last
                  used {{ date(key.last_used_at) }}
                </div>
              </div>
              <div v-if="!key.revoked_at && !expired(key.expires_at)">
                <v-btn
                  size="small"
                  variant="text"
                  :disabled="busy"
                  @click="secure(() => rotateKey(key))"
                >
                  Rotate </v-btn
                ><v-btn
                  size="small"
                  variant="text"
                  color="error"
                  :disabled="busy"
                  @click="revokeKey(key)"
                >
                  Revoke
                </v-btn>
              </div>
            </div>
          </v-card>
        </v-window-item>
        <v-window-item
          id="account-panel-3"
          role="tabpanel"
          aria-labelledby="account-tab-3"
          :aria-hidden="tab !== 3"
          :inert="tab !== 3 || undefined"
          :tabindex="tab === 3 ? 0 : -1"
          :value="3"
        >
          <v-card variant="outlined" class="pa-6">
            <h2 class="text-h6 mb-2">Browser sessions</h2>
            <p>
              Revoke a session to sign out that browser. API keys are managed
              separately.
            </p>
            <div
              v-for="browserSession in sessions"
              :key="browserSession.id"
              class="credential-row py-4"
            >
              <div class="session-info">
                <strong>{{
                  browserSession.current ? "This browser" : "Browser session"
                }}</strong>
                <div class="text-caption text-truncate">
                  {{ browserSession.device || "Unknown browser" }}
                </div>
                <div class="text-caption text-medium-emphasis">
                  Last active {{ date(browserSession.last_seen_at) }} ·
                  {{
                    browserSession.revoked_at
                      ? "Revoked"
                      : "Expires " + date(browserSession.expires_at)
                  }}
                </div>
              </div>
              <v-btn
                v-if="!browserSession.revoked_at"
                size="small"
                variant="text"
                color="error"
                :disabled="busy"
                @click="revokeSession(browserSession)"
              >
                {{ browserSession.current ? "Sign out" : "Revoke" }}
              </v-btn>
            </div>
          </v-card>
        </v-window-item>
        <v-window-item
          id="account-panel-5"
          role="tabpanel"
          aria-labelledby="account-tab-5"
          :aria-hidden="tab !== 5"
          :inert="tab !== 5 || undefined"
          :tabindex="tab === 5 ? 0 : -1"
          :value="5"
        >
          <v-card variant="outlined" class="pa-6">
            <div class="d-flex align-center justify-space-between mb-3">
              <h2 class="text-h6">Assigned studies</h2>
              <v-btn
                size="small"
                variant="outlined"
                :loading="studiesLoading"
                @click="loadActivity('studies', 0)"
              >
                Refresh
              </v-btn>
            </div>
            <p>
              These studies have an explicit curator assignment to your account.
              Editing depends on your current role.
            </p>
            <p v-if="['reviewer', 'admin'].includes(profile.role)">
              Your role also allows editing studies outside this assignment
              list.
            </p>
            <v-alert v-if="studiesError" type="error">
              {{ studiesError }}
            </v-alert>
            <p v-if="!studiesLoading && !studiesError && !studies.length">
              No assigned studies on this page.
            </p>
            <v-list>
              <v-list-item
                v-for="study in studies"
                :key="study.sid"
                :to="'/data/' + encodeURIComponent(study.sid)"
              >
                <div>
                  <v-list-item-title>
                    {{ study.name || study.sid }} </v-list-item-title
                  ><v-list-item-subtitle>{{ study.sid }}</v-list-item-subtitle>
                </div>
              </v-list-item>
            </v-list>
            <div class="d-flex justify-end mt-4">
              <v-btn
                variant="text"
                :disabled="studiesOffset === 0 || studiesLoading"
                @click="loadActivity('studies', studiesOffset - 50)"
              >
                Previous </v-btn
              ><v-btn
                variant="text"
                :disabled="studies.length < 50 || studiesLoading"
                @click="loadActivity('studies', studiesOffset + 50)"
              >
                Next
              </v-btn>
            </div>
          </v-card>
        </v-window-item>
        <v-window-item
          id="account-panel-6"
          role="tabpanel"
          aria-labelledby="account-tab-6"
          :aria-hidden="tab !== 6"
          :inert="tab !== 6 || undefined"
          :tabindex="tab === 6 ? 0 : -1"
          :value="6"
        >
          <v-card variant="outlined" class="pa-6">
            <div class="d-flex align-center justify-space-between mb-3">
              <h2 class="text-h6">Security history</h2>
              <v-btn
                size="small"
                variant="outlined"
                :loading="eventsLoading"
                @click="loadActivity('events', 0)"
              >
                Refresh
              </v-btn>
            </div>
            <p>
              Recent account and credential actions performed by your account,
              newest first.
            </p>
            <v-alert v-if="eventsError" type="error">{{ eventsError }}</v-alert>
            <p v-if="!eventsLoading && !eventsError && !events.length">
              No security events on this page.
            </p>
            <v-table v-if="events.length">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Action</th>
                  <th>Target</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="event in events" :key="event.id">
                  <td>{{ date(event.created_at) }}</td>
                  <td>{{ event.action }}</td>
                  <td>{{ event.target }}</td>
                </tr>
              </tbody>
            </v-table>
            <div class="d-flex justify-end mt-4">
              <v-btn
                variant="text"
                :disabled="eventsOffset === 0 || eventsLoading"
                @click="loadActivity('events', eventsOffset - 50)"
              >
                Previous </v-btn
              ><v-btn
                variant="text"
                :disabled="events.length < 50 || eventsLoading"
                @click="loadActivity('events', eventsOffset + 50)"
              >
                Next
              </v-btn>
            </div>
          </v-card>
        </v-window-item>
        <v-window-item
          id="account-panel-7"
          role="tabpanel"
          aria-labelledby="account-tab-7"
          :aria-hidden="tab !== 7"
          :inert="tab !== 7 || undefined"
          :tabindex="tab === 7 ? 0 : -1"
          :value="7"
          v-if="profile.role === 'admin'"
        >
          <admin-settings v-if="tab === 7" />
        </v-window-item>
      </v-window>
    </template>
    <v-dialog
      v-model="reauthDialog"
      max-width="440"
      @update:model-value="clearPending"
    >
      <v-card>
        <v-card-title>Confirm your identity</v-card-title
        ><v-card-text>
          <p>Enter your password to continue with this account change.</p>
          <v-alert v-if="reauthError" type="error" density="compact">
            {{ reauthError }} </v-alert
          ><v-form @submit.prevent="reauthenticate">
            <v-text-field
              v-model="reauthPassword"
              type="password"
              autocomplete="current-password"
              label="Password"
              variant="outlined"
              autofocus
            /><v-btn
              type="submit"
              color="primary"
              :loading="reauthBusy"
              :disabled="!reauthPassword"
            >
              Continue </v-btn
            ><v-btn
              variant="text"
              @click="
                reauthDialog = false;
                clearPending(false);
              "
            >
              Cancel
            </v-btn> </v-form
          >
        </v-card-text>
      </v-card>
    </v-dialog>
    <v-dialog v-model="secretDialog" max-width="620" persistent>
      <v-card>
        <v-card-title>Save your API key</v-card-title
        ><v-card-text>
          <p>
            This secret is shown only once. Store it securely before closing.
          </p>
          <v-textarea
            :model-value="secret"
            label="API key"
            readonly
            variant="outlined"
            rows="3"
            spellcheck="false"
          />
          <p v-if="rotated" class="text-caption">
            The previous key remains valid for up to 24 hours, bounded by its
            existing expiry. Revoke it now if it may be compromised.
          </p> </v-card-text
        ><v-card-actions>
          <v-spacer /><v-btn
            color="primary"
            @click="
              secret = '';
              secretDialog = false;
            "
          >
            I have saved the key
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>
<style scoped>
.account-page {
  max-width: 1040px;
}
.login-card {
  max-width: 440px;
}
.email-field {
  max-width: 520px;
}
.credential-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid #e5e7eb;
}
.credential-row:last-child {
  border-bottom: 0;
}
.session-info {
  min-width: 0;
}
@media (max-width: 600px) {
  .credential-row {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
