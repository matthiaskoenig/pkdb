<template>
  <v-card  outlined width="100%">
  <v-form>

    <v-card-title>
      <v-badge
          color="red"
          :content="individual_count.toString()"
      >
        Individuals
      </v-badge>
      <v-spacer></v-spacer>
      &
      <v-spacer></v-spacer>

        <v-badge
            color="red"
            :content="group_count.toString()"
        >
          Groups
        </v-badge>
      <v-spacer></v-spacer>

    </v-card-title>
        <v-container fluid>
          <v-row>
            <v-col cols="12">
              <v-switch color="#41b883" v-model="individuals"  label="Individuals"  hide-details></v-switch>
            </v-col>
            <v-col cols="12">
              <v-switch  color="#41b883" v-model="groups" label="Groups" hide-details></v-switch>
            </v-col>
          </v-row>
        </v-container>
        <measurement-type-choice-search ntype="measurement_type" @selected_entries="emit_search_query"/>
  </v-form>
  </v-card>
</template>


<script>
import MeasurementTypeChoiceSearch from "./MeasurementTypeSearchChoice";
import {lookupIcon} from "@/icons"

export default {
  name: "SubjectSearchForm",
  props:{
    group_count:0,
    individual_count:0,
  },
  components: {
    MeasurementTypeChoiceSearch
  },
  watch: {
    individuals: {
      handler() {
        this.emit_search_query(this.all_searches)
      }
    },
    groups: {
      handler() {
        this.emit_search_query(this.all_searches)
      }
    }
  },
  methods: {
    faIcon: function (key) {
      return lookupIcon(key)
    },
    emit_search_query(all_searches){
      var subject_queries = []
      var this_object = {}
      var new_key = ""
      this.all_searches = all_searches
      if (! this.individuals){
          subject_queries.push({"individuals__ids":["0"]})
        }
      if (! this.groups){
        subject_queries.push({"groups__ids":["0"]})
      }
      for (const this_query of all_searches) {
        for (const [key, value] of Object.entries(this_query)){
         if(this.individuals){
           this_object = {}
           new_key = "individuals__" + key
           this_object[new_key] = value
           subject_queries.push(this_object)}
          if(this.groups){
            this_object = {}
            new_key = "groups__" + key
            this_object[new_key] = value
            subject_queries.push(this_object)
          }
        }
      }

      this.$emit('subject_queries',subject_queries)
    }
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