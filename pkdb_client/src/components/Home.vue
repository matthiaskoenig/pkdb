<template>
    <div>
        <h1>Pharmacokinetics Database {{ statistics['version'] }}</h1>
        <ul>
            <li>References: {{ statistics['reference_count'] }}</li>
            <li>Studies: {{ statistics['study_count'] }}</li>
            <li>Groups: {{ statistics['group_count'] }}</li>
            <li>Individuals: {{ statistics['individual_count'] }}</li>
            <li>Interventions: {{ statistics['intervention_count'] }}</li>
            <li>Outputs: {{ statistics['output_count'] }}</li>
            <li>Timecourses: {{ statistics['timecourse_count'] }}</li>
        </ul>
    </div>
</template>

<script>
import axios from 'axios'
export default {
    name: 'Home',
    data() {
        return {
            statistics: null,
            errors: []
        }
    },
    mounted() {
        axios.get(`http://localhost:8000/api/v1/statistics/?format=json`)
            .then(response => {
                // JSON responses are automatically parsed.
                this.statistics = response.data
            })
            .catch(e => {
                this.errors.push(e)
            })
    }
}
</script>

<style>
</style>