<template>
    <div>
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
        props: {
            api: String
        },
        components: {
        },
        methods:{
        },
        data() {
            return {
                version: '',
                study_count: '-',
                group_count: '-',
                individual_count: '-',
                intervention_count: '-',
                output_count: '-',
                timecourse_count: '-',
                reference_count: '-',
            }
        },
        computed: {
            items(){
                return [
                    {
                        name: 'Studies',
                        to: '/studies',
                        icon: 'procedures',
                        count: this.study_count,
                    },
                    {
                        name: 'Groups',
                        to: '/groups',
                        icon: 'users',
                        count: this.group_count,
                    },
                    {
                        name: 'Individuals',
                        to: '/individuals',
                        icon: 'user',
                        count: this.individual_count,
                    },
                    {
                        name: 'Interventions',
                        to: '/interventions',
                        icon: 'capsules',
                        count: this.intervention_count,
                    },
                    {
                        name: 'Outputs',
                        to: '/outputs',
                        icon: 'chart-bar',
                        count: this.output_count,
                    },
                    {
                        name: 'Timecourses',
                        to: '/timecourses',
                        icon: 'chart-line',
                        count: this.timecourse_count,
                    },
                    {
                        name: 'References',
                        to: '/references',
                        icon: 'file-alt',
                        count: this.reference_count,
                    },
                ]
            }
        }
    }
</script>

<style>
</style>