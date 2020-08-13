<template>
  <div id="Search">

    <v-navigation-drawer
        v-model="drawer"
        temporary
        absolute
        width="100%"
    >
      <v-container >

          <v-row

          >
            <v-sheet height="50">

            </v-sheet>
          </v-row>




        <v-row>

        <v-col cols="4">
          <v-row
              justify='space-between'
          >
            <v-col>
              <v-btn
                  color="pink"
                  dark
                  @click.stop="drawer = !drawer"
              >
                Results
              </v-btn>

            </v-col>

            <v-col>

            <v-progress-circular
                indeterminate
                color="primary"
                v-if="loading"
            ></v-progress-circular>
            </v-col>

          </v-row>

            <v-row>

              <study-search-form
                  :count="study_data.length"
                  @studies__name__in="update_search_query"
              />
            </v-row>

            <v-row>

              <subjects-form
                  :individual_count="individual_data.length"
                  :group_count="group_data.length"
                  @subjects__type="update_search_query"
                  @subject_queries="update_subject_query"
              />
            </v-row>
            <v-row>

              <intervention-form
                  :count="intervention_data.length"
                  @interventions__substance_sid__in="update_search_query"
                  @interventions__route_sid__in="update_search_query"
                  @interventions__application_sid__in="update_search_query"
                  @interventions__measurement_type_sid__in="update_search_query"
                  @interventions__form_sid__in="update_search_query"
              />
            </v-row>
            <v-row>
              <output-form :count="output_data.length"
                  @outputs__substance_sid__in="update_search_query"
                  @outputs__tissue_sid__in="update_search_query"
                  @outputs__measurement_type_sid__in="update_search_query"
                  @outputs__method_sid__in="update_search_query"
              />
            </v-row>

        </v-col
            >
        <v-col cols="8">
              <info-node-detail
                  v-model="display_detail"
                  :data="detail_info" />
        </v-col>
        </v-row>

      </v-container>



        <!--
        <v-flex>
          The current search selection gives the following results:<br />
          Studies: {{study_data.length}}
          Groups: {{group_data.length}}
          Individuals: {{individual_data.length}}
          Interventions: {{intervention_data.length}}
          Outputs: {{output_data.length}}
          <v-progress-circular
              indeterminate
              color="primary"
              v-if="loading"
          >
          </v-progress-circular>
        </v-flex>
        -->




    </v-navigation-drawer>




    <v-layout row wrap>


      <v-flex xs12>
        <v-btn
            color="pink"
            dark
            @click.stop="drawer = !drawer"
        >
          Search
        </v-btn>
        <!-- Groups -->
        <v-flex ref="studies" xs12 >
          <studies-table
              :search_ids="true" :ids="study_data" :autofocus="false"/>
        </v-flex>

        <!-- Groups -->
        <v-flex ref="groups" xs12 >
          <groups-table  :search_ids="true" :ids="group_data" :autofocus="false"/>
        </v-flex>

        <!-- Individuals -->
        <v-flex  ref="individuals" xs12 >
          <individuals-table :search_ids="true" :ids="individual_data" :autofocus="false"/>
        </v-flex>

        <!-- Interventions -->
        <v-flex  ref="interventions" xs12 >
          <interventions-table  :search_ids="true" :ids="intervention_data" :autofocus="false"/>
        </v-flex>

        <!-- Groups -->
        <v-flex  ref="outputs" xs12 >
          <outputs-table :search_ids="true" :ids="output_data" :autofocus="false"/>
        </v-flex>


      </v-flex>

    </v-layout>
  </div>
</template>

<script>
import StudySearchForm from "./search/StudySearchForm";
import InterventionForm from "./search/InterventionSearchForm";
import SubjectsForm from "./search/SubjectSearchForm";
import OutputForm from "./search/OutputSearchForm";
import {searchTableMixin} from "./tables/mixins";

import StudiesTable from './tables/StudiesTable';
import IndividualsTable from './tables/IndividualsTable';
import InterventionsTable from "./tables/InterventionsTable";
import OutputsTable from "./tables/OutputsTable";
import GroupsTable from "./tables/GroupsTable";

import axios from 'axios'
import InfoNode from "./InfoNode";
import InfoNodeDetail from "./detail/InfoNodeDetail";

export default {
  mixins: [searchTableMixin],

  name: 'Search',
  components: {
    InfoNodeDetail,
    InfoNode,
    StudySearchForm,
    InterventionForm,
    SubjectsForm,
    OutputForm,

    StudiesTable,
    GroupsTable,
    IndividualsTable,
    InterventionsTable,
    OutputsTable,
  },
  computed: {
    url() {
      let url = this.resource_url

      for (const [key, value] of Object.entries(this.queries)) {
        if (value.length > 0) {
          url = url + "&" + key + "=" + value.join("__")
        }
      }
      for (const query of this.subject_queries){
        for (const [key, value] of Object.entries(query)) {
          url = url + "&" + key + "=" + value.join("__")
        }
      }
      return url
    },
    display_detail () {
      return this.$store.state.detail_display
    },
    detail_info(){
      return this.$store.state.detail_info
    }
  },

  methods: {
    update_subject_query(emitted_object){
      this.subject_queries = emitted_object;
    },
    update_search_query(emitted_object) {
      for (const [key, value] of Object.entries(emitted_object)) {
        this.queries[key] = value
      }
    },
    getData() {
      this.loading = true
      let headers = {};
      if (localStorage.getItem('token')) {
        headers = {Authorization: 'Token ' + localStorage.getItem('token')}
      }
      axios.get(this.url, {headers: headers})
          .then(res => {
            this.study_data = res.data.studies;
            this.intervention_data = res.data.interventions;
            this.group_data = res.data.groups;
            this.individual_data = res.data.individuals;
            this.output_data = res.data.outputs;
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
      drawer: true,
      study_data: [],
      intervention_data: [],
      group_data: [],
      individual_data: [],
      output_data: [],

      otype: "pkdata",
      otype_single: "pkdata",
      queries: {
        // studies
        studies__name__in: [],
        studies__reference_name__in: [],

        //subjects
        subjects_types:[],
        subjects_measurement_types:[],

        // interventions
        interventions__substance_sid__in: [],
        interventions__route_sid__in: [],
        interventions__measurement_type_sid__in: [],
        interventions__application_sid__in: [],

        interventions__form_sid__in: [],

        // outputs
        outputs__substance_sid__in:[],
        outputs__tissue_sid__in:[],
        outputs__measurement_type_sid__in:[],
        outputs__method_sid__in:[],
      },
      subject_queries: []
    }
  }

}

</script>

<style>
.mousescroll {
  overflow-y: scroll;
  height:100%;
}
.mousescroll:hover {
  overflow-y: scroll;
}
</style>