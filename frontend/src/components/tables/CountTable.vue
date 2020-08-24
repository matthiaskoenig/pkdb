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
import {lookupIcon} from "@/icons"

export default {
  name: 'CountTable',
  components: {},
  props: {
    version: {
      type: String,
      required: true,
    },
    study_count: {
      type: Number,
      required: true,
    },
    group_count: {
      type: Number,
      required: true,
    },
    individual_count: {
      type: Number,
      required: true,
    },
    intervention_count: {
      type: Number,
      required: true,
    },
    output_count: {
      type: Number,
      required: true
    },
    timecourse_count: {
      type: Number,
      required: true
    }
  },
  data() {
    return {
      headers: [
        {text: 'Count', value: 'count', sortable: false},
        {text: 'Data', value: 'name', sortable: false},
        {text: 'Description', value: 'description', sortable: false},
      ],
    }
  },
  methods: {
    faIcon: function (key) {
      return lookupIcon(key)
    },
  },
  computed: {

    items() {
      return [
        {
          name: 'Study',
          name_plural: 'Studies',
          to: '/data',
          icon: this.faIcon('studies'),
          count: this.study_count,
          description: "Clinical or experimental study measuring data in groups and/or individuals."
        },
        {
          name: 'Group',
          to: '/data',
          icon: this.faIcon('groups'),
          count: this.group_count,
          description: "Group of individuals for which data was measured, e.g., the control group and the group which received " +
              "an intervention. A group is described by certain characteristica, e.g., bodyweight, health status, smoking status or medication."
        },
        {
          name: 'Individual',
          to: '/data',
          icon: this.faIcon('individuals'),
          count: this.individual_count,
          description: "A single subject in the study. A subject is characterized by the group it belongs to " +
              "as well as individual characteristica like age, body weight or sex. Individuals are only created if outputs or timecourses have " +
              "been reported on the subject level (not group level)."
        },
        {
          name: 'Intervention',
          to: '/data',
          icon: this.faIcon('interventions'),
          count: this.intervention_count,
          description: "Intervention which was performed in the study. Often interventions consist of application of a " +
              "substance, e.g. caffeine or codeine. Other examples are changes in lifestyle like smoking cessation."
        },
        {
          name: 'Output',
          to: '/data',
          icon: this.faIcon('outputs'),
          count: this.output_count,
          description: "Clinical or experimental output. These can be single parameters or variables, e.g. pharmacokinetic " +
              "parameters like AUC, clearance or half-life of the applied substances. An output is always linked to the " +
              "respective intervention and group or individual."
        },
        {
          name: 'Timecourse',
          to: '/data',
          icon: this.faIcon('timecourses'),
          count: this.timecourse_count,
          description: "Clinical or experimental time course measurements. Often timecourses are concentration measurements." +
              "A timecourse is always linked to the respective intervention and group or individual."
        },
        /*
            {
                name: 'Reference',
                to: '/references',
                icon: this.faIcon('references'),
                count: this.reference_count,
                description: "Literature references from which the data was digitized and curated."
            },
             */
      ]
    }
  },
}
</script>

<style>
</style>