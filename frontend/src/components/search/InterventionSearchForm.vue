<template>
  <span>
    <info-node-search ntype="substance" @selected_entries="update_store"/>
    <info-node-search ntype="route" @selected_entries="update_store"/>
    <info-node-search ntype="application" @selected_entries="update_store"/>
    <info-node-search ntype="form" @selected_entries="update_store"/>
    <info-node-search ntype="measurement_type" @selected_entries="update_store"/>
  </span>
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
    update_store(emitted_object) {
      for (const [key, value] of Object.entries(emitted_object)) {
        const label = "interventions__" + key
        this.$store.state.queries[label] = value

      }
    }
  },
}
</script>