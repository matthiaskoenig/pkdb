<template>

  <v-card>
    Filter studies by
    <v-form>
      <v-container>
        <v-layout wrap>

          <v-flex xs12>
            <study-search @selected_entries="emit_selected_entries"/>
            <reference-search @selected_entries="emit_selected_entries"/>
          </v-flex>
        </v-layout>
      </v-container>
    </v-form>
    <v-divider></v-divider>
  </v-card>
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
    emit_selected_entries(emitted_object){
      for ( const key  of Object.keys(emitted_object)) {
        this.$emit(key,emitted_object)
      }
    }
  },

}
</script>