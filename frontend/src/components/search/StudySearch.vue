<template>

  <multiselect
      v-model="selected_entries"
      :options="entries"
      :close-on-select="false"
      :clear-on-select="false"
      :preserve-search="true"
      placeholder="Search for Studies"
      select-label=""
      label="name"
      track-by="name"
      :multiple="true"
      :loading="loading"
      :searchable="true"
      :internal-search="false"
      @search-change=sync_search>

    <template slot="tag" slot-scope="{ option, remove }">
        <span class="multiselect__tag">
          {{ option.name }}
          <span  @click="remove(option)">
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

          v-on:mouseover.native="mouseover(props.option)"
          v-on:mouseleave.native="mouseleave()">

        <text-highlight :queries="highlight">
          {{props.option.name}}
        </text-highlight>
      </v-btn>

    </template>


    <template slot="clear" slot-scope="props">
      <div class="multiselect__clear" v-if="selected_entries.length" @mousedown.prevent.stop="clearAll(props.search)"></div>
    </template><span slot="noResult">No results found.</span>

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
      selected_entries: [],
    }
  },
  watch:{
    selected_entries() {
      this.$emit('selected_entries',{"studies__name__in":this.selected_entries.map(x => x.name)})
    }
  },
  methods: {
    mouseover(option) {
      this.$store.state.show_type = "study"
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
    }
  }

}
</script>
