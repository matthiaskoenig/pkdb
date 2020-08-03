<template>

  <v-card>
    Filter interventions by
    <v-form>
      <v-container>
        <v-layout wrap>

          <v-flex xs12>
            <info-node-search ntype="substance"/>
            <info-node-search ntype="route"/>
            <info-node-search ntype="application"/>
            <info-node-search ntype="form"/>

          </v-flex>

        </v-layout>
      </v-container>
    </v-form>
    <v-divider></v-divider>
  </v-card>
</template>


<script>

import StudySearch from "./StudySearch";
import InfoNodeSearch from "./InfoNodeSearch";
export default {
  name: "StudyForm",
  components: {
    InfoNodeSearch,
    StudySearch,
  },
}
</script>