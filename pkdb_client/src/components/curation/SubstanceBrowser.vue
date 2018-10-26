<template>
    <span>
  <v-card dark>
    <v-card-title class="headline blue">
      {{ title }}
    </v-card-title>
    <v-card-text>
      <v-autocomplete
              v-model="model"
              :items="substances"
              color="white"
              hide-no-data
              hide-selected
              item-text="Description"
              item-value="API"
              label="Substances"
              placeholder="Start typing to Search"
              persistent-hint
              return-object
      ></v-autocomplete>
    </v-card-text>

    <v-divider></v-divider>
  </v-card>
  {{ substances }}
    </span>
</template>

<script>
    export default {
        name: "SubstanceBrowser",
        props: {
            substances: {
                type: Array,
                required: true
            },
            title: {
                type: String,
                required: true
            }
        },
        data: () => ({
            model: null,
        }),
        computed: {
            choices () {
                if (!this.model) {
                    return []
                }

                return []
            },
        },
    }
</script>

<style scoped>

</style>