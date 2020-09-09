<template>
  <v-main id="home" class="pl-1 pr-1">
    <v-container fluid>
      <v-row align="start"
             justify="center">
        <v-col xs="11" sm="11" md="10" lg="8">

            <h1>PK-DB - pharmacokinetics database</h1>

            <p align="justify">
              An open issue in the field of pharmacokinetics is the reproducible and reusable storage of data from
              experimental and clinical studies, which is especially important for computational modeling. We present PK-DB
              an open database for pharmacokinetics information from clinical trials as well as pre-clinical research.
              The focus of PK-DB is to provide high-quality
              pharmacokinetics data enriched with the required meta-information for computational modeling and data integration.
            </p>

            <h2>Data</h2>

            <p align="justify">

              Any pharmacokinetics study contains subjects under investigation. These subjects are characterised by properties
              like their sex, age, body weight, health status, and further accessible pharmacokinetics influencing characteristica.
              In PK-DB this data is saved as groups and individuals.
              Next, some kind of interventions are performed on the subjects, which is mostly a dosing of a substance to the body
              of the subject.

              Finally, pharmacokinetics measurements are performed on the subject.
              These are often some kind of concentration profiles in some tissue of the subject.
              Additionally, derived pharmacokinetics parameters e.g. AUC, clearance, or half-lives are commonly reported.
              Correlations between theses outputs are often shown in form of scatter plots.
            </p>

            <v-btn color="black"
                   text
                   width="100%"
                   to="/data"
                   title="Browse PK-DB data"
            >
              <v-icon left color="#1E90FF">{{ faIcon('data') }}</v-icon>
              data
            </v-btn>

            <p>
              <count-table/>
            </p>

            <curation-example />

            <!--
            <h2>Features</h2>
            <p>
            <ul>
              <li>Experimental errors and variation</li>
              <li>Normalisation of units</li>
              <li>Automatic calculation of PKs from timecourses</li>
              <li>Annotations to biological Ontologies</li>
              <li>REST API</li>
              <li>Simple curation workflow</li>
              <li>Strong validation rules during curation</li>
            </ul>
            </p>
            -->

            <about />

        </v-col>
      </v-row>
    </v-container>
  </v-main>
</template>

<script>
import CurationExample from "./CurationExample";
import CountTable from "./tables/CountTable";
import About from './About';
import {IconsMixin} from "@/icons";

export default {
  name: "Home",
  components: {
    // StatisticsVegaPlot,
    CountTable,
    CurationExample,
    About
  },
  mixins: [IconsMixin],
}
</script>

<style>
</style>