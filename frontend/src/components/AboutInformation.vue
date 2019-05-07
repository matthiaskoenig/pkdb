<template>
    <v-card id="about-information">
        <v-toolbar color="secondary" dark dense>
            <v-toolbar-title>About PK-DB</v-toolbar-title>
        </v-toolbar>
        <v-container fluid>
            <v-layout row wrap>
                <v-flex xs12>
                    <strong>Version</strong>: {{ version }}<br />
                    <p>
                        <span v-for="item in contact_items">
                            <a :href="item.to" :title="item.title"><v-icon color="black" small>{{ item.icon }}</v-icon></a>&nbsp;<a :href="item.to" :title="item.title">{{ item.title }}</a><br/>
                        </span>
                    </p>
                    <p>
                        <strong>Citation</strong>:&nbsp;<a href="https://doi.org/10.5281/zenodo.1406979"><img src="https://zenodo.org/badge/DOI/10.5281/zenodo.1406979.svg" alt="DOI"></a>
                    </p>

                    <h2>Curation workflow</h2>
                    <p>
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
                    <p>
                        <v-img src="/assets/images/workflow.png" max-width="600"/>
                    </p>


                    <h2>Funding</h2>
                    <p>
                        This project is supported by the Federal Ministry of Education and Research (BMBF, Germany) within the research network Systems Medicine of the Liver (LiSyM, grant number 031L0054).
                        <br /><br/>
                        <a href="https://www.bmbf.de/" target="_blank"><img src="/assets/images/bmbf.png" height="75"></img></a>&nbsp;
                        <a href="http://www.lisym.org" target="_blank"><img src="/assets/images/lisym.png" height="50"></img></a>
                    </p>


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
