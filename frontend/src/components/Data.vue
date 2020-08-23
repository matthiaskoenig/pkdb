<template>
  <v-card flat width="100%">

    <v-row no-gutters>
      <!-- Top data bar (see also search bar) -->
      <v-col cols="8">
        <v-btn title="Go to search"
               color="#41b883"
               width="100%"
               to="/search"
        >
          <v-icon left small>{{ faIcon('search') }}</v-icon>
          Search
        </v-btn>
      </v-col>
    </v-row>


    <v-row align="start" justify="center">

      <v-col xs="12" sm="6" md="8" lg="8">
        <!-- Data tabs components -->
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
          <v-card flat style="padding-top: 50px">

            <v-btn
                @click="downloadData"
                :loading="loadingDownload"
                :disabled="loadingDownload"
                text
                width="100%"
                title="Download current results"
            >
              <v-icon small left color="#1E90FF">{{ faIcon('download') }}</v-icon>
              Download
            </v-btn>
            <info-node-detail
                v-model="data_info"
                v-if="data_info_type === 'info_node'"
                :data="data_info"
            />
          </v-card>
        </v-navigation-drawer>

        <!--<study-overview v-if="data_info_type === 'study'" :study="data_info"/>-->
      </v-col>

    </v-row>
  </v-card>
</template>

<script>
import {searchTableMixin} from "./tables/mixins";

import StudyOverview from "./detail/StudyOverview";
import StudiesTable from './tables/StudiesTable';
import IndividualsTable from './tables/IndividualsTable';
import GroupsTable from "./tables/GroupsTable";

import InterventionsTable from "./tables/InterventionsTable";
import OutputsTable from "./tables/OutputsTable";
import TimecoursesTable from "./tables/TimecoursesTable";
import {IconsMixin} from "../icons";
import {SearchMixin} from "../search";
import InfoNodeDetail from "./detail/InfoNodeDetail";
import InfoNode from "./deprecated/InfoNode";

export default {
  mixins: [searchTableMixin, IconsMixin, SearchMixin],
  name: "Data",
  components: {
    InfoNodeDetail,
    InfoNode,
    StudyOverview,
    StudiesTable,
    GroupsTable,
    IndividualsTable,
    InterventionsTable,
    OutputsTable,
    TimecoursesTable
  },
  computed: {
    results() {
      return this.$store.state.results
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
      this.results = this.$store.state.results
    }
  },

}
</script>

<style scoped>

</style>