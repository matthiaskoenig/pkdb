<template>
  <v-data-table :headers="headers"
                :items="items"
                hide-default-footer
                hide-default-header
  >
    <template v-slot:item.name="{ item }">
      <strong>
        <span v-if="item.name_plural">{{ item.name_plural }}</span>
        <span v-else>{{ item.name }}s</span>
      </strong>
    </template>
    <template v-slot:item.count="{ item }">
      <count-chip :count="item.count"
                  :icon="item.icon"
                  :name="item.name"
                  :to="item.to"
      />
    </template>
  </v-data-table>
</template>

<script>
import axios from 'axios'
import {IconsMixin} from "@/icons";

export default {
  name: 'CountTable',
  mixins: [IconsMixin],
  components: {},
  data() {
    return {
      data: {
        version: "",
        study_count: 0,
        group_count: 0,
        individual_count: 0,
        intervention_count: 0,
        output_count: 0,
        timecourse_count: 0,
        scatter_count: 0,
        reference_count: 0,
      },
      headers: [
        {text: 'Count', value: 'count', sortable: false},
        {text: 'Data', value: 'name', sortable: false},
        {text: 'Description', value: 'description', sortable: false},
      ],
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
          to: '/data?tab=studies',
          icon: this.faIcon('studies'),
          count: this.data.study_count,
          description: "Clinical or experimental study measuring data in groups and/or individuals."
        },
        {
          name: 'Group',
          to: '/data?tab=groups',
          icon: this.faIcon('groups'),
          count: this.data.group_count,
          description: "Group of individuals for which data was reported, e.g., the control group and the group which received " +
              "an intervention. A group is described by certain characteristica, e.g., bodyweight, health status, smoking status or medication."
        },
        {
          name: 'Individual',
          to: '/data?tab=individuals',
          icon: this.faIcon('individuals'),
          count: this.data.individual_count,
          description: "A single subject in the study. A subject is characterized by the group it belongs to " +
              "as well as individual characteristica like age, body weight or sex. Individuals are only created if outputs or timecourses have " +
              "been reported on the subject level (not group level)."
        },
        {
          name: 'Intervention',
          to: '/data?tab=interventions',
          icon: this.faIcon('interventions'),
          count: this.data.intervention_count,
          description: "Intervention which was performed in the study. Often interventions consist of application of a " +
              "substance, e.g. caffeine or codeine. Other examples are changes in lifestyle like smoking cessation."
        },
        {
          name: 'Output',
          to: '/data?tab=outputs',
          icon: this.faIcon('outputs'),
          count: this.data.output_count,
          description: "Clinical or experimental output. These can be single parameters or variables, e.g. pharmacokinetic " +
              "parameters like AUC, clearance or half-life of the applied substances. An output is always linked to the " +
              "respective intervention and group or individual."
        },
        {
          name: 'Timecourse',
          to: '/data?tab=timecourses',
          icon: this.faIcon('timecourses'),
          count: this.data.timecourse_count,
          description: "Clinical or experimental time course measurements. Often timecourses are concentration measurements." +
              " A timecourse is always linked to the respective intervention and group or individual."
        },
        {
          name: 'Scatter',
          to: '/data?tab=scatter',
          icon: 'scatter',
          count: this.data.scatter_count,
          description: "Correlations between outputs are often shown by scatter plots (e.g. age " +
              "versus clearance). "
        },
      ]
    }
  },
  created() {
    this.fetch_data(this.resource_url);
  }
}
</script>

<style>
</style>