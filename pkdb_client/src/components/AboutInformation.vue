<template>
    <div id="about-information">
        <h2>Pharmacokinetics database (PK-DB)</h2>
        <p>
            Version: {{ version }}<br/>
        </p>
        <p>

        </p
        >
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
