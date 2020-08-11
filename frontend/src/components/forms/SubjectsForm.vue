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
  methods: {
    faIcon: function (key) {
      return lookupIcon(key)
    },
    emit_search_query(all_searches){
      var query_dict = {}

      for (var [this_key, value] of all_searches) {
        if(this.individuals){
          query_dict["individuals__"+this_key] = value
        }
        if(this.groups){
          query_dict["groups__"+this_key] = value
      }
    }
      console.log(query_dict)
      this.$emit('subject_queries',query_dict)





    }
  },
  data() {
    return {
      individuals: true,
      groups: true,
    }
  }

}
</script>