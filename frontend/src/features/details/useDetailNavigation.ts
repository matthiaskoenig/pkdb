import { ref } from "vue";
import type { Relation } from "./types";

// Drill-down state stays inside the detail view; the parent owns URL/tab/scroll.
export function useDetailNavigation() {
  const trail = ref<Relation[]>([]);
  function open(relation: Relation) {
    trail.value = [...trail.value, relation];
  }
  function back() {
    trail.value = trail.value.slice(0, -1);
  }
  function reset() {
    trail.value = [];
  }
  return { trail, open, back, reset };
}
