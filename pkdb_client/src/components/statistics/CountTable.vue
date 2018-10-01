<template>
    <div>
        Version: {{ data.version }}<br />
        <a :href="api+'/statistics/?format=json'" title="JSON" target="_blank"><font-awesome-icon icon="code"/></a>
        <br />
    <md-table class="my-table">
        <md-table-row v-for="(item, name) in items" :key="item.name">
            <md-table-cell>
                <router-link tag="span" :to="item.to">
                    <a href="#"><font-awesome-icon :icon="item.icon" /></a>
                </router-link>
            </md-table-cell>
            <md-table-cell>
                {{ item.count }}
            </md-table-cell>
        </md-table-row>
    </md-table>
    </div>
</template>

<script>
    import axios from 'axios'

    export default {
        name: 'CountTable',
        components: {
        },
        methods: {
            get: function () {
                var api_url = this.api + '/statistics/?format=json';
                console.log("api_url:" + api_url);
                axios.get(api_url)
                    .then(response => {
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
                data: {
                    version: '-',
                    study_count: '-',
                    group_count: '-',
                    individual_count: '-',
                    intervention_count: '-',
                    output_count: '-',
                    timecourse_count: '-',
                    reference_count: '-',
                }
            }
        },
        computed: {
            api() {
                return this.$store.state.endpoints.api;
            },
            items(){
                return [
                    {
                        name: 'Studies',
                        to: '/studies',
                        icon: 'procedures',
                        count: this.data.study_count,
                    },
                    {
                        name: 'Groups',
                        to: '/groups',
                        icon: 'users',
                        count: this.data.group_count,
                    },
                    {
                        name: 'Individuals',
                        to: '/individuals',
                        icon: 'user',
                        count: this.data.individual_count,
                    },
                    {
                        name: 'Interventions',
                        to: '/interventions',
                        icon: 'capsules',
                        count: this.data.intervention_count,
                    },
                    {
                        name: 'Outputs',
                        to: '/outputs',
                        icon: 'chart-bar',
                        count: this.data.output_count,
                    },
                    {
                        name: 'Timecourses',
                        to: '/timecourses',
                        icon: 'chart-line',
                        count: this.data.timecourse_count,
                    },
                    {
                        name: 'References',
                        to: '/references',
                        icon: 'file-alt',
                        count: this.data.reference_count,
                    },
                ]
            }
        },
        created() {
            this.get()
        }
    }
</script>

<style>
</style>