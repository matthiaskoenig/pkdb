<template>
    <div>
        <md-tabs class="md-layout">
                <md-tab id="tab-home" md-label="Home" :md-icon="home" to="/"> </md-tab>
                <md-tab id="tab-studies" md-label="Studies" :md-icon="procedures" to="/studies"></md-tab>
                <md-tab id="tab-groups" md-label="Groups" :md-icon="users" to="/groups"></md-tab>
                <md-tab id="tab-individuals" md-label="Individuals" :md-icon="user" to="/individuals"></md-tab>
                <md-tab id="tab-interventions" md-label="Interventions" :md-icon="capsules" to="/interventions"></md-tab>
                <md-tab id="tab-outputs" md-label="Outputs" :md-icon="chart_bar" to="/outputs"></md-tab>
                <md-tab id="tab-timecourses" md-label="Timecourses" :md-icon="chart_line" to="/timecourses"></md-tab>
                <md-tab id="tab-references" md-label="References"  :md-icon="file_alt" to="/references"></md-tab>

                <!-- TODO: right aligned -->
                <md-tab to="/about" md-active-tab="false"  id="tab-about" :md-icon="info_circle" md-label="About"></md-tab>
                <md-tab id="tab-api" md-label="API" :md-icon="code" :href="api+'/api/v1/'"></md-tab>
                <md-tab id="tab-github" md-label="Code" :md-icon="github" href="https://www.github.com/matthiaskoenig/pkdb"></md-tab>

                <md-tab id="tab-admin" md-label="Admin" :md-icon="cogs" :href="domain+'/admin/'"></md-tab>
                <md-tab id="tab-accounts" md-label="Account" :md-icon="user_circle" to="/account"></md-tab>
        </md-tabs>

    </div>

</template>

<script>
    export default {
        name: 'Navigation',
        props: {
            api: String,
            domain: String
        },
        data(){
            return {}
        },
        computed: {
            home () {
                return require('../assets/images/fontawesome/svgs/solid/home.svg')
            },
            user () {
                return require('../assets/images/fontawesome/svgs/solid/user.svg')
            },
            user_circle () {
                return require('../assets/images/fontawesome/svgs/solid/user-circle.svg')
            },
            users () {
                return require('../assets/images/fontawesome/svgs/solid/users.svg')
            },
            capsules () {
                return require('../assets/images/fontawesome/svgs/solid/capsules.svg')
            },
            code () {
                return require('../assets/images/fontawesome/svgs/solid/code.svg')
            },
            cogs () {
                return require('../assets/images/fontawesome/svgs/solid/cogs.svg')
            },

            procedures () {
                return require('../assets/images/fontawesome/svgs/solid/procedures.svg')
            },
            chart_bar () {
                return require('../assets/images/fontawesome/svgs/solid/chart-bar.svg')
            },
            chart_line () {
                return require('../assets/images/fontawesome/svgs/solid/chart-line.svg')
            },
            github () {
                return require('../assets/images/fontawesome/svgs/brands/github.svg')
            },
            file_alt () {
                return require('../assets/images/fontawesome/svgs/solid/file-alt.svg')
            },
            info_circle () {
                return require('../assets/images/fontawesome/svgs/solid/info-circle.svg')
            }
        }
    }
</script>

<style>


</style>