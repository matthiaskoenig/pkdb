<template>
  <v-navigation-drawer
      v-model="drawer"
      :mini-variant.sync="hide_search"
      clipped
      permanent
      app
      dark
      mini-variant-width="40"
      width="420"
  >
    <v-list-item @click.stop="hide_search = !hide_search" title="Hide search panel">
      <v-list-item-avatar title="Show search panel">
        <v-icon>{{ faIcon('search') }}</v-icon>
      </v-list-item-avatar>
      <v-spacer/>
      <v-progress-circular
          indeterminate
          color="primary"
          v-if="loading"
      />

      <v-btn v-if="results.studies.count>0"
             fab
             x-small
             text
             @click="downloadData"
             :loading="loadingDownload"
             :disabled="loadingDownload"
             title="Download selected data"
      >
        <v-icon small>{{ faIcon('download') }}</v-icon>

      </v-btn>
      <v-btn
          x-small
          fab text
          title="Clear current search"
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

      <v-btn
          class="ml-4"
          x-small
          icon
          title="Hide search panel"
          @click.stop="hide_search = !hide_search"
      >
        <v-icon>{{ faIcon("left_arrow") }}</v-icon>
      </v-btn>
    </v-list-item>
    <v-divider v-if="!hide_search"/>


    <div v-if="!hide_search">
      <v-list-item class="ma-0 pl-1 pr-1">
        <v-list-item-content>
          <v-list-item-title class="mt-0 ml-2 mr-2">
            <v-icon left small>{{faIcon("studies")}}</v-icon>
            <v-badge color="black" :content="results.studies.count.toString()" right inline >
              Studies
            </v-badge>
          </v-list-item-title>

          <study-search-form/>

          <v-list-item-title class="ml-2 mr-2">
            <v-icon left small>{{faIcon("groups")}}</v-icon>
            <v-badge color="black" :content="results.groups.count.toString()" right inline >
              Groups
            </v-badge>
            |
            <v-icon left small>{{faIcon("individuals")}}</v-icon>
            <v-badge color="black" :content="results.individuals.count.toString()" right inline >
              Individuals
            </v-badge>
          </v-list-item-title>

          <subjects-form
              @subjects__type="update_search_query"
              @subject_queries="update_subject_query"
          />

          <v-list-item-title class="ml-2 mr-2">
            <v-icon left small>{{faIcon("interventions")}}</v-icon>
            <v-badge color="black" :content="results.interventions.count.toString()" right inline >
              Interventions
            </v-badge>
          </v-list-item-title>

          <intervention-form/>

          <v-list-item-title class="ml-2 mr-2">
            <v-icon left small>{{faIcon("outputs")}}</v-icon>
            <v-badge color="black" :content="results.outputs.count.toString()" right inline >
              Outputs
            </v-badge>
            |
            <v-icon left small>{{faIcon("timecourses")}}</v-icon>
            <v-badge color="black" :content="results.timecourses.count.toString()" right inline >
              Timecourses
            </v-badge>
            |
            <v-badge color="black" :content="results.scatter.count.toString()" right inline >
              Scatter
            </v-badge>
          </v-list-item-title>
          <output-form/>

        </v-list-item-content>
      </v-list-item>
    </div>
  </v-navigation-drawer>
</template>


<script>
import axios from 'axios'

import CountBadge from "../lib/CountBadge";
import StudySearchForm from "../search/StudySearchForm";
import InterventionForm from "../search/InterventionSearchForm";
import SubjectsForm from "../search/SubjectSearchForm";
import OutputForm from "../search/OutputSearchForm";

import InfoNode from "../deprecated/InfoNode";
import InfoNodeDetail from "../detail/InfoNodeDetail";
import SearchHelp from "../search/SearchHelp";
import StudyOverview from "../detail/StudyOverview";
import {searchTableMixin} from "../tables/mixins";
import {SearchMixin} from "../../search";


export default {
  mixins: [searchTableMixin, SearchMixin],
  name: "SearchNavigation",
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
    display_detail: {
      get() {
        return this.$store.state.display_detail
      },
      set(value) {
        this.$store.dispatch('updateAction', {
          key: "display_detail",
          value: value,
        })
      }
    },
    hide_search:  {
      get() {
        return this.$store.state.hide_search
      },
      set(value) {
        this.$store.dispatch('updateAction', {
          key: "hide_search",
          value: value,
        })
      }
    },
    detail_info: {
      get() {
        return this.$store.state.detail_info
      },
      set(value) {
        this.$store.dispatch('updateAction', {
          key: "detail_info",
          value: value,
        })
      }
    },
    show_type: {
      get() {
        return this.$store.state.show_type
      },
      set(value) {
        this.$store.dispatch('updateAction', {
          key: "show_type",
          value: value,
        })
      }
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
      this.show_type = 'help'
      this.display_detail = true
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
      drawer: true,
      items: [
        {title: 'Studies', icon: this.faIcon('studies'),},
        {title: 'Subjects', icon: this.faIcon('groups')},
        {title: 'Interventions', icon: this.faIcon('interventions')},
      ],
      loadingDownload: false,
      results: {
        studies: {"hash": "", "count": 0},
        interventions: {"hash": "", "count": 0},
        groups: {"hash": "", "count": 0},
        individuals: {"hash": "", "count": 0},
        outputs: {"hash": "", "count": 0},
        timecourses: {"hash": "", "count": 0},
        scatter: {"hash": "", "count": 0},

      },
      otype: "pkdata",
      otype_single: "pkdata",
    }
  }
}
</script>

<style scoped>
</style>