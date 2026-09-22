<script setup lang="ts">
import { onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { accountApi } from "../../../api/account";
import { useSessionStore } from "../../../stores/session";
import { useAccountAction } from "../useAccountAction";
const emit = defineEmits<{ complete: [] }>();
const session = useSessionStore(),
  router = useRouter();
const username = ref(""),
  email = ref(""),
  token = ref(""),
  invited = ref(false),
  complete = ref(false);
const { busy, error, run } = useAccountAction();
onUnmounted(() => {
  token.value = "";
});
function submit() {
  return run(async (current) => {
    if (invited.value) await accountApi.claimInvitation(token.value.trim());
    else await accountApi.onboarding(username.value, email.value);
    if (current()) {
      token.value = "";
      complete.value = true;
    }
  });
}
async function openAccount() {
  await session.refreshProfile();
  await router.replace("/account");
  emit("complete");
}
</script>
<template>
  <v-card class="pa-6">
    <h1 class="text-h5 mb-4">Complete your account</h1>
    <v-alert v-if="error" type="error" role="alert">{{ error }}</v-alert
    ><v-alert v-if="complete" type="success">
      {{
        invited
          ? "Your existing account is ready."
          : "Check your email to verify your contact address before signing in."
      }}<v-btn
        v-if="invited"
        variant="text"
        @click="
          run(async () => {
            await openAccount();
          })
        "
      >
        Account settings
      </v-btn> </v-alert
    ><template v-else>
      <v-switch
        v-model="invited"
        :disabled="busy"
        label="I have an invitation for an existing account"
      /><v-form @submit.prevent="submit">
        <template v-if="invited">
          <p>Your role and study assignments will be preserved.</p>
          <v-text-field
            v-model="token"
            label="Invitation token"
            autocomplete="off"
            maxlength="1024"
          /> </template
        ><template v-else>
          <v-text-field
            v-model="username"
            label="Username"
            autocomplete="username"
          /><v-text-field
            v-model="email"
            type="email"
            label="Email address"
            autocomplete="email"
          /> </template
        ><v-btn
          type="submit"
          color="primary"
          :loading="busy"
          :disabled="invited ? !token.trim() : !username || !email"
        >
          {{ invited ? "Claim existing account" : "Create account" }}
        </v-btn>
      </v-form>
    </template>
  </v-card>
</template>
