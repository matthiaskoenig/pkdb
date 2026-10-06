<script setup lang="ts">
import { computed } from "vue";
const props = defineProps<{ text: string }>();
// A line may break after the slash between two words (`substance/Name`), never
// inside a word or an operator such as `×/÷`.
const pieces = computed(() =>
  props.text.split(/(?<=[\p{L}\p{N}]\/)(?=[\p{L}\p{N}])/u),
);
</script>
<template>
  <template v-for="(piece, index) in pieces" :key="index"
    >{{ piece }}<wbr v-if="piece.endsWith('/')"
  /></template>
</template>
