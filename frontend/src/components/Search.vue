<template>
  <div id="Search">

    <v-navigation-drawer
        v-model="drawer"
        temporary
        absolute
        width="100%"
    >
      <v-flex>

        <v-row>
          <v-col cols="4">
            <v-row justify='space-between'>
              <v-col class="pl-0 ml-0"/>
            </v-row>

            <v-row>
              <!--- Start Search Component -->
              <v-card flat tile width="100%">

                <v-btn
                    :loading="loading"
                    color="#41b883"
                    dark
                    @click.stop="drawer = !drawer"
                >
                  Results
                </v-btn>

                <label title="Search and filter data by study information">
                  <count-badge text="Studies" :count="study_data.count"/>
                  <v-spacer/>
                  <v-btn color="black" fab x-small dark outlined @click.stop="show_help">
                    <v-icon>fas fa fa-question</v-icon>
                  </v-btn>
                </label>
                  <study-search-form
                      @studies__name__in="update_search_query"
                      @studies__creator__in="update_search_query"
                      @studies__curators__in="update_search_query"
                  />

                  <label title="Search and filter data by subjects">
                  <count-badge text="Groups" :count="group_data.count"/>
                  <span style="padding-left: 20px; padding-right: 20px;">&</span>
                  <count-badge text="Individuals" :count="individual_data.count"/>
                  </label>
                  <subjects-form
                      @subjects__type="update_search_query"
                      @subject_queries="update_subject_query"
                  />

                <label title="Search and filter data by intervention">
                  <count-badge text="Interventions" :count="intervention_data.count"/>
                </label>
                  <intervention-form
                      @interventions__substance_sid__in="update_search_query"
                      @interventions__route_sid__in="update_search_query"
                      @interventions__application_sid__in="update_search_query"
                      @interventions__measurement_type_sid__in="update_search_query"
                      @interventions__form_sid__in="update_search_query"
                  />

                <label title="Search and filter data by outputs">
                  <count-badge text="Outputs" :count="output_data.count"/>
                  <span style="padding-left: 20px; padding-right: 20px;">&</span>
                  <count-badge text="Timecourses" :count="timecourse_data.count"/>
                  <span style="padding-left: 20px; padding-right: 20px;">&</span>
                  <count-badge text="Scatters" :count="scatter_data.count"/>
                </label>

                <output-form
                    @outputs__substance_sid__in="update_search_query"
                    @outputs__tissue_sid__in="update_search_query"
                    @outputs__measurement_type_sid__in="update_search_query"
                    @outputs__method_sid__in="update_search_query"
                />

              </v-card>
              <!--- End Search Component -->
            </v-row>
          </v-col>

          <v-col cols="8">
            <v-row>
              <v-sheet height="60">
              </v-sheet>
            </v-row>

            <info-node-detail
                v-model="display_detail"
                v-if="show_type === 'info_node'"
                :data="detail_info"
            />
            <search-help v-if="show_type === 'help'"/>
            <study-overview v-if="show_type === 'study'" :study="detail_info"/>
          </v-col>
        </v-row>
      </v-flex>


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
        <v-flex ref="studies" xs12>
          <studies-table :search_hash="true" :hash="study_data.hash" :autofocus="false"/>
        </v-flex>

        <!-- Groups -->
        <v-flex ref="groups" xs12>
          <groups-table :search_hash="true" :hash="group_data.hash" :autofocus="false"/>
        </v-flex>

        <!-- Individuals -->
        <v-flex ref="individuals" xs12>
          <individuals-table :search_hash="true" :hash="individual_data.hash" :autofocus="false"/>
        </v-flex>

        <!-- Interventions -->
        <v-flex ref="interventions" xs12>
          <interventions-table :search_hash="true" :hash="intervention_data.hash" :autofocus="false"/>
        </v-flex>

        <!-- Groups -->
        <v-flex ref="outputs" xs12>
          <outputs-table :search_hash="true" :hash="output_data.hash" :autofocus="false"/>
        </v-flex>

        <v-flex ref="timecourses" xs12>
          <timecourses-table :search_hash="true" :hash="timecourse_data.hash" :autofocus="false"/>
        </v-flex>
      </v-flex>

    </v-layout>
  </div>
