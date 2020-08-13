<template>
  <v-card outlined  width="100%">
    <v-form>
      <v-card-title>
        <v-badge
            color="red"
            :content="count"
        >
          Studies
        </v-badge>
      </v-card-title>

        <study-search @selected_entries="emit_selected_entries"/>
    </v-form>
  </v-card>
</template>


<script>
  import StudySearch from "./StudySearch";

  export default {
    props:{count:0},
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