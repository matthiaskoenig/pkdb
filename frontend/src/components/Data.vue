<template>
    <v-card flat>
      <!--<v-card-title>Search results</v-card-title>-->

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
            <studies-table v-if="item.tab === 'Studies'" :search_hash="true" :hash="studies.hash" :autofocus="false"/>
            <groups-table v-if="item.tab === 'Groups'" :search_hash="true" :hash="groups.hash" :autofocus="false"/>
            <individuals-table v-if="item.tab === 'Individuals'" :search_hash="true" :hash="individuals.hash" :autofocus="false"/>
            <interventions-table v-if="item.tab === 'Interventions'" :search_hash="true" :hash="interventions.hash" :autofocus="false"/>
            <outputs-table v-if="item.tab === 'Outputs'" :search_hash="true" :hash="outputs.hash" :autofocus="false"/>
            <timecourses-table v-if="item.tab === 'Timecourses'" :search_hash="true" :hash="timecourses.hash" :autofocus="false"/>
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

export default {
  mixins: [searchTableMixin],
  name: "Data",
  props: {
    studies: Object,
    groups: Object,
    individuals: Object,
    interventions: Object,
    outputs: Object,
    timecourses: Object,
  },
  components: {
    StudiesTable,
    GroupsTable,
    IndividualsTable,
    InterventionsTable,
    OutputsTable,
    TimecoursesTable
  },
  data(){
    return {
      tab: null,
      items: [
        { tab: 'Studies'},
        { tab: 'Groups'},
        { tab: 'Individuals'},
        { tab: 'Interventions'},
        { tab: 'Outputs'},
        { tab: 'Timecourses'},
      ],
    }
  }
}
</script>

<style scoped>

</style>