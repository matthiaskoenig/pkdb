<script setup lang="ts">
import { computed, onScopeDispose, ref, watch } from "vue";
import type { FilterField } from "../fields";
import { suggestions } from "../../../api/search";
import type { Suggestion } from "../../../api/search";
import { errorMessage } from "../../../api/client";
import { useSessionStore } from "../../../stores/session";
const props = defineProps<{ field: FilterField; modelValue: string[] }>();
const emit = defineEmits<{ "update:modelValue": [value: string[]] }>();
const options = ref<Suggestion[]>([]),
  loading = ref(false),
  error = ref(""),
  session = useSessionStore();
let timer: ReturnType<typeof setTimeout> | undefined,
  controller: AbortController | undefined,
  generation = 0;
const items = computed(() => {
  const map = new Map(options.value.map((item) => [item.id, item]));
  for (const id of props.modelValue)
    if (!map.has(id))
      map.set(id, {
        id,
        title: id,
        description: "Selected identifier; its label may be unavailable.",
      });
  return [...map.values()];
});
function cancel() {
  generation++;
  clearTimeout(timer);
  controller?.abort();
  loading.value = false;
}
function schedule(text: string) {
  cancel();
  const own = generation;
  timer = setTimeout(async () => {
    controller = new AbortController();
    loading.value = true;
    error.value = "";
    try {
      const values = await suggestions(props.field, text, controller.signal);
      if (own === generation) options.value = values;
    } catch (cause) {
      if (own === generation) error.value = errorMessage(cause);
    } finally {
      if (own === generation) loading.value = false;
    }
  }, 200);
}
watch(
  () => session.epoch,
  () => {
    cancel();
    options.value = [];
    error.value = "";
  },
);
onScopeDispose(cancel);
</script>
<template>
  <div class="filter-control">
    <v-combobox
      v-if="field.idKey === 'username'"
      :model-value="modelValue"
      :label="field.label"
      :items="items.map((item) => item.id)"
      multiple
      chips
      closable-chips
      clearable
      :loading="loading"
      :error-messages="error"
      @update:model-value="emit('update:modelValue', $event ?? [])"
      @update:search="schedule"
      @focus="schedule('')"
    />
    <v-autocomplete
      v-else
      :model-value="modelValue"
      :label="field.label"
      :items="items"
      item-title="title"
      item-value="id"
      multiple
      chips
      closable-chips
      clearable
      :loading="loading"
      :error-messages="error"
      no-filter
      @update:model-value="emit('update:modelValue', $event ?? [])"
      @update:search="schedule"
      @focus="schedule('')"
    >
      <template #item="{ props: itemProps, item }">
        <v-list-item v-bind="itemProps" :subtitle="item.description" />
      </template>
    </v-autocomplete>
    <details class="field-help">
      <summary>{{ field.label }} help</summary>
      <p>{{ field.help }}</p>
    </details>
  </div>
</template>
