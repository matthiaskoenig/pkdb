<template>
  <multiselect
      v-model="selected_entries"
      :options="entries"
      :close-on-select="false"
      :clear-on-select="false"
      :preserve-search="true"
      :placeholder="'Search for ' + label()"
      track-by="sid"
      :multiple="true"
      :loading="loading"
      :searchable="true"
      :internal-search="false"
      @search-change=sync_search>

    <template slot="tag" slot-scope="{ option, remove }">
        <span class="multiselect__tag">

           { option.label }}

          <span  @click="remove(option)">
            <i class="multiselect__tag-icon"></i>
          </span>
        </span>
    </template>
    <template
        slot="option"
        slot-scope="props"
    >
      <v-btn icon
             v-on:mouseover.native="mouseover(props.option)"
             v-on:mouseleave.native="mouseleave()">

        <v-icon color="white">{{ faIcon('about') }}</v-icon>
      </v-btn>
      <text-highlight :queries="highlight">
        {{props.option.label}}
      </text-highlight>

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
  watch:{
    selected_entries() {
      var emit_object = {}
      emit_object[this.$props.ntype + "_sid__in"] = this.selected_entries.map(x => x.sid)
      this.$emit('selected_entries',emit_object)
    }
  },
  methods: {
    mouseover(option) {
      this.$store.state.show_type = "info_node"
      this.$store.state.detail_info = option
      this.$store.state.detail_display = true
    },
    mouseleave() {
      this.$store.state.detail_display = false
      this.$store.state.detail_info = {}

    },
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
 .detail {
   position:absolute

 }
</style>