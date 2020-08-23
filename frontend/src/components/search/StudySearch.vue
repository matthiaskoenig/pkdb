<template>

  <multiselect
      :value="studies__sid__in"
      :options="entries"
      :close-on-select="true"
      :clear-on-select="false"
      :preserve-search="true"
      placeholder="Select Studies"
      select-label=""
      deselectLabel=""
      label="name"
      track-by="name"
      :multiple="true"
      :loading="loading"
      :searchable="true"
      :internal-search="false"
      @input = update_store
      @search-change=sync_search>

    <template slot="tag" slot-scope="{ option, remove }">
        <span class="multiselect__tag">
          {{ option.name }}
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
          @mouseover.native="mouseover(props.option)">

        <text-highlight :queries="highlight">
          {{props.option.name}}
        </text-highlight>
      </v-btn>
    </template>

  <span slot="noResult">No results found.</span>

  </multiselect>
</template>

<script>
import Multiselect from 'vue-multiselect'
import {searchTableMixin} from "../tables/mixins";

export default {
  name: "StudySearch",
  mixins: [searchTableMixin],
  components: {
    Multiselect
  },
  data () {
    return {
      otype: "studies",
      otype_single: "study",
      autoUpdate: true,
    }
  },
  computed: {
    studies__sid__in(){
      return this.$store.state.queries.studies__sid__in
    },
  },
  methods: {
    update_store(value){
      this.$store.dispatch('updateQueryAction', {
        query_type:"queries",
        key: "studies__sid__in",
        value: value,
      })
    },
    mouseover(option) {
      this.$store.state.show_type = "study"
      this.$store.state.detail_info = option
      this.$store.state.detail_display = true
    },
    sync_search(search)
    {
      this.search = search
    }
  },

}
</script>
