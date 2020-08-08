<template>
  <multiselect
      v-model="selected_entries"
      :options="entries"
      :close-on-select="false"
      :clear-on-select="false"
      :preserve-search="true"
      placeholder="Search for Studies"
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
