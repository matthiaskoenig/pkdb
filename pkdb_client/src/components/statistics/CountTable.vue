<template>
    <div>
        <TableHeading title="Overview" :resource_url="resource_url"/>

        <md-table class="my-table">
            <md-table-row v-for="item in items" :key="item.name">
                <md-table-cell>
                    <router-link tag="span" :to="item.to">
                        <a href="#">
                            <font-awesome-icon :icon="item.icon"/>
                        </a>&nbsp;&nbsp;
                    </router-link>
                    <router-link tag="span" :to="item.to">
                        <a href="#">{{ item.name }}</a>
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
    import JsonButton from "../lib/JsonButton";

    export default {
        name: 'CountTable',
        components: {
            JsonButton
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
                        console.log(e);
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
            resource_url() {
                return this.api + '/statistics/?format=json'
            },
            api() {
                return this.$store.state.endpoints.api;
            },
            items() {
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