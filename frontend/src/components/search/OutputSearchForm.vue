<template>
  <span>
      <info-node-search ntype="measurement_type" on="outputs" />
      <info-node-search ntype="substance"  on="outputs"/>
      <info-node-search ntype="tissue"  on="outputs" />
      <!--<info-node-search ntype="method" @selected_entries="update_store"/>-->
  </span>
</template>

<script>
import InfoNodeSearch from "./InfoNodeSearch";

export default {
  name: "OutputSearchForm",
  components: {
    InfoNodeSearch,
  }
}
</script>