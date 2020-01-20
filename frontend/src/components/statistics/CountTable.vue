<template>
    <v-card id="count-table">
        <v-data-table :headers="headers"
                      :items="items"
                      hide-default-footer
                      hide-default-header
                      class="elevation-1"
        >
            <template v-slot:item.name="{ item }">
                <strong>{{ item.name }}s</strong>
            </template>
            <template v-slot:item.count="{ item }">
                <count-chip :count="item.count"
                            :icon="item.icon"
                            :name="item.name"
                            :to="item.to"
                />
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
                    { text: 'Count', value: 'count', sortable: false},
                    { text: 'Data', value: 'name', sortable: false},
                    { text: 'Description', value: 'description', sortable: false},
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
                        name: 'Study',
                        to: '/studies',
                        icon: this.icon('studies'),
                        count: this.data.study_count,
                        description: "Clinical or experimental study measuring data in either single or multiple groups and/or single or multiple individuals."
                    },
                    {
                        name: 'Group',
                        to: '/groups',
                        icon: this.icon('groups'),
                        count: this.data.group_count,
                        description: "Group of individuals defined by certain characteristica, e.g., smoking status or medication."
                    },
                    {
                        name: 'Individual',
                        to: '/individuals',
                        icon: this.icon('individuals'),
                        count: this.data.individual_count,
                        description: "A single subject, characterized by the group it belongs to and personal characteristica like age, body weight or sex."
                    },
                    {
                        name: 'Intervention',
                        to: '/interventions',
                        icon: this.icon('interventions'),
                        count: this.data.intervention_count,
                        description: "Intervention which was performed in the study. Often this is the application of substances, e.g. caffeine or codeine, or changes in " +
                            "lifestyle like smoking cessation."
                    },
                    {
                        name: 'Output',
                        to: '/outputs',
                        icon: this.icon('outputs'),
                        count: this.data.output_count,
                        description: "Clinical or experimental output. These can be single parameters or variables, e.g. pharmacokinetic parameters like AUC, clearance or half-life of the applied substances."
                    },
                    {
                        name: 'Timecourse',
                        to: '/timecourses',
                        icon: this.icon('timecourses'),
                        count: this.data.timecourse_count,
                        description: "Clinical or experimental time course measurements."
                    },
                    {
                        name: 'Reference',
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