<template>
  <v-card height="100%">
    <v-form>
      <v-card-title>Outputs</v-card-title>
      <info-node-search ntype="substance" @selected_entries="emit_selected_entries"/>
      <info-node-search ntype="tissue" @selected_entries="emit_selected_entries"/>
      <info-node-search ntype="measurement_type" @selected_entries="emit_selected_entries"/>
      <info-node-search ntype="method" @selected_entries="emit_selected_entries"/>
    </v-form>
  </v-card>
</template>

<script>
import InfoNodeSearch from "./InfoNodeSearch";

export default {
  name: "OutputSearchForm",
  components: {
    InfoNodeSearch,
  },
  methods: {
    emit_selected_entries(emitted_object) {
      for (const [key, value] of Object.entries(emitted_object)) {

        const label = "outputs__" + key
        let this_object = {}
        this_object[label] = value
        this.$emit(label, this_object)
      }
    }
  },
}
</script>