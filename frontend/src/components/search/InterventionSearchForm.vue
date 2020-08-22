<template>
  <span>
    <info-node-search ntype="substance" on="interventions" />
    <info-node-search ntype="route"  on="interventions"/>
    <info-node-search ntype="application"  on="interventions" />
    <info-node-search ntype="form" on="interventions" />
    <info-node-search ntype="measurement_type"  on="interventions"/>
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