import { computed, type ComputedRef, type Ref } from "vue";
import { fieldKeys, sameField, type MetadataForm } from "../metadata";

/**
 * The fields whose values differ between `base` and `form`, in the order of `fieldKeys`. Each
 * field is compared in a computed of its own, which depends only on the values of that field: a
 * keystroke compares the field that it changed, and the list changes only when a field turns
 * changed or unchanged.
 */
export function useChangedFields(
  base: Readonly<Ref<MetadataForm | null>>,
  form: Readonly<Ref<MetadataForm | null>>,
): ComputedRef<string[]> {
  const fields = new Map<string, ComputedRef<boolean>>();

  function changedAt(key: string): ComputedRef<boolean> {
    let changed = fields.get(key);
    if (!changed) {
      changed = computed(() => base.value !== null && form.value !== null && !sameField(base.value, form.value, key));
      fields.set(key, changed);
    }
    return changed;
  }

  const keys = computed(() => [
    ...new Set([...(base.value ? fieldKeys(base.value) : []), ...(form.value ? fieldKeys(form.value) : [])]),
  ]);
  return computed(() => keys.value.filter((key) => changedAt(key).value));
}
