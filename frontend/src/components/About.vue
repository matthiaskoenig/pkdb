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
    </div>
</template>

<script>
    import Statistics from './statistics/Statistics'
    import AboutInformation from "./AboutInformation";
    export default {
        name: 'About',

        components: {
            AboutInformation,
            Statistics,
        }
    }
</script>

<style scoped></style>
