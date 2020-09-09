<template>
  <v-main>
    <detail-drawer/>

    <v-tabs
        v-model="tab"
        background-color="transparent"
        show-arrows
        class="fixed-tabs-bar"
        icons-and-text
    >
      <v-tab
          v-for="item in items"
          :key="item.tab"
          :href="'#'+ item.tab"
      >
        {{ item.tab }} ({{results[item.tab].count}})
        <scatter-icon v-if="item.tab === 'scatter'"/>
        <v-icon small v-else>{{ faIcon(item.tab) }}</v-icon>

      </v-tab>
    </v-tabs>

    <v-tabs-items v-model="tab">
      <v-tab-item
          v-for="item in items"
          :key="item.tab"
          :value="item.tab"
      >
        <studies-table v-if="item.tab === 'studies'" :search_hash="true" :hash="results.studies.hash"
                       :autofocus="false"/>
        <groups-table v-if="item.tab === 'groups'" :search_hash="true" :hash="results.groups.hash"
                      :autofocus="false"/>
        <individuals-table v-if="item.tab === 'individuals'" :search_hash="true" :hash="results.individuals.hash"
                           :autofocus="false"/>
        <interventions-table v-if="item.tab === 'interventions'" :search_hash="true"
                             :hash="results.interventions.hash" :autofocus="false"/>
        <outputs-table v-if="item.tab === 'outputs'" :search_hash="true" :hash="results.outputs.hash"
                       :autofocus="false"/>
        <timecourses-table v-if="item.tab === 'timecourses'" :search_hash="true" :hash="results.timecourses.hash" data_type="timecourse"
                           :autofocus="false"/>
        <scatter-table v-if="item.tab === 'scatter'" :search_hash="true" :hash="results.scatter.hash" data_type="scatter"
                           :autofocus="false"/>
      </v-tab-item>
    </v-tabs-items>
  </v-main>
</template>

<script>
import axios from 'axios';
import DetailDrawer from "../navigation/DetailDrawer";

import {searchTableMixin} from "./mixins";

import StudyOverview from "../detail/StudyOverview";
import StudiesTable from './StudiesTable';
import IndividualsTable from './IndividualsTable';
import GroupsTable from "./GroupsTable";

import InterventionsTable from "./InterventionsTable";
import OutputsTable from "./OutputsTable";
import TimecoursesTable from "./TimecoursesTable";
import ScatterTable from "./ScatterTable";

import {SearchMixin} from "../../search";
import {IconsMixin} from "../../icons";
import ScatterIcon from "../detail/ScatterIcon";


export default {
  mixins: [searchTableMixin, SearchMixin, IconsMixin],
  name: "TableTabs",
  components: {
    DetailDrawer,
    StudyOverview,
    StudiesTable,
    GroupsTable,
    IndividualsTable,
    InterventionsTable,
    OutputsTable,
    TimecoursesTable,
    ScatterTable,
    ScatterIcon,
  },
  computed: {
    tab: {
      set (tab) {
        this.$router.replace({ query: { ...this.$route.query, tab } })
      },
      get () {
        return this.$route.query.tab
      }
    },
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
      items: [
        {tab: 'studies'},
        {tab: 'groups'},
        {tab: 'individuals'},
        {tab: 'interventions'},
        {tab: 'outputs'},
        {tab: 'timecourses'},
        {tab: 'scatter'},
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