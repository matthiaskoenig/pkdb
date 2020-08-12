
<template>
  <v-container class="grey lighten-5">

    <v-row>

      <v-col>
        <v-btn icon @click="remove_parent(option_parent)"> <v-icon> {{faIcon('delete')}}</v-icon></v-btn>
      </v-col>
      <v-col>
        {{ option_parent.label }}
      </v-col>

      <v-col>

        <multiselect
            v-model="selected_entries"
            v-if="option_parent.measurement_type.choices.length > 0"
            :options="option_parent.measurement_type.choices"
            :close-on-select="false"
            :clear-on-select="false"
            :preserve-searchpul="true"
            placeholder="Search for Choices"
            label="label"
            track-by="sid"
            :multiple="true"
            :searchable="true"
            tagPosition="bottom"
            @search-change=sync_search>

          <template slot="tag" slot-scope="{ option, remove }">
        <span class="multiselect__tag">
          {{ option.label }}
          <span  @click="remove(option)">
            <i class="multiselect__tag-icon"></i>
          </span>
        </span>
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
    option_parent : null,
    remove_parent : null,
  },
  components: {
    Multiselect
  },
  name: "MeasurementTypeSearchSingle",
  data () {
    return {
      selected_entries: [],
      option_child: {}
    }
  },
  beforeMount () {
    this.option_child = this.option_parent // save props data to itself's data
  },

  watch:{
    selected_entries() {
      if(this.option_parent){
        this.$emit('selected_entries',{"sid":this.option_child.sid, "choices__in": this.selected_entries.map(x => x.sid)})
      }
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