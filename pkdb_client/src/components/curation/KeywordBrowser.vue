<template>
    <span>
  <v-card dark>
    <v-card-title class="headline blue">
      {{ title }}
    </v-card-title>
    <v-card-text>
      <v-autocomplete
              v-model="model"
              :items="items"
              color="white"
              hide-no-data
              hide-selected
              item-text="Description"
              item-value="API"
              label="Keywords"
              placeholder="Start typing to Search"
              persistent-hint
              return-object
      ></v-autocomplete>
    </v-card-text>

    <v-divider></v-divider>
  </v-card>
      {{ keywords }}

    </span>
</template>

<script>
    export default {
        name: "KeywordBrowser",
        props: {
            keywords: {
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
            items () {
                var items = [];
                for (var k=0; k<this.keywords.length; k++){
                    var keyword = this.keywords[k];
                    items.push(keyword['name'])
                }
                return items;
            },
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