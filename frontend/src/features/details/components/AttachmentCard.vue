<script setup lang="ts">
import { computed, watch } from "vue";
import { VBtn } from "vuetify/components";
import { useImagePreview } from "../useImagePreview";
const props = defineProps<{ path: string; name: string }>();
const { busy, failure, preview, load, clear } = useImagePreview();
const image = computed(() => /\.(png|jpe?g|gif|webp|avif)$/i.test(props.name));
watch(() => props.path, clear);
</script>
<template>
  <article class="attachment">
    <h4>{{ name }}</h4>
    <div class="actions">
      <VBtn
        v-if="image"
        :disabled="busy"
        variant="outlined"
        @click="load(path)"
      >
        Preview image </VBtn
      ><VBtn v-if="busy || preview" variant="text" @click="clear">
        {{ busy ? "Cancel" : "Close preview" }}
      </VBtn>
    </div>
    <p v-if="busy" role="status">Loading attachment…</p>
    <p v-if="failure" role="alert">{{ failure }}</p>
    <img v-if="preview" :src="preview" :alt="name" />
  </article>
</template>
<style scoped>
.attachment {
  margin-block: 1rem;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
img {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
}
</style>
