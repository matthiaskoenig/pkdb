<template>
  <v-card outlined class="pa-6">
    <h2 class="text-h6 mb-2">User administration</h2><p>Role changes take effect immediately. Administrator privileges are reserved for the designated account.</p>
    <v-alert v-if="error" type="error">{{ error }}</v-alert><v-alert v-if="notice" type="success">{{ notice }}</v-alert>
    <v-alert v-if="!recent" type="info">Confirm your identity in account settings and verify your authenticator before making administrator changes.</v-alert>
    <v-form @submit.prevent="search"><v-text-field v-model="query" label="Search usernames" outlined append-icon="fas fa-search" @click:append="search"/></v-form>
    <v-simple-table><thead><tr><th>User</th><th>Role</th><th>Status</th><th>Action</th><th>Activity</th></tr></thead><tbody><tr v-for="user in users" :key="user.id"><td><strong>{{ user.display_name }}</strong><div class="text-caption">@{{ user.username }} · ID {{ user.id }} · {{ user.email || 'No email' }}</div></td><td><v-select v-if="user.role!=='admin'" v-model="user.proposedRole" :items="roles" dense hide-details style="min-width:120px"/><span v-else>Administrator</span></td><td>{{ statusLabel(user) }}</td><td v-if="user.role!=='admin'"><v-btn small text :disabled="busy || user.proposedRole===user.role" @click="update(user, {role:user.proposedRole})">Save role</v-btn><v-btn v-if="user.active || user.can_activate" small text :color="user.active ? 'error' : 'primary'" :disabled="busy" @click="update(user, {active:!user.active})">{{ user.active ? 'Suspend' : 'Activate' }}</v-btn><v-btn v-if="user.can_invite" small text color="primary" :disabled="busy || !recent" @click="invitationError=''; invitationUser=user">Invite</v-btn></td><td v-else>Protected</td><td><v-btn small text :disabled="busy" @click="loadUsage(user)">Usage</v-btn></td></tr></tbody></v-simple-table>
    <div class="d-flex justify-end mt-4"><v-btn text :disabled="offset===0 || busy" @click="offset-=50; load()">Previous</v-btn><v-btn text :disabled="users.length<50 || busy" @click="offset+=50; load()">Next</v-btn></div>
    <v-dialog :value="!!invitationUser" @input="closeInvitation" max-width="480"><v-card><v-card-title>Send account invitation</v-card-title><v-card-text v-if="invitationUser"><p>Invite <strong>@{{ invitationUser.username }}</strong> to claim their existing account as {{ invitationUser.role }}.</p><p>Send to <strong>{{ invitationUser.email }}</strong>. Confirm this is the reviewed contact address for this person.</p><p>The invitation expires in seven days. Sending again replaces their previous invitation.</p><v-alert v-if="invitationError" type="error">{{ invitationError }}</v-alert></v-card-text><v-card-actions><v-spacer/><v-btn text :disabled="busy" @click="invitationUser=null">Cancel</v-btn><v-btn color="primary" :loading="busy" :disabled="!recent" @click="sendInvitation">Send invitation</v-btn></v-card-actions></v-card></v-dialog>
    <v-card v-if="usageUser" outlined class="pa-4 mt-5">
      <div class="d-flex justify-space-between align-center"><h3 class="text-subtitle-1">Current usage · @{{ usageUser.username }}</h3><v-btn small text :disabled="busy" @click="loadUsage(usageUser)">Refresh</v-btn></div>
      <p class="text-caption grey--text mt-2">Current request budgets are shared across this account's sessions and API keys.</p>
      <v-simple-table v-if="usage"><thead><tr><th>Request class</th><th>Requests</th><th>Window resets</th></tr></thead><tbody><tr v-for="kind in ['account','upload','export']" :key="kind"><td>{{ usageLabels[kind] }}</td><td>{{ usage[kind].requests }}</td><td>{{ date(usage[kind].resets_at) }}</td></tr></tbody></v-simple-table>
    </v-card>
    <v-divider class="my-6"/><h2 class="text-h6 mb-3">Curator access requests</h2><p v-if="!requests.length">No pending requests.</p><div v-for="request in requests" :key="request.id" class="mb-4"><strong>{{ request.username }}</strong><p class="my-2">{{ request.reason }}</p><v-btn small color="primary" :disabled="busy" @click="resolve(request, 'approved')">Approve</v-btn><v-btn small text :disabled="busy" @click="resolve(request, 'rejected')">Reject</v-btn></div>
    <v-divider class="my-6"/><h2 class="text-h6 mb-3">Study access</h2><p>Load the existing grants before changing curator assignments, readers or visibility.</p>
    <v-form @submit.prevent="loadStudy"><v-text-field v-model="studySid" label="Study identifier" outlined/><v-btn type="submit" outlined :disabled="!studySid || busy">Load study access</v-btn></v-form>
    <v-form v-if="studyAccess" class="mt-5" @submit.prevent="saveStudy">
      <p class="font-weight-medium">{{ loadedSid }}</p>
      <v-select v-model="studyAccess.access" :items="['public','private']" label="Visibility" outlined/>
      <v-select v-model="studyAccess.licence" :items="['open','closed']" label="File licence" outlined/>
      <v-text-field v-model="curatorIds" label="Assigned curator account IDs" hint="Comma-separated IDs from user management" persistent-hint outlined/>
      <v-text-field v-model="readerIds" label="Reader account IDs" hint="Comma-separated IDs; these grant read access only" persistent-hint outlined class="mt-4"/>
      <v-btn type="submit" color="primary" class="mt-4" :disabled="busy">Save study access</v-btn>
    </v-form>
    <v-divider class="my-6"/>
    <div class="d-flex align-center justify-space-between mb-3"><h2 class="text-h6">Security audit events</h2><v-btn outlined small :disabled="busy" @click="auditOffset=0; loadAudit()">{{ auditLoaded ? 'Refresh' : 'Load events' }}</v-btn></div>
    <p class="text-caption grey--text">Account, credential and access changes. Events are shown newest first.</p>
    <p v-if="auditLoaded && !events.length">No events in this page.</p>
    <v-simple-table v-if="events.length"><thead><tr><th>Time</th><th>Actor ID</th><th>Action</th><th>Target</th><th>Details</th></tr></thead><tbody><tr v-for="event in events" :key="event.id"><td class="text-no-wrap">{{ date(event.created_at) }}</td><td>{{ event.actor_id || 'System' }}</td><td>{{ event.action }}</td><td>{{ event.target }}</td><td><details v-if="event.details && Object.keys(event.details).length"><summary>View changes</summary><pre class="audit-details">{{ JSON.stringify(event.details, null, 2) }}</pre></details><span v-else>None</span></td></tr></tbody></v-simple-table>
    <div v-if="auditLoaded" class="d-flex justify-end mt-4"><v-btn text :disabled="auditOffset===0 || busy" @click="auditOffset-=50; loadAudit()">Previous events</v-btn><v-btn text :disabled="events.length<50 || busy" @click="auditOffset+=50; loadAudit()">Next events</v-btn></div>
  </v-card>
