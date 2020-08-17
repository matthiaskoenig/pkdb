<template>
 <div>
      <study-search @selected_entries="emit_selected_entries"/>
      <user-search on="creator" @selected_entries="emit_selected_entries"/>
      <user-search on="curators" @selected_entries="emit_selected_entries"/>
 </div>
</template>

<script>
import StudySearch from "./StudySearch";
import UserSearch from "./UserSearch";

export default {
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