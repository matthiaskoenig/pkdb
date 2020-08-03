<template>
    <div id="Search">
          <v-layout row wrap>
            <v-flex xs6>
              <study-form/>
            </v-flex>
            <v-flex xs6>
              <subjects-form/>
            </v-flex>
            <v-flex xs6>
              <intervention-form/>
            </v-flex>
            <v-flex xs6>
              <output-form/>
            </v-flex>
            <v-flex xs12>
            <v-btn depressed >
              Query Now
            </v-btn>
            </v-flex>
          </v-layout>


    </div>
</template>

<script>
  import StudyForm from "./forms/StudyForm";
  import InterventionForm from "./forms/InterventionForm";
  import SubjectsForm from "./forms/SubjectsForm";
  import OutputForm from "./forms/OutputForm";
    export default {
        name: 'Search',
        components: {
          StudyForm,
          InterventionForm,
          SubjectsForm,
          OutputForm
        },

    }
</script>

<style>
</style>