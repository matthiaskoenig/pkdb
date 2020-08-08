<template>

  <v-card>
    Filter interventions by
    <v-form>
      <v-container>
        <v-layout wrap>

          <v-flex xs12>
            <info-node-search ntype="substance" @selected_entries="emit_selected_entries"/>
            <info-node-search ntype="route"  @selected_entries="emit_selected_entries"/>
            <info-node-search ntype="application"  @selected_entries="emit_selected_entries"/>
            <info-node-search ntype="form"  @selected_entries="emit_selected_entries"/>

          </v-flex>

        </v-layout>
      </v-container>
    </v-form>
    <v-divider></v-divider>
  </v-card>
</template>


<script>

import StudySearch from "./StudySearch";
import InfoNodeSearch from "./InfoNodeSearch";
export default {
  name: "StudyForm",
  components: {
    InfoNodeSearch,
    StudySearch,
  },
  methods: {
    emit_selected_entries(emitted_object){
      for ( const [key,value] of Object.entries(emitted_object)) {

        const label = "interventions__" + key
        var this_object = {}
        this_object[label] = value
        this.$emit(label, this_object)
      }
    }
  },
}


</script>