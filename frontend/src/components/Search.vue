<template>
  <div id="Search">
    <div class="search-navbar">
      <v-btn
          :title="drawer ? 'Go to search results' : 'Go to search form'"
          color="#41b883"
          width="100%"
          dark
          @click.stop="drawer = !drawer"
      >
        {{ drawer ? 'Show Results': 'Show Search' }}
      </v-btn>
    </div>


    <v-navigation-drawer
        v-model="drawer"
        temporary
        absolute
        width="100%"
        class="search-content"
    >
      <v-flex>

        <v-row>
          <v-col cols="4">
              <!--- Start Search Component -->
              <v-card flat tile width="100%">
                <label class="form-label" title="Search and filter data by study information">
                  <count-badge text="Studies" :count="study_data.count"/>
                  <v-spacer/>
                  <v-btn color="black" fab x-small dark outlined @click.stop="show_help">
                    <v-icon>fas fa fa-question</v-icon>
                  </v-btn>
                  <v-progress-circular
                      indeterminate
                      color="primary"
                      v-if="loading"
                  ></v-progress-circular>
                </label>
                  <study-search-form />

                  <label class="form-label" title="Search and filter data by subjects">
                  <count-badge text="Groups" :count="group_data.count"/>
                  <span style="padding-left: 20px; padding-right: 20px;">&</span>
                  <count-badge text="Individuals" :count="individual_data.count"/>
                  </label>
                  <subjects-form
                      @subjects__type="update_search_query"
                      @subject_queries="update_subject_query"
                  />

                <label class="form-label" title="Search and filter data by intervention">
                  <count-badge text="Interventions" :count="intervention_data.count"/>
                </label>
                  <intervention-form/>

                <label class="form-label" title="Search and filter data by outputs">
                  <count-badge text="Outputs" :count="output_data.count"/>
                  <span style="padding-left: 20px; padding-right: 20px;">&</span>
                  <count-badge text="Timecourses" :count="timecourse_data.count"/>
                  <span style="padding-left: 20px; padding-right: 20px;">&</span>
                  <count-badge text="Scatters" :count="scatter_data.count"/>
                </label>

                <output-form/>
              </v-card>
              <!--- End Search Component -->
          </v-col>
          <v-col cols="8">
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


    <div class="results-content">
    <v-layout row wrap>

        <v-flex ref="studies" xs12>
          <studies-table :search_hash="true" :hash="study_data.hash" :autofocus="false"/>
        </v-flex>

        <v-flex ref="groups" xs12>
          <groups-table :search_hash="true" :hash="group_data.hash" :autofocus="false"/>
        </v-flex>

        <v-flex ref="individuals" xs12>
          <individuals-table :search_hash="true" :hash="individual_data.hash" :autofocus="false"/>
        </v-flex>

        <v-flex ref="interventions" xs12>
          <interventions-table :search_hash="true" :hash="intervention_data.hash" :autofocus="false"/>
        </v-flex>

        <v-flex ref="outputs" xs12>
          <outputs-table :search_hash="true" :hash="output_data.hash" :autofocus="false"/>
        </v-flex>

        <v-flex ref="timecourses" xs12>
          <timecourses-table :search_hash="true" :hash="timecourse_data.hash" :autofocus="false"/>
        </v-flex>

    </v-layout>
    </div>
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

      for (const [key, value] of Object.entries(this.$store.state.queries)) {
        if (value.length > 0) {

          url = url + "&" + key + "=" + value.join("__")
        }
      }
      for (const  [key, value] of Object.entries(this.$store.state.subjects_queries)) {
        if (this.$store.state.groups_query){
          if (value.length < 0) {
          url = url + "&" + "groups__"+key + "=" + value.join("__")
        }}
        else{
            url = url + "&" + "groups__"+key + "=0"
          }
        if (this.$store.state.individuals_query){
            if (value.length < 0) {
              url = url + "&" + "individuals__" + key + "=" + value.join("__")
            }
        }
        else{
          url = url + "&" + "individuals__"+key + "=0"
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
    }
  }

}

</script>

<style>
.form-label {
}
.search-navbar {
  position: fixed;
  top: 48px;
  left: 0;
  z-index: 9999;
  width: 100%;
  height: 32px;
  background-color: #CCCCCC;
}
.search-content {
  margin-top: 80px;
}
.results-content {
  margin-top: 50px;
}

.mousescroll {
  overflow-y: scroll;
  height: 100%;
}

.mousescroll:hover {
  overflow-y: scroll;
}
</style>