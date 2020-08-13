<template>
  <v-card  outlined height="100%">
    <v-form>
      <v-card-title>Interventions</v-card-title>
      <info-node-search ntype="substance" @selected_entries="emit_selected_entries"/>
      <info-node-search ntype="route" @selected_entries="emit_selected_entries"/>
      <info-node-search ntype="application" @selected_entries="emit_selected_entries"/>
      <info-node-search ntype="measurement_type" @selected_entries="emit_selected_entries"/>
      <info-node-search ntype="form" @selected_entries="emit_selected_entries"/>
    </v-form>
  </v-card>

</template>


<script>
import StudySearch from "./StudySearch";
import InfoNodeSearch from "./InfoNodeSearch";

export default {
  name: "InterventionSearchForm",
  components: {
    InfoNodeSearch,
    StudySearch,
  },
  methods: {
    emit_selected_entries(emitted_object) {
      for (const [key, value] of Object.entries(emitted_object)) {

        const label = "interventions__" + key
        let this_object = {}
        this_object[label] = value
        this.$emit(label, this_object)
      }
    }
  },
}
</script>