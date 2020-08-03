<template>

  <v-card>
    Filter subjects by
    <v-form>
      <v-container>
        <v-layout wrap>
          <v-flex xs12>
            <measurement-type-choice-search/>
          </v-flex>

          <v-flex xs12>
          </v-flex>

        </v-layout>
      </v-container>
    </v-form>
    <v-divider></v-divider>
  </v-card>
</template>


<script>

import MeasurementTypeChoiceSearch from "./MeasurementTypeChoiceSearch";
export default {
  name: "SubjectForm",
  components: {
    MeasurementTypeChoiceSearch
  },
}
</script>