<template>
    <div class="md-layout">
        <div class="col-5">
            <vue-plotly :data="interventions.data" :layout="interventions.layout" :options="options"/>
        </div>
        <div class="col-2">&nbsp;</div>
        <div class="col-5">
            <vue-plotly :data="individuals.data" :layout="individuals.layout" :options="options"/>
        </div>
    </div>
</template>

<script>
    import axios from 'axios'
    import VuePlotly from '@statnett/vue-plotly'

    // size of individual plots
    var height = 600;
    var width = 600;

    export default {
        name: "Statistics",
        components: {
            VuePlotly,
        },
        methods: {
            get: function () {
                var api_url;
                api_url = this.api + '/statistics_data/?format=json';
                console.log("api_url:" + api_url);
                axios.get(api_url)
                    .then(response => {
                        // JSON responses are automatically parsed.
                        this.data = response.data
                    })
                    .catch(e => {
                        console.log(e)
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

<style scoped>

</style>