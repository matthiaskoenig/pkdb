<template>
    <span>
  <v-card color="blue lighten-1" dark>
    <v-card-title class="headline blue">
      Browse options
    </v-card-title>
    <v-card-text>
      <v-autocomplete
              v-model="options"
              :items="items"
              :search-input.sync="search"
              color="white"
              hide-no-data
              hide-selected
              item-text="Description"
              item-value="API"
              label="Categories"
              placeholder="Start typing to Search"
              return-object
      ></v-autocomplete>
    </v-card-text>

    <v-divider></v-divider>

    <v-expand-transition>
      <v-list v-if="options" class="red lighten-3">
        <v-list-tile
                v-for="(field, i) in fields"
                :key="i"
        >
          <v-list-tile-content>
            <v-list-tile-title v-text="field.value"></v-list-tile-title>
            <v-list-tile-sub-title v-text="field.key"></v-list-tile-sub-title>
          </v-list-tile-content>
        </v-list-tile>
      </v-list>
    </v-expand-transition>

      <!--
    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn
              :disabled="!options"
              color="grey darken-3"
              @click="model = null"
      >
        Clear
        <v-icon right>fas fa-trash-alt</v-icon>
      </v-btn>
    </v-card-actions>
    -->
  </v-card>

        {{ options }}
    </span>
</template>

<script>
    export default {
        name: "OptionsBrowser",
        props: {
            options: {
                type: Object,
                required: true
            }
        },
        data: () => ({
            categories: [],
            class: null,
            dtype: null,
            choices: [],
            entries: [],
            model: null,
            search: null
        }),
        computed: {
            items () {
                return this.options.keys
            },
            fields () {
                if (!this.model) return []

                return Object.keys(this.model).map(key => {
                    return {
                        key: key,
                        value: this.model[key] || 'n/a'
                    }
                })
            },
        },
    }





</script>

<style scoped>

</style>