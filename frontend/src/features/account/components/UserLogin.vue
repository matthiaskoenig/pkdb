<script setup lang="ts">
import { onUnmounted, ref } from "vue";
import { useSessionStore } from "../../../stores/session";
import { errorMessage } from "../../../api/client";
import MfaChallenge from "./MfaChallenge.vue";
import ProviderLogin from "./ProviderLogin.vue";
const emit = defineEmits<{ close: [] }>();
const session = useSessionStore();
const username = ref(""),
  password = ref(""),
  error = ref(""),
  busy = ref(false);
let active = true;
onUnmounted(() => {
  active = false;
  password.value = "";
});
async function login() {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    await session.login(username.value, password.value);
    if (active && session.profile && !session.profile.mfa_required)
      emit("close");
  } catch (cause) {
    if (active) error.value = errorMessage(cause);
  } finally {
    password.value = "";
    if (active) busy.value = false;
  }
}
async function logout() {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    await session.logout();
    if (active) emit("close");
  } catch (cause) {
    if (active) error.value = errorMessage(cause);
  } finally {
    if (active) busy.value = false;
  }
}
</script>
<template>
  <v-card class="pa-5">
    <h1 class="text-h5 mb-4">
      {{ session.profile ? "Your account" : "Sign in to PK-DB" }}
    </h1>
    <v-alert v-if="error" type="error" role="alert">{{ error }}</v-alert
    ><MfaChallenge
      v-if="session.profile?.mfa_required"
      @verified="emit('close')"
    /><template v-else-if="session.profile">
      <p>{{ session.profile.display_name }} · {{ session.profile.role }}</p>
      <v-btn to="/account" color="primary" @click="emit('close')">
        Account settings </v-btn
      ><v-btn variant="text" :loading="busy" @click="logout">
        Sign out
      </v-btn> </template
    ><v-form v-else @submit.prevent="login">
      <v-text-field
        v-model="username"
        label="Username"
        autocomplete="username"
        required
      /><v-text-field
        v-model="password"
        label="Password"
        type="password"
        autocomplete="current-password"
        required
      /><v-btn
        type="submit"
        color="primary"
        :loading="busy"
        :disabled="!username || !password"
        block
      >
        Sign in
      </v-btn>
      <div class="d-flex flex-wrap ga-4 my-4">
        <router-link to="/registration" @click="emit('close')">
          Create account </router-link
        ><router-link to="/request-password-reset" @click="emit('close')">
          Forgot password? </router-link
        ><router-link to="/invitation" @click="emit('close')">
          Accept an invitation
        </router-link>
      </div>
      <ProviderLogin />
    </v-form>
  </v-card>
</template>
