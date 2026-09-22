<template>
  <v-container class="account-page py-8">
    <provider-onboarding v-if="onboarding"/>
    <user-login v-else-if="!profile" class="login-card mx-auto"/>
    <mfa-challenge v-else-if="profile.mfa_required"/>
    <template v-else>
      <div class="d-flex align-center mb-7">
        <v-avatar size="72" color="grey lighten-3" class="mr-5"><img :src="avatarUrl" :alt="profile.display_name" style="object-fit:cover"/></v-avatar>
        <div><h1 class="text-h4 font-weight-medium">Account settings</h1><p class="mb-0 mt-2 grey--text text--darken-1">@{{ profile.username }} <v-chip small class="ml-2">{{ profile.role }}</v-chip></p></div>
      </div>
      <v-alert v-if="error" type="error" dismissible @input="error=''">{{ error }}</v-alert>
      <v-alert v-if="notice" type="success" dismissible @input="notice=''">{{ notice }}</v-alert>
      <v-btn v-if="profile.role==='admin'" outlined class="mb-4" @click="secure(() => {mfaDialog=true})">Confirm administrator identity</v-btn>
      <v-card v-if="profile.role==='user'" outlined class="pa-5 mb-5"><h2 class="text-h6">Request curator access</h2><p>Curators can upload studies and edit studies assigned to them.</p><v-textarea v-model="curatorReason" label="Tell us about your planned contributions" outlined rows="2" maxlength="2000"/><v-btn color="primary" :disabled="!curatorReason.trim() || busy" @click="requestCurator">Send request</v-btn></v-card>
      <v-tabs v-model="tab" class="mb-6" show-arrows><v-tab>Profile</v-tab><v-tab>Email addresses</v-tab><v-tab>API keys</v-tab><v-tab>Sessions</v-tab><v-tab>Connected accounts</v-tab><v-tab>Assigned studies</v-tab><v-tab>Security history</v-tab><v-tab v-if="profile.role==='admin'">Administration</v-tab></v-tabs>
      <v-tabs-items v-model="tab">
        <v-tab-item>
          <v-card outlined class="pa-6">
            <h2 class="text-h6 mb-2">Public profile</h2>
            <p class="grey--text text--darken-1">These details can appear with your scientific contributions. Your email addresses stay private.</p>
            <v-row><v-col cols="12" md="8">
              <v-text-field v-model="form.display_name" label="Display name" outlined maxlength="200" hint="Leave blank to use your username" persistent-hint/>
              <v-row><v-col cols="12" sm="4"><v-text-field v-model="form.title" label="Title (optional)" outlined maxlength="100"/></v-col><v-col cols="12" sm="8"><v-text-field v-model="form.affiliation" label="Affiliation (optional)" outlined maxlength="250"/></v-col></v-row>
              <v-text-field v-model="form.github" label="GitHub handle (optional)" outlined :readonly="profile.github_provenance==='authenticated'" hint="A public reference; entering a handle does not connect a login" persistent-hint maxlength="39"/>
              <v-checkbox v-model="form.github_visible" label="Show GitHub on my public profile" hint="This does not change your connected sign-in account" persistent-hint/>
              <v-text-field v-model="form.orcid" label="ORCID iD (optional)" outlined :readonly="profile.orcid_provenance==='authenticated'" placeholder="0000-0000-0000-0000" hint="A public reference; entering an iD does not verify ownership" persistent-hint class="mt-4"/>
              <v-checkbox v-model="form.orcid_visible" label="Show ORCID on my public profile" hint="This does not change your connected sign-in account" persistent-hint/>
              <v-btn color="primary" :loading="busy" class="mt-4" @click="saveProfile">Save profile</v-btn>
            </v-col><v-col cols="12" md="4">
              <h3 class="text-subtitle-1 mb-3">Profile photo</h3>
              <v-file-input v-model="photo" accept="image/jpeg,image/png,image/webp" label="Choose photo" outlined dense hint="JPEG, PNG or WebP. Up to 5 MiB." persistent-hint/>
              <v-btn small color="primary" :disabled="!photo || busy" class="mt-4 mr-2" @click="uploadPhoto">Upload</v-btn><v-btn small text :disabled="busy" class="mt-4" @click="removePhoto">Remove photo</v-btn>
            </v-col></v-row>
          </v-card>
        </v-tab-item>
        <v-tab-item>
          <v-card outlined class="pa-6">
            <h2 class="text-h6 mb-2">Private contact addresses</h2><p>Verify an address before using it for recovery or making it primary.</p>
            <v-list><v-list-item v-for="email in profile.emails" :key="email.id" class="px-0">
              <v-list-item-content><v-list-item-title>{{ email.email }}</v-list-item-title><v-list-item-subtitle>{{ email.is_primary ? 'Primary · ' : '' }}{{ email.is_verified ? 'Verified' : 'Awaiting verification' }}</v-list-item-subtitle></v-list-item-content>
              <v-btn v-if="!email.is_verified" small text :disabled="busy" @click="resend(email)">Resend</v-btn>
              <v-btn v-if="!email.is_primary && email.is_verified" small text :disabled="busy" @click="secure(() => makePrimary(email))">Make primary</v-btn>
              <v-btn v-if="!email.is_primary" small text color="error" :disabled="busy" @click="secure(() => removeEmail(email))">Remove</v-btn>
            </v-list-item></v-list>
            <v-form v-if="profile.emails.length < 2" @submit.prevent="secure(addEmail)" class="mt-5">
              <v-text-field v-model="newEmail" type="email" label="Secondary email" outlined class="email-field"/>
              <v-btn type="submit" color="primary" :disabled="!newEmail || busy">Add and verify</v-btn>
            </v-form>
          </v-card>
        </v-tab-item>
        <v-tab-item>
          <v-card outlined class="pa-6">
            <h2 class="text-h6 mb-2">Personal API keys</h2><p>Use a separate key for each script or application. Keys follow your current role and study assignments.</p>
            <v-form @submit.prevent="secure(createKey)">
              <v-row align="center"><v-col cols="12" md="6"><v-text-field v-model="keyName" label="Key name" placeholder="Laptop analysis" outlined maxlength="100" hide-details/></v-col><v-col cols="6" md="3"><v-text-field v-model.number="keyDays" type="number" min="1" max="365" label="Expires in days" outlined hide-details/></v-col><v-col cols="6" md="3"><v-btn type="submit" color="primary" :disabled="!keyName.trim() || busy">Create key</v-btn></v-col></v-row>
              <v-checkbox v-if="canWrite" v-model="keyWrite" label="Allow study uploads and edits within my permissions"/>
              <p v-else class="text-caption mt-3">Read access only</p>
            </v-form>
            <v-divider class="my-5"/>
            <p v-if="!keys.length" class="grey--text">No API keys yet.</p>
            <div v-for="key in keys" :key="key.id" class="credential-row py-4">
              <div><strong>{{ key.name }}</strong> <v-chip small class="ml-2">{{ key.revoked_at ? 'Revoked' : expired(key.expires_at) ? 'Expired' : key.scopes.join(', ') }}</v-chip><div class="text-caption grey--text text--darken-1 mt-2">{{ key.prefix }}… · Expires {{ date(key.expires_at) }} · Last used {{ date(key.last_used_at) }}</div></div>
              <div v-if="!key.revoked_at && !expired(key.expires_at)"><v-btn small text :disabled="busy" @click="secure(() => rotateKey(key))">Rotate</v-btn><v-btn small text color="error" :disabled="busy" @click="revokeKey(key)">Revoke</v-btn></div>
            </div>
          </v-card>
        </v-tab-item>
        <v-tab-item>
          <v-card outlined class="pa-6"><h2 class="text-h6 mb-2">Browser sessions</h2><p>Revoke a session to sign out that browser. API keys are managed separately.</p>
            <div v-for="session in sessions" :key="session.id" class="credential-row py-4"><div class="session-info"><strong>{{ session.current ? 'This browser' : 'Browser session' }}</strong><div class="text-caption text-truncate">{{ session.device || 'Unknown browser' }}</div><div class="text-caption grey--text">Last active {{ date(session.last_seen_at) }} · {{ session.revoked_at ? 'Revoked' : 'Expires ' + date(session.expires_at) }}</div></div><v-btn v-if="!session.revoked_at" small text color="error" :disabled="busy" @click="revokeSession(session)">{{ session.current ? 'Sign out' : 'Revoke' }}</v-btn></div>
          </v-card>
        </v-tab-item>
        <v-tab-item><v-card outlined class="pa-6"><h2 class="text-h6 mb-2">Connected sign-in accounts</h2><p>Connect a provider only after proving ownership. Public profile references do not connect a sign-in method.</p>
          <p v-if="!providers.length" class="grey--text">External sign-in providers are not configured.</p>
          <div v-for="identity in identities" :key="identity.id" class="credential-row py-4"><div><strong>{{ identity.provider === 'github' ? 'GitHub' : 'ORCID' }}</strong><p class="mb-0">{{ identity.label }}</p></div><v-btn text small :disabled="busy" @click="secure(() => unlink(identity))">Disconnect</v-btn></div>
          <v-btn v-for="provider in availableProviders" :key="provider" outlined class="mt-4 mr-3" @click="secure(() => link(provider))">Connect {{ provider === 'github' ? 'GitHub' : 'ORCID' }}</v-btn>
        </v-card></v-tab-item>
        <v-tab-item><v-card outlined class="pa-6">
          <div class="d-flex align-center justify-space-between mb-3"><h2 class="text-h6">Assigned studies</h2><v-btn small outlined :loading="studiesLoading" @click="loadActivity('studies', 0)">Refresh</v-btn></div>
          <p>These studies have an explicit curator assignment to your account. Editing depends on your current role.</p>
          <p v-if="['reviewer', 'admin'].includes(profile.role)">Your role also allows editing studies outside this assignment list.</p>
          <v-alert v-if="studiesError" type="error">{{ studiesError }}</v-alert>
          <p v-if="!studiesLoading && !studiesError && !studies.length">No assigned studies on this page.</p>
          <v-list><v-list-item v-for="study in studies" :key="study.sid" :to="{name: 'DataSingle', params: {sid: study.sid}}"><v-list-item-content><v-list-item-title>{{ study.name || study.sid }}</v-list-item-title><v-list-item-subtitle>{{ study.sid }}</v-list-item-subtitle></v-list-item-content></v-list-item></v-list>
          <div class="d-flex justify-end mt-4"><v-btn text :disabled="studiesOffset===0 || studiesLoading" @click="loadActivity('studies', studiesOffset-50)">Previous</v-btn><v-btn text :disabled="studies.length<50 || studiesLoading" @click="loadActivity('studies', studiesOffset+50)">Next</v-btn></div>
        </v-card></v-tab-item>
        <v-tab-item><v-card outlined class="pa-6">
          <div class="d-flex align-center justify-space-between mb-3"><h2 class="text-h6">Security history</h2><v-btn small outlined :loading="eventsLoading" @click="loadActivity('events', 0)">Refresh</v-btn></div>
          <p>Recent account and credential actions performed by your account, newest first.</p>
          <v-alert v-if="eventsError" type="error">{{ eventsError }}</v-alert>
          <p v-if="!eventsLoading && !eventsError && !events.length">No security events on this page.</p>
          <v-simple-table v-if="events.length"><thead><tr><th>Time</th><th>Action</th><th>Target</th></tr></thead><tbody><tr v-for="event in events" :key="event.id"><td>{{ date(event.created_at) }}</td><td>{{ event.action }}</td><td>{{ event.target }}</td></tr></tbody></v-simple-table>
          <div class="d-flex justify-end mt-4"><v-btn text :disabled="eventsOffset===0 || eventsLoading" @click="loadActivity('events', eventsOffset-50)">Previous</v-btn><v-btn text :disabled="events.length<50 || eventsLoading" @click="loadActivity('events', eventsOffset+50)">Next</v-btn></div>
        </v-card></v-tab-item>
        <v-tab-item v-if="profile.role==='admin'"><admin-settings/></v-tab-item>
      </v-tabs-items>
    </template>
    <v-dialog v-model="mfaDialog" max-width="500"><mfa-challenge v-if="mfaDialog" @verified="mfaDialog=false"/></v-dialog>
    <v-dialog v-model="reauthDialog" max-width="440" @input="clearPending"><v-card><v-card-title>Confirm your identity</v-card-title><v-card-text><p>Enter your password to continue with this account change.</p><v-alert v-if="reauthError" type="error" dense>{{ reauthError }}</v-alert><v-form @submit.prevent="reauthenticate"><v-text-field v-model="reauthPassword" type="password" autocomplete="current-password" label="Password" outlined autofocus/><v-btn type="submit" color="primary" :loading="busy" :disabled="!reauthPassword">Continue</v-btn><v-btn text @click="reauthDialog=false; clearPending(false)">Cancel</v-btn></v-form><v-divider v-if="identities.length" class="my-4"/><v-btn v-for="identity in identities" :key="identity.id" outlined block class="mt-2" @click="providerReauth(identity.provider)">Confirm with {{ identity.provider === 'github' ? 'GitHub' : 'ORCID' }}</v-btn><p v-if="identities.length" class="text-caption mt-3">After returning, repeat the action you want to perform.</p></v-card-text></v-card></v-dialog>
    <v-dialog v-model="secretDialog" max-width="620" persistent><v-card><v-card-title>Save your API key</v-card-title><v-card-text><p>This secret is shown only once. Store it securely before closing.</p><v-textarea :value="secret" label="API key" readonly outlined rows="3" spellcheck="false"/><p v-if="rotated" class="text-caption">The previous key remains valid for up to 24 hours, bounded by its existing expiry. Revoke it now if it may be compromised.</p></v-card-text><v-card-actions><v-spacer/><v-btn color="primary" @click="secret=''; secretDialog=false">I have saved the key</v-btn></v-card-actions></v-card></v-dialog>
  </v-container>
