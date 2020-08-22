<template>
  <div id="home">
    <v-row>
      <v-col>
        <h2>PK-DB </h2>
        <p></p>
        <count-table/>
      </v-col>
    </v-row>

    <v-row>
      <v-col>
        <about-information/>
      </v-col>
    </v-row>

    <!--
    <v-row>
      <v-col>
      <statistics-vega-plot ></statistics-vega-plot>
      </v-col>
    </v-row>
    -->
  </div>
</template>

<script>
import CountTable from './tables/CountTable'
import AboutInformation from './AboutInformation'
import StatisticsVegaPlot from "./plots/StatisticsVegaPlot";

export default {
  name: 'Home',
  components: {
    StatisticsVegaPlot,
    CountTable,
    AboutInformation,
  }
}
</script>

<style>
</style>