<template>
    <div id="home">
        <v-layout row wrap>
            <v-flex xs6>
                <count-table />
                <br />
                <statistics-vega-plot></statistics-vega-plot>
            </v-flex>
            <v-flex xs6>
                <about-information />
            </v-flex>
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