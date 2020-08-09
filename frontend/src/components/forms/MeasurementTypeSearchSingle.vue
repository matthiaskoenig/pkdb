<template>
  <v-container class="grey lighten-5">
  <v-row>
    <v-col>
    <span @click="remove(option)">❌</span>
    </v-col>
    <v-col>

    {{ option.name }}
    </v-col>
    <v-col>

    <multiselect
            v-model="selected_entries"
            v-if="option.measurement_type.choices.length > 0"
            :options="option.measurement_type.choices"
            :close-on-select="false"
            :clear-on-select="false"
            :preserve-search="true"
            placeholder="Search for Choices"
            :show-labels="false"
            :multiple="true"
            :searchable="true"
            @search-change=sync_search>

          <template slot="tag" slot-scope="{ option, remove }">

            <v-chip
                close
                @click:close="remove(option)"
                class="chip--select-multi"
            >
              {{option}}
            </v-chip>
          </template>
          <template slot="clear" slot-scope="props">
            <div class="multiselect__clear" v-if="selected_entries.length" @mousedown.prevent.stop="clearAll(props.search)"></div>
          </template><span slot="noResult">Oops! No elements found. Consider changing the search query.</span>
        </multiselect>
    </v-col>
  </v-row>
  </v-container>

</template>

<script>
import Multiselect from 'vue-multiselect'
import {lookupIcon} from "@/icons"

export default {
  props: {
    option : null,
    remove : null,
  },
  components: {
    Multiselect
  },
  name: "MeasurementTypeSearchSingle",
  data () {
    return {
      selected_entries: [],
    }
  },
  methods: {
    faIcon: function (key) {
      return lookupIcon(key)
    },
    clearAll () {
      this.selected_entries = []
    },
    sync_search(search)
    {
      this.search = search
    },
  }
}
</script>
