<template>
  <multiselect
      v-model="selected_entries"
      :options="entries"
      :close-on-select="false"
      :clear-on-select="false"
      :preserve-search="true"
      select-label=""
      deselectLabel=""

      :placeholder="'Search for ' + label()"
      track-by="sid"
      :multiple="true"
      :loading="loading"
      :searchable="true"
      :internal-search="false"
      @search-change=sync_search>

    <template slot="tag" slot-scope="{ option, remove }">
        <span class="multiselect__tag">

           {{ option.label }}

          <span @click="remove(option)">
            <i class="multiselect__tag-icon"></i>
          </span>
        </span>
    </template>
    <template
        slot="option"
        slot-scope="props"
    >
      <v-btn
          block
          text
          large
          v-on:mouseover.native="mouseover(props.option)">

        <text-highlight :queries="highlight">
          {{ props.option.label }}
        </text-highlight>
      </v-btn>

    </template>

    <template slot="clear" slot-scope="props">
      <div class="multiselect__clear" v-if="selected_entries.length"
           @mousedown.prevent.stop="clearAll(props.search)"></div>
    </template>
    <span slot="noResult">Oops! No elements found. Consider changing the search query.</span>
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
  props:{
    _label:String
  },
  data() {

    return {
      detail_display: false,
      otype: "info_nodes",
      otype_single: "info_node",
      exclude_abstract: true,
      autoUpdate: true,
      selected_entries: [],
      isUpdating: false,
      isLoading: false,
      option: {}
    }
  },
  watch: {
    selected_entries() {
      let emit_object = {}
      const key = this.$props.ntype + "_sid__in"
      emit_object[key] = this.selected_entries.map(x => x.sid)
      this.$emit('selected_entries', emit_object)
    }
  },
  methods: {
    mouseover(option) {
      this.$store.state.show_type = "info_node"
      this.$store.state.detail_info = option
      this.$store.state.detail_display = true
    },

    clearAll() {
      this.selected_entries = []
    },
    sync_search(search) {
      this.search = search
    },
    label() {
      const labels = {
        "substance": "Substance",
        "measurement_type": "Measurement Type",
        "form": "Application Form",
        "route": "Application Route",
        "choice": "Choices",
        "tissue": "Tissue",
        "method": "Method",
        "application": "Application Type",
      }
      if(this._label){
        return this._label
      }
      return labels[this.ntype]
    },
  }


}

</script>

<style scoped>
.detail {
  position: absolute

}
</style>