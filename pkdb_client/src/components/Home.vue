<template>
    <div class="container">
        <div class="row">
            <div class="col-1" />
            <div class="col-10" >
            <h1>Pharmacokinetics Database {{ version }}</h1>
            </div>
            <div class="col-1" >
                <a :href="api+'/statistics/?format=json'" title="JSON" target="_blank"><font-awesome-icon icon="code"/></a>
            </div>

        </div>
        <div class="row">
            <div class="col-3" />
            <div class="col-6">
                <table class="table">
                <tbody>
                <tr>
                    <td>
                        <router-link tag="span" to="/studies">
                            <a href="#"><font-awesome-icon icon="procedures" /></a>
                        </router-link>
                    </td><td>Studies</td><td>{{study_count}}</td>
                </tr>
                <tr>
                    <td>
                        <router-link tag="span" to="/groups">
                            <a href="#"><font-awesome-icon icon="users" /></a>
                        </router-link>
                    </td><td>Groups</td><td>{{group_count}}</td>
                </tr>
                <tr>
                    <td>
                        <router-link tag="span" to="/individuals">
                            <a href="#"><font-awesome-icon icon="user" /></a>
                        </router-link>
                    </td><td>Individuals</td><td>{{individual_count}}</td>
                </tr>
                <tr>
                    <td>
                        <router-link tag="span" to="/interventions">
                            <a href="#"><font-awesome-icon icon="capsules" /></a>
                        </router-link>
                    </td><td>Interventions</td><td>{{intervention_count}}</td>
                </tr>
                <tr>
                    <td>
                        <router-link tag="span" to="/outputs">
                            <a href="#"><font-awesome-icon icon="chart-bar" /></a>
                        </router-link>
                    </td><td>Outputs</td><td>{{output_count}}</td>
                </tr>
                <tr>
                    <td>
                        <router-link tag="span" to="/timecourses">
                            <a href="#"><font-awesome-icon icon="chart-line" /></a>
                        </router-link>
                    </td><td>Timecourses</td><td>{{timecourse_count}}</td>
                </tr>
                <tr>
                    <td>
                        <router-link tag="span" to="/references">
                            <a href="#"><font-awesome-icon icon="file-alt" /></a>
                        </router-link>
                        </td><td>References</td><td>{{reference_count}}</td>
                </tr>
                </tbody>
                </table>

            </div>

        </div>
        <vue-plotly :data="interventions_data" :layout="layout" :options="options"/>
        <vue-plotly :data="individuals_data" :layout="layout" :options="options"/>

    </div>
</template>

<script>
import axios from 'axios'
import VuePlotly from '@statnett/vue-plotly'

export default {
    name: 'Home',
    props: {
        api: String
    },
    components: {
        VuePlotly,
    },
    methods:{
        get: function(){
            var api_url;
            api_url = this.api + '/statistics/?format=json';
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
            version: '',
            study_count: '',
            group_count: '',
            individual_count: '',
            intervention_count: '',
            output_count: '',
            timecourse_count: '',
            reference_count: '',
            data: {},

        }
    },
    computed: {
        interventions_data(){
            return [{
                values: this.data.intervention_count,
                labels: this.data.labels,
                type: 'pie'
            }];

        },
        individuals_data(){

            return [{
                values: this.data.individual_count,
                labels: this.data.labels,
                type: 'pie'
            }];

        },
        layout(){
            //xaxis: {title: this.timecourse.time_unit },
            var height = 400;
            var width = 500;
            return {height:height,width:width};
        },
        options(){
            return {};
        },


    },
    created() {
        this.get()
    }
}
</script>

<style>
</style>