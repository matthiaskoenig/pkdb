<template>
  <span>
      <info-node-search ntype="measurement_type" @selected_entries="update_store"/>
      <info-node-search ntype="substance" @selected_entries="update_store"/>
      <info-node-search ntype="tissue" @selected_entries="update_store"/>
      <!--<info-node-search ntype="method" @selected_entries="update_store"/>-->
  </span>
</template>

<script>
import InfoNodeSearch from "./InfoNodeSearch";

export default {
  name: "OutputSearchForm",
  components: {
    InfoNodeSearch,
  },
  methods: {
    update_store(emitted_object) {
      for (const [key, value] of Object.entries(emitted_object)) {
        const label = "outputs__" + key
        this.$store.state.queries[label] = value

      }
    }
  },
}
</script>