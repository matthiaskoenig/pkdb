<template>
  <v-card>
    <v-card-title>{{ user ? 'Your account' : 'Sign in to PK-DB' }}</v-card-title>
    <v-card-text>
      <v-alert v-if="error" type="error" dense>{{ error }}</v-alert>
      <mfa-challenge v-if="user && user.mfa_required" @verified="$emit('close')"/>
      <template v-else-if="user">
        <p class="text-h6 mb-1">{{ user.display_name }}</p>
        <p>@{{ user.username }} · {{ user.role }}</p>
        <v-btn color="primary" to="/account" @click="$emit('close')">Account settings</v-btn>
        <v-btn text :loading="busy" @click="logout">Sign out</v-btn>
      </template>
      <v-form v-else @submit.prevent="login">
        <v-text-field v-model="username" label="Username" autocomplete="username" required outlined/>
        <v-text-field v-model="password" label="Password" type="password" autocomplete="current-password" required outlined/>
        <v-btn type="submit" color="primary" :loading="busy" :disabled="!username || !password" block>Sign in</v-btn>
        <div class="d-flex justify-space-between mt-4">
          <router-link to="/registration" @click.native="$emit('close')">Create account</router-link>
          <router-link to="/request-password-reset" @click.native="$emit('close')">Forgot password?</router-link>
        </div>
        <div class="mt-4 text-center"><router-link to="/invitation" @click.native="$emit('close')">Accept an invitation</router-link></div>
        <provider-login/>
      </v-form>
    </v-card-text>
  </v-card>
</template>
<script>
import {errorMessage} from '../../http';
import MfaChallenge from './MfaChallenge';
import ProviderLogin from './ProviderLogin';
export default {
  name: 'UserLogin', components: {MfaChallenge, ProviderLogin},
  data: () => ({username: '', password: '', busy: false, error: ''}),
  computed: {user() { return this.$store.state.profile; }},
  methods: {
    async login() {
      this.busy = true; this.error = '';
      try { await this.$store.dispatch('login', {username: this.username, password: this.password}); this.password = ''; if (!this.user.mfa_required) this.$emit('close'); }
      catch (error) { this.error = errorMessage(error); }
      finally { this.busy = false; }
    },
    async logout() {
      this.busy = true; this.error = '';
      try { await this.$store.dispatch('logout'); this.$emit('close'); }
      catch (error) { this.error = errorMessage(error); }
      finally { this.busy = false; }
    }
  }
};
</script>
