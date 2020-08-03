<template>

  <v-card>
    Filter outputs by
    <v-form>
      <v-container>
        <v-layout wrap>

          <v-flex xs12>

          </v-flex>

          <v-flex xs12>
            <info-node-search ntype="substance"/>
            <info-node-search ntype="tissue"/>
            <info-node-search ntype="measurement_type"/>
            <info-node-search ntype="method"/>
          </v-flex>

        </v-layout>
      </v-container>
    </v-form>
    <v-divider></v-divider>
  </v-card>
</template>

<script>

import InfoNodeSearch from "./InfoNodeSearch";
export default {
  name: "OutputForm",
  components: {
    InfoNodeSearch,
  },
}
</script>