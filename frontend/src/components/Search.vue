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
          <v-col cols="4">
            <!--- Start Search Component -->
            <v-card flat tile width="100%">
              <label class="form-label" title="Search and filter data by study information">
                <count-badge text="Studies" :count="results.studies.count"/>
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
              <study-search-form/>

              <label class="form-label" title="Search and filter data by subjects">
                <count-badge text="Groups" :count="results.groups.count"/>
                <span style="padding-left: 20px; padding-right: 20px;">&</span>
                <count-badge text="Individuals" :count="results.individuals.count"/>
              </label>
              <subjects-form
                  @subjects__type="update_search_query"
                  @subject_queries="update_subject_query"
              />

              <label class="form-label" title="Search and filter data by intervention">
                <count-badge text="Interventions" :count="results.interventions.count"/>
              </label>
              <intervention-form/>

              <label class="form-label" title="Search and filter data by outputs">
                <count-badge text="Outputs" :count="results.outputs.count"/>
                <span style="padding-left: 20px; padding-right: 20px;">&</span>
                <count-badge text="Timecourses" :count="results.timecourses.count"/>
                <span style="padding-left: 20px; padding-right: 20px;">&</span>
                <count-badge text="Scatters" :count="results.scatters.count"/>
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

import InfoNode from "./InfoNode";
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
    url() {
      /* Create the search query url.*/
      let url = this.resource_url

      for (const [key, value] of Object.entries(this.$store.state.queries)) {
        if (value.length > 0) {
          url = url + "&" + key + "=" + value.join("__")
        }
      }
      for (const [key, value] of Object.entries(this.$store.state.subjects_queries)) {
        // handle groups
        console.log(value)

        if (this.$store.state.groups_query) {
          if (value.length > 0) {
            url = url + "&" + "groups__" + key + "=" + value.join("__")
          }
        } else {
          url = url + "&" + "groups__" + key + "=0"
        }

        // handle individuals
        if (this.$store.state.individuals_query) {
          if (value.length > 0) {
            url = url + "&" + "individuals__" + key + "=" + value.join("__")
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
  },

  data() {
    return {
      drawer: true,
      results: {
        studies: {"hash": "", "count": 0},
        interventions: {"hash": "", "count": 0},
        groups: {"hash": "", "count": 0},
        individuals: {"hash": "", "count": 0},
        outputs: {"hash": "", "count": 0},
        timecourses: {"hash": "", "count": 0},
        scatters: {"hash": "", "count": 0},
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