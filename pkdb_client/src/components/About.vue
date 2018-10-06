<template>
    <div id="about">
        <v-layout row>
            <v-flex xs12 lg6>
                <AboutInformation/>
            </v-flex>
            <v-flex xs12 lg6>
                <Statistics/>
            </v-flex>
        </v-layout>

        <v-layout row>
            <SearchAuto/>
        </v-layout>

    </div>
</template>

<script>
    import Statistics from '@/components/statistics/Statistics'
    import AboutInformation from "./AboutInformation";
    import SearchAuto from "@/views/SearchAuto"
    export default {
        name: 'About',

        components: {
            AboutInformation,
            Statistics,
            SearchAuto
        }
    }
</script>

<style scoped></style>
