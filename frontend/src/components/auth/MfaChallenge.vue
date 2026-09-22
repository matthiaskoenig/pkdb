<template>
  <v-card outlined class="pa-5">
    <h2 class="text-h6 mb-3">Administrator verification</h2>
    <v-alert v-if="error" type="error" dense>{{ error }}</v-alert>
    <template v-if="!profile.mfa_enrolled && !enrollment && !recovery.length">
      <p>Set up an authenticator before using administrator access.</p>
      <v-btn color="primary" :loading="busy" @click="enroll">Set up authenticator</v-btn>
    </template>
    <template v-else-if="recovery.length">
      <p>Save these recovery codes securely. Each code can be used once.</p>
      <pre class="recovery-codes">{{ recovery.join('\n') }}</pre>
      <v-btn color="primary" @click="complete">I have saved the codes</v-btn>
    </template>
    <v-form v-else @submit.prevent="verify">
      <template v-if="enrollment">
        <p>Add this secret to your authenticator using a time-based code:</p>
        <v-text-field :value="enrollment.secret" readonly outlined label="Authenticator secret"/>
      </template>
      <p v-else>Enter a code from your authenticator, or an unused recovery code.</p>
      <v-text-field v-model="code" label="Verification code" autocomplete="one-time-code" outlined autofocus/>
      <v-btn type="submit" color="primary" :loading="busy" :disabled="!code">Verify</v-btn>
    </v-form>
  </v-card>
</template>
<script>
import axios from 'axios';
import {apiBase, errorMessage} from '../../http';
export default {
  name: 'MfaChallenge',
  data: () => ({enrollment: null, recovery: [], code: '', busy: false, error: ''}),
  computed: {profile() { return this.$store.state.profile; }},
  beforeDestroy() { this.enrollment = null; this.recovery = []; this.code = ''; },
  methods: {
    async enroll() { this.busy = true; this.error = ''; try { this.enrollment = (await axios.post(apiBase + '/api/v1/auth/mfa/enroll')).data; } catch (error) { this.error = errorMessage(error); } finally { this.busy = false; } },
    async verify() { this.busy = true; this.error = ''; try { const response = await axios.post(apiBase + '/api/v1/auth/mfa/' + (this.enrollment ? 'confirm' : 'verify'), {code: this.code}); this.code = ''; this.enrollment = null; this.recovery = response.data.recovery_codes || []; if (!this.recovery.length) await this.complete(); } catch (error) { this.error = errorMessage(error); } finally { this.busy = false; } },
    async complete() { this.recovery = []; await this.$store.dispatch('refreshProfile'); this.$emit('verified'); }
  }
};
</script>
<style scoped>.recovery-codes { padding:16px; background:#f1f5f9; line-height:1.8; user-select:all; }</style>
