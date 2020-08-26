<template>
  <v-sheet flat width="100%">
    <v-tabs
        v-model="tab"
        background-color="transparent"
        show-arrows
        class="fixed-tabs-bar"
    >
      <v-tab
          v-for="item in items"
          :key="item.tab"
      >
        {{ item.tab }}
      </v-tab>
    </v-tabs>

    <v-tabs-items v-model="tab">
      <v-tab-item
          v-for="item in items"
          :key="item.tab"
      >
        <studies-table v-if="item.tab === 'Studies'" :search_hash="true" :hash="results.studies.hash"
                       :autofocus="false"/>
        <groups-table v-if="item.tab === 'Groups'" :search_hash="true" :hash="results.groups.hash"
                      :autofocus="false"/>
        <individuals-table v-if="item.tab === 'Individuals'" :search_hash="true" :hash="results.individuals.hash"
                           :autofocus="false"/>
        <interventions-table v-if="item.tab === 'Interventions'" :search_hash="true"
                             :hash="results.interventions.hash" :autofocus="false"/>
        <outputs-table v-if="item.tab === 'Outputs'" :search_hash="true" :hash="results.outputs.hash"
                       :autofocus="false"/>
        <timecourses-table v-if="item.tab === 'Timecourses'" :search_hash="true" :hash="results.timecourses.hash"
                           :autofocus="false"/>
      </v-tab-item>
    </v-tabs-items>
  </v-sheet>
</template>

<script>
import axios from 'axios'

import {searchTableMixin} from "./mixins";

import StudyOverview from "../detail/StudyOverview";
import StudiesTable from './StudiesTable';
import IndividualsTable from './IndividualsTable';
import GroupsTable from "./GroupsTable";

import InterventionsTable from "./InterventionsTable";
import OutputsTable from "./OutputsTable";
import TimecoursesTable from "./TimecoursesTable";
import {IconsMixin} from "../../icons";
import {SearchMixin} from "../../search";


export default {
  mixins: [searchTableMixin, IconsMixin, SearchMixin],
  name: "TableTabs",
  components: {
    StudyOverview,
    StudiesTable,
    GroupsTable,
    IndividualsTable,
    InterventionsTable,
    OutputsTable,
    TimecoursesTable
  },
  computed: {
    results: {
      get(){
        return this.$store.state.results
      },
      set (value) {
        for (const key of Object.keys(this.$store.state.results)){
          this.$store.dispatch('updateQueryAction', {
            query_type: "results",
            key: key,
            value: value[key] })
        }

      },
    },
    data_info_type() {
      /** Type of information to display */
      return this.$store.state.data_info_type
    },
    data_info() {
      /** actual information to display */
      return this.$store.state.data_info
    },

  },
  data() {
    return {
      loadingDownload: false,
      tab: null,
      items: [
        {tab: 'Studies'},
        {tab: 'Groups'},
        {tab: 'Individuals'},
        {tab: 'Interventions'},
        {tab: 'Outputs'},
        {tab: 'Timecourses'},
      ],
    }
  },
  methods: {

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
          })
          .catch(err => {
            console.log(err.response.data);
            this.loading = false
          })
          .finally(() => this.loading = false);
    },
  },

}
</script>

<style scoped>

</style>

<style>
.fixed-tabs-bar .v-tabs__bar {
  position: -webkit-sticky;
  position: sticky;
  top: 4rem;
  z-index: 2;
}
</style>