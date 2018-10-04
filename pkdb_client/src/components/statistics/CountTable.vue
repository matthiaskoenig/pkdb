<template>
    <div id="count-table">

        <v-data-table :headers="headers" :items="items" hide-actions class="elevation-1">
            <template slot="items" slot-scope="props">
                <td>
                    <v-icon>{{ props.item.icon }}</v-icon>
                </td>
                <td class="text-xs-right">
                    <Heading :title="props.item.name" :count="parseInt(props.item.count)"/>
                </td>
                <td class="text-xs-left">{{ props.item.description }}</td>
            </template>
        </v-data-table>
    </div>
</template>

<script>
    import axios from 'axios'
    import {lookup_icon} from "@/icons"

    export default {
        name: 'CountTable',
        data() {
            return {
                headers: [
                    { text: 'Data', value: 'name'},
                    { text: 'Count', value: 'count' },
                    { text: 'Description', value: 'description' },
                ],
                data: {
                    study_count: '-',
                    group_count: '-',
                    individual_count: '-',
                    intervention_count: '-',
                    output_count: '-',
                    timecourse_count: '-',
                    reference_count: '-',
                },
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
                        description: "Clinical or experimental study measuring data in either single or multiple groups and/or single or multiple individuals."
                    },
                    {
                        name: 'Groups',
                        to: '/groups',
                        icon: this.icon('groups'),
                        count: this.data.group_count,
                        description: "Group of individuals defined by certain characteristica, e.g., smoking status or medication."
                    },
                    {
                        name: 'Individuals',
                        to: '/individuals',
                        icon: this.icon('individuals'),
                        count: this.data.individual_count,
                        description: "A single subject, characterized by the group it belongs to and personal characteristica like age, body weight or sex."
                    },
                    {
                        name: 'Interventions',
                        to: '/interventions',
                        icon: this.icon('interventions'),
                        count: this.data.intervention_count,
                        description: "Intervention which was performed in the study. Often this is the application of substances, e.g. caffeine or codeine, or changes in " +
                            "lifestyle like smoking cessation."
                    },
                    {
                        name: 'Outputs',
                        to: '/outputs',
                        icon: this.icon('outputs'),
                        count: this.data.output_count,
                        description: "Clinical or experimental output. These can be single parameters or variables, e.g. pharmacokinetic parameters like AUC, clearance or half-life of the applied substances."
                    },
                    {
                        name: 'Timecourses',
                        to: '/timecourses',
                        icon: this.icon('timecourses'),
                        count: this.data.timecourse_count,
                        description: "Clinical or experimental time course measurements."
                    },
                    {
                        name: 'References',
                        to: '/references',
                        icon: this.icon('references'),
                        count: this.data.reference_count,
                        description: "Literature references."
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