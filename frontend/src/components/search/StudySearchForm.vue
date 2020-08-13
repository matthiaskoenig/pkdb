<template>
  <v-card outlined  width="100%">
    <v-form>
      <v-card-title>
        <v-badge
            color="red"
            :content="count.toString()"
        >
          Studies
        </v-badge>
      </v-card-title>
        <study-search @selected_entries="emit_selected_entries"/>
        <user-search  on="creator" @selected_entries="emit_selected_entries"/>
        <user-search  on="curators" @selected_entries="emit_selected_entries"/>

    </v-form>
  </v-card>
</template>


<script>
  import StudySearch from "./StudySearch";
  import UserSearch from "./UserSearch";

  export default {
    props:{count:0},
    name: "StudySearchForm",
    components: {

      StudySearch,
      UserSearch,
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