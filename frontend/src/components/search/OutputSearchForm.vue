<template>
  <span>
      <info-node-search ntype="measurement_type" query_type="queries" query_key="outputs__measurement_type_sid__in" />
      <info-node-search ntype="substance" query_type="queries" query_key="outputs__substance_sid__in"/>
      <info-node-search ntype="tissue" query_type="queries" query_key="outputs__tissue_sid__in" />
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