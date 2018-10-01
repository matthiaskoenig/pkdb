<template>
    <div>
        <vue-plotly :data="interventions_data" :layout="layout" :options="options"/>
        <vue-plotly :data="individuals_data" :layout="layout" :options="options"/>
    </div>
</template>

<script>
    import axios from 'axios'
    import VuePlotly from '@statnett/vue-plotly'

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
            interventions_data() {
                return [{
                    values: this.data.intervention_count,
                    labels: this.data.labels,
                    type: 'pie'
                }];
            },
            individuals_data() {
                return [{
                    values: this.data.individual_count,
                    labels: this.data.labels,
                    type: 'pie'
                }];
            },
            layout() {
                // xaxis: {title: this.timecourse.time_unit },
                var height = 400;
                var width = 500;
                return {height: height, width: width};
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