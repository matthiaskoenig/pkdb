<script setup lang="ts">
import type { Component } from "vue";
import DiskVersion from "./DiskVersion.vue";

/**
 * A Vuetify field that shows the disk version of its field, where there is one. The slot of the
 * field is made here and not in the form: a field with a slot is rendered again whenever the
 * form that holds it is, even if none of its props changed, so every keystroke would redraw the
 * fields beside the one that the curator types into. This component gets only props and is
 * rendered again only when one of them changes.
 */
defineOptions({ inheritAttrs: false });
defineProps<{ control: Component; field: string; shown: boolean }>();
const emit = defineEmits<{ use: [] }>();
</script>

<template>
  <component :is="control" v-bind="$attrs">
    <template v-if="shown" #details>
      <DiskVersion :field="field" @use="emit('use')" />
    </template>
  </component>
</template>
