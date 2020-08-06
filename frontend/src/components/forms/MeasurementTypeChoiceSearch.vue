<template>
  <v-autocomplete
      v-model="selected_entries"
      :disabled="isUpdating"
      :loading="isLoading"
      :items="entries"
      :search-input.sync="search"
      chips
      dense
      :label="label()"
      item-text="name"
      item-value="name"
      no-filter
      multiple
      :v-click-outside="nothing"
  >
    <template v-slot:selection="data">
      <v-chip
          close
          @click:close="remove(data.item)"
          class="chip--select-multi"
      >
        {{ data.item.name }}
      </v-chip>
    </template>
    <template v-slot:item="data">
      <measurement-type-search-single :measurement_type="data.item" :search_measurement_type="search"/>
    </template>
  </v-autocomplete>
</template>

<script>

import {searchTableMixin} from "../tables/mixins";
import MeasurementTypeSearchSingle from "./MeasurementTypeSearchSingle"
export default {
  name: "InfoNodeSearch",
  components: {MeasurementTypeSearchSingle},
  mixins: [searchTableMixin, MeasurementTypeSearchSingle],
  data () {

    return {
      ntype: "measurement_type",
      otype: "info_nodes",
      otype_single: "info_nodes",
      autoUpdate: true,
      selected_entries: [],
      selected_choices: [],
      choices: [],
      isUpdating: false,
      isLoading: false,
    }
  },
  methods: {
    nothing(){},
    remove (item) {
      const index = this.selected_entries.indexOf(item.name)
      if (index >= 0) this.selected_entries.splice(index, 1)
    },
    label(){
      const labels = {
        "substance": "Substances",
        "measurement_type": "Measurement Types",
        "form": "Forms",
        "route": "Routes",
        "choice": "Choices",
        "tissue":"Tissues",
        "method":"Methods",
        "application":"Applications",

      }
      return labels[this.ntype]
    }
  }

}
</script>

<style scoped>

</style>