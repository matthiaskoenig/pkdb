<template>
    <v-card id="about-information">
        <v-container fluid>
            <v-layout row wrap>
                <v-flex xs12>
                    <h2>PK-DB Team</h2>
                    <p>
                        PK-DB is developed from the <a href="https://livermetabolism.com">Systems Medicine of the Liver Group</a> of Matthias König at the Humboldt-University Berlin.
                    </p>
                    <p>
                        <user-avatar username="mkoenig"/>
                        <user-avatar username="janekg"/>
                        <user-avatar username="kgreen"/>
                        <user-avatar username="dimitra"/>
                        <user-avatar username="jbrandhorst"/>
                        <user-avatar username="deepa"/>
                        <user-avatar username="yduport"/>
                        <user-avatar username="FlorBar"/>
                        <user-avatar username="adriankl"/>
                    </p>
                    <p>
                    <strong>Version</strong>: {{ version }}
                    </p>

                    <h2>Licensing</h2>
                    <p>
                        All data is governed by the PK-DB's <a href="https://github.com/matthiaskoenig/pkdb/blob/develop/TERMS_OF_USE.md">Terms of use</a>
                    </p>

                    <h2>How to cite</h2>
                    <p>
                        <i>PK-DB: PharmacoKinetics DataBase for Individualized and Stratified Computational Modeling</i><br />
                        Jan Grzegorzewski, Janosch Brandhorst, Dimitra Eleftheriadou, Kathleen Green, Matthias König<br />
                        bioRxiv 760884; doi: <a href="https://doi.org/10.1101/760884">https://doi.org/10.1101/760884</a>
                    </p>
                    <p>
                    If you use PK-DB code cite also
                        <a href="https://doi.org/10.5281/zenodo.1406979"><img src="https://zenodo.org/badge/DOI/10.5281/zenodo.1406979.svg"/></a>
                    </p>
                    <h2>Report an issue</h2>
                    <p>
                        <a href="https://github.com/matthiaskoenig/pkdb/issues/new" title="Report an issue" target="_blank">
                            <v-icon color="black" small>fas fa-fire</v-icon></a> <a href="https://github.com/matthiaskoenig/pkdb/issues/new" title="Report an issue" target="_blank">https://github.com/matthiaskoenig/pkdb/issues/new</a>
                    </p>

                    <h2>Contact</h2>
                    <p>
                        <span v-for="item in contact_items" :key="item.name">
                            <a :href="item.to" :title="item.title"><v-icon color="black" small>{{ item.icon }}</v-icon></a>&nbsp;<a :href="item.to" :title="item.title">{{ item.title }}</a><br/>
                        </span>
                    </p>

                    <h2>Funding</h2>
                    <p>
                        This project is supported by the Federal Ministry of Education and Research (BMBF, Germany) within the research network Systems Medicine of the Liver (LiSyM, grant number 031L0054).
                        <br /><br/>
                        <a href="https://www.bmbf.de/" target="_blank"><img src="/assets/images/bmbf.png" height="50" /></a>&nbsp;
                        <a href="http://www.lisym.org" target="_blank"><img src="/assets/images/lisym.png" height="50" /></a>
                    </p>
                </v-flex>
            </v-layout>
        </v-container>
    </v-card>
</template>

<script>
    import axios from 'axios'

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
        },
        mounted() {
            axios.get(this.api + `statistics/?format=json`)
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