</template>
<script>
import axios from 'axios';
import UserLogin from './UserLogin';
import MfaChallenge from './MfaChallenge';
import ProviderOnboarding from './ProviderOnboarding';
import AdminSettings from './AdminSettings';
import {apiBase, errorMessage} from '../../http';
export default {
  name: 'Account', components: {UserLogin, MfaChallenge, ProviderOnboarding, AdminSettings},
  data: () => ({studies: [], events: [], studiesOffset: 0, eventsOffset: 0, studiesLoading: false, eventsLoading: false, studiesError: '', eventsError: '', activityGeneration: 0, curatorReason: '', recentlyConfirmed: false, mfaDialog: false, onboarding: false, tab: 0, form: {}, photo: null, busy: false, error: '', notice: '', keys: [], sessions: [], identities: [], providers: [], newEmail: '', keyName: '', keyDays: 90, keyWrite: false, reauthDialog: false, reauthPassword: '', reauthError: '', pending: null, secretDialog: false, secret: '', rotated: false}),
  computed: {
    profile() { return this.$store.state.profile; },
    avatarUrl() { return apiBase + this.profile.avatar_url; },
    availableProviders() { return this.providers.filter(provider => !this.identities.some(item => item.provider === provider)); },
    canWrite() { return this.profile && ['curator', 'reviewer', 'admin'].includes(this.profile.role); }
  },
  watch: {profile: {immediate: true, handler(profile) { this.resetActivity(); if (profile) { this.form = Object.fromEntries(['display_name', 'affiliation', 'title', 'github', 'orcid'].map(field => [field, profile[field] || ''])); ['github', 'orcid'].forEach(provider => { this.form[provider + '_visible'] = profile[provider + '_visible'] !== false; }); if (!profile.mfa_required) { this.loadCredentials(); this.loadActivity('studies', 0); this.loadActivity('events', 0); } } else { this.secret = ''; this.secretDialog = false; this.reauthDialog = false; this.reauthPassword = ''; } }}},
  created() { if (this.$route.query.oauth) { this.onboarding = this.$route.query.oauth === 'onboarding'; this.recentlyConfirmed = ['authenticated', 'linked'].includes(this.$route.query.oauth); if (this.$route.query.oauth === 'error') this.error = 'Provider sign-in did not complete. Please try again.'; this.$router.replace({path: this.$route.path, query: {}}); } },
  beforeDestroy() { this.resetActivity(); this.secret = ''; this.reauthPassword = ''; this.pending = null; },
  methods: {
    resetActivity() { this.activityGeneration++; ['studies', 'events'].forEach(kind => { this[kind] = []; this[kind + 'Offset'] = 0; this[kind + 'Loading'] = false; this[kind + 'Error'] = ''; }); },
    async loadActivity(kind, offset) {
      if (!this.profile || this.profile.mfa_required || this[kind + 'Loading']) return;
      const generation = this.activityGeneration;
      this[kind + 'Loading'] = true; this[kind + 'Error'] = '';
      try {
        const response = await axios.get(apiBase + '/api/v1/me/' + (kind === 'studies' ? 'studies' : 'security-events'), {params: {offset, limit: 50}});
        if (generation !== this.activityGeneration) return;
        this[kind] = response.data; this[kind + 'Offset'] = offset;
      } catch (error) { if (generation === this.activityGeneration) this[kind + 'Error'] = errorMessage(error); }
      finally { if (generation === this.activityGeneration) this[kind + 'Loading'] = false; }
    },
    date(value) { return value ? new Date(value).toLocaleString() : 'Never'; },
    expired(value) { return new Date(value) <= new Date(); },
    async run(action, message) { this.busy = true; this.error = ''; this.notice = ''; try { await action(); if (message) this.notice = message; } catch (error) { if (error.response && error.response.status === 403) this.recentlyConfirmed = false; this.error = errorMessage(error); } finally { this.busy = false; } },
    async loadCredentials() { try { const [keys, sessions, identities, providers] = await Promise.all([axios.get(apiBase + '/api/v1/me/api-keys'), axios.get(apiBase + '/api/v1/me/sessions'), axios.get(apiBase + '/api/v1/me/identities'), axios.get(apiBase + '/api/v1/auth/providers')]); this.keys = keys.data; this.sessions = sessions.data; this.identities = identities.data; this.providers = providers.data.providers; } catch (error) { this.error = errorMessage(error); } },
    requestCurator() { return this.run(async () => { await axios.post(apiBase + '/api/v1/me/role-requests', {reason: this.curatorReason.trim()}); this.curatorReason = ''; }, 'Your curator access request has been sent.'); },
    link(provider) { return this.run(async () => { const response = await axios.post(apiBase + '/api/v1/me/identities/' + provider + '/link'); window.location.assign(response.data.authorization_url); }); },
    unlink(identity) { return this.run(async () => { await axios.delete(apiBase + '/api/v1/me/identities/' + identity.id); await this.$store.dispatch('refreshProfile'); }, 'Account disconnected.'); },
    providerReauth(provider) { return this.run(async () => { const response = await axios.post(apiBase + '/api/v1/me/identities/' + provider + '/reauthenticate'); window.location.assign(response.data.authorization_url); }); },
    saveProfile() { return this.run(async () => { const values = Object.assign({}, this.form); ['github', 'orcid'].forEach(field => { if (this.profile[field + '_provenance'] === 'authenticated') delete values[field]; }); await axios.patch(apiBase + '/api/v1/me', values); await this.$store.dispatch('refreshProfile'); }, 'Profile saved.'); },
    uploadPhoto() { if (this.photo.size > 5 * 1024 * 1024) { this.error = 'Please choose an image smaller than 5 MiB.'; return; } return this.run(async () => { await axios.put(apiBase + '/api/v1/me/avatar', this.photo, {headers: {'Content-Type': this.photo.type}}); await this.$store.dispatch('refreshProfile'); this.photo = null; }, 'Photo updated.'); },
    removePhoto() { return this.run(async () => { await axios.delete(apiBase + '/api/v1/me/avatar'); await this.$store.dispatch('refreshProfile'); }, 'Photo removed.'); },
    secure(action) { if (this.recentlyConfirmed) return action(); this.pending = action; this.reauthPassword = ''; this.reauthError = ''; this.reauthDialog = true; },
    clearPending(open) { if (!open) { this.pending = null; this.reauthPassword = ''; } },
    async reauthenticate() { this.busy = true; try { await axios.post(apiBase + '/api/v1/auth/reauthenticate', {password: this.reauthPassword}); this.recentlyConfirmed = true; const action = this.pending; this.reauthDialog = false; this.clearPending(false); if (action) await action(); } catch (error) { this.reauthError = errorMessage(error); } finally { this.busy = false; } },
    createKey() { return this.run(async () => { const response = await axios.post(apiBase + '/api/v1/me/api-keys', {name: this.keyName.trim(), lifetime_days: this.keyDays, scopes: this.keyWrite ? ['read', 'studies:write'] : ['read']}); this.secret = response.data.secret; this.rotated = false; this.secretDialog = true; this.keyName = ''; await this.loadCredentials(); }); },
    rotateKey(key) { return this.run(async () => { const response = await axios.post(apiBase + '/api/v1/me/api-keys/' + key.id + '/rotate', {overlap_hours: 24}); this.secret = response.data.secret; this.rotated = true; this.secretDialog = true; await this.loadCredentials(); }); },
    revokeKey(key) { return this.run(async () => { await axios.delete(apiBase + '/api/v1/me/api-keys/' + key.id); await this.loadCredentials(); }, 'API key revoked.'); },
    revokeSession(session) { return this.run(async () => { await axios.delete(apiBase + '/api/v1/me/sessions/' + session.id); if (session.current) this.$store.commit('setProfile', null); else await this.loadCredentials(); }, 'Session revoked.'); },
    addEmail() { return this.run(async () => { await axios.post(apiBase + '/accounts/emails/', {email: this.newEmail}); this.newEmail = ''; await this.$store.dispatch('refreshProfile'); }, 'Verification email requested.'); },
    makePrimary(email) { return this.run(async () => { await axios.patch(apiBase + '/accounts/emails/' + email.id + '/', {is_primary: true}); await this.$store.dispatch('refreshProfile'); }, 'Primary address updated.'); },
    removeEmail(email) { return this.run(async () => { await axios.delete(apiBase + '/accounts/emails/' + email.id + '/'); await this.$store.dispatch('refreshProfile'); }, 'Address removed.'); },
    resend(email) { return this.run(() => axios.post(apiBase + '/accounts/resend-verification/', {email: email.email}), 'Verification email requested.'); }
  }
};
</script>
<style scoped>
.account-page { max-width: 1040px; }
.login-card { max-width: 440px; }
.email-field { max-width: 520px; }
.credential-row { display:flex; align-items:center; justify-content:space-between; gap:16px; border-bottom:1px solid #e5e7eb; }
.credential-row:last-child { border-bottom:0; }
.session-info { min-width:0; }
@media(max-width:600px) { .credential-row { align-items:flex-start; flex-direction:column; } }
</style>
