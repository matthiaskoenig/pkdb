<template>
    <div>
    <md-tabs md-sync-route>

        <!-- TODO: figure out font-awesome and material icons -->
        <md-tab id="tab-home" md-label="PK-DB" md-icon="home" to="/"></md-tab>
        <!-- icon: procedures -->
        <md-tab id="tab-studies" md-label="Studies" to="/studies"></md-tab>

        <!-- icon: users -->
        <md-tab id="tab-groups" md-label="Groups" to="/groups"></md-tab>
        <!-- icon: user -->
        <md-tab id="tab-individuals" md-label="Individuals" to="/individuals"></md-tab>
        <!-- icon: capsules -->
        <md-tab id="tab-interventions" md-label="Interventions" to="/interventions"></md-tab>
        <!-- icon: chart-bar -->
        <md-tab id="tab-outputs" md-label="Outputs" to="/outputs"></md-tab>
        <!-- icon: chart-line -->
        <md-tab id="tab-timecourses" md-label="Timecourses" to="/timecourses"></md-tab>
        <!-- icon: file-alt -->
        <md-tab id="tab-references" md-label="References" to="/references"></md-tab>
    </md-tabs>
    <md-tabs md-sync-route md-alignment="right">
        <!-- TODO: right aligned -->
        <!-- icon: info-circle -->
        <md-tab id="tab-about" md-label="About" to="/about"></md-tab>
        <!-- icon: chart-line -->
        <md-tab id="tab-api" md-label="API" to="http://www.pk-db.com/api/v1/"></md-tab>
        <!-- icon: file-alt -->
        <md-tab id="tab-github" md-label="Code" to="http://www.github.com/matthiaskoenig/pkdb"></md-tab>
    </md-tabs>
    </div>
</template>

<script>
    export default {
        name: 'Navigation',
        data() {
            return {}
        }
    }
</script>

<style>

</style>