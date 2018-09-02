<template>
    <div class="container">
        <div class="row">
            <div class="col-12" >
            <h1>Pharmacokinetics Database {{ version }}</h1>
            </div>
        </div>
        <div class="row">
            <div class="col-3" />
            <div class="col-6">
                <table class="table">
                <tbody>
                <tr>
                    <td><a href="#" to="/studies">


                        <font-awesome-icon icon="procedures" /></a></td><td>Studies</td><td>{{study_count}}</td>
                </tr>
                <tr>
                    <td><font-awesome-icon icon="users" /></td><td>Groups</td><td>{{group_count}}</td>
                </tr>
                <tr>
                    <td><font-awesome-icon icon="user" /></td><td>Individuals</td><td>{{individual_count}}</td>
                </tr>
                <tr>
                    <td><font-awesome-icon icon="capsules" /></td><td>Interventions</td><td>{{intervention_count}}</td>
                </tr>
                <tr>
                    <td><font-awesome-icon icon="chart-bar" /></td><td>Outputs</td><td>{{output_count}}</td>
                </tr>
                <tr>
                    <td><font-awesome-icon icon="chart-line" /></td><td>Timecourses</td><td>{{timecourse_count}}</td>
                </tr>
                <tr>
                    <td><font-awesome-icon icon="file-alt" /></td><td>References</td><td>{{reference_count}}</td>
                </tr>
                </tbody>
                </table>
            </div>
            <div class="col-3">
                <a :href="api+'/statistics/?format=json'" title="JSON" target="_blank"><font-awesome-icon icon="code" /></a>
            </div>
        </div>
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