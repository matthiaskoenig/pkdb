<template>
  <v-card outlined class="pa-6 mx-auto" style="max-width:520px">
    <h1 class="text-h5 mb-4">Complete your account</h1>
    <v-alert v-if="error" type="error">{{ error }}</v-alert>
    <v-alert v-if="complete" type="success">{{ invited ? 'Your existing account is ready. Open account settings to continue.' : 'Check your email to verify your contact address before signing in.' }}<v-btn v-if="invited" text color="primary" @click="openAccount">Account settings</v-btn></v-alert>
    <template v-else>
      <v-switch v-model="invited" label="I have an invitation for an existing account" @change="error=''"/>
      <v-form v-if="invited" @submit.prevent="claimInvitation">
        <p>Enter the token from your invitation email to connect this sign-in method to your existing account. Your role and study assignments will be preserved.</p>
        <v-text-field v-model="token" label="Invitation token" outlined autocomplete="off" maxlength="1024"/>
        <v-btn type="submit" color="primary" :loading="busy" :disabled="!token.trim()">Claim existing account</v-btn>
      </v-form>
      <v-form v-else @submit.prevent="submit">
        <p>Choose your PK-DB username and a private contact address. New accounts have read access.</p>
        <v-text-field v-model="username" label="Username" outlined maxlength="150" autocomplete="username"/>
        <v-text-field v-model="email" type="email" label="Email address" outlined autocomplete="email"/>
        <v-btn type="submit" color="primary" :loading="busy" :disabled="!username || !email">Create account</v-btn>
      </v-form>
    </template>
  </v-card>
</template>
<script>
import axios from 'axios';
import {apiBase, errorMessage} from '../../http';
export default {
  name: 'ProviderOnboarding',
  data: () => ({username: '', email: '', token: '', invited: false, busy: false, complete: false, error: ''}),
  beforeDestroy() { this.token = ''; },
  methods: {
    async submit() {
      this.busy = true; this.error = '';
      try { await axios.post(apiBase + '/api/v1/auth/onboarding', {username: this.username, email: this.email}); this.complete = true; }
      catch (error) { this.error = errorMessage(error); }
      finally { this.busy = false; }
    },
    async claimInvitation() {
      if (this.busy) return;
      this.busy = true; this.error = '';
      try {
        await axios.post(apiBase + '/api/v1/auth/onboarding/invitation', {token: this.token.trim()});
        this.token = ''; this.complete = true;
      } catch (error) { this.error = errorMessage(error); }
      finally { this.busy = false; }
    },
    async openAccount() { await this.$store.dispatch('refreshProfile'); window.location.assign('/account'); }
  }
};
</script>
