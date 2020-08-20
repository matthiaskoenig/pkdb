<template>
  <div>
    <!--
    <measurement-type-choice-search ntype="measurement_type" @selected_entries="update_store"/>
    -->
    <info-node-search ntype='measurement_type' @selected_entries="update_store"/>
    <info-node-search ntype='choice' @selected_entries="update_store"/>


    <v-checkbox color="#41b883" v-model="groups" label="Groups" hide-details></v-checkbox>
    <v-checkbox color="#41b883" v-model="individuals" label="Individuals" hide-details></v-checkbox>

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
  watch: {
    individuals: {
      handler() {
        this.$store.state.individuals_query = this.individuals
      }
    },
    groups: {
      handler() {
        this.$store.state.groups_query = this.groups
      }
    }
  },
  methods: {
    faIcon: function (key) {
      return lookupIcon(key)
    },

    update_store(emitted_object) {
      for (const [key, value] of Object.entries(emitted_object)) {
        console.log(key)
        console.log(value)
        this.$store.state.subjects_queries[key] = value
      }}
  },
  data() {
    return {
      individuals: true,
      groups: true,
      all_searches : []
    }
  }

}
</script>