</template>
<script>
import axios from 'axios';
import {apiBase, errorMessage} from '../../http';
export default {
  name: 'AdminSettings', data: () => ({invitationUser: null, invitationError: '', query: '', users: [], requests: [], roles: ['user', 'curator', 'reviewer'], busy: false, error: '', notice: '', offset: 0, studySid: '', loadedSid: '', studyAccess: null, curatorIds: '', readerIds: '', usageUser: null, usage: null, usageLabels: {account: 'All requests', upload: 'Study uploads', export: 'Exports'}, events: [], auditOffset: 0, auditLoaded: false}),
  computed: {recent() { return this.$store.state.profile.mfa_recent; }},
  created() { this.load(); },
  methods: {
    closeInvitation(value) { if (!value) { this.invitationUser = null; this.invitationError = ''; } },
    statusLabel(user) { return ({active: 'Active', suspended: 'Suspended', pending: 'Awaiting verification', unclaimed: 'Unclaimed', inactive: 'Inactive'})[user.status] || 'Inactive'; },
    async sendInvitation() {
      if (!this.invitationUser || this.busy) return;
      this.busy = true; this.invitationError = ''; this.notice = '';
      const user = this.invitationUser;
      try {
        await axios.post(apiBase + '/api/v1/admin/users/' + user.id + '/invitations', {email_id: user.invitation_email_id});
        user.status = 'pending';
        this.invitationUser = null;
        this.notice = 'Invitation sent to ' + user.email + '. It expires in seven days.';
      } catch (error) { this.invitationError = errorMessage(error); }
      finally { this.busy = false; }
    },
    date(value) { return value ? new Date(value).toLocaleString() : 'No active window'; },
    async loadUsage(user) { this.busy = true; this.error = ''; this.usageUser = user; this.usage = null; try { this.usage = (await axios.get(apiBase + '/api/v1/admin/usage', {params: {user_id: user.id}})).data; } catch (error) { this.error = errorMessage(error); } finally { this.busy = false; } },
    async loadAudit() { this.busy = true; this.error = ''; this.events = []; try { this.events = (await axios.get(apiBase + '/api/v1/admin/audit-events', {params: {offset: this.auditOffset, limit: 50}})).data; this.auditLoaded = true; } catch (error) { this.error = errorMessage(error); } finally { this.busy = false; } },
    async resolve(request, status) { this.busy = true; this.error = ''; try { await axios.patch(apiBase + '/api/v1/admin/role-requests/' + request.id, {status}); await this.load(); this.notice = 'Request ' + status + '.'; } catch (error) { this.error = errorMessage(error); } finally { this.busy = false; } },
    async loadStudy() { this.busy = true; this.error = ''; this.studyAccess = null; try { this.loadedSid = this.studySid.trim(); this.studyAccess = (await axios.get(apiBase + '/api/v1/admin/studies/' + encodeURIComponent(this.loadedSid) + '/access')).data; this.curatorIds = this.studyAccess.curator_ids.join(', '); this.readerIds = this.studyAccess.reader_ids.join(', '); } catch (error) { this.error = errorMessage(error); } finally { this.busy = false; } },
    async saveStudy() { this.busy = true; this.error = ''; try { const ids = value => value.trim() ? value.split(',').map(item => { const id = Number(item.trim()); if (!Number.isSafeInteger(id) || id < 1) throw new Error('Enter positive account IDs separated by commas.'); return id; }) : []; const data = Object.assign({}, this.studyAccess, {curator_ids: ids(this.curatorIds), reader_ids: ids(this.readerIds)}); await axios.put(apiBase + '/api/v1/admin/studies/' + encodeURIComponent(this.loadedSid) + '/access', data); this.notice = 'Study access updated.'; } catch (error) { this.error = error.response ? errorMessage(error) : error.message; } finally { this.busy = false; } },
    search() { this.offset = 0; this.load(); },
    async load() { this.busy = true; this.error = ''; try { this.users = (await axios.get(apiBase + '/api/v1/admin/users', {params: {q: this.query, offset: this.offset, limit: 50}})).data.map(user => Object.assign({}, user, {proposedRole: user.role})); this.requests = (await axios.get(apiBase + '/api/v1/admin/role-requests')).data.filter(item => item.status === 'pending'); } catch (error) { this.error = errorMessage(error); } finally { this.busy = false; } },
    async update(user, values) { this.busy = true; this.error = ''; this.notice = ''; try { await axios.patch(apiBase + '/api/v1/admin/users/' + user.id, values); await this.load(); this.notice = 'Account updated.'; } catch (error) { this.error = errorMessage(error); } finally { this.busy = false; } }
  }
};
</script>

<style scoped>
.audit-details { max-width: 380px; white-space: pre-wrap; overflow-wrap: anywhere; padding: 8px 0; font-size: 12px; }
summary { cursor: pointer; }
</style>
