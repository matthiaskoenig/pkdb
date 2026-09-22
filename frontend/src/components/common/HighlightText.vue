<script setup lang="ts">
import { computed } from "vue";
const props = defineProps<{ text: string; query?: string }>();
const parts = computed(() => {
  const q = props.query?.trim();
  if (!q) return [{ text: props.text, match: false }];
  const text = props.text.toLocaleLowerCase(),
    needle = q.toLocaleLowerCase(),
    out: { text: string; match: boolean }[] = [];
  let offset = 0,
    index = text.indexOf(needle);
  while (index >= 0) {
    out.push(
      { text: props.text.slice(offset, index), match: false },
      { text: props.text.slice(index, index + q.length), match: true },
    );
    offset = index + q.length;
    index = text.indexOf(needle, offset);
  }
  out.push({ text: props.text.slice(offset), match: false });
  return out;
});
</script>
<template>
  <span
    ><template v-for="(part, index) in parts" :key="index"
      ><mark v-if="part.match">{{ part.text }}</mark
      ><template v-else>{{ part.text }}</template></template
    ></span
  >
</template>
