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
      <v-card-text v-if="name">
          <!-- <strong>Name:</strong> {{ name }}<br /> -->
          <strong>Data type:</strong> {{ dtype }}<br />
          <strong>Units:</strong> {{ units }}

      </v-card-text>

    <v-expand-transition color="blue lighten-1">

      <v-list v-if="choices.length">
          <v-card-text><strong> Choices: </strong></v-card-text>
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
            name: null,
            dtype: null,
            units: null,
            substances: null,
        }),
        computed: {
            items () {
                return Object.keys(this.options['measurement_types']).sort()

            },

            choices () {
                if (!this.model) {
                    this.name = null;
                    this.dtype = null;
                    this.units = null;
                    return []
                }
                var data = this.options['measurement_types'][this.model];
                this.name = data['name'];
                this.dtype = data['dtype'];
                this.units = data['units'];
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