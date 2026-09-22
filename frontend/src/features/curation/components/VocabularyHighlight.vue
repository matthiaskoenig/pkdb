<script setup lang="ts">
import { computed } from "vue";
const props = defineProps<{ value: string; query: string }>();
const parts = computed(() => {
  const terms = props.query
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((term) => term.toLocaleLowerCase());
  if (!terms.length) return [{ value: props.value, match: false }];
  const lower = props.value.toLocaleLowerCase();
  const matches = Array.from({ length: props.value.length }, () => false);
  for (const term of terms) {
    let offset = lower.indexOf(term);
    while (offset >= 0) {
      for (let index = offset; index < offset + term.length; index++)
        matches[index] = true;
      offset = lower.indexOf(term, offset + Math.max(1, term.length));
    }
  }
  const result: { value: string; match: boolean }[] = [];
  for (let index = 0; index < props.value.length; index++) {
    const match = matches[index] ?? false;
    const previous = result.at(-1);
    if (previous?.match === match) previous.value += props.value[index];
    else result.push({ value: props.value[index] ?? "", match });
  }
  return result;
});
</script>
<template>
  <span
    ><template v-for="(part, index) in parts" :key="index"
      ><mark v-if="part.match">{{ part.value }}</mark
      ><template v-else>{{ part.value }}</template></template
    ></span
  >
</template>
<style scoped>
mark {
  background: #ffe69a;
  color: #202020;
}
</style>
