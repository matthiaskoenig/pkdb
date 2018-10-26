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
              label="Categories"
              placeholder="Start typing to Search"
              persistent-hint
              return-object
      ></v-autocomplete>
    </v-card-text>

    <v-divider></v-divider>
      <v-card-text v-if="class_category">
          <strong>Class:</strong> {{ class_category }}<br />
          <strong>Data type:</strong> {{ dtype }}<br />
          <strong>Units:</strong> {{ units }}
      </v-card-text>

    <v-expand-transition color="blue lighten-1">

      <v-list v-if="choices.length">
          <v-card-text>Choices</v-card-text>
        <v-list-tile v-for="(field, i) in choices" :key="i">
          <v-list-tile-content>
            <v-list-tile-title v-text="field"></v-list-tile-title>
          </v-list-tile-content>
        </v-list-tile>
      </v-list>
    </v-expand-transition>
  </v-card>
        <!--{{ options }}-->

    </span>
</template>

<script>
    export default {
        name: "CharacteristicaBrowser",
        props: {
            options: {
                type: Object,
                required: true
            },
            title: {
                type: String,
                required: true
            }
        },
        data: () => ({
            model: null,
            class_category: null,
            dtype: null,
            units: null
        }),
        computed: {
            items () {
                return Object.keys(this.options['categories'])

            },

            choices () {
                if (!this.model) {
                    this.class_category = null;
                    this.dtype = null;
                    this.units = null;
                    return []
                }
                var data = this.options['categories'][this.model];
                this.class_category = data['category'];
                this.dtype = data['dtype'];
                this.units = data['units'];
                if (this.units){
                    this.units = Object.keys(this.units)
                }
                var choices = data['choices'];
                if (choices){
                    return choices.sort()
                } else {
                    return []
                }
            },
        },
    }

</script>

<style scoped>

</style>