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
              <intervention-form/>
            </v-flex>
            <v-flex xs6>
              <output-form/>
            </v-flex>
          <v-flex xs1>studies:{{study_count}}</v-flex>
          <v-flex xs1>interventions: {{intervention_count}}</v-flex>
          <v-flex xs1>groups: {{group_count}}</v-flex>
          <v-flex xs1>individuals: {{individual_count}}</v-flex>
          <v-flex xs1>outputs: {{output_count}}</v-flex>
          <v-flex xs1>
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
          var url = this.resource_url
          if(this.queries.studies__name__in.length > 0){
          url = url + "&studies__name__in=" + this.queries.studies__name__in.join("__")}
          if(this.queries.studies__reference_name__in.length > 0) {
            url = url + "&studies__reference_name__in=" + this.queries.studies__reference_name__in.join("__")
          }
          return url
        },
      },
      methods: {
        update_search_query(emitted_object){
          for (const [key, value] of Object.entries(emitted_object)){
            this.queries[key] = value
          }
        },
        getData() {
          this.loading = true
          if (localStorage.getItem('token')) {
            var headers = {Authorization: 'Token ' + localStorage.getItem('token')}
          } else {
            headers = {}
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


      data () {
    return {
      study_count: 0,
      intervention_count: 0,
      group_count: 0,
      individual_count: 0,
      output_count: 0,

      otype: "pkdata",
      otype_single: "pkdata",
      queries :{
        studies__name__in:[],
        studies__reference_name__in:[],
      },
      search_params: {
        interventions: {
        },
        groups: {
        },
        individuals: {
        },
        outputs: {
        },
        studies: {
          names: [],
          references: [],
        },
      },
    }
    }

    }

</script>

<style>
</style>