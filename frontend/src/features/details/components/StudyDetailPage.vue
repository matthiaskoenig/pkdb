<script setup lang="ts">
import { useRoute, useRouter } from "vue-router";
import DetailPanel from "./DetailPanel.vue";
import { useSessionStore } from "../../../stores/session";
import { studyOrigin } from "../resultPosition";
import { studyLocation } from "../studyPath";
import type { DetailRecord } from "../types";
const props = defineProps<{ sid: string }>();
const router = useRouter();
const route = useRoute();
const session = useSessionStore();
// The API answers the PKDB identifier of a released study with the study
// itself; the address then names the study by its own sid.
function loaded(study: DetailRecord) {
  if (typeof study.sid !== "string" || study.sid === props.sid) return;
  void router.replace({
    path: studyLocation(study.sid),
    query: route.query,
    hash: route.hash,
  });
}
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
  <DetailPanel
    entity="studies"
    :identifier="sid"
    @close="close"
    @loaded="loaded"
  />
</template>
