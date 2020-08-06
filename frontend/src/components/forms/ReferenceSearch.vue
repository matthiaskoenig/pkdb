<template>

  <v-autocomplete
      v-model="selected_entries"
      :items.sync="entries"
      :loading="loading"
      :search-input.sync="search"
      allow-overflow
      dense
      label="References"
      item-text="name"
      item-value="name"
      no-filter
      multiple
  >
    <template v-slot:selection="data">
      <v-chip
          close
          @click:close="remove(data.item)"
          class="chip--select-multi"
      >
        {{ data.item.name }}
      </v-chip>
    </template>
    <template v-slot:item="data">
      <reference-dialog v-if="showReferenceDialog" :data="data"/>
      <v-list-item-content>
        <v-list-item-title v-if="data.item.title">  <text-highlight :queries="search.split(/[ ,]+/)">{{ truncated(data.item.title) }}</text-highlight> </v-list-item-title>
        <v-list-item-title v-html="data.item.name">  </v-list-item-title>
        <v-list-item-title v-html="data.item.sid"></v-list-item-title>
        <v-list-item-subtitle v-if="data.item.abstract"> {{ truncated(data.item.abstract) }}</v-list-item-subtitle>
        <v-list-item-action>

          <v-btn icon>
            <v-icon color="grey lighten-1"  @click="showReferenceDialog=true">{{ faIcon('info') }}</v-icon>
          </v-btn>
        </v-list-item-action>

      </v-list-item-content>
    </template>
  </v-autocomplete>
</template>


<script>

import {searchTableMixin} from "../tables/mixins";
import ReferenceDialog from "../dialogs/ReferenceDialog";

export default {
  name: "ReferenceSearch",
  components: {ReferenceDialog},
  mixins: [searchTableMixin],
  data () {
    return {
      otype: "references",
      autoUpdate: true,
      otype_single: "reference",
      selected_entries: [],
      abstractLimit: 100,

    }
  },
  watch:{
    selected_entries() {
      this.$emit('selected_entries',{"studies__reference_name__in":this.selected_entries})
    }
  },
  methods: {
    remove (item) {
      const index = this.selected_entries.indexOf(item.name)
      if (index >= 0) this.selected_entries.splice(index, 1)
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