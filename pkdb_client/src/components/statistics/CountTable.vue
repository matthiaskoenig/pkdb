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
    import {lookup_icon} from "@/icons"

    export default {
        name: 'CountTable',
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
                        icon: this.icon('studies'),
                        count: this.data.study_count,
                    },
                    {
                        name: 'Groups',
                        to: '/groups',
                        icon: this.icon('groups'),
                        count: this.data.group_count,
                    },
                    {
                        name: 'Individuals',
                        to: '/individuals',
                        icon: this.icon('individuals'),
                        count: this.data.individual_count,
                    },
                    {
                        name: 'Interventions',
                        to: '/interventions',
                        icon: this.icon('interventions'),
                        count: this.data.intervention_count,
                    },
                    {
                        name: 'Outputs',
                        to: '/outputs',
                        icon: this.icon('outputs'),
                        count: this.data.output_count,
                    },
                    {
                        name: 'Timecourses',
                        to: '/timecourses',
                        icon: this.icon('timecourses'),
                        count: this.data.timecourse_count,
                    },
                    {
                        name: 'References',
                        to: '/references',
                        icon: this.icon('references'),
                        count: this.data.reference_count,
                    },
                ]
            }
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
            },
            icon: function (key) {
                return lookup_icon(key)
            }
        },
        created() {
            this.get()
        }
    }
</script>

<style>
</style>