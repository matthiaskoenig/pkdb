<template>
  <div id="Search">
    <v-layout row wrap>
      <v-flex xs6>
        <study-form
            @studies__name__in="update_search_query"
            @studies__reference_name__in="update_search_query"
        />
      </v-flex>
      <v-flex xs6>
        <subjects-form/>
      </v-flex>
      <v-flex xs6>
        <intervention-form
            @interventions__substance_name__in="update_search_query"
            @interventions__route_name__in="update_search_query"
            @interventions__application_name__in="update_search_query"
            @interventions__form_name_in="update_search_query"
        />
      </v-flex>
      <v-flex xs6>
        <output-form/>
      </v-flex>

      <v-flex xs2>studies: {{ study_count }}</v-flex>
      <v-flex xs2>interventions: {{ intervention_count }}</v-flex>
      <v-flex xs2>groups: {{ group_count }}</v-flex>
      <v-flex xs2>individuals: {{ individual_count }}</v-flex>
      <v-flex xs2>outputs: {{ output_count }}</v-flex>
      <v-flex xs2>

        <v-progress-circular
            indeterminate
            color="primary"
            v-if="loading"
        >
        </v-progress-circular>
      </v-flex>

    </v-layout>
  </div>
</template>

<script>
import StudyForm from "./forms/StudyForm";
import InterventionForm from "./forms/InterventionForm";
import SubjectsForm from "./forms/SubjectsForm";
import OutputForm from "./forms/OutputForm";
import {searchTableMixin} from "./tables/mixins";

import axios from 'axios'

export default {
  mixins: [searchTableMixin],

  name: 'Search',
  components: {
    StudyForm,
    InterventionForm,
    SubjectsForm,
    OutputForm
  },
  computed: {
    url() {
      let url = this.resource_url

      for (const [key, value] of Object.entries(this.queries)) {
        if (value.length > 0) {
          url = url + "&" + key + "=" + value.join("__")
        }
      }
      return url
    },
  },
  methods: {
    update_search_query(emitted_object) {
      for (const [key, value] of Object.entries(emitted_object)) {

        this.queries[key] = value
      }
    },
    getData() {
      this.loading = true
      let headers = {};
      if (localStorage.getItem('token')) {
        let headers = {Authorization: 'Token ' + localStorage.getItem('token')}
      }
      axios.get(this.url, {headers: headers})
          .then(res => {
            this.study_count = res.data.studies.data.count;
            this.intervention_count = res.data.interventions.data.count;
            this.group_count = res.data.groups.data.count;
            this.individual_count = res.data.individuals.data.count;
            this.output_count = res.data.outputs.data.count;
          })
          .catch(err => {
            console.log(err.response.data);
            this.loading = false
          })
          .finally(() => this.loading = false);
    },
  },


  data() {
    return {
      study_count: 0,
      intervention_count: 0,
      group_count: 0,
      individual_count: 0,
      output_count: 0,

      otype: "pkdata",
      otype_single: "pkdata",
      queries: {
        studies__name__in: [],
        studies__reference_name__in: [],
        interventions__substance_name__in: [],
        interventions__route_name__in: [],
        interventions__application_name__in: [],
        interventions__form_name__in: [],
      }
    }
  }

}

</script>

<style>
</style>