<!--
not yet implemented.
-->
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
import Multiselect from 'vue-multiselect'
import {searchTableMixin} from "../tables/mixins";

export default {
  name: "CreatorSearch",
  components: {
    Multiselect
  },
  data () {

    return {
      users : [
        {"username":"mkoenig","first_name":"Matthias","last_name":"König"},
        {"username":"dimitra","first_name":"Dimitra","last_name":"Eleftheriadou"},
        {"username": "janekg","first_name": "Jan","last_name": "Grzegorzewski"},

      ],
      selected_entries: [],
    }
  },
  watch:{
    selected_entries() {
      this.$emit('selected_entries',{"studies__creator__in":this.selected_entries.map(x => x.name)})
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
