<template>
  <div>
    <info-node-search ntype='choice' query_key="choice_sid__in" query_type="subjects_queries" />
    <info-node-search ntype='measurement_type' query_key="measurement_type_sid__in" query_type="subjects_queries"/>

    <v-row>
      <v-checkbox class="ma-0 pa-1 pl-4" v-model="groups_query" label="Groups" hide-details></v-checkbox>
      <v-checkbox class="ma-0 pa-1 pl-4" v-model="individuals_query" label="Individuals" hide-details></v-checkbox>
    </v-row>
  </div>
</template>


<script>
import InfoNodeSearch from "./InfoNodeSearch";

import {lookupIcon} from "@/icons"

export default {
  name: "SubjectSearchForm",
  components: {
    InfoNodeSearch
  },
  methods: {
    faIcon: function (key) {
      return lookupIcon(key)
    },
  },
  computed: {
    individuals_query: {
      get(){
        return this.$store.state.subjects_boolean.individuals_query
      },
      set (value) {
        this.$store.dispatch('updateQueryAction', {
          query_type: "subjects_boolean",
          key: "individuals_query",
          value: value,      })
    }
    },
    groups_query: {
      get(){
        return this.$store.state.subjects_boolean.groups_query
      },
      set (value) {
        this.$store.dispatch('updateQueryAction', {
          query_type: "subjects_boolean",
          key: "groups_query",
          value: value,      })
      },
    },
  },
  data() {
    return {
      all_searches : []
    }
  }


}
</script>