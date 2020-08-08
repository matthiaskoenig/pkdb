<template>

  <multiselect
    v-model="selected_entries"
    :options="entries"
    :close-on-select="false"
    :clear-on-select="false"
    :preserve-search="true"
    _placeholder="Search for Measurement Types"
    label="name"
    track-by="name"
    :multiple="true"
    :loading="loading"
    :searchable="true"
    :internal-search="false"
    @search-change=sync_search
  >
      <template slot="tag" slot-scope="{ option, remove }">
        <v-sheet         elevation="1">
          <measurement-type-search-single :option="option" :remove="remove" />
        </v-sheet>

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
      choices: [],
      search:""
    }
  },
  methods: {
    clearAll () {
      this.selected_entries = []
    },
    sync_search(search)
    {
      this.search = search
    }
  }

}
</script>

<style scoped>

</style>