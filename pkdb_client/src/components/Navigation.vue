<template>
    <div>
        <md-tabs class="md-layout">
                <md-tab id="tab-home" md-label="Home" :md-icon="home" to="/"> </md-tab>
                <!-- icon: procedures -->
                <md-tab id="tab-studies" md-label="Studies" :md-icon="procedures" to="/studies"></md-tab>

                <!-- icon: users -->
                <md-tab id="tab-groups" md-label="Groups" :md-icon="users" to="/groups"></md-tab>
                <!-- icon: user -->
                <md-tab id="tab-individuals" md-label="Individuals" :md-icon="user" to="/individuals"></md-tab>
                <!-- icon: capsules -->
                <md-tab id="tab-interventions" md-label="Interventions" :md-icon="capsule" to="/interventions"></md-tab>
                <!-- icon: chart-bar -->
                <md-tab id="tab-outputs" md-label="Outputs" :md-icon="outputs" to="/outputs"></md-tab>
                <!-- icon: chart-line -->
                <md-tab id="tab-timecourses" md-label="Timecourses" :md-icon="chart_line" to="/timecourses"></md-tab>
                <!-- icon: file-alt -->
                <md-tab id="tab-references" md-label="References"  :md-icon="file_alt" to="/references"></md-tab>


                <!-- TODO: right aligned -->
                <!-- icon: info-circle -->
                <md-tab to="/about" md-active-tab="false"  id="tab-about" :md-icon="file_alt" md-label="About"></md-tab>
                <!-- icon: chart-line -->
                <md-tab id="tab-api" md-label="API" :md-icon="chart_line" href="http://www.pk-db.com/api/v1/"></md-tab>
                <!-- icon: file-alt -->
                <md-tab id="tab-github" md-label="Code" :md-icon="code" href="http://www.github.com/matthiaskoenig/pkdb"></md-tab>
        </md-tabs>

    </div>

</template>

<script>
    export default {
        name: 'Navigation',
        data() {
            return {}
        },
        computed: {
            home () {
                return require('../assets/fontawesome-free-5.3.1-web/svgs/solid/home.svg')

            },
            users () {
                return require('../assets/fontawesome-free-5.3.1-web/svgs/solid/users.svg')

            },
            capsule () {
                return require('../assets/fontawesome-free-5.3.1-web/svgs/solid/capsules.svg')

            },
            user () {
                return require('../assets/fontawesome-free-5.3.1-web/svgs/solid/user.svg')

            },

            procedures () {
                return require('../assets/fontawesome-free-5.3.1-web/svgs/solid/procedures.svg')

            },
            outputs () {
                return require('../assets/fontawesome-free-5.3.1-web/svgs/solid/chart-bar.svg')

            },
            code () {
                return require('../assets/fontawesome-free-5.3.1-web/svgs/solid/file-alt.svg')

            },
            chart_line () {
                return require('../assets/fontawesome-free-5.3.1-web/svgs/solid/chart-line.svg')

            },
            file_alt () {
                return require('../assets/fontawesome-free-5.3.1-web/svgs/solid/info-circle.svg')

            }
        }
    }
</script>

<style>


</style>