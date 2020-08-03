<template>
  <v-list-item-content>
    <v-flex xs6>
    <text-highlight :queries="search_measurement_type.split(/[ ,]+/)">{{ measurement_type.name }}</text-highlight>
    <v-list-item-subtitle v-html="measurement_type.description"></v-list-item-subtitle>
    </v-flex>
    <v-flex xs6>
      <span v-if="measurement_type.measurement_type.choices.length > 0">
         <v-autocomplete
             v-model="selected_choices"
             :disabled="isUpdating"
             :loading="isLoading"
             :items="measurement_type.measurement_type.choices"
             :search-input.sync="search"
             label="Choices"
             filled
             chips
             small-chips
             solo
             dense
             multiple
         >
    </v-autocomplete>
      </span>


    </v-flex>

  </v-list-item-content>

</template>

<script>
export default {
  props: {
    measurement_type : null,
    search_measurement_type: "",
  },
  name: "MeasurementTypeSearchSingle",
  data () {
    return {
      selected_choices: [],
      search: "",
      autoUpdate: true,
      isUpdating: false,
      isLoading: false,
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
