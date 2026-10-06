<script setup lang="ts">
import { computed } from "vue";
// Text of at most `keepUpTo` characters is never broken; longer text may break.
const props = withDefaults(defineProps<{ text: string; keepUpTo?: number }>(), {
  keepUpTo: 0,
});
// A line may break after the slash between two words (`substance/Name`), never
// inside a word or an operator such as `×/÷`.
const kept = computed(() => props.text.length <= props.keepUpTo);
const pieces = computed(() =>
  kept.value
    ? [props.text]
    : props.text.split(/(?<=[\p{L}\p{N}]\/)(?=[\p{L}\p{N}])/u),
);
</script>
<template>
  <template v-for="(piece, index) in pieces" :key="index"
    >{{ piece }}<wbr v-if="!kept && piece.endsWith('/')"
  /></template>
</template>
