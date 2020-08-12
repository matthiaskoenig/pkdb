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
          {{ option.label }}
          <span  @click="remove(option)">
            <i class="multiselect__tag-icon"></i>
          </span>
        </span>
    </template>
    <template
        slot="option"
        slot-scope="{option, search}"

     >
      <v-btn icon
             v-on:click.native="mouseover(option)">
        <v-icon color="white">{{ faIcon('about') }}</v-icon>
      </v-btn>

       {{option.label}}



    </template>

    <template slot="clear" slot-scope="props">
      <div class="multiselect__clear" v-if="selected_entries.length" @mousedown.prevent.stop="clearAll(props.search)"></div>
    </template><span slot="noResult">Oops! No elements found. Consider changing the search query.</span>

    <v-overlay
        :value="detail_display"
        :absolute="true"
        max-width="290"
    >
      <v-card-text>
        Let Google help apps determine location. This means sending anonymous location data to Google, even when no apps are running.
      </v-card-text>

    </v-overlay>

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
      this.option = option
      this.detail_display = true
    },
    mouseleave() {
      this.detail_display = false
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