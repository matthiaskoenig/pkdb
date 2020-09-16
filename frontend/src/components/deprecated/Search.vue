<template>

  <v-card flat width="100%">
    <div class="search-navbar" style="left:0px; width: 65%">
      <v-btn v-if="results.studies.count>0" title="Go to results"
             color="#1E90FF"
             width="100%"
             to="/data"
      >
        <span v-if="results.studies.count!=0">
          <v-icon left small>{{ faIcon('data') }}</v-icon> Results
        </span>
      </v-btn>
    </div>

    <v-row><v-col><!-- spacing --></v-col></v-row>

    <v-row align="start" justify="left">
        <v-col xs="8" sm="8" md="8" lg="8">

        <!--- Search Component -->
        <v-card tile flat width="100%">
          <v-row no-glutter>
            <v-col cols="9">
              <h1>Search</h1>
            </v-col>
            <v-col cols="3" justify="end">

              <v-btn
                  x-small
                  fab text
                  title="Clear search"
                  v-on:click="reset"
              >
                <v-icon small>fas fa fa-trash-alt</v-icon>
              </v-btn>
              <v-btn
                  x-small
                  fab text
                  title="Search help with examples"
                  @click.stop="show_help"
              >
                <v-icon small>fas fa fa-question</v-icon>
              </v-btn>
              <v-progress-circular
                  indeterminate
                  color="primary"
                  v-if="loading"
              ></v-progress-circular>
            </v-col>
          </v-row>

          <v-row class="mt-4 ml-3">
            <label class="text-subtitle-1 form-label" title="Search and filter data by study information">
              <count-badge text="Studies" :count="results.studies.count"/>
            </label>
          </v-row>

          <study-search-form/>
          <v-row class="mt-4 ml-3">

            <label class=" text-subtitle-1 form-label" title="Search and filter data by subjects">
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

            <label class="text-subtitle-1 form-label" title="Search and filter data by intervention">
              <count-badge text="Interventions" :count="results.interventions.count"/>
            </label>
          </v-row>

          <intervention-form/>
          <v-row class="mt-4 ml-3">
            <label class="text-subtitle-1 form-label" title="Search and filter data by outputs">
              <count-badge text="Outputs" :count="results.outputs.count"/>
              <span style="padding-left: 20px; padding-right: 20px;">&</span>
              <count-badge text="Timecourses" :count="results.timecourses.count"/>
            </label>
          </v-row>
          <output-form/>
        </v-card>
        <!--- End Search Component -->

      </v-col>
        <v-col xs="12" sm="6" md="4" lg="4">
          <v-navigation-drawer
              floating
              permanent
              fixed
              right
              width="35%"
              height="100%"
          >
            <v-card flat style="padding-top: 100px">
              <div class="search-navbar" style="left:0; width:95%; background-color: white;">
              <v-btn v-if="results.studies.count>0"
                  @click="downloadData"
                  :loading="loadingDownload"
                  :disabled="loadingDownload"
                  text
                  width="100%"
                  title="Download current results"
              >
                <v-icon small left>{{ faIcon('download') }}</v-icon>
                Download
              </v-btn>
              </div>
        <info-node-detail
            v-model="display_detail"
            v-if="show_type === 'info_node'"
            :data="detail_info"
        />
        <search-help v-if="show_type === 'help'"/>
        <study-overview v-if="show_type === 'study'" :study="detail_info"/>
            </v-card>
              </v-navigation-drawer>
      </v-col>
    </v-row>
  </v-card>
</template>

<script>
import axios from 'axios'

import CountBadge from "../lib/CountBadge";
import StudySearchForm from "../search/StudySearchForm";
import InterventionForm from "../search/InterventionSearchForm";
import SubjectsForm from "../search/SubjectSearchForm";
import OutputForm from "../search/OutputSearchForm";

import InfoNode from "./InfoNode";
import InfoNodeDetail from "../detail/InfoNodeDetail";
import SearchHelp from "../search/SearchHelp";
import StudyOverview from "../detail/StudyOverview";
import {searchTableMixin} from "../tables/mixins";
import {SearchMixin} from "../../search";
import {StoreInteractionMixin} from "../../storeInteraction";

export default {
  mixins: [searchTableMixin, SearchMixin, StoreInteractionMixin],
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
      axios.get(this.url, {headers: headers})
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
