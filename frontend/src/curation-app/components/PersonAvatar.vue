<script setup lang="ts">
import { computed } from "vue";
import { VAvatar } from "vuetify/components";
import type { Profile } from "../api/types";

/** The avatar of a curator, or the initials of the name; decorative beside the name. */
const props = withDefaults(defineProps<{ profile: Profile; size?: number }>(), { size: 28 });

const initials = computed(() =>
  props.profile.display_name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join(""),
);
</script>

<template>
  <VAvatar
    :size="size"
    :color="profile.avatar_url ? undefined : 'primary'"
    :variant="profile.avatar_url ? 'flat' : 'tonal'"
    class="person-avatar"
    aria-hidden="true"
  >
    <img v-if="profile.avatar_url" :src="profile.avatar_url" alt="" class="person-avatar-image" />
    <span v-else class="person-avatar-initials">{{ initials }}</span>
  </VAvatar>
</template>

<style scoped>
.person-avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.person-avatar-initials {
  font-size: 0.75rem;
  font-weight: 600;
}
</style>
