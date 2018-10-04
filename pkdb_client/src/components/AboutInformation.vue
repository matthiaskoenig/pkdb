<template>
    <div id="about-information">
        <h2>Pharmacokinetics database (PK-DB)</h2>
        <p>
            <strong>Version</strong>: {{ version }}<br/>
        </p>
        <p>
        Data base for the standardized storage of clinical and experimental data sets from pharmacokinetics studies.
        </p>
        <p>
        <img src="/assets/images/workflow.png" width="600"/>
        </p>
        <strong>Overview of data data curation workflow</strong>
        A) Literature research is performed for
        substances in liver function tests. Study
        data for the integration of datasets with
        computational models is extracted. This
        includes information about study design,
        subjects, interventions, and dosing
        schema. Important lifestyle factors like
        smoking behavior, alcohol consumption,
        oral contraceptives, or coffee
        consumption are recorded. Datasets
        depicted in the figures and tables are
        digitized in machine-readable formats
        and basic metadata is annotated.
        Pharmacokinetics parameters are
        extracted from publication text, tables
        and figures. B) Study information,
        datasets, and corresponding metadata
        are made accessible under FAIR
        principles.
        </p>


        <h3>Contact</h3>
        <p>
            <ul>
                <li>Website: <a :href="web" target="_blank">{{web}}</a></li>
                <li>Email: <a :href="'mailto:'+email" target="_blank">{{email}}</a></li>
            </ul>
        </p>
    </div>
</template>

<script>
    import axios from 'axios'
    import Statistics from '@/components/statistics/Statistics'

    export default {
        name: 'AboutInformation',
        data() {
            return {
                version: "-",
                email: 'koenigmx@hu-berlin.de',
                web: 'https://livermetabolism.com',
                statistics: null,
                errors: []
            }
        },
        computed: { // vuex store
            api() {return this.$store.state.endpoints.api}
        },
        mounted() {
            axios.get(this.api + `/statistics/?format=json`)
                .then(response => {
                    // JSON responses are automatically parsed.
                    this.statistics = response.data
                    this.version = this.statistics["version"]
                })
                .catch(e => {
                    this.errors.push(e)
                })
        }

    }
</script>

<style scoped></style>
