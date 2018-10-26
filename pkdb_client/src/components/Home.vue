<template>
    <div id="home">
        <v-layout row wrap>
            <v-flex xs6>
                <count-table />
            </v-flex>
            <v-flex xs6>
                <about-information />
            </v-flex>

            <!--
            <v-flex xs12>

                Navigation Test
                <navigation-test :drawer="true"/>
            </v-flex>
            -->
        </v-layout>
    </div>
</template>

<script>
    import CountTable from './statistics/CountTable'
    import AboutInformation from './AboutInformation'
    import NavigationTest from './NavigationTest'

    export default {
        name: 'Home',
        components: {
            CountTable,
            AboutInformation,
            // NavigationTest
        }
    }
</script>

<style>
</style>