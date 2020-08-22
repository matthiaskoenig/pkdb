<template>
  <div class="main" id="overview">
    <h1>PK-DB - pharmacokinetics database
      <!--
    <v-chip v-if="data.version"
            flat
            small
            color="white"
    >
      Version: {{ data.version }}
    </v-chip>
    -->
    </h1>
    <p>
      PK-DB is an open database for pharmacokinetics information from clinical trials including pre-clinical research.
      Data in PK-DB consists of outputs and timecourses linked to their respective study, group/individual and
      intervention.
    </p>
    <count-table v-bind="data"/>
    <!--<statistics-vega-plot />-->
    <v-row>
      <v-col>

        <v-btn color="#1E90FF"
               width="100%"
               to="/data"
        >
          <v-icon left>{{ faIcon('data') }}</v-icon>
          Data
        </v-btn>
      </v-col>
      <v-col>
        <v-btn color="#41b883"
               width="100%"
               to="/search"
        >
          <v-icon left>{{ faIcon('search') }}</v-icon>
          Search
        </v-btn>
      </v-col>
    </v-row>
  </div>


</template>

<script>
import axios from 'axios'
// import StatisticsVegaPlot from "./plots/StatisticsVegaPlot";
import CountTable from "./tables/CountTable";
import {IconsMixin} from "@/icons";

export default {
  name: "Overview",
  components: {
    // StatisticsVegaPlot,
    CountTable,
  },
  mixins: [IconsMixin],
  data() {
    return {
      headers: [
        {text: 'Count', value: 'count', sortable: false},
        {text: 'Data', value: 'name', sortable: false},
        {text: 'Description', value: 'description', sortable: false},
      ],
      data: {
        version: "",
        study_count: 0,
        group_count: 0,
        individual_count: 0,
        intervention_count: 0,
        output_count: 0,
        timecourse_count: 0,
        reference_count: 0,
      },
    }
  },
  computed: {
    resource_url() {
      return this.api + 'statistics/?format=json'
    },
    api() {
      return this.$store.state.endpoints.api;
    },
    items() {
      return [
        {
          name: 'Study',
          name_plural: 'Studies',
          to: '/studies',
          icon: this.faIcon('studies'),
          count: this.data.study_count,
          description: "Clinical or experimental study measuring data in either single or multiple groups and/or single or multiple individuals."
        },
        {
          name: 'Group',
          to: '/groups',
          icon: this.faIcon('groups'),
          count: this.data.group_count,
          description: "Group of individuals defined by certain characteristica, e.g., smoking status or medication."
        },
        {
          name: 'Individual',
          to: '/individuals',
          icon: this.faIcon('individuals'),
          count: this.data.individual_count,
          description: "A single subject, characterized by the group it belongs to and personal characteristica like age, body weight or sex."
        },
        {
          name: 'Intervention',
          to: '/interventions',
          icon: this.faIcon('interventions'),
          count: this.data.intervention_count,
          description: "Intervention which was performed in the study. Often this is the application of substances, e.g. caffeine or codeine, or changes in " +
              "lifestyle like smoking cessation."
        },
        {
          name: 'Output',
          to: '/outputs',
          icon: this.faIcon('outputs'),
          count: this.data.output_count,
          description: "Clinical or experimental output. These can be single parameters or variables, e.g. pharmacokinetic parameters like AUC, clearance or half-life of the applied substances."
        },
        {
          name: 'Timecourse',
          to: '/timecourses',
          icon: this.faIcon('timecourses'),
          count: this.data.timecourse_count,
          description: "Clinical or experimental time course measurements."
        },
        {
          name: 'Reference',
          to: '/references',
          icon: this.faIcon('references'),
          count: this.data.reference_count,
          description: "Literature references from which the data was digitized and curated."
        },
      ]
    }
  },
  methods: {
    fetch_data(url) {
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
    }
  },
  created() {
    this.fetch_data(this.resource_url);
  }
}
</script>

<style scoped>

</style>