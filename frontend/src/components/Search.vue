<template>
  <div id="Search">
    <div class="search-navbar">
      <v-btn
          :title="drawer ? 'Go to search results' : 'Go to search form'"
          color="#41b883"
          :disabled="results.studies.count==0"
          width="100%"
          dark
          @click.stop="drawer = !drawer"
      >
        <span v-if="results.studies.count!=0">{{ drawer ? 'Show Results' : 'Show Search' }}</span>
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
          <v-col class="pl-10" cols="4">
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
                    @click="downloadData"
                    :loading="loadingDownload"
                    :disabled="loadingDownload"
                    small
                    outlined
                    class="ma-2"
                >
                  Download
                  <v-icon small right dark>{{faIcon('download')}}</v-icon>
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
                <label class="text-h5 form-label" title="Search and filter data by study information">
                  <count-badge text="Studies" :count="results.studies.count"/>
                </label>
                <v-spacer/>
              </v-row>


              <study-search-form/>
              <v-row class="mt-4 ml-3">

              <label class=" text-h5 form-label" title="Search and filter data by subjects">
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

              <label class="text-h5 form-label" title="Search and filter data by intervention">
                <count-badge text="Interventions" :count="results.interventions.count"/>
              </label>
              </v-row>

                <intervention-form/>
              <v-row class="mt-4 ml-3">
              <label class="text-h5 form-label" title="Search and filter data by outputs">
                <count-badge text="Outputs" :count="results.outputs.count"/>
                <span style="padding-left: 20px; padding-right: 20px;">&</span>
                <count-badge text="Timecourses" :count="results.timecourses.count"/>
              </label>
              </v-row>
              <output-form/>
            </v-card>
            <!--- End Search Component -->
          </v-col>
          <v-col cols="8" class="pr-10 mt-6">
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
        <search-results v-bind="results"></search-results>
      </v-layout>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

import CountBadge from "./lib/CountBadge";
import StudySearchForm from "./search/StudySearchForm";
import InterventionForm from "./search/InterventionSearchForm";
import SubjectsForm from "./search/SubjectSearchForm";
import OutputForm from "./search/OutputSearchForm";
import SearchResults from "./SearchResults";

import InfoNode from "./deprecated/InfoNode";
import InfoNodeDetail from "./detail/InfoNodeDetail";
import SearchHelp from "./search/SearchHelp";
import StudyOverview from "./detail/StudyOverview";
import {searchTableMixin} from "./tables/mixins";

export default {
  mixins: [searchTableMixin],
  name: 'Search',
  components: {
    SearchResults,
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
    url_download(){
      return this.url + "&" + "download=true"
    },
    url() {
      /* Create the search query url.*/
      let url = this.resource_url

      for (const [key, value] of Object.entries(this.$store.state.queries)) {
        if (value.length > 0) {

          url = url + "&" + key + "=" + value.map(i => i.sid).join("__")
        }
      }
      for (const [key, value] of Object.entries(this.$store.state.queries_users)) {
        if (value.length > 0) {

          url = url + "&" + key + "=" + value.map(i => i.username).join("__")
        }
      }
      for (const [key, value] of Object.entries(this.$store.state.subjects_queries)) {
        // handle groups

        if (this.$store.state.subjects_boolean.groups_query) {
          if (value.length > 0) {
            url = url + "&" + "groups__" + key + "=" + value.map(i => i.sid).join("__")
          }
        } else {
          url = url + "&" + "groups__" + key + "=0"
        }

        // handle individuals
        if (this.$store.state.subjects_boolean.individuals_query) {
          if (value.length > 0) {
            url = url + "&" + "individuals__" + key + "=" + value.map(i => i.sid).join("__")
          }
        } else {
          url = url + "&" + "individuals__" + key + "=0"
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
          })
          .catch(err => {
            console.log(err.response.data);
            this.loading = false
          })
          .finally(() => this.loading = false);
    },
    downloadData() {
      this.loadingDownload = true
      let headers = {};
      if (localStorage.getItem('token')) {
        headers = {Authorization: 'Token ' + localStorage.getItem('token')}
      }

        axios.get(this.url + "&download=true", {headers: headers, responseType: 'arraybuffer',})
            .then(response => {
              let blob = new Blob([response.data], {type: 'application/zip'}),
                  url = window.URL.createObjectURL(blob)
              window.open(url)
            })
            .catch(err => {
              console.log(err.response.data);
              this.loadingDownload = false
            })
            .finally(() => this.loadingDownload = false);
      }
  },
  data() {
    return {
      loadingDownload:false,
      drawer: true,
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