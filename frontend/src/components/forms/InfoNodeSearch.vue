<template>
  <multiselect
      v-model="selected_entries"
      :options="entries"
      :close-on-select="false"
      :clear-on-select="false"
      :preserve-search="true"
      :placeholder="'Search for ' + label()"
      label="name"
      track-by="name"
      :multiple="true"
      :loading="loading"
      :searchable="true"
      :internal-search="false"
      @search-change=sync_search>

    <template slot="tag" slot-scope="{ option, remove }">
      <v-chip
          close
          @click:close="remove(option)"
          class="chip--select-multi"
      >
        {{ option.name }}
      </v-chip>
    </template>

    <template slot="clear" slot-scope="props">
      <div class="multiselect__clear" v-if="selected_entries.length" @mousedown.prevent.stop="clearAll(props.search)"></div>
    </template><span slot="noResult">Oops! No elements found. Consider changing the search query.</span>

  </multiselect>
</template>

<script>

import {searchTableMixin} from "../tables/mixins";
import Multiselect from 'vue-multiselect'

export default {
  name: "InfoNodeSearch",
  components: {
    Multiselect
  },
  mixins: [searchTableMixin],
  data () {

    return {
      otype: "info_nodes",
      otype_single: "info_node",
      autoUpdate: true,
      selected_entries: [],
      isUpdating: false,
      isLoading: false,
    }
  },
  watch:{
    selected_entries() {
      var emit_object = {}
      emit_object[this.$props.ntype + "_name__in"] = this.selected_entries.map(x => x.name)
      this.$emit('selected_entries',emit_object)
    }
  },
  methods: {
    clearAll () {
      this.selected_entries = []
    },
    sync_search(search)
    {
      this.search = search
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