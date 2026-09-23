<script setup lang="ts">
import { onUnmounted, ref, watch } from "vue";
import { accountApi } from "../../../api/account";
import { useSessionStore } from "../../../stores/session";
import { useAccountAction } from "../useAccountAction";
const emit = defineEmits<{ verified: [] }>();
const session = useSessionStore();
const enrollment = ref<{ secret: string } | null>(null),
  recovery = ref<string[]>([]),
  code = ref("");
const { busy, error, run } = useAccountAction();
function clear() {
  enrollment.value = null;
  recovery.value = [];
  code.value = "";
}
watch(() => session.epoch, clear, { flush: "sync" });
onUnmounted(clear);
function enroll() {
  return run(async (current) => {
    const result = await accountApi.enroll();
    if (current()) enrollment.value = result;
  });
}
async function complete() {
  clear();
  await session.refreshProfile();
  emit("verified");
}
function verify() {
  return run(async (current) => {
    const result = await accountApi.verifyMfa(code.value, !!enrollment.value);
    if (!current()) return;
    code.value = "";
    enrollment.value = null;
    recovery.value = result;
    if (!result.length) await complete();
  });
}
</script>
<template>
  <v-card variant="outlined" class="pa-5">
    <h2 class="text-h6 mb-3">Administrator verification</h2>
    <v-alert v-if="error" type="error" role="alert">{{ error }}</v-alert
    ><template
      v-if="!session.profile?.mfa_enrolled && !enrollment && !recovery.length"
    >
      <p>Set up an authenticator before using administrator access.</p>
      <v-btn color="primary" :loading="busy" @click="enroll">
        Set up authenticator
      </v-btn> </template
    ><template v-else-if="recovery.length">
      <p>Save these recovery codes securely. Each code can be used once.</p>
      <pre class="pa-4" style="white-space: pre-wrap">{{
        recovery.join("\n")
      }}</pre>
      <v-btn
        color="primary"
        @click="
          run(async () => {
            await complete();
          })
        "
      >
        I have saved the codes
      </v-btn> </template
    ><v-form v-else @submit.prevent="verify">
      <template v-if="enrollment">
        <p>Add this time-based secret to your authenticator.</p>
        <v-text-field
          :model-value="enrollment.secret"
          readonly
          label="Authenticator secret"
        />
      </template>
      <p v-else>Enter an authenticator code or unused recovery code.</p>
      <v-text-field
        v-model="code"
        label="Verification code"
        autocomplete="one-time-code"
      /><v-btn type="submit" color="primary" :loading="busy" :disabled="!code">
        Verify
      </v-btn>
    </v-form>
  </v-card>
</template>
