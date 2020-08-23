<template>
  <v-card flat width="100%">

    <v-row no-gutters>
      <v-col cols="10">

        <v-btn title="Go to results"
               color="#1E90FF"
               :disabled="results.studies.count==0"
               width="100%"
               to="/data"
        >
        <span v-if="results.studies.count!=0">
          <v-icon left small>{{ faIcon('data') }}</v-icon> Results
        </span>
        </v-btn>
      </v-col>
      <v-col cols="2">
        <v-btn
            @click="downloadData"
            :loading="loadingDownload"
            :disabled="loadingDownload"
            width="100%"
            text
            flat
            title="Download current results"
        >
          <v-icon small left>{{ faIcon('download') }}</v-icon>
          Download
        </v-btn>
      </v-col>
    </v-row>


    <v-row align="start" justify="center">
      <v-col xs="12" sm="6" md="4" lg="4">

        <!--- Start Search Component -->
        <v-card flat tile width="100%">
          <v-row class="mt-3 mb-4" justify="end">
            <v-btn color="black"
                   class="ma-2"
                   small
                   dark
                   outlined
                   @click.stop="show_help">
              Help
              <v-icon small>fas fa fa-question</v-icon>
            </v-btn>


            <v-btn
                small
                class="ma-2"
                outlined
                v-on:click="reset">
              Clear Search
            </v-btn>
          </v-row>

          <v-row justify="end">
            <v-progress-circular
                indeterminate
                color="primary"
                v-if="loading"
            ></v-progress-circular>

          </v-row>

          <v-row class="mt-4 ml-3">
            <label class="text-h7 form-label" title="Search and filter data by study information">
              <count-badge text="Studies" :count="results.studies.count"/>
            </label>
            <v-spacer/>
          </v-row>

          <study-search-form/>
          <v-row class="mt-4 ml-3">

            <label class=" text-h7 form-label" title="Search and filter data by subjects">
              <count-badge text="Groups" :count="results.groups.count"/>
              <span style="padding-left: 20px; padding-right: 20px;">&</span>
              <count-badge text="Individuals" :count="results.individuals.count"/>
            </label>
          </v-row>
          <subjects-form
              @subjects__type="update_search_query"
              @subject_queries="update_subject_query"
          />
          <v-row class="mt-4 ml-3">

            <label class="text-h7 form-label" title="Search and filter data by intervention">
              <count-badge text="Interventions" :count="results.interventions.count"/>
            </label>
          </v-row>

          <intervention-form/>
          <v-row class="mt-4 ml-3">
            <label class="text-h7 form-label" title="Search and filter data by outputs">
              <count-badge text="Outputs" :count="results.outputs.count"/>
              <span style="padding-left: 20px; padding-right: 20px;">&</span>
              <count-badge text="Timecourses" :count="results.timecourses.count"/>
            </label>
          </v-row>
          <output-form/>
        </v-card>

        <!--- End Search Component -->
      </v-col>
      <v-col xs="12" sm="6" md="8" lg="8">

        <info-node-detail
            v-model="display_detail"
            v-if="show_type === 'info_node'"
            :data="detail_info"
        />
        <search-help v-if="show_type === 'help'"/>
        <study-overview v-if="show_type === 'study'" :study="detail_info"/>
      </v-col>
    </v-row>
  </v-card>
</template>

<script>
import axios from 'axios'

import CountBadge from "./lib/CountBadge";
import StudySearchForm from "./search/StudySearchForm";
import InterventionForm from "./search/InterventionSearchForm";
import SubjectsForm from "./search/SubjectSearchForm";
import OutputForm from "./search/OutputSearchForm";

import InfoNode from "./deprecated/InfoNode";
import InfoNodeDetail from "./detail/InfoNodeDetail";
import SearchHelp from "./search/SearchHelp";
import StudyOverview from "./detail/StudyOverview";
import {searchTableMixin} from "./tables/mixins";
import {SearchMixin} from "../search";

export default {
  mixins: [searchTableMixin, SearchMixin],
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
  },
  computed: {
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
    reset() {
      this.$store.commit('resetQuery');
    },
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
      axios.get(this.search_url, {headers: headers})
          .then(res => {
            this.results = res.data
            // store results in store
            this.$store.state.results = this.results
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
      loadingDownload: false,
      results: {
        studies: {"hash": "", "count": 0},
        interventions: {"hash": "", "count": 0},
        groups: {"hash": "", "count": 0},
        individuals: {"hash": "", "count": 0},
        outputs: {"hash": "", "count": 0},
        timecourses: {"hash": "", "count": 0},
      },
      otype: "pkdata",
      otype_single: "pkdata",
    }
  }
}
</script>

<style scoped>
</style>