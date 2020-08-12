<template>
  <v-form>
    <label>Subjects</label>
        <v-container fluid>
          <v-row>
            <v-col cols="6">
              <v-switch color="#41b883" v-model="individuals"  label="Individuals"  hide-details></v-switch>
            </v-col>
            <v-col cols="6">
              <v-switch  color="#41b883" v-model="groups" label="Groups" hide-details></v-switch>
            </v-col>
          </v-row>

        </v-container>
        <measurement-type-choice-search ntype="measurement_type" @selected_entries="emit_search_query"/>
  </v-form>
</template>


<script>
import MeasurementTypeChoiceSearch from "./MeasurementTypeChoiceSearch";
import {lookupIcon} from "@/icons"

export default {
  name: "SubjectForm",
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