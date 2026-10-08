<script setup lang="ts">
import { computed, ref, useId, watch } from "vue";
import {
  VAlert,
  VBtn,
  VCard,
  VCardActions,
  VCardItem,
  VCardText,
  VCardTitle,
  VCheckbox,
  VDialog,
  VSpacer,
} from "vuetify/components";
import type { StudyRow } from "../api/types";
import { useReturnFocus, type FocusTarget } from "../composables/useReturnFocus";
import { uploadBlocker, webUrl } from "../overview";
import { useOverviewStore } from "../stores/overview";
import { messageOf } from "../study";

const open = defineModel<boolean>({ default: false });
const props = defineProps<{
  study: StudyRow | null;
  /** Takes the focus when the dialog closes and the control that opened it is gone. */
  fallbackFocus?: FocusTarget;
}>();
const emit = defineEmits<{ done: [study: StudyRow] }>();

const overview = useOverviewStore();
const titleId = useId();
useReturnFocus(open, () => props.fallbackFocus?.());
const acknowledged = ref(false);
const busy = ref(false);
const error = ref<string | null>(null);

/** The upload with the unknown outcome. */
const job = computed(
  () => overview.snapshot?.jobs.find((item) => item.study_id === props.study?.id && item.status === "unknown") ?? null,
);
/** Resume reconciled the upload with the server, for example while the dialog was open. */
const settled = computed(() => job.value === null);
const previous = computed(() => job.value?.endpoint ?? null);
const endpoint = computed(() => overview.snapshot?.endpoint ?? "");
/** The server retries only to the server of the uncertain upload. */
const otherServer = computed(() => previous.value !== null && previous.value !== endpoint.value);
const blocker = computed(() => (overview.snapshot ? uploadBlocker(overview.snapshot) : null));

/** The publication state of the study on the previous server, for an http or https server only. */
const inspectUrl = computed(() => {
  const sid = job.value?.sid ?? props.study?.id;
  const server = webUrl(previous.value);
  if (!server || !sid) return null;
  const path = sid.split("/").map(encodeURIComponent).join("/");
  return `${new URL(server).href.replace(/\/+$/, "")}/api/v2/studies/${path}/publication`;
});

watch(open, (value) => {
  if (value) {
    acknowledged.value = false;
    error.value = null;
  }
});

async function confirm(): Promise<void> {
  const study = props.study;
  if (!study || !acknowledged.value) return;
  busy.value = true;
  error.value = null;
  try {
    await overview.retry(study.id, { acknowledgeUnknown: true });
    open.value = false;
    emit("done", study);
  } catch (caught) {
    error.value = messageOf(caught);
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <VDialog v-model="open" max-width="560" scrollable :aria-labelledby="titleId">
    <VCard v-if="study">
      <VCardItem>
        <VCardTitle :id="titleId" tag="h2">Review uncertain upload</VCardTitle>
      </VCardItem>
      <VCardText class="retry-body">
        <p>
          The last upload of <strong>{{ study.id }}</strong> has no clear outcome. The server may have saved it. Check
          the study on the server before you upload it again. A new upload can replace it.
        </p>
        <dl class="panel-facts">
          <dt>Previous server</dt>
          <dd>{{ previous ?? "Not recorded" }}</dd>
          <dt>Upload goes to</dt>
          <dd>{{ endpoint || "Not configured" }}</dd>
          <template v-if="job?.message">
            <dt>Message</dt>
            <dd>{{ job.message }}</dd>
          </template>
        </dl>
        <div v-if="inspectUrl" class="retry-check">
          <a :href="inspectUrl" target="_blank" rel="noopener noreferrer" class="retry-inspect">
            Check the publication state on the previous server
          </a>
          <p class="retry-note">
            The server may ask you to sign in. Resume in File watching first checks the upload with your API key.
          </p>
        </div>
        <VAlert v-if="settled" type="info" variant="tonal" density="compact" class="status-alert">
          The outcome of this upload is known now. The study needs no retry.
        </VAlert>
        <VAlert v-else-if="otherServer" type="warning" variant="tonal" density="compact" class="status-alert">
          The upload can only be retried on the previous server. Change the server in the settings first.
        </VAlert>
        <VAlert v-else-if="blocker" type="warning" variant="tonal" density="compact" class="status-alert">
          {{ blocker }}
        </VAlert>
        <VCheckbox
          v-model="acknowledged"
          label="I checked the server. Upload this study again."
          color="primary"
          hide-details
          class="retry-acknowledge"
        />
        <VAlert v-if="error" type="error" variant="tonal" density="compact" class="status-alert">{{ error }}</VAlert>
      </VCardText>
      <VCardActions class="dialog-actions">
        <VSpacer />
        <VBtn variant="text" @click="open = false">Cancel</VBtn>
        <VBtn
          variant="flat"
          color="primary"
          :disabled="!acknowledged || settled || otherServer || blocker !== null"
          :loading="busy"
          @click="confirm"
        >
          Validate and upload again
        </VBtn>
      </VCardActions>
    </VCard>
  </VDialog>
</template>

<style scoped>
.retry-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.retry-body p {
  margin: 0;
  line-height: 1.5;
}
.retry-check {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.retry-body .retry-note {
  font-size: 0.875rem;
  color: rgba(var(--v-theme-on-surface), var(--v-medium-emphasis-opacity));
}
/* The box lines up with the text above. */
.retry-acknowledge {
  margin-inline-start: -10px;
}
</style>
