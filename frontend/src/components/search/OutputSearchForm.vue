<template>
  <span>
      <info-node-search ntype="measurement_type" query_type="queries" query_key="outputs__measurement_type_sid__in" />
      <info-node-search ntype="substance" query_type="queries" query_key="outputs__substance_sid__in"/>
      <info-node-search ntype="tissue" query_type="queries" query_key="outputs__tissue_sid__in" />

    <v-row>
      <v-checkbox class="ma-0 pa-1 pl-4" v-model="output_query" label="Outputs" hide-details></v-checkbox>
      <v-checkbox class="ma-0 pa-1 pl-4" v-model="timecourse_query" label="Timecourse"  hide-details></v-checkbox>
      <v-checkbox class="ma-0 pa-1 pl-4" v-model="scatter_query" label="Scatter"  hide-details></v-checkbox>
    </v-row>
  </span>
</template>

<script>
import InfoNodeSearch from "./InfoNodeSearch";

export default {
  name: "OutputSearchForm",
  components: {
    InfoNodeSearch,
  },
  computed: {
    output_query: {
      get(){
        return this.$store.state.queries_output_types.output_query
      },
      set (value) {
        this.$store.dispatch('updateQueryAction', {
          query_type: "queries_output_types",
          key: "output_query",
          value: value })
      }
    },
    timecourse_query: {
      get(){
        return this.$store.state.queries_output_types.timecourse_query
      },
      set (value) {
        this.$store.dispatch('updateQueryAction', {
          query_type: "queries_output_types",
          key: "timecourse_query",
          value: value })
      },
    },
    scatter_query: {
      get(){
        return this.$store.state.queries_output_types.scatter_query
      },
      set (value) {
        this.$store.dispatch('updateQueryAction', {
          query_type: "queries_output_types",
          key: "scatter_query",
          value: value })
      },
    },
  },
}
</script>