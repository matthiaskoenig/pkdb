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
    </div>
</template>

<script>
    import Statistics from '@/components/statistics/Statistics'
    import AboutInformation from "./AboutInformation";

    export default {
        name: 'About',

        components: {
            AboutInformation,
            Statistics
        },
    }
</script>

<style scoped></style>
