<script setup lang="ts">
import { VBtn } from "vuetify/components";
import { fieldLabel } from "../metadata";

/** Replaces the edit of a field that changed on both sides with the version on disk. */
defineProps<{ field: string }>();
const emit = defineEmits<{ use: [] }>();
</script>

<template>
  <VBtn
    variant="text"
    color="primary"
    size="small"
    :aria-label="`Use the disk version of ${fieldLabel(field)}`"
    class="disk-version"
    @click="emit('use')"
  >
    Use the disk version
  </VBtn>
</template>