</template>

<script>
import CountBadge from "./lib/CountBadge";
import StudySearchForm from "./search/StudySearchForm";
import InterventionForm from "./search/InterventionSearchForm";
import SubjectsForm from "./search/SubjectSearchForm";
import OutputForm from "./search/OutputSearchForm";
import {searchTableMixin} from "./tables/mixins";

import StudiesTable from './tables/StudiesTable';
import IndividualsTable from './tables/IndividualsTable';
import GroupsTable from "./tables/GroupsTable";

import InterventionsTable from "./tables/InterventionsTable";
import OutputsTable from "./tables/OutputsTable";
import TimecoursesTable from "./tables/TimecoursesTable";

import axios from 'axios'
import InfoNode from "./InfoNode";
import InfoNodeDetail from "./detail/InfoNodeDetail";
import SearchHelp from "./search/SearchHelp";
import StudyOverview from "./detail/StudyOverview";

export default {
  mixins: [searchTableMixin],

  name: 'Search',
  components: {
    CountBadge,
    StudyOverview,
    SearchHelp,
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
    TimecoursesTable
  },
  computed: {
    url() {
      let url = this.resource_url

      for (const [key, value] of Object.entries(this.queries)) {
        if (value.length > 0) {
          url = url + "&" + key + "=" + value.join("__")
        }
      }
      for (const query of this.subject_queries) {
        for (const [key, value] of Object.entries(query)) {
          url = url + "&" + key + "=" + value.join("__")
        }
      }
      return url
    },
    display_detail() {
      return this.$store.state.detail_display
    },
    detail_info() {
      return this.$store.state.detail_info
    },

    show_type() {
      return this.$store.state.show_type
    }
  },

  methods: {
    update_subject_query(emitted_object) {
      this.subject_queries = emitted_object;
    },
    show_help() {
      this.$store.state.show_type = 'help'
      this.$store.state.detail_display = true

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
            this.timecourse_data = res.data.timecourses;
            this.scatter_data = res.data.scatters;

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
      study_data: {"hash": "", "count": 0},
      intervention_data: {"hash": "", "count": 0},
      group_data: {"hash": "", "count": 0},
      individual_data: {"hash": "", "count": 0},
      output_data: {"hash": "", "count": 0},
      timecourse_data: {"hash": "", "count": 0},
      scatter_data: {"hash": "", "count": 0},

      otype: "pkdata",
      otype_single: "pkdata",
      queries: {
        // studies
        studies__name__in: [],
        studies__creator__in: [],
        studies__curators__in: [],

        //subjects
        subjects_types: [],
        subjects_measurement_types: [],

        // interventions
        interventions__substance_sid__in: [],
        interventions__route_sid__in: [],
        interventions__measurement_type_sid__in: [],
        interventions__application_sid__in: [],

        interventions__form_sid__in: [],

        // outputs
        outputs__substance_sid__in: [],
        outputs__tissue_sid__in: [],
        outputs__measurement_type_sid__in: [],
        outputs__method_sid__in: [],
      },
      subject_queries: []
    }
  }

}

</script>

<style>
.rot-neg-90 {
  -moz-transform:rotate(-270deg);
  -moz-transform-origin: bottom left;
  -webkit-transform: rotate(-270deg);
  -webkit-transform-origin: bottom left;
  -o-transform: rotate(-270deg);
  -o-transform-origin:  bottom left;
  filter: progid:DXImageTransform.Microsoft.BasicImage(rotation=1);
}
.mousescroll {
  overflow-y: scroll;
  height: 100%;
}

.mousescroll:hover {
  overflow-y: scroll;
}
</style>