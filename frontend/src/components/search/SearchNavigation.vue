<template>
  <v-navigation-drawer
      v-model="drawer"
      :mini-variant.sync="hide_search"
      clipped
      permanent
      app
      mini-variant-width="40"
      width="420"
      height="100%"
      dark
  >
    <v-list-item  class="ma-0 pa-0" @click.stop="hide_search = !hide_search">
      <v-list-item-avatar title="Show search panel">
        <v-icon>{{ faIcon('search') }}</v-icon>
      </v-list-item-avatar>
      <!-- Checkbox for consing the results -->
      <concise-check-box/>
      <v-spacer/>

      <!-- Hide search -->
      <hide-search-button/>
    </v-list-item>

    <v-divider v-if="!hide_search"/>

    <v-list-item class="ma-0 pa-0">
      <!-- Download button -->
      <v-list-item-avatar title="Download Data">
        <download-button :study_count="results.studies"/>
      </v-list-item-avatar>


      <v-spacer/>
      <!-- Query progression spinner -->
      <v-progress-circular indeterminate color="primary"  v-if="loading"/>


      <!-- Clear current search filter -->
      <clear-search-button/>

      <!-- Open search help in right detail drawer -->
      <search-help-button/>

    </v-list-item>


    <span v-if="!hide_search">

      <v-list-item  class=" ma-0 pl-1 pr-1">
            <v-card
                width="100%"
                class="parent_color"
                flat
                dark
            >

        <v-list-item-content>
          <v-list-item-title class="mt-0 ml-2 mr-2">
            <v-icon left small>{{faIcon("studies")}}</v-icon>
            <v-badge color="black" :content="results.studies.toString()" right inline >
              Studies
            </v-badge>
          </v-list-item-title>

          <study-search-form/>

          <v-list-item-title class="ml-2 mr-2">
            <v-icon left small>{{faIcon("groups")}}</v-icon>
              <v-badge color="black" :content="results.groups.toString()" right inline >
                Groups
              </v-badge>
              |
              <v-icon left small>{{faIcon("individuals")}}</v-icon>
              <v-badge color="black" :content="results.individuals.toString()" right inline >
                Individuals
              </v-badge>
          </v-list-item-title>

          <subjects-form @subjects__type="update_search_query" @subject_queries="update_subject_query" />

          <v-list-item-title class="ml-2 mr-2">
            <v-icon left small>{{faIcon("interventions")}}</v-icon>
            <v-badge color="black" :content="results.interventions.toString()" right inline >
              Interventions
            </v-badge>
          </v-list-item-title>

          <intervention-form/>

          <v-list-item-title class="ml-2 mr-2">
            <v-icon left small>{{faIcon("outputs")}}</v-icon>
            <v-badge color="black" :content="results.outputs.toString()" right inline >
              Outputs
            </v-badge>
            |
            <v-icon left small>{{faIcon("timecourses")}}</v-icon>
            <v-badge color="black" :content="results.timecourses.toString()" right inline >
              Timecourses
            </v-badge>
            |
            <v-badge color="black" :content="results.scatters.toString()" right inline >
              Scatter
            </v-badge>
          </v-list-item-title>
          <output-form/>

        </v-list-item-content>
        </v-card>
      </v-list-item>

    </span>

  </v-navigation-drawer>
</template>


<script>
import axios from 'axios'

import CountBadge from "../lib/CountBadge";
import StudySearchForm from "../search/StudySearchForm";
import InterventionForm from "../search/InterventionSearchForm";
import SubjectsForm from "../search/SubjectSearchForm";
import OutputForm from "../search/OutputSearchForm";

import InfoNodeDetail from "../detail/InfoNodeDetail";
import SearchHelp from "../search/SearchHelp";
import StudyOverview from "../detail/StudyOverview";
import {searchTableMixin} from "../tables/mixins";
import {SearchMixin} from "../../search";
import ConciseCheckBox from "./ConciseCheckBox";
import ClearSearchButton from "../lib/buttons/ClearSearchButton";
import DownloadButton from "../lib/buttons/DownloadButton";
import SearchHelpButton from "../lib/buttons/SearchHelpButton";
import {StoreInteractionMixin} from "../../storeInteraction";
import HideSearchButton from "../lib/buttons/HideSearchButton";

export default {
  mixins: [searchTableMixin, SearchMixin, StoreInteractionMixin],
  name: "SearchNavigation",
  components: {
    HideSearchButton,
    SearchHelpButton,
    DownloadButton,
    ClearSearchButton,
    ConciseCheckBox,
    CountBadge,
    StudyOverview,
    SearchHelp,
    InfoNodeDetail,
    StudySearchForm,
    InterventionForm,
    SubjectsForm,
    OutputForm,
  },
  methods: {
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
      otype: "pkdata",
      otype_single: "pkdata",
    }
  }
}
</script>

<style scoped>
.parent_color{
  background-color: inherit;
}
</style>