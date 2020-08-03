<template>

  <v-card>
    Filter studies by
    <v-form>
      <v-container>
        <v-layout wrap>

          <v-flex xs12>
            <study-search/>
          </v-flex>
        </v-layout>
      </v-container>
    </v-form>
    <v-divider></v-divider>
  </v-card>
</template>


<script>

import StudySearch from "./StudySearch";
export default {
  name: "StudyForm",
  components: {
    StudySearch,
  },
}
</script>