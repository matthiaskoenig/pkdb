<template>
  <multiselect
      :value="selected_entries"
      :options="entries"
      :close-on-select="true"
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
      @input = update_store
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
        class="v-btn"
    >
      <v-btn
          block
          text
          large
          text-left
          class="v-btn-multiselect"
          v-on:mouseover.native="mouseover(props.option)">
        <text-highlight :queries="highlight">
            {{ props.option.label }}
          <!-- <template v-if="props.option.description" > {{props.option.description}}</template> -->
        </text-highlight>
        <span class="text--disabled text-ellipse pl-2">{{props.option.description}}</span>

      </v-btn>

    </template>
    <span slot="noResult">No results found.</span>
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

    query_key:{
      type: String,
      required: true,
    },
    query_type:{
      type: String,
      required: false,
      default:() =>  "queries"
    }
  },
  data() {

    return {
      otype: "info_nodes",
      otype_single: "info_node",
      exclude_abstract: true,
      autoUpdate: true,
      isUpdating: false,
      isLoading: false,
      options: {
        itemsPerPage:50,
        page:1
      }
    }
  },
  computed: {
    selected_entries() {

      return this.$store.state[this.query_type][this.query_key]
    }
  },
  methods: {
    mouseover(option) {
      this.$store.state.show_type = "info_node"
      this.$store.state.detail_info = option
      this.$store.state.detail_display = true
    },
    update_store(value){
      this.$store.dispatch('updateQueryAction', {
        query_type:this.query_type,
        key: this.query_key,
        value: value,
      })
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
      return labels[this.ntype]
    },
  }


}

</script>

<style scoped>
.detail {
  position: absolute
}
.text-ellipse{
  text-align: left;
  text-overflow: ellipsis;
  overflow: hidden;
  text-rendering: optimizelegibility;
  white-space: nowrap;
  word-break: normal;

  font-size: 12px;
}
</style>
<style>
.multiselect__option {
  padding: 0 !important;
}
.multiselect__option {
  width: 100% !important;

}
.multiselect__content-wrapper {
  overflow-x: -moz-hidden-unscrollable !important;
  overflow-y: auto !important;
  z-index: 100;
  width: 100% !important;

}
.v-btn-multiselect {
  text-transform: none;
  white-space: nowrap;
  justify-content: left;
  text-overflow: ellipsis;
  width:100%
}

</style>