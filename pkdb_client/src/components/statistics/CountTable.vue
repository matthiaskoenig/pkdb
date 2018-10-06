<template>
    <v-card id="count-table">
        <v-toolbar color="secondary" dark dense>
            <v-toolbar-title>Pharmacokinetics Database (PK-DB)</v-toolbar-title>
        </v-toolbar>
        <v-data-table :headers="headers" :items="items" hide-actions class="elevation-1">
            <template slot="items" slot-scope="table">

                <td xs2>
                    <LinkButton :to="table.item.to" :title="table.item.name" :icon="table.item.icon"/>
                </td>
                <td class="text-xs-right" xs4>
                    <Heading :title="table.item.name" :count="parseInt(table.item.count)"/>
                </td>
                <td class="text-xs-left" xs6>{{ table.item.description }}</td>
            </template>
        </v-data-table>
    </v-card>
</template>

<script>
    import axios from 'axios'
    import {lookup_icon} from "@/icons"

    export default {
        name: 'CountTable',
        data() {
            return {
                headers: [
                    { text: 'Data', value: 'name', sortable: false},
                    { text: 'Count', value: 'count', sortable: false},
                    { text: 'Description', value: 'description', sortable: false},
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
                        console.log(this.data)
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