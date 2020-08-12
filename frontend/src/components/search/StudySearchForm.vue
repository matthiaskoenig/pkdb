<template>
  <v-card>
    <v-form>
      <v-card-title>Studies</v-card-title>
        <study-search @selected_entries="emit_selected_entries"/>
    </v-form>
  </v-card>
</template>


<script>
  import StudySearch from "./StudySearch";

  export default {
    name: "StudySearchForm",
    components: {

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