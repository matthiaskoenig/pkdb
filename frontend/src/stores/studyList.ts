import { defineStore } from "pinia";
import { shallowRef } from "vue";
import type { LocationQueryRaw } from "vue-router";

/** The address of the Studies page as the reader left it, which All studies of a study page returns to (#963). */
export const useStudyListStore = defineStore("studyList", () => {
  const query = shallowRef<LocationQueryRaw>({});
  return { query };
});
