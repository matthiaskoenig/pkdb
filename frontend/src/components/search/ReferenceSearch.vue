<template>
  <multiselect
      v-model="selected_entries"
      :options="entries"
      :close-on-select="false"
      :clear-on-select="false"
      :preserve-search="true"
      placeholder="Search for Reference"
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


    <template slot="clear" slot-scope="props">
      <div class="multiselect__clear" v-if="selected_entries.length" @mousedown.prevent.stop="clearAll(props.search)"></div>
    </template><span slot="noResult">No results found.</span>

  </multiselect>
</template>


<script>

import {searchTableMixin} from "../tables/mixins.js";
import ReferenceDialog from "../dialogs/ReferenceDialog";
import Multiselect from 'vue-multiselect'

export default {
  name: "ReferenceSearch",
  components: {ReferenceDialog, Multiselect},
  mixins: [searchTableMixin],

  data () {
    return {
      otype: "references",
      otype_single: "reference",
      selected_entries: [],
      abstractLimit: 100,

    }
  },
  watch:{
    selected_entries() {
      this.$emit('selected_entries',{"studies__reference_name__in":this.selected_entries.map(x => x.name)})
    }
  },
  methods: {
    sync_search(search)
    {
      this.search = search
    },
    clearAll () {
      this.selected_entries = []
    },
    truncated(item){
      return item.length > this.abstractLimit ? item.slice(0, this.abstractLimit) + '...'
        : item
    }
  }
}
</script>
<style>
.v-autocomplete__content {
  max-width: 0px;
}
</style>