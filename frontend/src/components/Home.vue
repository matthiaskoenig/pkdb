<template>
    <div id="home">
        <v-layout row wrap>
          <v-row>

            <v-col cols="6">
                <count-table />
                <br />
                <statistics-vega-plot ></statistics-vega-plot>
            </v-col>
            <v-col cols="6">
                <about-information />
            </v-col>
          </v-row>

        </v-layout>
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