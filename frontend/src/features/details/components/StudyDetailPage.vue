<script setup lang="ts">
import { useRoute, useRouter } from "vue-router";
import DetailPanel from "./DetailPanel.vue";
import { useSessionStore } from "../../../stores/session";
import { studyOrigin } from "../resultPosition";
defineProps<{ sid: string }>();
const router = useRouter();
const route = useRoute();
const session = useSessionStore();
function close() {
  const origin = studyOrigin(session.epoch);
  const previous: unknown = window.history.state;
  if (
    origin &&
    typeof previous === "object" &&
    previous !== null &&
    "back" in previous &&
    previous.back === origin.path
  )
    router.back();
  else if (origin) void router.push(origin.path);
  else void router.push({ path: "/data", query: route.query });
}
</script>
<template>
  <DetailPanel entity="studies" :identifier="sid" @close="close" />
</template>
