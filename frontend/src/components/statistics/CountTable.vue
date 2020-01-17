<template>
    <v-card id="count-table">
        <v-toolbar color="secondary" dark dense>
            <v-toolbar-title>Pharmacokinetics Database (PK-DB)</v-toolbar-title>
        </v-toolbar>

        <v-data-table :headers="headers" :items="items" hide-default-footer class="elevation-1">
            <template slot="items" slot-scope="table">
                <td xs3>
                    <strong>{{table.item.name}}</strong><br />
                    <link-button :to="table.item.to" :title="table.item.name" :icon="table.item.icon"/>
                </td>
                <td class="text-xs-left" xs7>{{ table.item.description }}</td>
                <td class="text-xs-left" xs3>
                    <count-chip :count="table.item.count" :icon="table.item.icon_name"></count-chip>
                </td>
            </template>
        </v-data-table>
    </v-card>
</template>

<script>
    import axios from 'axios'
    import {lookup_icon} from "@/icons"
    import CountChip from "../detail/CountChip";

    export default {
        name: 'CountTable',
        components: {
            CountChip
        },
        data() {
            return {
                headers: [
                    { text: 'Data', value: 'name', sortable: false},
                    { text: 'Description', value: 'description', sortable: false},
                    { text: 'Count', value: 'count', sortable: false},
                ],
                data: {
                    study_count: 0,
                    group_count: 0,
                    individual_count: 0,
                    intervention_count: 0,
                    output_count: 0,
                    timecourse_count: 0,
                    reference_count: 0,
                },
            }
        },
        computed: {
            resource_url() {
                return this.api + 'statistics/?format=json'
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
                        icon_name: 'studies',
                        count: this.data.study_count,
                        description: "Clinical or experimental study measuring data in either single or multiple groups and/or single or multiple individuals."
                    },
                    {
                        name: 'Groups',
                        to: '/groups',
                        icon: this.icon('groups'),
                        icon_name: 'groups',
                        count: this.data.group_count,
                        description: "Group of individuals defined by certain characteristica, e.g., smoking status or medication."
                    },
                    {
                        name: 'Individuals',
                        to: '/individuals',
                        icon: this.icon('individuals'),
                        icon_name: 'individuals',
                        count: this.data.individual_count,
                        description: "A single subject, characterized by the group it belongs to and personal characteristica like age, body weight or sex."
                    },
                    {
                        name: 'Interventions',
                        to: '/interventions',
                        icon: this.icon('interventions'),
                        icon_name: 'interventions',
                        count: this.data.intervention_count,
                        description: "Intervention which was performed in the study. Often this is the application of substances, e.g. caffeine or codeine, or changes in " +
                            "lifestyle like smoking cessation."
                    },
                    {
                        name: 'Outputs',
                        to: '/outputs',
                        icon: this.icon('outputs'),
                        icon_name: 'outputs',
                        count: this.data.output_count,
                        description: "Clinical or experimental output. These can be single parameters or variables, e.g. pharmacokinetic parameters like AUC, clearance or half-life of the applied substances."
                    },
                    {
                        name: 'Timecourses',
                        to: '/timecourses',
                        icon: this.icon('timecourses'),
                        icon_name: 'timecourses',
                        count: this.data.timecourse_count,
                        description: "Clinical or experimental time course measurements."
                    },
                    {
                        name: 'References',
                        to: '/references',
                        icon: this.icon('references'),
                        icon_name: 'references',
                        count: this.data.reference_count,
                        description: "Literature references from which the data was digitized and curated."
                    },
                ]
            }
        },
        methods: {
            icon: function (key) {
                return lookup_icon(key)
            },
            fetch_data(url){
                axios.get(url)
                    .then(response => {
                        this.data = response.data;
                    })
                    .catch((error)=>{
                        this.data = null;
                        console.error(this.resource_url);
                        console.error(error);
                        this.errors = error.response.data;
                    })
            }
        },
        created() {
                this.fetch_data(this.resource_url);
        }
    }
</script>

<style>
</style>