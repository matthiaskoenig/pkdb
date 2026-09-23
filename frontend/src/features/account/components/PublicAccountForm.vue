<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { accountApi } from "../../../api/account";
import { useAccountAction } from "../useAccountAction";
const props = defineProps<{
  mode:
    "registration" | "verification" | "request-reset" | "reset" | "invitation";
}>();
const route = useRoute();
const username = ref(""),
  email = ref(""),
  password = ref(""),
  token = ref(""),
  complete = ref(false);
const { busy, error, run, reset } = useAccountAction();
const title = computed(
  () =>
    ({
      registration: "Create an account",
      verification: "Verify your email",
      "request-reset": "Request a password reset",
      reset: "Set a new password",
      invitation: "Accept your invitation",
    })[props.mode],
);
const message = computed(
  () =>
    ({
      registration:
        "If registration can be completed, verification instructions will be emailed to you.",
      verification: "Your email has been verified. You can now sign in.",
      "request-reset":
        "If the address is eligible, recovery instructions will be emailed to you.",
      reset: "Your password has been updated. Sign in with the new password.",
      invitation: "Your account is ready. Sign in to continue.",
    })[props.mode],
);
const routeKey = computed(() =>
  typeof route.params.id === "string" ? route.params.id : "",
);
const usesPassword = computed(() =>
  ["registration", "reset", "invitation"].includes(props.mode),
);
function submit() {
  return run(async (current) => {
    if (props.mode === "registration")
      await accountApi.register(username.value, email.value, password.value);
    else if (props.mode === "verification")
      await accountApi.verify(routeKey.value);
    else if (props.mode === "request-reset")
      await accountApi.requestReset(email.value.toLowerCase());
    else if (props.mode === "reset")
      await accountApi.reset(routeKey.value, password.value);
    else await accountApi.invite(token.value, password.value);
    if (current()) {
      complete.value = true;
      password.value = "";
      token.value = "";
    }
  });
}
watch(
  routeKey,
  () => {
    reset();
    complete.value = false;
    if (props.mode === "verification") void submit();
  },
  { immediate: true },
);
onUnmounted(() => {
  password.value = "";
  token.value = "";
});
</script>
<template>
  <v-container style="max-width: 560px" class="py-8">
    <v-card class="pa-6">
      <h1 class="text-h5 mb-4">{{ title }}</h1>
      <v-alert v-if="error" type="error" role="alert">{{ error }}</v-alert
      ><v-alert v-if="complete" type="success" role="status">
        {{ message }} <router-link to="/account">Sign in</router-link> </v-alert
      ><v-form v-else @submit.prevent="submit">
        <p v-if="mode === 'request-reset'" class="mb-4">
          Use your verified email address. To protect privacy, the response does
          not reveal whether an account exists.
        </p>
        <v-text-field
          v-if="mode === 'registration'"
          v-model="username"
          label="Username"
          autocomplete="username"
          maxlength="150"
          required
        /><v-text-field
          v-if="mode === 'registration' || mode === 'request-reset'"
          v-model="email"
          type="email"
          label="Email address"
          autocomplete="email"
          required
        /><v-text-field
          v-if="mode === 'invitation'"
          v-model="token"
          label="Invitation token"
          autocomplete="off"
          maxlength="1024"
          required
        /><v-text-field
          v-if="usesPassword"
          v-model="password"
          type="password"
          label="New password"
          autocomplete="new-password"
          minlength="8"
          required
          hint="At least 8 characters"
          persistent-hint
        /><v-btn
          type="submit"
          color="primary"
          :loading="busy"
          :disabled="busy || (usesPassword && password.length < 8)"
        >
          {{
            mode === "verification"
              ? "Retry verification"
              : mode === "invitation"
                ? "Activate account"
                : "Submit"
          }}
        </v-btn> </v-form
      >
    </v-card>
  </v-container>
</template>
