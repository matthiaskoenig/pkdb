<template>
  <v-autocomplete
      v-model="selected_entries"
      :disabled="isUpdating"
      :items="entries"
      :loading="loading"
      :search-input.sync="search"
      chips
      dense
      label="Names"
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


      <v-list-item-content>

        <text-highlight :queries="search.split(/[ ,]+/)">{{ data.item.name }}</text-highlight>
        <!-- <v-list-item-title v-html="data.item.name"></v-list-item-title> -->
        <v-list-item-subtitle v-html="data.item.sid"></v-list-item-subtitle>
      </v-list-item-content>

      <user-avatar :user="data.item.creator"
                   :search="search"
      />

    </template>
  </v-autocomplete>
</template>

<script>

import {searchTableMixin} from "../tables/mixins";

export default {
  name: "StudySearch",
  mixins: [searchTableMixin],
  data () {

    return {
      otype: "studies",
      otype_single: "study",
      autoUpdate: true,
      selected_entries: [],
      isUpdating: false,
    }
  },
  watch:{
    selected_entries() {
      this.$emit('selected_entries',{"studies__name__in":this.selected_entries})
    }
  },
  methods: {
    remove (item) {
      const index = this.selected_entries.indexOf(item.name)
      if (index >= 0) this.selected_entries.splice(index, 1)
    }
  }

}
</script>
