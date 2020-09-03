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

    <p align="justify">
      An open issue in the field of pharmacokinetics is the reproducible and reusable storage of data from
      experimental and clinical studies, which is especially important for computational modeling. We present PK-DB
      an open database for pharmacokinetics information from clinical trials as well as pre-clinical research.
      The focus of PK-DB is to provide high-quality
      pharmacokinetics data enriched with the required meta-information for computational modeling and data integration.
    </p>

    <h2>Data</h2>



    <p align="justify">

      Any pharmacokinetics study consist of subjects under investigation. These subjects are characterised by properties
      like their sex, age, body weight, health status, and further accessible pharmacokinetics influencing characteristica.
      In PK-DB this data is saved as groups and individuals.
      Next, some kind of interventions are performed on the subjects, which is mostly a dosing of a substance to the body
      of the subject.

      Finally, pharmacokinetics measurements are performed on the subject.
      These are often some kind of concentration profiles in some tissue of the subject.
      Additionally, derived pharmacokinetics parameters e.g. AUC, clearance, or half-lives are commonly reported.
      Correlations between theses outputs are often shown in form of scatter plots.

    </p>
    <count-table v-bind="data"/>

    <v-img src="/assets/images/pkexample2.png" width="100%" class="mb-2">

      <v-sheet  color="rgb(255,255,255, 0.9)"  rounded class="text-on-image text-caption text-right pl-2 pr-2" >
        <strong> Curation Example</strong>
        <v-spacer/>
        RV Patwardhan, P V Desmond, R F Johnson, S Schenker
        <v-spacer/>
        <span class="font-italic text">
          The Journal of Laboratory and clinical medicine, 1980-05-30
        </span>


      </v-sheet>
    </v-img>


    <div>

    </div>

    <h2>Features</h2>
    <v-chip class="ma-1">  Experimental Errors and Variation
    </v-chip>
    <v-chip class="ma-1">  Normalisation of Units
    </v-chip>
    <v-chip class="ma-1">  Automatic Calculation of PKs from Timecourses
  </v-chip>
    <v-chip class="ma-1">  Annotations to Biological Ontologies
  </v-chip>
    <v-chip class="ma-1">  REST API
    </v-chip>
    <v-chip class="ma-1">  Simple Curation Workflow
    </v-chip>
    <v-chip class="ma-1">  Strong Validation Rules During Curation
    </v-chip>



    <!--<statistics-vega-plot />-->
    <!--
    <v-row>
      <v-col>
        <v-btn
          width="100%"
          to="/results"
          >
          <v-icon color="#1E90FF" left>{{ faIcon('data') }}</v-icon>
          Data
        </v-btn>
      </v-col>
    </v-row>
    -->

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
                scatter_count: 0,
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
        .text-on-image {
          margin-right: 0;
          float: right;
          position:absolute;
          bottom: 0;
          right: 0;
        }

        </style>