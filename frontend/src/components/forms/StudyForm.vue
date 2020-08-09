<template>
  <div>
    <v-form>
      <label>Studies</label>
      <study-search @selected_entries="emit_selected_entries"/>
      <reference-search @selected_entries="emit_selected_entries"/>
    </v-form>
  </div>
</template>


<script>
  import StudySearch from "./StudySearch";
  import ReferenceSearch from "./ReferenceSearch";

  export default {
    name: "StudyForm",
    components: {
      ReferenceSearch,
      StudySearch,
    },
    methods: {
      emit_selected_entries(emitted_object) {
        for (const key of Object.keys(emitted_object)) {
          this.$emit(key, emitted_object)
        }
      }
    },
  }
</script>