<template>
    <div>
        <h1>Pharmacokinetics Database {{ version }}</h1>
        <ul>
            <li>References: {{ reference_count }}</li>
            <li>Studies: {{ study_count }}</li>
            <li>Groups: {{ group_count }}</li>
            <li>Individuals: {{ individual_count }}</li>
            <li>Interventions: {{ intervention_count }}</li>
            <li>Outputs: {{ output_count }}</li>
            <li>Timecourses: {{ timecourse_count }}</li>
        </ul>
    </div>
</template>

<script>
import axios from 'axios'
export default {
    name: 'Home',
    props: {
        api: String
    },
    methods:{
        get: function(){
            var api_url
            api_url = this.api + '/statistics/?format=json'


            axios.get(api_url)
                .then(response => {
                    // JSON responses are automatically parsed.
                    this.data = response.data
                })
                .catch(e => {
                    this.errors.push(e)
                })
        }
    },
    data() {
        return {
            data: {
                'version': null,
                'reference_count': null,
                'study_count': null,
                'group_count': null,
                'individual_count': null,
                'intervention_count': null,
                'output_count': null,
                'timecourse_count': null,
            },
            errors: []
        }
    },
    computed: {
        version: function () {
            return this.data['version']
        },
        reference_count: function () {
            return this.data['reference_count']
        },
        study_count: function () {
            return this.data['study_count']
        },
        group_count: function () {
            return this.data['group_count']
        },
        individual_count: function () {
            return this.data['individual_count']
        },
        intervention_count: function () {
            return this.data['intervention_count']
        },
        output_count: function () {
            return this.data['output_count']
        },
        timecourse_count: function () {
            return this.data['timecourse_count']
        },
    },
    created() {
        this.get()
    }
}
</script>

<style>
</style>