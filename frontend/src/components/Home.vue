<template>
    <div id="home">
        <v-layout row wrap>
            <v-flex xs6>
                <count-table />
            </v-flex>
            <v-flex xs6>
                <about-information />
            </v-flex>
        </v-layout>
    </div>
</template>

<script>
    import CountTable from './statistics/CountTable'
    import AboutInformation from './AboutInformation'

    export default {
        name: 'Home',
        components: {
            CountTable,
            AboutInformation,
        }
    }
</script>

<style>
</style>