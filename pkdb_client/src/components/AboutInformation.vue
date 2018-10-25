<template>
    <v-card id="about-information">
        <v-toolbar color="secondary" dark dense>
            <v-toolbar-title>About</v-toolbar-title>
        </v-toolbar>
        <v-container fluid>
            <v-layout row wrap>
                <v-flex xs12>
                    <p>
                        <heading title="Pharmacokinetics database (PK-DB)"/><br/>
                        <strong>Version</strong>: {{ version }}
                    </p>
                    <p>
                        Data base for the standardized storage of clinical and experimental data sets from
                        pharmacokinetics studies.
                    </p>

                    <p>
                        <v-img src="/assets/images/workflow.png" max-width="600"/>
                    </p>

                    <p>
                        <strong>Overview of data data curation workflow</strong><br/>
                        A) Literature research is performed for substances in liver function tests. Study data for
                        the integration
                        of datasets with computational models is extracted. This includes information about study
                        design, subjects,
                        interventions, and dosing schema. Important lifestyle factors like smoking behavior, alcohol
                        consumption,
                        oral contraceptives, or coffee consumption are recorded. Datasets depicted in the figures
                        and tables are
                        digitized in machine-readable formats and basic metadata is annotated. Pharmacokinetics
                        parameters are
                        extracted from publication text, tables and figures. B) Study information, datasets, and
                        corresponding
                        metadata are made accessible under FAIR principles.
                    </p>

                    <h3>Contact</h3>
                    <span v-for="item in contact_items">

                <v-btn color="primary" fab small dark flat :title="item.name" :to="item.to"><v-icon>{{ item.icon }}</v-icon></v-btn>
                <a :href="item.to" :title="item.title">{{ item.title }}</a>
                </span>
                </v-flex>
            </v-layout>
        </v-container>
    </v-card>
</template>

<script>
    import axios from 'axios'
    import {lookup_icon} from "@/icons"

    export default {
        name: 'AboutInformation',
        data() {
            return {
                version: "-",

                web: 'https://livermetabolism.com',
                statistics: null,
                errors: [],
                contact_items: [
                    {
                        name: 'Email',
                        icon: 'fas fa-envelope',
                        title: 'koenigmx@hu-berlin.de',
                        to: 'mailto:koenigmx@hu-berlin.de'
                    },
                    {
                        name: 'GitHub',
                        icon: 'fab fa-github',
                        title: 'https://github.com/matthiaskoenig/pkdb',
                        to: 'https://github.com/matthiaskoenig/pkdb'
                    }

                ]

            }
        },
        computed: { // vuex store
            api() {
                return this.$store.state.endpoints.api
            }
        },
        methods: {
            icon: function (key) {
                return lookup_icon(key)
            }
        },
        mounted() {
            axios.get(this.api + `/statistics/?format=json`)
                .then(response => {
                    // JSON responses are automatically parsed.
                    this.statistics = response.data;
                    this.version = this.statistics["version"];
                })
                .catch(e => {
                    this.errors.push(e)
                })
        }

    }
</script>

<style scoped>

</style>
