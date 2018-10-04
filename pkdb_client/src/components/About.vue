<template>
    <div id="about">
        <v-layout row wrap>
            <v-flex xs6>
                <AboutInformation/>
            </v-flex>
            <v-flex xs6>
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
