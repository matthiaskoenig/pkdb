<template>
    <div id="about">
        <v-layout row>
            <v-flex xs12 lg6>
                <about-information/>
            </v-flex>
            <v-flex xs12 lg6>
                <statistics/>
            </v-flex>
        </v-layout>

        <v-layout row>
            <!--<search-auto/> -->
            <search-table></search-table>
        </v-layout>
    </div>
</template>

<script>
    import Statistics from './statistics/Statistics'
    import AboutInformation from "./AboutInformation";
    import SearchAuto from "./views/SearchAuto"
    import SearchTable from "./tables/ReferencesTable2"
    export default {
        name: 'About',

        components: {
            AboutInformation,
            Statistics,
            SearchAuto,
            SearchTable
        }
    }
</script>

<style scoped></style>
