<template>

  <multiselect
    v-model="selected_entries"
    :options="entries"
    :close-on-select="false"
    :clear-on-select="false"
    :preserve-search="true"
    placeholder="Search for Measurement Types"
    label="name"
    track-by="name"
    :multiple="true"
    :loading="loading"
    :searchable="true"
    tagPosition="bottom"
    :internal-search="false"
    @search-change=sync_search
  >

      <template slot="tag" slot-scope="{ option, remove }">

        <v-container>
        <v-sheet  elevation="1">
          <measurement-type-search-single
              :option_parent="option"
              :remove_parent="remove"
              @selected_entries="emit_selected_entries"
          />
        </v-sheet>
        </v-container>

      </template>

  </multiselect>
</template>

<script>

import {searchTableMixin} from "../tables/mixins";
import MeasurementTypeSearchSingle from "./MeasurementTypeSearchSingle"
import Multiselect from 'vue-multiselect'

export default {
  name: "InfoNodeSearch",
  components: {
    MeasurementTypeSearchSingle,
    Multiselect},
  mixins: [searchTableMixin, MeasurementTypeSearchSingle],
  data () {

    return {
      otype: "info_nodes",
      otype_single: "info_node",
      autoUpdate: true,
      selected_entries: [],
      child_choices : {},

      search:""
    }
  },
  watch: {
    selected_entries: {
      handler() {
        this.$emit('selected_entries', this.q(this.child_choices))
      },
      deep: true
    }
  },
  methods: {
    q(child_choices) {
      var query_dict = []
      for (var selected of this.selected_entries) {
        if (selected.sid in child_choices){
          if( child_choices[selected.sid].length > 0){
            query_dict.push({"choice_sid__in":child_choices[selected.sid]})
          }
          else{
            query_dict.push({"measurement_type_sid":[selected.sid]})
          }
        }
        else {
          query_dict.push({"measurement_type_sid":[selected.sid]})
        }
      }
      return query_dict
    },
    clearAll () {
      this.selected_entries = []
    },
    sync_search(search)
    {
      this.search = search
    },
    emit_selected_entries(emitted_object) {
      this.child_choices[emitted_object.sid] = emitted_object.choices__in
      this.$emit('selected_entries',this.q(this.child_choices))

    }
  }

}
</script>

<style scoped>

</style>