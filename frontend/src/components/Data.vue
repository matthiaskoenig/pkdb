<template>
    <v-card flat width="100%">
      <!--<v-card-title>Search results</v-card-title>-->

      <v-row no-gutters>
        <v-col cols="10">
        <v-btn title="Go to search"
               color="#41b883"
               width="100%"
               to="/search"
        >
          <v-icon left small>{{ faIcon('search') }}</v-icon> Search
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
            <v-icon small left>{{ faIcon('download') }}</v-icon> Download
          </v-btn>
        </v-col>

      </v-row>

      <v-tabs
          v-model="tab"
          background-color="transparent"
      >
        <v-tab
            v-for="item in items"
            :key="item.tab"
        >
          {{ item.tab }}
          <!--<count-chip name="studies" :count="studies.count" icon:></count-chip> -->

        </v-tab>
      </v-tabs>

      <v-tabs-items v-model="tab">
        <v-tab-item
            v-for="item in items"
            :key="item.tab"
        >
          <v-flex xs12 >
            <studies-table v-if="item.tab === 'Studies'" :search_hash="true" :hash="results.studies.hash" :autofocus="false"/>
            <groups-table v-if="item.tab === 'Groups'" :search_hash="true" :hash="results.groups.hash" :autofocus="false"/>
            <individuals-table v-if="item.tab === 'Individuals'" :search_hash="true" :hash="results.individuals.hash" :autofocus="false"/>
            <interventions-table v-if="item.tab === 'Interventions'" :search_hash="true" :hash="results.interventions.hash" :autofocus="false"/>
            <outputs-table v-if="item.tab === 'Outputs'" :search_hash="true" :hash="results.outputs.hash" :autofocus="false"/>
            <timecourses-table v-if="item.tab === 'Timecourses'" :search_hash="true" :hash="results.timecourses.hash" :autofocus="false"/>
          </v-flex>

        </v-tab-item>
      </v-tabs-items>
    </v-card>
</template>

<script>
import {searchTableMixin} from "./tables/mixins";

import StudiesTable from './tables/StudiesTable';
import IndividualsTable from './tables/IndividualsTable';
import GroupsTable from "./tables/GroupsTable";

import InterventionsTable from "./tables/InterventionsTable";
import OutputsTable from "./tables/OutputsTable";
import TimecoursesTable from "./tables/TimecoursesTable";
import {IconsMixin} from "../icons";
import {SearchMixin} from "../search";

export default {
  mixins: [searchTableMixin, IconsMixin, SearchMixin],
  name: "Data",
  components: {
    StudiesTable,
    GroupsTable,
    IndividualsTable,
    InterventionsTable,
    OutputsTable,
    TimecoursesTable
  },
  computed: {
    results () {
      return this.$store.state.results
    }
  },
  data(){
    return {
      loadingDownload: false,
      tab: null,
      items: [
        { tab: 'Studies'},
        { tab: 'Groups'},
        { tab: 'Individuals'},
        { tab: 'Interventions'},
        { tab: 'Outputs'},
        { tab: 'Timecourses'},
      ],
      /*
      results: {
        studies: {"hash": "", "count": 0},
        interventions: {"hash": "", "count": 0},
        groups: {"hash": "", "count": 0},
        individuals: {"hash": "", "count": 0},
        outputs: {"hash": "", "count": 0},
        timecourses: {"hash": "", "count": 0},
      },
      */
    }
  },
  methods: {
    fetch_results() {
      /*
      axios.get(url)
          .then(response => {
            this.data = response.data;
          })
          .catch((error) => {
            this.data = null;
            console.error(this.resource_url);
            console.error(error);
            this.errors = error.response.data;
          })

       */
      this.results = this.$store.state.results
    }
  },
  /*
  created() {
    this.fetch_data(this.resource_url);
  }
   */
}
</script>

<style scoped>

</style>