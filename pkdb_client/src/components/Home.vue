<template>
    <div id="home">

        <div>
            <h4> with a green background </h4>
            <span class=".primary">Test Primary</span> <span class="warning">Test Warning</span>
        </div>

        <v-layout row wrap>
            <v-flex xs6>
                <CountTable />
            </v-flex>
            <v-flex xs6>
                <AboutInformation />
            </v-flex>
        </v-layout>
    </div>
</template>

<script>
    import CountTable from '@/components/statistics/CountTable'
    import AboutInformation from '@/components/AboutInformation'

    export default {
        name: 'Home',
        components: {
            CountTable,
            AboutInformation
        }
    }
</script>

<style>
</style>