<template>
    <div id="statistics">
        <v-card>
            <v-toolbar color="primary" dark>
                <v-toolbar-title>Statistics<br/>
                </v-toolbar-title>
            </v-toolbar>
            <v-container fluid grid-list-lg>
                <v-layout row wrap>
                    <v-flex xs12>
                        <vue-plotly :data="interventions.data" :layout="interventions.layout" :options="options" :autoResize="false"/>
                        <vue-plotly :data="individuals.data" :layout="individuals.layout" :options="options" :autoResize="false"/>
                    </v-flex>
                </v-layout>
            </v-container>
        </v-card>
        </div>
    </div>
</template>

<script>
    import axios from 'axios'
    import VuePlotly from '@statnett/vue-plotly'

    // size of individual plots
    var height = 500;
    var width = 500;

    export default {
        name: "Statistics",
        components: {
            VuePlotly,
        },
        methods: {
            get: function () {
                var api_url;
                api_url = this.api + '/statistics_data/?format=json';
                axios.get(api_url)
                    .then(response => {
                        // JSON responses are automatically parsed.
                        this.data = response.data
                    })
                    .catch(e => {
                        this.errors.push(e)
                    })
            }
        },
        data() {
            return {
                data: {},
            }
        },
        computed: {
            api() {
                    return this.$store.state.endpoints.api;
            },
            interventions() {
                return {
                    layout: {
                        title: 'Interventions',
                        height: height,
                        width: width
                    },
                    data: [{
                        values: this.data.intervention_count,
                        labels: this.data.labels,
                        type: 'pie'
                    }]
                };
            },
            individuals() {
                return {
                    layout: {
                        title: 'Individuals',
                        height: height,
                        width: width
                    },
                    data: [{
                        values: this.data.individual_count,
                        labels: this.data.labels,
                        type: 'pie'
                    }]
                };
            },
            options() {
                return {};
            },
        },
        created() {
            this.get()
        }

    }
</script>

<style>

</style>